"""
Context retriever agent - reads Notion context and judges sufficiency.
Determines if Notion content covers the outline topics adequately.
"""
import os
from ai.src.state import GraphState
from ai.src.schemas import SufficiencyJudgment
from ai.tools.notion_reader import read_page_context
from ai.llm import get_llm
from ai.utils.prompt_loader import load_prompt
from ai.utils import AppError
from ai.utils.logger import get_logger
import yaml
from pathlib import Path

logger = get_logger(__name__)


def context_retriever(state: GraphState) -> dict:
    """
    Retrieve Notion context and judge if it sufficiently covers the outline topics.

    Args:
        state: Current graph state with "outline" field

    Returns:
        Partial state update with "notion_context" (str) and "sufficiency" (SufficiencyJudgment)

    Raises:
        AppError: If context retrieval or judgment fails
    """
    outline = state.get("outline")
    if not outline:
        raise AppError("No outline found in state", component="context_retriever")

    logger.info(
        f"Context retriever: reading Notion context for outline '{outline.title}' "
        f"({len(outline.slide_topics)} topics)"
    )

    try:
        # Step 1: Read Notion context
        page_id = os.getenv("PAGE_ID") or os.getenv("NOTION_PAGE_ID")
        if not page_id:
            raise AppError(
                "PAGE_ID or NOTION_PAGE_ID environment variable not set",
                component="context_retriever"
            )

        notion_context = read_page_context(page_id)
        logger.info(f"Retrieved Notion context: {len(notion_context)} characters")

        # Step 2: Judge sufficiency
        # Load config to get pro model name
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        pro_model = config["models"]["pro"]

        # Load system prompt
        system_prompt = load_prompt("context_retriever")

        # Get LLM with structured output
        llm = get_llm(pro_model, temperature=0.3)
        structured_llm = llm.with_structured_output(SufficiencyJudgment)

        # Build prompt with outline topics and Notion context
        topics_list = "\n".join([f"{i+1}. {topic}" for i, topic in enumerate(outline.slide_topics)])

        human_message = f"""Deck Title: {outline.title}

Slide Topics:
{topics_list}

Notion Context:
{notion_context}

Judge whether the Notion context sufficiently covers these topics."""

        messages = [
            ("system", system_prompt),
            ("human", human_message)
        ]

        # Invoke LLM
        sufficiency: SufficiencyJudgment = structured_llm.invoke(messages)

        logger.info(
            f"Sufficiency judgment: sufficient={sufficiency.sufficient}, "
            f"missing_count={len(sufficiency.missing)}"
        )
        if sufficiency.missing:
            logger.info(f"Missing topics: {sufficiency.missing}")

        return {
            "notion_context": notion_context,
            "sufficiency": sufficiency
        }

    except AppError:
        raise
    except Exception as e:
        logger.exception("Context retriever failed")
        raise AppError(
            f"Failed to retrieve and judge context: {str(e)}",
            component="context_retriever"
        )


# Test block
if __name__ == "__main__":
    from ai import config_env  # Load .env first
    from ai.agents.manager import manager

    print("=" * 80)
    print("Testing Context Retriever Agent")
    print("=" * 80)

    # Step 1: Generate outline using manager
    query = "Meridian's Aurora Nexus enterprise AI platform"
    print(f"\n1. Generating outline for: '{query}'")
    print("-" * 80)

    manager_state = {"query": query}
    manager_result = manager(manager_state)
    outline = manager_result["outline"]

    print(f"Outline Title: {outline.title}")
    print(f"Topics: {len(outline.slide_topics)}")

    # Step 2: Run context retriever
    print(f"\n2. Retrieving Notion context and judging sufficiency...")
    print("-" * 80)

    retriever_state = {"outline": outline}
    result = context_retriever(retriever_state)

    # Step 3: Display results
    print(f"\nNotion Context Length: {len(result['notion_context'])} characters")
    print(f"\nSufficiency Judgment:")
    print(f"  Sufficient: {result['sufficiency'].sufficient}")
    print(f"  Missing Topics ({len(result['sufficiency'].missing)}):")
    if result['sufficiency'].missing:
        for topic in result['sufficiency'].missing:
            print(f"    - {topic}")
    else:
        print("    (none - all topics covered)")

    print("\n" + "=" * 80)
    print("Context Retriever Test Complete")
    print("=" * 80)
