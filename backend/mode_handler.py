# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

from ai.src.graph import run_fast, run_max
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def generate_deck(mode: str, query: str, answers: dict = None) -> dict:
    """
    Generate a presentation deck using the specified mode.

    Args:
        mode: Generation mode ("fast" or "max")
        query: User query describing the presentation topic
        answers: Optional dict of answers to clarifying questions (required for max mode)

    Returns:
        Final state dict from the graph execution

    Raises:
        AppError: If mode is unknown or generation fails
    """
    logger.info(f"Mode handler: generating deck | mode={mode} | query_length={len(query)}")

    if mode == "fast":
        return run_fast(query)
    elif mode == "max":
        if not answers:
            raise AppError(
                message="Max mode requires 'answers' to clarifying questions",
                component="mode_handler"
            )
        return run_max(query, answers)
    else:
        raise AppError(
            message=f"Unknown mode '{mode}'. Valid modes: fast, max",
            component="mode_handler"
        )
