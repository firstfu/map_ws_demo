// Uber 車輛模擬主類別：管理地圖、WebSocket 連線和車輛顯示
class UberSimulation {
    constructor() {
        // 初始化類別屬性
        this.map = null;                    // Leaflet 地圖實例
        this.websocket = null;              // WebSocket 連線
        this.vehicles = new Map();          // 車輛資料儲存 (ID -> 車輛資料)
        this.markers = new Map();           // 地圖標記儲存 (ID -> 標記)
        this.userLocationMarker = null;     // 使用者位置標記
        this.userLocation = null;           // 使用者位置座標
        this.isSimulationRunning = true;    // 模擬執行狀態
        this.reconnectAttempts = 0;         // 重連嘗試次數
        this.maxReconnectAttempts = 5;      // 最大重連次數

        this.init();
    }

    init() {
        this.getUserLocation();
        this.initMap();
        this.connectWebSocket();
        this.setupEventListeners();
    }

    getUserLocation() {
        if ('geolocation' in navigator) {
            this.updateStatus('獲取位置中...', 'loading');

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.userLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    this.updateStatus('位置已獲取', 'connected');

                    // Update map center if already initialized
                    if (this.map) {
                        this.map.setView([this.userLocation.lat, this.userLocation.lng], 14);
                        this.updateUserLocationMarker();
                    }

                    // Send location to server
                    this.sendUserLocation();
                },
                (error) => {
                    console.error('Geolocation error:', error);
                    this.updateStatus('無法獲取位置，使用預設位置', 'disconnected');
                    // Use default location (Taipei)
                    this.userLocation = { lat: 25.1, lng: 121.55 };
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000 // 5 minutes
                }
            );
        } else {
            console.error('Geolocation not supported');
            this.updateStatus('瀏覽器不支援定位', 'disconnected');
            this.userLocation = { lat: 25.1, lng: 121.55 };
        }
    }

    initMap() {
        // Initialize map centered on user location or default
        const center = this.userLocation || [25.1, 121.55];
        this.map = L.map('map').setView(center, 14);

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.map);

        // Add user location marker if available
        if (this.userLocation) {
            this.updateUserLocationMarker();
        }

        // Add map click handler to close popups
        this.map.on('click', () => {
            this.map.closePopup();
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.updateStatus('已連接', 'connected');
                this.reconnectAttempts = 0;
            };

            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateStatus('已斷線', 'disconnected');
                this.attemptReconnect();
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateStatus('連接錯誤', 'disconnected');
            };

        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.updateStatus('連接失敗', 'disconnected');
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            this.updateStatus(`重新連接中... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'disconnected');

            setTimeout(() => {
                this.connectWebSocket();
            }, 3000 * this.reconnectAttempts);
        } else {
            this.updateStatus('連接失敗 - 請重新整理頁面', 'disconnected');
        }
    }

    sendUserLocation() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN && this.userLocation) {
            const message = {
                type: 'user_location',
                lat: this.userLocation.lat,
                lng: this.userLocation.lng
            };
            this.websocket.send(JSON.stringify(message));
        }
    }

    updateUserLocationMarker() {
        if (!this.userLocation || !this.map) return;

        // Remove existing marker
        if (this.userLocationMarker) {
            this.map.removeLayer(this.userLocationMarker);
        }

        // Create user location marker with blue circle
        const userIcon = L.divIcon({
            className: 'user-location-marker',
            html: '<div class="user-location-dot"></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        this.userLocationMarker = L.marker([this.userLocation.lat, this.userLocation.lng], {
            icon: userIcon,
            zIndexOffset: 1000 // Keep on top
        });

        this.userLocationMarker.bindPopup(`
            <div class="popup-content">
                <h4>📍 您的位置</h4>
                <p><strong>緯度:</strong> ${this.userLocation.lat.toFixed(6)}</p>
                <p><strong>經度:</strong> ${this.userLocation.lng.toFixed(6)}</p>
            </div>
        `);

        this.userLocationMarker.addTo(this.map);
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'initial_data':
                this.updateVehicles(data.vehicles);
                if (data.user_location && !this.userLocation) {
                    this.userLocation = data.user_location;
                    this.updateUserLocationMarker();
                }
                break;
            case 'vehicle_update':
                this.updateVehicles(data.vehicles);
                break;
            case 'location_updated':
                this.updateVehicles(data.vehicles);
                if (data.user_location) {
                    this.userLocation = data.user_location;
                    this.updateUserLocationMarker();
                }
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    updateVehicles(vehiclesData) {
        if (!this.isSimulationRunning) return;

        vehiclesData.forEach(vehicleData => {
            const vehicle = {
                ...vehicleData,
                lastUpdate: Date.now()
            };

            this.vehicles.set(vehicle.id, vehicle);
            this.updateVehicleMarker(vehicle);
        });

        this.updateSidebar();
    }

    updateVehicleMarker(vehicle) {
        const { id, lat, lng, status, speed, direction } = vehicle;

        if (this.markers.has(id)) {
            // Update existing marker
            const marker = this.markers.get(id);

            // Animate marker movement
            const currentLatLng = marker.getLatLng();
            const newLatLng = L.latLng(lat, lng);

            // Smooth animation
            this.animateMarker(marker, currentLatLng, newLatLng);

            // Update popup content
            marker.setPopupContent(this.createPopupContent(vehicle));

        } else {
            // Create new marker
            const marker = this.createVehicleMarker(vehicle);
            marker.addTo(this.map);
            this.markers.set(id, marker);
        }
    }

    createVehicleMarker(vehicle) {
        const { id, lat, lng, status } = vehicle;

        // Create custom icon
        const icon = L.divIcon({
            className: 'vehicle-marker',
            html: `<div class="vehicle-marker ${status}">🚗</div>`,
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        });

        const marker = L.marker([lat, lng], { icon });

        // Add popup
        marker.bindPopup(this.createPopupContent(vehicle));

        // Add click handler to focus on vehicle in sidebar
        marker.on('click', () => {
            this.focusVehicleInSidebar(id);
        });

        return marker;
    }

    createPopupContent(vehicle) {
        const { id, speed, status, direction } = vehicle;

        return `
            <div class="popup-content">
                <h4>${id}</h4>
                <p><strong>狀態:</strong> ${this.getStatusText(status)}</p>
                <p><strong>速度:</strong> ${speed} km/h</p>
                <p><strong>方向:</strong> ${Math.round(direction)}°</p>
                <p><strong>最後更新:</strong> ${new Date().toLocaleTimeString()}</p>
            </div>
        `;
    }

    animateMarker(marker, fromLatLng, toLatLng) {
        let start = null;
        const duration = 500; // 0.5 seconds to match server update rate

        const animate = (timestamp) => {
            if (!start) start = timestamp;
            const progress = Math.min((timestamp - start) / duration, 1);

            // Smooth easing function
            const easeProgress = progress * (2 - progress);

            const lat = fromLatLng.lat + (toLatLng.lat - fromLatLng.lat) * easeProgress;
            const lng = fromLatLng.lng + (toLatLng.lng - fromLatLng.lng) * easeProgress;

            marker.setLatLng([lat, lng]);

            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    updateSidebar() {
        const vehicles = Array.from(this.vehicles.values());

        // Update statistics
        const stats = this.calculateStats(vehicles);
        document.getElementById('totalVehicles').textContent = stats.total;
        document.getElementById('availableVehicles').textContent = stats.available;
        document.getElementById('busyVehicles').textContent = stats.busy;
        document.getElementById('offlineVehicles').textContent = stats.offline;

        // Update vehicle list
        this.updateVehicleList(vehicles);
    }

    calculateStats(vehicles) {
        return vehicles.reduce((stats, vehicle) => {
            stats.total++;
            stats[vehicle.status]++;
            return stats;
        }, { total: 0, available: 0, busy: 0, offline: 0 });
    }

    updateVehicleList(vehicles) {
        const vehicleList = document.getElementById('vehicleList');

        // Sort vehicles by ID
        const sortedVehicles = vehicles.sort((a, b) => a.id.localeCompare(b.id));

        vehicleList.innerHTML = sortedVehicles.map(vehicle => `
            <div class="vehicle-item" data-vehicle-id="${vehicle.id}">
                <div class="vehicle-header">
                    <span class="vehicle-id">${vehicle.id}</span>
                    <span class="vehicle-status ${vehicle.status}">${this.getStatusText(vehicle.status)}</span>
                </div>
                <div class="vehicle-info">
                    <span>速度: <strong>${vehicle.speed} km/h</strong></span>
                    <span>方向: <strong>${Math.round(vehicle.direction)}°</strong></span>
                    <span>位置: <strong>${vehicle.lat.toFixed(4)}, ${vehicle.lng.toFixed(4)}</strong></span>
                    <span>更新: <strong>${new Date(vehicle.lastUpdate).toLocaleTimeString()}</strong></span>
                </div>
            </div>
        `).join('');

        // Add click handlers to vehicle items
        vehicleList.querySelectorAll('.vehicle-item').forEach(item => {
            item.addEventListener('click', () => {
                const vehicleId = item.dataset.vehicleId;
                this.focusVehicle(vehicleId);
            });
        });
    }

    focusVehicle(vehicleId) {
        const vehicle = this.vehicles.get(vehicleId);
        if (vehicle && this.markers.has(vehicleId)) {
            const marker = this.markers.get(vehicleId);
            this.map.setView([vehicle.lat, vehicle.lng], 15);
            marker.openPopup();
        }
    }

    focusVehicleInSidebar(vehicleId) {
        const vehicleItem = document.querySelector(`[data-vehicle-id="${vehicleId}"]`);
        if (vehicleItem) {
            vehicleItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            vehicleItem.style.backgroundColor = '#e3f2fd';
            setTimeout(() => {
                vehicleItem.style.backgroundColor = '';
            }, 2000);
        }
    }

    getStatusText(status) {
        const statusTexts = {
            available: '可用',
            busy: '忙碌',
            offline: '離線'
        };
        return statusTexts[status] || status;
    }

    updateStatus(message, type = '') {
        const statusElement = document.getElementById('status');
        statusElement.textContent = message;
        statusElement.className = `status ${type}`;
    }

    toggleSimulation() {
        this.isSimulationRunning = !this.isSimulationRunning;
        const button = document.getElementById('toggleSimulation');

        if (this.isSimulationRunning) {
            button.textContent = '暫停模擬';
            this.updateStatus('模擬進行中', 'connected');
        } else {
            button.textContent = '開始模擬';
            this.updateStatus('模擬已暫停', 'disconnected');
        }
    }

    setupEventListeners() {
        // Toggle simulation button
        document.getElementById('toggleSimulation').addEventListener('click', () => {
            this.toggleSimulation();
        });

        // Handle page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log('Page hidden - maintaining WebSocket connection');
            } else {
                console.log('Page visible');
                // Optionally refresh data when page becomes visible
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            if (this.map) {
                this.map.invalidateSize();
            }
        });
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Uber Vehicle Simulation...');
    new UberSimulation();
});