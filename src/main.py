# Synapse-Backend/app/main.py

import asyncio
import json
import uuid
import sys
import os
from contextlib import asynccontextmanager

# Add the parent directory to Python path to access src
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(APP_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware 
from starlette_prometheus import PrometheusMiddleware, metrics
import structlog

from src.core.config import settings
from src.api.endpoints import processing, websockets, auth, users, conversation
from src.core.redis_client import redis_client
from src.websockets.manager import connection_manager
from src.core.logging_config import setup_logging
from src.services.real.vector_store_service import RealVectorStoreService

# Rest of your original main.py code...