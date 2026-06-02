# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

from ai.src.graph import run_fast
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def generate_deck(mode: str, query: str) -> dict:
    """
    Generate a presentation deck using the specified mode.

    Args:
        mode: Generation mode ("fast", "pro", or "max")
        query: User query describing the presentation topic

    Returns:
        Final state dict from the graph execution

    Raises:
        AppError: If mode is unknown or generation fails
    """
    logger.info(f"Mode handler: generating deck | mode={mode} | query_length={len(query)}")

    if mode == "fast":
        return run_fast(query)
    elif mode in ("pro", "max"):
        raise AppError(
            message=f"Mode '{mode}' not yet implemented",
            component="mode_handler"
        )
    else:
        raise AppError(
            message=f"Unknown mode '{mode}'. Valid modes: fast, pro, max",
            component="mode_handler"
        )
