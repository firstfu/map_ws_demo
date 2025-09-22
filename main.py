# 匯入必要的程式庫
import asyncio
import json
import random
import time
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# 建立 FastAPI 應用程式實例
app = FastAPI(title="Uber Vehicle Simulation")

# 設定靜態檔案服務目錄
app.mount("/static", StaticFiles(directory="static"), name="static")

# 車輛類別：模擬 Uber 車輛的行為和狀態
class Vehicle:
    def __init__(self, vehicle_id: str, lat: float, lng: float):
        """初始化車輛

        Args:
            vehicle_id: 車輛唯一識別碼
            lat: 緯度座標
            lng: 經度座標
        """
        self.id = vehicle_id               # 車輛 ID
        self.lat = lat                     # 緯度
        self.lng = lng                     # 經度
        self.speed = random.uniform(40, 80)  # 車輛速度 (km/h)
        self.direction = random.uniform(0, 360)  # 移動方向 (度數)
        self.status = random.choice(["available", "busy", "offline"])  # 車輛狀態

    def update_position(self):
        """更新車輛位置

        模擬車輛的真實移動行為，包括：
        - 速度轉換為位移
        - 隨機方向變化
        - 邊界檢查（防止車輛移動太遠）
        - 狀態隨機變化
        """
        # 模擬真實的車輛移動
        # 將速度從 km/h 轉換為每秒移動的度數（粗略近似值）
        speed_deg_per_sec = self.speed / 111000 / 3600

        # 為方向添加隨機變化，模擬真實駕駛
        self.direction += random.uniform(-30, 30)
        self.direction = self.direction % 360

        # 計算新的位置座標
        import math
        new_lat = self.lat + speed_deg_per_sec * math.cos(math.radians(self.direction))
        new_lng = self.lng + speed_deg_per_sec * math.sin(math.radians(self.direction))

        # 檢查新位置是否在使用者位置的合理範圍內
        # 計算與使用者位置的距離
        lat_diff = new_lat - user_location["lat"]
        lng_diff = new_lng - user_location["lng"]
        distance_from_user = math.sqrt(lat_diff**2 + lng_diff**2)

        # 如果車輛距離太遠（超過約 10 公里），則反向行駛
        max_distance = 0.09  # 約 10 公里的度數表示
        if distance_from_user > max_distance:
            # 調轉方向，朝使用者區域回行
            self.direction = (self.direction + 180) % 360
            # 這次不更新位置，只改變方向
        else:
            # 正常更新位置
            self.lat = new_lat
            self.lng = new_lng

        # 隨機改變速度和狀態，模擬真實情況
        if random.random() < 0.1:  # 10% 機率改變速度
            self.speed = random.uniform(40, 80)

        if random.random() < 0.05:  # 5% 機率改變狀態
            self.status = random.choice(["available", "busy", "offline"])

    def to_dict(self):
        """將車輛資料轉換為字典格式

        Returns:
            dict: 包含車輛所有資訊的字典
        """
        return {
            "id": self.id,                      # 車輛 ID
            "lat": round(self.lat, 6),          # 緯度（6位小數）
            "lng": round(self.lng, 6),          # 經度（6位小數）
            "speed": round(self.speed, 1),      # 速度（1位小數）
            "direction": round(self.direction, 1),  # 方向（1位小數）
            "status": self.status,              # 車輛狀態
            "timestamp": time.time()           # 時間戳記
        }

# WebSocket 連線管理器：處理多個客戶端的連線
class ConnectionManager:
    def __init__(self):
        """初始化連線管理器"""
        self.active_connections: List[WebSocket] = []  # 儲存活躍的 WebSocket 連線

    async def connect(self, websocket: WebSocket):
        """接受新的 WebSocket 連線

        Args:
            websocket: WebSocket 連線物件
        """
        await websocket.accept()                       # 接受連線
        self.active_connections.append(websocket)      # 加入活躍連線清單

    def disconnect(self, websocket: WebSocket):
        """移除 WebSocket 連線

        Args:
            websocket: 要移除的 WebSocket 連線物件
        """
        self.active_connections.remove(websocket)      # 從活躍連線清單中移除

    async def broadcast(self, message: str):
        """向所有活躍連線廣播訊息

        Args:
            message: 要廣播的訊息（JSON 字串）
        """
        for connection in self.active_connections:
            try:
                await connection.send_text(message)            # 發送訊息
            except:
                # 移除已斷線的客戶端
                self.active_connections.remove(connection)

# 建立連線管理器實例
manager = ConnectionManager()

# 全域變數：儲存使用者位置
user_location = {"lat": 25.1, "lng": 121.55}  # 預設為台北市

def create_vehicles_around_location(lat, lng, count=10, radius_km=5):
    """在指定位置周圍建立車輛

    Args:
        lat: 中心點緯度
        lng: 中心點經度
        count: 要建立的車輛數量
        radius_km: 分布半徑（公里）

    Returns:
        List[Vehicle]: 車輛物件清單
    """
    vehicles = []
    for i in range(1, count + 1):
        # 將半徑從公里轉換為度數（粗略近似值）
        radius_deg = radius_km / 111.0

        # 在半徑內產生隨機位置
        angle = random.uniform(0, 2 * 3.14159)      # 隨機角度
        distance = random.uniform(0, radius_deg)    # 隨機距離

        # 計算車輛座標
        vehicle_lat = lat + distance * math.cos(angle)
        vehicle_lng = lng + distance * math.sin(angle)

        # 建立車輛並加入清單
        vehicles.append(Vehicle(f"UBER-{i:03d}", vehicle_lat, vehicle_lng))

    return vehicles

# 在預設位置周圍初始化車輛
import math
vehicles = create_vehicles_around_location(user_location["lat"], user_location["lng"])

# 背景任務：更新車輛位置的模擬
async def vehicle_simulation():
    """車輛模擬的主迴圈

    持續更新所有車輛的位置並廣播給所有連線的客戶端
    """
    while True:
        # 更新所有車輛位置
        for vehicle in vehicles:
            vehicle.update_position()

        # 廣播更新資料給所有連線的客戶端
        vehicles_data = {
            "type": "vehicle_update",
            "vehicles": [vehicle.to_dict() for vehicle in vehicles]
        }
        await manager.broadcast(json.dumps(vehicles_data))

        # 每 0.5 秒更新一次，提供更流暢的移動效果
        await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    """應用程式啟動事件處理器

    啟動背景車輛模擬任務
    """
    # 在背景啟動車輛模擬任務
    asyncio.create_task(vehicle_simulation())

@app.get("/")
async def get():
    """根路徑處理器

    重定向到靜態檔案的主頁面

    Returns:
        HTMLResponse: 包含重定向 JavaScript 的 HTML 回應
    """
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Uber Vehicle Simulation</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
        <script>
            window.location.href = '/static/index.html';
        </script>
    </body>
    </html>
    """)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端點處理器

    處理 WebSocket 連線、初始資料傳送和使用者訊息

    Args:
        websocket: WebSocket 連線物件
    """
    global vehicles, user_location
    await manager.connect(websocket)  # 建立連線
    try:
        # 發送初始車輛資料
        initial_data = {
            "type": "initial_data",
            "vehicles": [vehicle.to_dict() for vehicle in vehicles],
            "user_location": user_location
        }
        await websocket.send_text(json.dumps(initial_data))

        # 保持連線並處理收到的訊息
        while True:
            data = await websocket.receive_text()  # 接收客戶端訊息
            message = json.loads(data)

            # 處理使用者位置更新
            if message.get("type") == "user_location":
                new_lat = message.get("lat")
                new_lng = message.get("lng")
                if new_lat and new_lng:
                    # 更新使用者位置
                    user_location["lat"] = new_lat
                    user_location["lng"] = new_lng

                    # 在新位置周圍重新產生車輛
                    vehicles = create_vehicles_around_location(new_lat, new_lng)

                    # 廣播更新的車輛資料給所有客戶端
                    update_data = {
                        "type": "location_updated",
                        "vehicles": [vehicle.to_dict() for vehicle in vehicles],
                        "user_location": user_location
                    }
                    await manager.broadcast(json.dumps(update_data))

    except WebSocketDisconnect:
        # WebSocket 斷線時移除連線
        manager.disconnect(websocket)

# 主程式進入點
if __name__ == "__main__":
    import uvicorn
    # 啟動 ASGI 伺服器，監聽所有網路介面的 8001 埠
    uvicorn.run(app, host="0.0.0.0", port=8001)