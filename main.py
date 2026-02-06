from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
from app import models, crud, migrations
from app.database import engine, SessionLocal
from app.ui import create_ui
from nicegui import ui

def init_db():
    # Create all tables
    models.Base.metadata.create_all(bind=engine)

    # Get a DB session
    db = SessionLocal()
    try:
        # Seed initial settings
        crud.update_setting(db, key='failover_threshold_count', value='2')
        crud.update_setting(db, key='failover_threshold_period_minutes', value='5')
        print("Database initialized and default settings seeded.")
    finally:
        db.close()

app = FastAPI(
    title="AI Provider API Server",
    description="An intelligent API server to manage and route requests to various AI providers.",
    version="0.1.0",
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    error_details = exc.errors()
    
    logger.error("--- 422 Unprocessable Entity Detected ---")
    logger.error(f"URL: {request.url}")
    logger.error(f"Method: {request.method}")
    logger.error(f"Request Body: {body.decode('utf-8', errors='ignore')}")
    logger.error(f"Validation Errors: {error_details}")
    logger.error("-----------------------------------------")
    
    # Format error message for OpenAI compatibility
    error_messages = []
    for err in error_details:
        loc = " -> ".join([str(l) for l in err.get("loc", [])])
        msg = err.get("msg")
        error_messages.append(f"{loc}: {msg}")
    
    combined_message = " | ".join(error_messages)
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": combined_message,
                "type": "invalid_request_error",
                "param": None,
                "code": None
            },
            "detail": error_details,
            "body_received": body.decode('utf-8', errors='ignore')
        },
    )

from app.api import router as api_router, proxy_router
app.include_router(api_router, prefix="/api")
app.include_router(proxy_router) # Mount proxy routes at root for compatibility

# Serve frontend static files if built (mounted at /admin)
import os

app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")

from fastapi.responses import JSONResponse
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # If detail is already a dict and has "error", use it directly
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail
    else:
        content = {
            "error": {
                "message": str(exc.detail),
                "type": "api_error",
                "param": None,
                "code": None
            }
        }
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )

# The @ui.page decorator is now used in ui.py, so we don't call create_ui() directly.
@app.on_event("startup")
async def on_startup():
    init_db()
    migrations.run_migrations()
    
    # Reset active calls to 0 on startup
    db = SessionLocal()
    try:
        crud.reset_all_active_calls(db)
        print("Active calls reset to 0.")
    finally:
        db.close()

# API routes should be included before NiceGUI
# (They are already included above)

create_ui()
ui.run_with(
    app,
    title="NiceAPI",
    favicon="images/favicon.png",
    storage_secret="a_super_secret_key_that_should_be_changed"
)