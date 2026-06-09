import uuid
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from hybrid_classifier import process_message, fuzzy

app = FastAPI()

@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")
    try:
        while True:
            data = await websocket.receive_json()
            content    = data.get("content", "")
            message_id = str(uuid.uuid4())[:8]

            # run sync code in a thread — doesn't block the event loop
            result = await asyncio.to_thread(process_message, message_id, content)

            await websocket.send_json(result)

    except WebSocketDisconnect:
        print("Client disconnected")

@app.get("/queue")
def queue_status():
    return fuzzy.queue_status()

@app.get("/")
def index():
    with open("test_client.html") as f:
        return HTMLResponse(f.read())
