# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

from langgraph.graph import StateGraph, START, END
from ai.src.state import GraphState
from ai.agents.intent_detector import intent_detector
from ai.agents.manager import manager
from ai.agents.context_retriever import context_retriever
from ai.agents.web_search import web_search
from ai.agents.ppt_generator import ppt_generator
from ai.utils.logger import get_logger
from ai.utils import AppError

logger = get_logger(__name__)


def route_after_intent(state: GraphState) -> str:
    """Route after intent detection based on query validity."""
    if state.get("valid_query") is False:
        return "reject"
    return "continue"


def route_after_context(state: GraphState) -> str:
    """Route after context retrieval based on sufficiency."""
    sufficiency = state.get("sufficiency")
    if sufficiency:
        # Handle both dict and object access patterns
        sufficient = sufficiency.get("sufficient") if isinstance(sufficiency, dict) else getattr(sufficiency, "sufficient", None)
        if sufficient is True:
            return "generate"
    return "search"


def build_fast_graph() -> StateGraph:
    """Build and compile the LangGraph StateGraph for fast mode."""
    logger.info("Building fast mode graph")

    # Create graph
    graph = StateGraph(GraphState)

    # Add nodes
    graph.add_node("intent_detector", intent_detector)
    graph.add_node("manager", manager)
    graph.add_node("context_retriever", context_retriever)
    graph.add_node("web_search", web_search)
    graph.add_node("ppt_generator", ppt_generator)

    # Add edges
    graph.add_edge(START, "intent_detector")

    # Conditional after intent_detector
    graph.add_conditional_edges(
        "intent_detector",
        route_after_intent,
        {
            "reject": END,
            "continue": "manager"
        }
    )

    # Linear edge from manager to context_retriever
    graph.add_edge("manager", "context_retriever")

    # Conditional after context_retriever
    graph.add_conditional_edges(
        "context_retriever",
        route_after_context,
        {
            "generate": "ppt_generator",
            "search": "web_search"
        }
    )

    # Linear edge from web_search to ppt_generator
    graph.add_edge("web_search", "ppt_generator")

    # Final edge to END
    graph.add_edge("ppt_generator", END)

    # Compile and return
    compiled = graph.compile()
    logger.info("Fast mode graph compiled successfully")
    return compiled


def run_fast(query: str) -> dict:
    """
    Run the fast mode graph with the given query.

    Args:
        query: User query string

    Returns:
        Final state dict with deck_id, deck_path, or user_message if rejected

    Raises:
        AppError: If graph execution fails
    """
    logger.info(f"Starting fast mode graph | query_length={len(query)}")

    try:
        # Build graph
        graph = build_fast_graph()

        # Initial state
        initial_state = {
            "mode": "fast",
            "query": query
        }

        # Invoke graph
        final_state = graph.invoke(initial_state)

        # Log completion
        if final_state.get("valid_query") is False:
            logger.info(f"Fast mode completed with rejection | message={final_state.get('user_message', 'N/A')}")
        else:
            logger.info(f"Fast mode completed successfully | deck_id={final_state.get('deck_id', 'N/A')} | deck_path={final_state.get('deck_path', 'N/A')}")

        return final_state

    except Exception as e:
        logger.exception(f"Fast mode graph execution failed | query={query[:100]}")
        raise AppError(
            message=f"Failed to execute presentation generation pipeline: {str(e)}",
            component="graph.run_fast"
        )


def run_max(query: str, answers: dict) -> dict:
    """
    Run the max mode graph with the given query and user answers to clarifying questions.
    Uses the SAME fast mode pipeline but merges answers into state for context.

    Args:
        query: User query string
        answers: Dict of {question: answer} pairs from clarifying questions

    Returns:
        Final state dict with deck_id, deck_path, or user_message if rejected

    Raises:
        AppError: If graph execution fails
    """
    logger.info(f"Starting max mode graph | query_length={len(query)} | answers_count={len(answers)}")

    try:
        # Build same graph as fast mode
        graph = build_fast_graph()

        # Initial state with answers merged
        initial_state = {
            "mode": "max",
            "query": query,
            "answers": answers  # Agents will use this for additional context
        }

        # Invoke graph
        final_state = graph.invoke(initial_state)

        # Log completion
        if final_state.get("valid_query") is False:
            logger.info(f"Max mode completed with rejection | message={final_state.get('user_message', 'N/A')}")
        else:
            logger.info(
                f"Max mode completed successfully | deck_id={final_state.get('deck_id', 'N/A')} | "
                f"deck_path={final_state.get('deck_path', 'N/A')}"
            )

        return final_state

    except Exception as e:
        logger.exception(f"Max mode graph execution failed | query={query[:100]}")
        raise AppError(
            message=f"Failed to execute max mode pipeline: {str(e)}",
            component="graph.run_max"
        )


if __name__ == "__main__":
    print("=== Test 1: Fast mode - Valid enterprise query ===")
    try:
        result1 = run_fast("Meridian Aurora Nexus enterprise AI platform")
        if result1.get("valid_query") is False:
            print(f"Rejected: {result1.get('user_message')}")
        else:
            print(f"Success!")
            print(f"  deck_id: {result1.get('deck_id')}")
            print(f"  deck_path: {result1.get('deck_path')}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== Test 2: Fast mode - Invalid general knowledge query ===")
    try:
        result2 = run_fast("what is the capital of India")
        if result2.get("valid_query") is False:
            print(f"Rejected: {result2.get('user_message')}")
        else:
            print(f"Success!")
            print(f"  deck_id: {result2.get('deck_id')}")
            print(f"  deck_path: {result2.get('deck_path')}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== Test 3: Max mode - With clarifying answers ===")
    try:
        answers = {
            "audience": "executives",
            "focus": "ROI and roadmap"
        }
        result3 = run_max("Meridian Aurora Nexus enterprise AI platform", answers)
        if result3.get("valid_query") is False:
            print(f"Rejected: {result3.get('user_message')}")
        else:
            print(f"Success!")
            print(f"  deck_id: {result3.get('deck_id')}")
            print(f"  deck_path: {result3.get('deck_path')}")
            print(f"  answers used: {answers}")
    except Exception as e:
        print(f"Error: {e}")
