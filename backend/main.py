"""
FastAPI backend - entry point for the API server.
"""
# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

import os
import subprocess
import shutil
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from backend.mode_handler import generate_deck
from ai.agents.research_agent import research_agent
from ai.agents.intent_detector import intent_detector
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PPT Generator API",
    description="Agentic AI application that generates Slidev presentations",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # Alternative frontend
        "null",  # file:// protocol (frontend/index.html opened directly)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class GenerateRequest(BaseModel):
    mode: str
    query: str
    answers: dict = None  # Required for max mode


class MaxQuestionsRequest(BaseModel):
    query: str


class ModeInfo(BaseModel):
    id: str
    label: str
    description: str


# Global exception handlers
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Handle custom AppError exceptions."""
    logger.exception(f"AppError: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Application Error",
            "detail": str(exc)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/modes")
async def get_modes():
    """Get available generation modes."""
    return [
        ModeInfo(
            id="fast",
            label="Fast",
            description="Multi-agent deck grounded in Notion"
        ),
        ModeInfo(
            id="max",
            label="Max",
            description="Fast + clarifying questions for deeper context"
        )
    ]


@app.post("/max/questions")
async def get_max_questions(request: MaxQuestionsRequest):
    """
    Get clarifying questions for max mode.
    First validates the query, then generates questions.

    Returns:
        - If query is invalid: {"valid": false, "user_message": "..."}
        - If successful: {"valid": true, "questions": [...]}
    """
    logger.info(f"Max questions endpoint called | query_length={len(request.query)}")

    # Validate query first
    validation_state = {"query": request.query}
    validation_result = intent_detector(validation_state)

    if not validation_result.get("valid_query"):
        logger.info(f"Query rejected in max questions | message={validation_result.get('user_message')}")
        return {
            "valid": False,
            "user_message": validation_result.get("user_message", "Query was rejected")
        }

    # Generate clarifying questions
    questions_result = research_agent(request.query)

    logger.info(f"Generated {len(questions_result.questions)} clarifying questions")

    return {
        "valid": True,
        "questions": questions_result.questions
    }


@app.post("/generate")
async def generate(request: GenerateRequest):
    """
    Generate a presentation deck.

    Returns:
        - If query is rejected: {"valid": false, "user_message": "..."}
        - If successful: {"valid": true, "deck_id": "...", "deck_path": "...", "slide_count": 10}
    """
    logger.info(f"Generate endpoint called | mode={request.mode} | query_length={len(request.query)}")

    # Call mode handler
    result = generate_deck(request.mode, request.query, request.answers)

    # Check if query was rejected
    if result.get("valid_query") is False:
        logger.info(f"Query rejected | message={result.get('user_message', 'N/A')}")
        return {
            "valid": False,
            "user_message": result.get("user_message", "Query was rejected")
        }

    # Success - extract deck info
    deck = result.get("deck")
    slide_count = len(deck.slides) if deck else 10  # Default to 10 if deck object not available

    logger.info(f"Deck generated successfully | deck_id={result.get('deck_id')} | slides={slide_count}")

    return {
        "valid": True,
        "deck_id": result.get("deck_id"),
        "deck_path": result.get("deck_path"),
        "slide_count": slide_count
    }


@app.get("/deck/{deck_id}")
async def get_deck(deck_id: str):
    """
    Retrieve the generated deck markdown content.

    Returns:
        {"deck_id": "...", "content": "...", "path": "..."}
    """
    logger.info(f"Fetching deck: {deck_id}")

    # Deck is always written to slidev/slides.md
    deck_path = Path("slidev/slides.md")

    if not deck_path.exists():
        logger.error(f"Deck file not found: {deck_path}")
        return JSONResponse(
            status_code=404,
            content={"error": "Deck not found", "detail": f"No deck at {deck_path}"}
        )

    content = deck_path.read_text(encoding='utf-8')

    return {
        "deck_id": deck_id,
        "content": content,
        "path": str(deck_path)
    }


@app.post("/build/{deck_id}")
async def build_deck(deck_id: str):
    """
    Build the Slidev presentation into a static site.

    Runs `npx slidev build` which takes ~20 seconds.

    Returns:
        {"built": true, "url": "/slides/"}
    """
    logger.info(f"Building Slidev deck: {deck_id}")

    try:
        # Get Slidev directory from env
        slidev_dir = Path(os.getenv("SLIDEV_DIR", "./slidev"))

        if not slidev_dir.exists():
            raise AppError(
                f"Slidev directory not found: {slidev_dir}",
                component="build_deck"
            )

        slides_md = slidev_dir / "slides.md"
        if not slides_md.exists():
            raise AppError(
                f"No slides.md found at {slides_md}. Generate a deck first.",
                component="build_deck"
            )

        # Build command: npx slidev build slides.md --base /slides/ --out dist
        # Use shutil.which to resolve npx path (handles npx.cmd on Windows)
        npx_path = shutil.which("npx")
        if not npx_path:
            raise AppError(
                "npx not found on PATH. Ensure Node.js and npm are installed.",
                component="build_deck"
            )

        logger.info(f"Running Slidev build in {slidev_dir} using npx at {npx_path}")

        result = subprocess.run(
            [npx_path, "slidev", "build", "slides.md", "--base", "/slides/", "--out", "dist"],
            cwd=str(slidev_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,  # 60 second timeout
            shell=False
        )

        # Log both stdout and stderr regardless of success/failure
        if result.stdout:
            logger.info(f"Slidev build stdout:\n{result.stdout}")
        if result.stderr:
            logger.info(f"Slidev build stderr:\n{result.stderr}")

        if result.returncode != 0:
            logger.error(f"Slidev build failed with code {result.returncode}")
            error_output = result.stderr or result.stdout or "No output captured"
            raise AppError(
                f"Slidev build failed (exit code {result.returncode}): {error_output}",
                component="build_deck"
            )

        logger.info(f"Slidev build completed successfully")

        # Verify dist directory was created
        dist_dir = slidev_dir / "dist"
        if not dist_dir.exists():
            raise AppError(
                "Build completed but dist directory not found",
                component="build_deck"
            )

        return {
            "built": True,
            "url": "/slides/",
            "deck_id": deck_id
        }

    except subprocess.TimeoutExpired:
        logger.exception("Slidev build timed out")
        raise AppError(
            "Slidev build timed out after 60 seconds",
            component="build_deck"
        )
    except AppError:
        raise
    except Exception as e:
        logger.exception(f"Failed to build Slidev deck: {e}")
        raise AppError(
            f"Failed to build Slidev deck: {str(e)}",
            component="build_deck"
        )


# Startup message
@app.on_event("startup")
async def startup_event():
    logger.info("PPT Generator API starting up")

    # Ensure Slidev dist directory exists and mount it
    slidev_dir = Path(os.getenv("SLIDEV_DIR", "./slidev"))
    dist_dir = slidev_dir / "dist"

    # Create dist directory if it doesn't exist
    if not dist_dir.exists():
        logger.info(f"Creating dist directory at {dist_dir}")
        dist_dir.mkdir(parents=True, exist_ok=True)

    # Mount static files for built Slidev presentations
    logger.info(f"Mounting Slidev static files from {dist_dir} at /slides")
    try:
        app.mount("/slides", StaticFiles(directory=str(dist_dir), html=True), name="slides")
        logger.info("Successfully mounted /slides static route")
    except Exception as e:
        logger.error(f"Failed to mount static files: {e}")

    logger.info("FastAPI app initialized successfully")
