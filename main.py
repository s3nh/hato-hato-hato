import uuid
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from classifier import classify_message
from bucket_manager import BucketManager

app = FastAPI()
manager = BucketManager()

class ChatMessage(BaseModel):
    content: str
    guest_id: str
    timestamp: str          # ISO-8601

@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_json()
            msg = ChatMessage(**raw)

            # 1. Classify in a thread so we don't block the event loop
            topic, confidence = await asyncio.to_thread(
                classify_message, msg.content
            )

            # 2. Update bucket + check saturation
            message_id = str(uuid.uuid4())
            status = manager.add_message(topic, message_id)

            # 3. Build response
            response = {
                "message_id": message_id,
                "classified_topic": topic,
                "confidence": round(confidence, 3),
                "queue_depth": status.count,
                "saturated": status.is_saturated,
            }

            if status.is_saturated:
                response["suggestion"] = {
                    "message": f"We have many questions about '{topic}' already. "
                               f"Consider asking about one of these instead:",
                    "alternatives": status.suggested_topics,
                }

            await websocket.send_json(response)

    except WebSocketDisconnect:
        pass

# Optional REST endpoint to see live bucket state
@app.get("/queue/status")
def queue_status():
    return manager.get_all_counts()
