"""
PPT generator agent - writes the complete deck.
Generates structured slide content grounded in provided context.
"""
import uuid
from ai.src.state import GraphState
from ai.src.schemas import DeckSpec
from ai.tools.slides_writer import write_deck
from ai.llm import get_llm
from ai.utils.prompt_loader import load_prompt
from ai.utils import AppError
from ai.utils.logger import get_logger
import yaml
from pathlib import Path

logger = get_logger(__name__)


def ppt_generator(state: GraphState) -> dict:
    """
    Generate the complete presentation deck grounded in context.

    Args:
        state: Current graph state with "outline", "notion_context", and optionally "web_context"

    Returns:
        Partial state update with "deck", "deck_id", and "deck_path"

    Raises:
        AppError: If deck generation fails
    """
    outline = state.get("outline")
    notion_context = state.get("notion_context", "")
    web_context = state.get("web_context", "")

    if not outline:
        raise AppError("No outline found in state", component="ppt_generator")

    logger.info(
        f"PPT generator: creating deck for '{outline.title}' "
        f"(notion_context={len(notion_context)} chars, web_context={len(web_context)} chars)"
    )

    try:
        # Load config to get pro model name
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        pro_model = config["models"]["pro"]

        # Load system prompt
        system_prompt = load_prompt("ppt_generator")

        # Get LLM with structured output
        llm = get_llm(pro_model, temperature=0.3)
        structured_llm = llm.with_structured_output(DeckSpec)

        # Build comprehensive prompt with all context
        topics_list = "\n".join([f"{i+1}. {topic}" for i, topic in enumerate(outline.slide_topics)])

        human_message = f"""Create a 10-slide presentation deck.

Deck Title: {outline.title}

Slide Topics (create one slide for each):
{topics_list}

Notion Context (knowledge base):
{notion_context}
"""

        if web_context:
            human_message += f"""

Web Context (additional research):
{web_context}
"""

        # Add user answers if present (max mode)
        answers = state.get("answers")
        if answers:
            logger.info(f"PPT generator: incorporating {len(answers)} user answers for tailoring")
            answers_text = "\n".join([f"- {k}: {v}" for k, v in answers.items()])
            human_message += f"""

User Requirements (tailor the presentation to these):
{answers_text}
"""

        human_message += """

Generate exactly 10 slides, each with a heading and 3-5 bullet points. Ground all content in the provided context - use specific facts, names, and numbers from the context. Do NOT invent information."""

        messages = [
            ("system", system_prompt),
            ("human", human_message)
        ]

        # Invoke LLM
        deck: DeckSpec = structured_llm.invoke(messages)

        logger.info(
            f"Generated deck: '{deck.title}' with {len(deck.slides)} slides"
        )

        # Generate unique deck ID
        deck_id = uuid.uuid4().hex[:12]  # 12-char hex string

        # Write deck to Slidev markdown
        deck_path = write_deck(deck, deck_id)

        logger.info(f"Deck written: deck_id={deck_id}, path={deck_path}")

        return {
            "deck": deck,
            "deck_id": deck_id,
            "deck_path": deck_path
        }

    except AppError:
        raise
    except Exception as e:
        logger.exception("PPT generator failed")
        raise AppError(
            f"Failed to generate presentation: {str(e)}",
            component="ppt_generator"
        )


# Test block
if __name__ == "__main__":
    from ai import config_env  # Load .env first
    from ai.agents.manager import manager
    from ai.agents.context_retriever import context_retriever

    print("=" * 80)
    print("Testing PPT Generator Agent (Full Pipeline)")
    print("=" * 80)

    # Step 1: Generate outline
    query = "Meridian's Aurora Nexus enterprise AI platform"
    print(f"\n1. Generating outline for: '{query}'")
    print("-" * 80)

    manager_state = {"query": query}
    manager_result = manager(manager_state)
    outline = manager_result["outline"]

    print(f"Outline: {outline.title}")
    print(f"Topics: {len(outline.slide_topics)}")

    # Step 2: Retrieve context
    print(f"\n2. Retrieving Notion context and judging sufficiency...")
    print("-" * 80)

    retriever_state = {"outline": outline}
    retriever_result = context_retriever(retriever_state)

    print(f"Notion context: {len(retriever_result['notion_context'])} characters")
    print(f"Sufficient: {retriever_result['sufficiency'].sufficient}")
    print(f"Missing topics: {len(retriever_result['sufficiency'].missing)}")

    # Step 3: Generate deck
    print(f"\n3. Generating presentation deck...")
    print("-" * 80)

    ppt_state = {
        "outline": outline,
        "notion_context": retriever_result["notion_context"],
        "web_context": ""  # Empty for this test
    }
    ppt_result = ppt_generator(ppt_state)

    # Step 4: Display results
    print(f"\n" + "=" * 80)
    print("DECK GENERATED SUCCESSFULLY")
    print("=" * 80)
    print(f"Deck Title: {ppt_result['deck'].title}")
    print(f"Slide Count: {len(ppt_result['deck'].slides)}")
    print(f"Deck ID: {ppt_result['deck_id']}")
    print(f"Written to: {ppt_result['deck_path']}")
    print("\nSlide Headings:")
    for i, slide in enumerate(ppt_result['deck'].slides, 1):
        print(f"  {i:2d}. {slide.heading}")

    print("\n" + "=" * 80)
    print("PPT Generator Test Complete")
    print("=" * 80)
    print("\nThe deck has been written to slidev/slides.md")
    print("If Slidev is running at http://localhost:3030, you can view it now!")
