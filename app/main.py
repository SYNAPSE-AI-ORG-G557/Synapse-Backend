# Synapse-Backend/app/main.py

import sys
import os

# Add project root (two levels up from this file) to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from src.api.endpoints import processing  # import your router here

app = FastAPI(title="Synapse Backend API")

@app.get("/")
def read_root():
    return {"message": "Hello, Synapse Backend is running!"}

# Register the processing router under '/jobs' prefix
app.include_router(processing.router, prefix="/jobs", tags=["Processing"])
