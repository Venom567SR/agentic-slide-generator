"""
LLM factory - single entry point for all model interactions.
Backend switch between Vertex AI and Gemini API based on USE_VERTEX env var.
"""
# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def get_llm(model_name: str, temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    """
    Get a configured LLM instance.

    Args:
        model_name: Model name (e.g., "gemini-2.5-flash", "gemini-2.5-pro")
        temperature: Sampling temperature (0.0-1.0)

    Returns:
        Configured ChatGoogleGenerativeAI instance

    Raises:
        ValueError: If required environment variables are missing
    """
    use_vertex = os.getenv("USE_VERTEX", "false").lower() == "true"

    logger.info(f"Initializing LLM: model={model_name}, temperature={temperature}, use_vertex={use_vertex}")

    if use_vertex:
        # Vertex AI mode - requires GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION")

        if not project or not location:
            raise ValueError(
                "USE_VERTEX=true requires GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION "
                "environment variables to be set"
            )

        logger.info(f"Using Vertex AI: project={project}, location={location}")

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=None,  # Will use ADC (Application Default Credentials)
            vertexai=True
        )
    else:
        # Gemini API mode - requires GEMINI_API_KEY
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "USE_VERTEX=false requires GEMINI_API_KEY environment variable to be set"
            )

        logger.info("Using Gemini API")

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=api_key
        )
