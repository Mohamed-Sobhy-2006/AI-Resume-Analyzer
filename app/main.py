"""FastAPI application entry point.  Run with:  uvicorn app.main:app --reload"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import analysis, auth, career, jobs, recommendations, resumes
from app.services.llm_service import llm_service
from app.services.seed_service import seed_database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    seed_database()          # creates tables; inserts sample data only if the tables are empty
    if not llm_service.is_configured():
        logger.warning("GEMINI_API_KEY is not set - running in fallback mode (no AI generation).")
    yield


app = FastAPI(
    title="AI Resume Analyzer",
    description="Resume analysis, job matching and career advice using AI agents and RAG.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


def _friendly_validation_message(exc: RequestValidationError) -> str:
    messages = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path"))
        if err["type"] == "missing":
            messages.append(f"{field or 'A required field'} is required.")
        else:
            messages.append(str(err["msg"]).removeprefix("Value error, "))
    return " ".join(dict.fromkeys(messages)) or "Invalid request."


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": _friendly_validation_message(exc)})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server. Please try again."})


@app.get("/api/health", tags=["System"], summary="Health check")
def health():
    return {"status": "ok", "ai_configured": llm_service.is_configured()}


for module in (auth, resumes, analysis, jobs, recommendations, career):
    app.include_router(module.router)

# The frontend is served by FastAPI itself (must be mounted LAST so /api and /docs keep working).
app.mount("/", StaticFiles(directory=str(settings.FRONTEND_DIR), html=True), name="frontend")
