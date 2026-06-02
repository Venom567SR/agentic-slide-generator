"""
Web search agent - fills gaps in Notion context using Google Search grounding.
Uses Gemini's built-in grounding capability to search for missing topics.
"""
from ai.src.state import GraphState
from ai.llm import get_llm
from ai.utils.prompt_loader import load_prompt
from ai.utils import AppError
from ai.utils.logger import get_logger
import yaml
from pathlib import Path

logger = get_logger(__name__)


def web_search(state: GraphState) -> dict:
    """
    Search the web for information on topics missing from Notion context.

    Args:
        state: Current graph state with "outline" and "sufficiency" fields

    Returns:
        Partial state update with "web_context" (str)

    Raises:
        AppError: If web search fails
    """
    outline = state.get("outline")
    sufficiency = state.get("sufficiency")

    if not outline or not sufficiency:
        raise AppError(
            "Missing outline or sufficiency in state",
            component="web_search"
        )

    missing_topics = sufficiency.missing
    logger.info(
        f"Web search: searching for {len(missing_topics)} missing topics "
        f"from outline '{outline.title}'"
    )

    if missing_topics:
        logger.info(f"Missing topics: {missing_topics}")

    try:
        # Load config to get pro model name
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        pro_model = config["models"]["pro"]

        # Load system prompt
        system_prompt = load_prompt("web_search")

        # Get LLM with Google Search grounding
        # IMPORTANT: Use bind_tools with plain dict, NOT with_structured_output
        llm = get_llm(pro_model, temperature=0.3)
        grounded_llm = llm.bind_tools([{"google_search": {}}])

        # Build query focusing on missing topics
        if not missing_topics:
            # No missing topics - return empty context
            logger.info("No missing topics, skipping web search")
            return {"web_context": ""}

        topics_list = "\n".join([f"- {topic}" for topic in missing_topics])

        human_message = f"""Deck Title: {outline.title}

Missing Topics (not covered by Notion context):
{topics_list}

Search the web and provide concise, factual information for each of these missing topics. Focus on current, relevant information that can be used to create presentation slides."""

        messages = [
            ("system", system_prompt),
            ("human", human_message)
        ]

        # Invoke grounded LLM
        result = grounded_llm.invoke(messages)

        # Extract text content from response
        web_context = result.content
        logger.info(f"Web search complete: retrieved {len(web_context)} characters of grounded content")

        return {
            "web_context": web_context
        }

    except Exception as e:
        logger.exception("Web search failed")
        raise AppError(
            f"Failed to search web for missing topics: {str(e)}",
            component="web_search"
        )


# Test block
if __name__ == "__main__":
    from ai import config_env  # Load .env first
    from ai.src.schemas import Outline, SufficiencyJudgment

    print("=" * 80)
    print("Testing Web Search Agent")
    print("=" * 80)

    # Create fake state with a missing topic
    print("\nCreating fake state with missing topic: 'latest open-source LLM benchmarks 2026'")
    print("-" * 80)

    fake_outline = Outline(
        title="State of AI in 2026",
        slide_topics=[
            "Introduction to AI Landscape",
            "Enterprise AI Adoption Trends",
            "Latest Open-Source LLM Benchmarks 2026",
            "Commercial LLM Offerings",
            "AI Safety and Alignment",
            "Regulatory Landscape",
            "Industry Use Cases",
            "Cost Analysis",
            "Future Predictions",
            "Getting Started"
        ]
    )

    fake_sufficiency = SufficiencyJudgment(
        sufficient=False,
        missing=["Latest Open-Source LLM Benchmarks 2026"]
    )

    state = {
        "outline": fake_outline,
        "sufficiency": fake_sufficiency
    }

    # Run web search
    print("\nRunning web search...")
    print("-" * 80)

    result = web_search(state)

    # Display results
    print(f"\nWeb Context (Grounded Findings):")
    print("=" * 80)
    print(result["web_context"])
    print("=" * 80)

    print(f"\nWeb Context Length: {len(result['web_context'])} characters")

    print("\n" + "=" * 80)
    print("Web Search Test Complete")
    print("=" * 80)
