"""
Research agent - generates clarifying questions for max mode.
Helps tailor the presentation to audience needs.
"""
from ai.src.schemas import ClarifyingQuestions
from ai.llm import get_llm
from ai.utils.prompt_loader import load_prompt
from ai.utils import AppError
from ai.utils.logger import get_logger
import yaml
from pathlib import Path

logger = get_logger(__name__)


def research_agent(query: str) -> ClarifyingQuestions:
    """
    Generate clarifying questions to better tailor the presentation.

    Args:
        query: User's presentation topic

    Returns:
        ClarifyingQuestions with 2-3 questions

    Raises:
        AppError: If question generation fails
    """
    logger.info(f"Research agent: generating clarifying questions | query_length={len(query)}")

    try:
        # Load config to get fast model name
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        fast_model = config["models"]["fast"]

        # Load system prompt
        system_prompt = load_prompt("research")

        # Get LLM with structured output
        llm = get_llm(fast_model, temperature=0.3)
        structured_llm = llm.with_structured_output(ClarifyingQuestions)

        # Create messages
        messages = [
            ("system", system_prompt),
            ("human", f"Generate clarifying questions for this presentation topic: {query}")
        ]

        # Invoke LLM
        result: ClarifyingQuestions = structured_llm.invoke(messages)

        logger.info(f"Research agent generated {len(result.questions)} questions")
        for i, q in enumerate(result.questions, 1):
            logger.info(f"  Q{i}: {q}")

        return result

    except Exception as e:
        logger.exception("Research agent failed")
        raise AppError(
            f"Failed to generate clarifying questions: {str(e)}",
            component="research_agent"
        )


# Test block
if __name__ == "__main__":
    from ai import config_env  # Load .env first

    print("=" * 80)
    print("Testing Research Agent")
    print("=" * 80)

    # Test: Generate questions for enterprise AI platform
    query = "Meridian's Aurora Nexus enterprise AI platform"
    print(f"\nQuery: '{query}'")
    print("-" * 80)

    result = research_agent(query)

    print(f"\nGenerated {len(result.questions)} clarifying questions:")
    for i, question in enumerate(result.questions, 1):
        print(f"\n{i}. {question}")

    print("\n" + "=" * 80)
    print("Research Agent Test Complete")
    print("=" * 80)
