# Synapse-Backend/app/main.py

from fastapi import FastAPI
from src.core.config import settings
from src.api.endpoints import processing  # Import the router from the processing endpoints file

# The sys.path manipulation is no longer needed because the PYTHONPATH
# is correctly set in the Docker environment, making imports work naturally.

# Initialize the FastAPI app, using the project name from our settings file.
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- Include API Routers ---
# This line registers all the endpoints from the processing.py file.
# We use the API_V1_STR from our settings file as a prefix, which is a
# best practice for versioning your API.
app.include_router(processing.router, prefix=settings.API_V1_STR, tags=["Processing"])


@app.get("/")
def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}