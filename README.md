# Uber Vehicle Simulation

一個使用 FastAPI 和 WebSocket 的實時車輛追蹤模擬應用，展示類似 Uber 的車輛在地圖上的隨機移動。

## 功能特色

- 🚗 **實時車輛模擬**: 10輛車在台北地區隨機移動
- 🗺️ **互動式地圖**: 使用 Leaflet.js 和 OpenStreetMap
- 📡 **WebSocket 連接**: 每2秒更新車輛位置
- 📊 **即時統計**: 顯示可用、忙碌和離線車輛數量
- 🎯 **點擊追蹤**: 點擊車輛標記或側邊欄項目聚焦車輛
- 📱 **響應式設計**: 支援桌面和移動設備

## 技術架構

### 後端
- **FastAPI**: Python web 框架
- **WebSocket**: 實時雙向通信
- **asyncio**: 異步車輛模擬

### 前端
- **純 HTML/CSS/JavaScript**: 無框架依賴
- **Leaflet.js**: 開源地圖庫
- **OpenStreetMap**: 免費地圖資料

## 快速開始

### 1. 安裝 uv 套件管理器

```bash
# 安裝 uv（如果尚未安裝）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 安裝依賴

```bash
# 使用 uv 同步依賴（會自動建立虛擬環境）
uv sync
```

### 3. 啟動服務器

```bash
# 方法一：使用 uv run
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# 方法二：激活虛擬環境後運行
source .venv/bin/activate  # Linux/Mac
# 或
.venv\\Scripts\\activate  # Windows
python main.py
```

### 4. 開啟瀏覽器

訪問 http://localhost:8080 即可看到車輛模擬應用。

## 專案結構

```
map_ws_demo/
├── main.py              # FastAPI 主程式
├── pyproject.toml       # 專案配置和依賴套件
├── .venv/               # uv 建立的虛擬環境
├── static/
│   ├── index.html       # 主頁面
│   ├── style.css        # 樣式表
│   └── app.js           # JavaScript 邏輯
└── README.md           # 說明文件
```

## 應用功能

### 車輛模擬
- 10輛虛擬車輛在台北地區移動
- 隨機速度變化（20-60 km/h）
- 自然的方向轉換
- 三種狀態：可用、忙碌、離線

### 地圖互動
- 縮放和平移地圖
- 點擊車輛標記查看詳細資訊
- 平滑的車輛移動動畫
- 根據車輛狀態的顏色編碼

### 實時更新
- WebSocket 連接狀態指示器
- 自動重連機制
- 暫停/恢復模擬功能
- 車輛統計即時更新

## API 端點

- `GET /`: 主頁面（重導向到 /static/index.html）
- `GET /static/*`: 靜態檔案服務
- `WebSocket /ws`: WebSocket 連接端點

## 開發說明

### 車輛資料格式

```json
{
  "id": "UBER-001",
  "lat": 25.0330,
  "lng": 121.5654,
  "speed": 45.2,
  "direction": 180.0,
  "status": "available",
  "timestamp": 1694789123.456
}
```

### WebSocket 訊息格式

```json
{
  "type": "vehicle_update",
  "vehicles": [...]
}
```

## 自定義設定

### 修改車輛數量
在 `main.py` 中修改：
```python
vehicles = [
    Vehicle(f"UBER-{i:03d}", ...)
    for i in range(1, 11)  # 改變這個數字
]
```

### 修改更新頻率
在 `vehicle_simulation()` 函數中：
```python
await asyncio.sleep(2)  # 改變秒數
```

### 修改地圖中心
在 `app.js` 中：
```javascript
this.map = L.map('map').setView([25.1, 121.55], 12);
```

## 部署建議

### 生產環境
```bash
# 使用 uv
uv run uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
```

### Docker 部署
```dockerfile
FROM python:3.11-slim

# 安裝 uv
RUN pip install uv

WORKDIR /app
COPY pyproject.toml .
RUN uv sync --no-dev

COPY . .
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## 故障排除

### 常見問題

1. **端口被占用**
   ```bash
   # 檢查端口使用情況
   lsof -i :8080
   # 或使用不同端口
   uv run uvicorn main:app --port 8081
   ```

2. **WebSocket 連接失敗**
   - 檢查防火牆設定
   - 確保服務器正在運行
   - 檢查瀏覽器控制台錯誤

3. **地圖不顯示**
   - 檢查網路連接（需要載入 Leaflet 和地圖圖層）
   - 檢查瀏覽器 JavaScript 控制台

## 許可證

本專案僅供演示目的，使用開源技術堆疊。