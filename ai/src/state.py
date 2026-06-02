"""
Graph state definition for the LangGraph pipeline.
Single shared state dictionary passed through all nodes.
"""
from typing import TypedDict
from ai.src.schemas import Outline, SufficiencyJudgment, DeckSpec


class GraphState(TypedDict, total=False):
    """
    State for the LangGraph pipeline.

    total=False means all fields are optional - nodes return partial updates.
    """
    # Input
    mode: str
    query: str
    mode_config: dict

    # Intent validation (intent_detector)
    valid_query: bool
    user_message: str

    # Planning (manager)
    outline: Outline

    # Context retrieval (context_retriever)
    notion_context: str
    sufficiency: SufficiencyJudgment

    # Web search (web_search)
    web_context: str

    # Max mode (research)
    clarifying_questions: list[str]
    answers: dict

    # Deck generation (ppt_generator)
    deck: DeckSpec

    # Output
    deck_id: str
    deck_path: str
