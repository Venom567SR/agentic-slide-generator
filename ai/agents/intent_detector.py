"""
Intent detector agent - validates user queries.
Input guardrail that runs first in the pipeline.
"""
from ai.src.state import GraphState
from ai.src.schemas import ValidationResult
from ai.llm import get_llm
from ai.utils.prompt_loader import load_prompt
from ai.utils import AppError
from ai.utils.logger import get_logger
import yaml
from pathlib import Path

logger = get_logger(__name__)


def intent_detector(state: GraphState) -> dict:
    """
    Validate user query - reject if harmful or not a presentation request.

    Args:
        state: Current graph state with "query" field

    Returns:
        Partial state update with "valid_query" and "user_message"

    Raises:
        AppError: If validation fails due to system error
    """
    query = state.get("query", "")
    logger.info(f"Intent detector: validating query (length={len(query)})")

    try:
        # Load config to get fast model name
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)
        fast_model = config["models"]["fast"]

        # Load system prompt
        system_prompt = load_prompt("intent_detector")

        # Get LLM with structured output
        llm = get_llm(fast_model, temperature=0.3)
        structured_llm = llm.with_structured_output(ValidationResult)

        # Create messages
        messages = [
            ("system", system_prompt),
            ("human", query)
        ]

        # Invoke LLM
        result: ValidationResult = structured_llm.invoke(messages)

        logger.info(
            f"Intent detector result: valid_query={result.valid_query}, "
            f"reason='{result.reason}'"
        )

        if not result.valid_query:
            logger.info(f"Query rejected: {result.user_message}")

        return {
            "valid_query": result.valid_query,
            "user_message": result.user_message
        }

    except Exception as e:
        logger.exception("Intent detector failed")
        raise AppError(
            f"Failed to validate query: {str(e)}",
            component="intent_detector"
        )


# Test block
if __name__ == "__main__":
    from ai import config_env  # Load .env first

    print("=" * 80)
    print("Testing Intent Detector Agent")
    print("=" * 80)

    # Test case 1: Valid presentation request
    print("\n[Test 1] Query: 'AI agents in enterprise'")
    print("-" * 80)
    state1 = {"query": "AI agents in enterprise"}
    result1 = intent_detector(state1)
    print(f"Result: {result1}")
    print(f"Expected: valid_query=True")
    print(f"✓ PASS" if result1["valid_query"] else "✗ FAIL")

    # Test case 2: Generic question (should reject)
    print("\n[Test 2] Query: 'What is the capital of India?'")
    print("-" * 80)
    state2 = {"query": "What is the capital of India?"}
    result2 = intent_detector(state2)
    print(f"Result: {result2}")
    print(f"Expected: valid_query=False")
    print(f"User message: {result2.get('user_message', '')}")
    print(f"✓ PASS" if not result2["valid_query"] else "✗ FAIL")

    print("\n" + "=" * 80)
    print("Intent Detector Tests Complete")
    print("=" * 80)
