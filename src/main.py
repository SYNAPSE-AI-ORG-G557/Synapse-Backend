# Synapse-Backend/app/main.py

import sys
import os

# Add project root to sys.path so "src" imports work when running from app/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.endpoints import processing, auth, conversation, users, websockets

app = FastAPI(title="Synapse Backend API")

# Add CORS middleware for localhost support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4173", 
        "http://localhost:3000", 
        "http://127.0.0.1:4173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello, Synapse Backend is running!"}

# Register all routers
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(processing.router, prefix="/jobs", tags=["Processing"])
app.include_router(conversation.router, prefix="/api/v1", tags=["Conversations"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(websockets.router, prefix="/ws", tags=["WebSockets"])
