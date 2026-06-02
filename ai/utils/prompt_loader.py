"""
Utility to load system prompts from agents_prompts/*.txt files.
"""
from pathlib import Path
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def load_prompt(agent_name: str) -> str:
    """
    Load system prompt for an agent from agents_prompts/{agent_name}.txt.

    Args:
        agent_name: Name of the agent (e.g., "intent_detector", "manager")

    Returns:
        The prompt text as a string

    Raises:
        AppError: If the prompt file cannot be read
    """
    try:
        # Path relative to project root
        prompt_path = Path(__file__).parent.parent / "agents_prompts" / f"{agent_name}.txt"

        if not prompt_path.exists():
            raise AppError(
                f"Prompt file not found: {prompt_path}",
                component="prompt_loader"
            )

        prompt_text = prompt_path.read_text(encoding="utf-8")
        logger.debug(f"Loaded prompt for {agent_name}: {len(prompt_text)} characters")
        return prompt_text

    except AppError:
        raise
    except Exception as e:
        logger.exception(f"Failed to load prompt for {agent_name}")
        raise AppError(
            f"Failed to load prompt for {agent_name}: {str(e)}",
            component="prompt_loader"
        )
