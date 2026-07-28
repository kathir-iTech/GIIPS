import asyncio
import time
import logging
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from websockets.asyncio.client import connect as ws_connect
import jwt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ws_test")

# Simple test FastAPI app with our WS endpoint
app = FastAPI()

class TestManager:
    def __init__(self):
        self.connections = set()
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)
    async def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)

manager = TestManager()

@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket, token: str = Query(...)):
    if token != "valid-test-token":
        await websocket.close(code=4001)
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('"pong"')
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)

server_config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
server = uvicorn.Server(server_config)

async def run_server():
    await server.serve()

async def client_simulation():
    # Reconnection logic matching useDashboardSocket.ts
    INITIAL_RETRY_MS = 1000
    MAX_RETRY_MS = 30000
    retry_delay = INITIAL_RETRY_MS
    
    connected_event = asyncio.Event()
    reconnected_event = asyncio.Event()
    
    disconnect_detected_at = None
    reconnected_at = None

    async def client_loop():
        nonlocal retry_delay, disconnect_detected_at, reconnected_at
        while True:
            uri = "ws://127.0.0.1:8765/ws/dashboard?token=valid-test-token"
            try:
                logger.info("Client attempting connection to %s", uri)
                async with ws_connect(uri) as ws:
                    logger.info("Client connected successfully!")
                    connected_event.set()
                    if disconnect_detected_at is not None:
                        reconnected_at = time.time()
                        reconnected_event.set()
                    retry_delay = INITIAL_RETRY_MS
                    
                    # Keep alive loop
                    while True:
                        await ws.send("ping")
                        pong = await ws.recv()
                        await asyncio.sleep(2)
            except Exception as e:
                logger.warning("Client connection lost or failed: %s", e)
                if connected_event.is_set() and disconnect_detected_at is None:
                    disconnect_detected_at = time.time()
                
                delay_sec = retry_delay / 1000.0
                logger.info("Retrying in %.1f seconds (exponential backoff)...", delay_sec)
                await asyncio.sleep(delay_sec)
                retry_delay = min(retry_delay * 2, MAX_RETRY_MS)

    # Start client task
    client_task = asyncio.create_task(client_loop())

    # Test sequence:
    # 1. Wait for initial connection
    try:
        await asyncio.wait_for(connected_event.wait(), timeout=5.0)
        logger.info("--- TEST STEP 1: Initial connection established ---")
    except asyncio.TimeoutError:
        logger.error("Initial connection failed!")
        client_task.cancel()
        return

    # 2. Simulate server restart (shutdown server)
    logger.info("--- TEST STEP 2: Shutting down server (simulating cold-start / restart) ---")
    global server
    server.should_exit = True
    shutdown_time = time.time()

    # Wait a bit for client to detect disconnect
    await asyncio.sleep(2.0)
    
    if disconnect_detected_at:
        detect_duration = disconnect_detected_at - shutdown_time
        logger.info("-> Disconnect detected by client in %.2f seconds", detect_duration)
    else:
        logger.warning("-> Disconnect not explicitly flagged yet")

    # 3. Bring server back up after 3 seconds (simulating wake-up)
    logger.info("--- TEST STEP 3: Bringing server back up after 3s ---")
    await asyncio.sleep(3.0)
    
    # Reset server instance for restart
    server = uvicorn.Server(server_config)
    server_task = asyncio.create_task(server.serve())

    # 4. Wait for reconnection
    try:
        await asyncio.wait_for(reconnected_event.wait(), timeout=10.0)
        reconnect_duration = reconnected_at - shutdown_time
        logger.info("--- TEST STEP 4: Successfully reconnected! Total downtime handled: %.2f seconds ---", reconnect_duration)
    except asyncio.TimeoutError:
        logger.error("Reconnection failed within timeout!")
    
    server.should_exit = True
    client_task.cancel()
    try:
        await server_task
    except:
        pass

if __name__ == "__main__":
    async def main():
        server_task = asyncio.create_task(run_server())
        await asyncio.sleep(0.5) # let server start
        await client_simulation()
        server.should_exit = True
        try:
            await server_task
        except:
            pass

    asyncio.run(main())
