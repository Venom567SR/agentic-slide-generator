"""
Manager agent - plans the deck outline.
Creates title and slide topics from the query.
"""
from ai.src.state import GraphState
from ai.src.schemas import Outline
from ai.llm import get_llm
from ai.utils.prompt_loader import load_prompt
from ai.utils import AppError
from ai.utils.logger import get_logger
import yaml
from pathlib import Path

logger = get_logger(__name__)


def manager(state: GraphState) -> dict:
    """
    Plan the deck outline - generate title and exactly 10 slide topics.

    Args:
        state: Current graph state with "query" field

    Returns:
        Partial state update with "outline" (Outline object)

    Raises:
        AppError: If planning fails due to system error
    """
    query = state.get("query", "")
    logger.info(f"Manager: planning deck for query (length={len(query)})")

    try:
        # Load config to get fast model name
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        fast_model = config["models"]["fast"]

        # Load system prompt
        system_prompt = load_prompt("manager")

        # Get LLM with structured output
        llm = get_llm(fast_model, temperature=0.3)
        structured_llm = llm.with_structured_output(Outline)

        # Build human message with answers if present (max mode)
        human_message = f"Create a presentation outline for: {query}"
        answers = state.get("answers")
        if answers:
            logger.info(f"Manager: incorporating {len(answers)} user answers for tailoring")
            answers_text = "\n".join([f"- {k}: {v}" for k, v in answers.items()])
            human_message += f"\n\nAdditional user requirements:\n{answers_text}"

        # Create messages
        messages = [
            ("system", system_prompt),
            ("human", human_message)
        ]

        # Invoke LLM
        outline: Outline = structured_llm.invoke(messages)

        logger.info(
            f"Manager produced outline: title='{outline.title}', "
            f"slide_topics_count={len(outline.slide_topics)}"
        )

        return {
            "outline": outline
        }

    except Exception as e:
        logger.exception("Manager failed")
        raise AppError(
            f"Failed to plan deck outline: {str(e)}",
            component="manager"
        )


# Test block
if __name__ == "__main__":
    from ai import config_env  # Load .env first

    print("=" * 80)
    print("Testing Manager Agent")
    print("=" * 80)

    # Test case: Meridian's Aurora Nexus enterprise AI platform
    query = "Meridian's Aurora Nexus enterprise AI platform"
    print(f"\nQuery: '{query}'")
    print("-" * 80)

    state = {"query": query}
    result = manager(state)
    outline = result["outline"]

    print(f"\nDeck Title: {outline.title}")
    print(f"\nSlide Topics ({len(outline.slide_topics)}):")
    for i, topic in enumerate(outline.slide_topics, 1):
        print(f"  {i:2d}. {topic}")

    print("\n" + "=" * 80)
    print("Manager Test Complete")
    print("=" * 80)
