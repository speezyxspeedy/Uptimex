import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import init_db
from app.scheduler import start_scheduler, stop_scheduler, is_scheduler_running
from app.models import utc_now
from app.security import SecurityValidationError
from app.routes import monitors, checks, incidents, analytics, settings as settings_route


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database and Scheduler
    init_db()
    start_scheduler()
    yield
    # Shutdown: Stop Scheduler
    stop_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="UptimeX — Website Uptime & Performance Monitor API",
    lifespan=lifespan
)

# CORS configuration restricted to configured local origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        msg = err.get("msg", "Invalid input")
        # Strip internal Pydantic prefix if present
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        errors.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(errors)}
    )


@app.exception_handler(SecurityValidationError)
async def security_exception_handler(request: Request, exc: SecurityValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Ensure no internal stack traces or internal IP details are exposed to users
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred while processing the request."}
    )


# Health check endpoint
@app.get("/health", tags=["system"])
@app.get("/api/health", tags=["system"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "scheduler_active": is_scheduler_running(),
        "timestamp_utc": utc_now().isoformat()
    }


# Register API routers
app.include_router(monitors.router)
app.include_router(checks.router)
app.include_router(incidents.router)
app.include_router(analytics.router)
app.include_router(settings_route.router)

# Mount static frontend directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", tags=["frontend"])
    def serve_frontend_root():
        index_file = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "UptimeX API is running. Frontend static files not found."}
