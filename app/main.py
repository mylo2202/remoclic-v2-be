from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.main import api_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(api_router)

# 1. Add the Origins that are allowed to make requests to your API
origins = [
    "http://localhost:4200",   
    "http://127.0.0.1:4200",
]
# 2. Add the CORSMiddleware right after initializing the FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # Allow the Angular frontend
    allow_credentials=True,
    allow_methods=["*"],          # Allow all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],          # Allow all headers
)

