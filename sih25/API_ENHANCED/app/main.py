from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import asyncio
import json
from dotenv import load_dotenv
from .routers import chat_router, admin_router, data_router
from .routes_argo import router as argo_router
from .routes_natural_language import router as nl_router
from .pipecat_router_simplified import router as pipecat_router, cleanup_sessions
from .startup import init_db
from .realtime import manager, data_streamer, alert_system

load_dotenv()

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    asyncio.create_task(data_streamer.start_streaming())
    yield
    # Shutdown
    data_streamer.stop_streaming()
    await cleanup_sessions()

# Create FastAPI app with lifespan
app = FastAPI(title="FloatChat API", version="0.1.0", lifespan=lifespan)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/chat", tags=["Chat"])
app.include_router(data_router, prefix="/data", tags=["Data"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(argo_router, prefix="/argo", tags=["ARGO Integration"])
app.include_router(nl_router, prefix="/api", tags=["Natural Language"])
app.include_router(pipecat_router, prefix="/api/pipecat", tags=["Pipecat Voice AI"])

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {"message": "API is running"}

# Health endpoint
@app.get("/health", tags=["Root"])
async def health():
    return {"status": "ok"}

# WebSocket endpoints
@app.websocket("/ws/data-stream")
async def data_stream_ws(websocket: WebSocket):
    user_id = websocket.headers.get("user-id", "anonymous")
    await manager.connect(websocket, "data_updates", user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "subscribe_filters":
                filters = message.get("filters", {})
                await manager.send_personal_message(
                    json.dumps({"type": "subscription_confirmed", "filters": filters}),
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, "data_updates", user_id)

@app.websocket("/ws/analytics")
async def analytics_ws(websocket: WebSocket):
    user_id = websocket.headers.get("user-id", "anonymous")
    await manager.connect(websocket, "analytics", user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "analytics", user_id)

@app.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    user_id = websocket.headers.get("user-id", "anonymous")
    await manager.connect(websocket, "alerts", user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, "alerts", user_id)

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    user_id = websocket.headers.get("user-id", "anonymous")
    await manager.connect(websocket, "chat", user_id)
    chat_history = {}
    chat_history.setdefault(user_id, [])
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            chat_history[user_id].append(message)
            response = {
                "type": "chat_response",
                "message": f"Received: {message.get('content', '')}",
                "timestamp": asyncio.get_event_loop().time(),
                "user_id": user_id
            }
            await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        manager.disconnect(websocket, "chat", user_id)

# Removed placeholder export and search endpoints (use data_router exports instead)