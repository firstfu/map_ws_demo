import asyncio
import json
import random
import time
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI(title="Uber Vehicle Simulation")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class Vehicle:
    def __init__(self, vehicle_id: str, lat: float, lng: float):
        self.id = vehicle_id
        self.lat = lat
        self.lng = lng
        self.speed = random.uniform(40, 80)  # km/h
        self.direction = random.uniform(0, 360)  # degrees
        self.status = random.choice(["available", "busy", "offline"])

    def update_position(self):
        # Simulate realistic movement
        # Convert speed from km/h to degrees per second (rough approximation)
        speed_deg_per_sec = self.speed / 111000 / 3600

        # Add some randomness to direction
        self.direction += random.uniform(-30, 30)
        self.direction = self.direction % 360

        # Update position
        import math
        self.lat += speed_deg_per_sec * math.cos(math.radians(self.direction))
        self.lng += speed_deg_per_sec * math.sin(math.radians(self.direction))

        # Keep vehicles within bounds around user location (±0.1 degrees ~ 11km)
        lat_min = user_location["lat"] - 0.1
        lat_max = user_location["lat"] + 0.1
        lng_min = user_location["lng"] - 0.1
        lng_max = user_location["lng"] + 0.1

        self.lat = max(lat_min, min(lat_max, self.lat))
        self.lng = max(lng_min, min(lng_max, self.lng))

        # Occasionally change speed and status
        if random.random() < 0.1:
            self.speed = random.uniform(40, 80)

        if random.random() < 0.05:
            self.status = random.choice(["available", "busy", "offline"])

    def to_dict(self):
        return {
            "id": self.id,
            "lat": round(self.lat, 6),
            "lng": round(self.lng, 6),
            "speed": round(self.speed, 1),
            "direction": round(self.direction, 1),
            "status": self.status,
            "timestamp": time.time()
        }

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Global variable to store user location
user_location = {"lat": 25.1, "lng": 121.55}  # Default to Taipei

def create_vehicles_around_location(lat, lng, count=10, radius_km=5):
    """Create vehicles within a radius around the given location"""
    vehicles = []
    for i in range(1, count + 1):
        # Convert radius from km to degrees (rough approximation)
        radius_deg = radius_km / 111.0

        # Generate random position within radius
        angle = random.uniform(0, 2 * 3.14159)
        distance = random.uniform(0, radius_deg)

        vehicle_lat = lat + distance * math.cos(angle)
        vehicle_lng = lng + distance * math.sin(angle)

        vehicles.append(Vehicle(f"UBER-{i:03d}", vehicle_lat, vehicle_lng))

    return vehicles

# Initialize vehicles around default location
import math
vehicles = create_vehicles_around_location(user_location["lat"], user_location["lng"])

# Background task to update vehicle positions
async def vehicle_simulation():
    while True:
        # Update all vehicle positions
        for vehicle in vehicles:
            vehicle.update_position()

        # Broadcast updates to all connected clients
        vehicles_data = {
            "type": "vehicle_update",
            "vehicles": [vehicle.to_dict() for vehicle in vehicles]
        }
        await manager.broadcast(json.dumps(vehicles_data))

        # Update every 0.5 seconds for faster movement
        await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    # Start the vehicle simulation in the background
    asyncio.create_task(vehicle_simulation())

@app.get("/")
async def get():
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
    global vehicles, user_location
    await manager.connect(websocket)
    try:
        # Send initial vehicle data
        initial_data = {
            "type": "initial_data",
            "vehicles": [vehicle.to_dict() for vehicle in vehicles],
            "user_location": user_location
        }
        await websocket.send_text(json.dumps(initial_data))

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle user location update
            if message.get("type") == "user_location":
                new_lat = message.get("lat")
                new_lng = message.get("lng")
                if new_lat and new_lng:
                    user_location["lat"] = new_lat
                    user_location["lng"] = new_lng

                    # Regenerate vehicles around new location
                    vehicles = create_vehicles_around_location(new_lat, new_lng)

                    # Broadcast updated vehicles to all clients
                    update_data = {
                        "type": "location_updated",
                        "vehicles": [vehicle.to_dict() for vehicle in vehicles],
                        "user_location": user_location
                    }
                    await manager.broadcast(json.dumps(update_data))

    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)