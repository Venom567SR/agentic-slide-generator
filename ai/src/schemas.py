"""
Pydantic schemas for the LangGraph pipeline.
All structured outputs from LLM calls use these models.
"""
from pydantic import BaseModel, field_validator
from ai.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationResult(BaseModel):
    """Result from intent_detector agent - validates user query."""
    valid_query: bool
    reason: str
    user_message: str  # shown to user when valid_query is False


class Outline(BaseModel):
    """Deck outline from manager agent."""
    title: str
    slide_topics: list[str]  # length == slide_count (10)

    @field_validator("slide_topics")
    @classmethod
    def validate_slide_count(cls, v: list[str]) -> list[str]:
        """
        Ensure exactly 10 slide topics.
        Accepts 8-12 topics and adjusts to 10: truncates if too many, pads if too few.
        """
        count = len(v)
        target = 10

        # Accept 8-12, adjust to target
        if count < 8 or count > 12:
            raise ValueError(
                f"slide_topics must have 8-12 items for adjustment, got {count}. "
                "This indicates a serious prompt/model issue."
            )

        if count < target:
            # Pad with generic topics
            padding_needed = target - count
            logger.warning(f"Outline has {count} topics, padding with {padding_needed} to reach {target}")
            for i in range(padding_needed):
                v.append(f"Additional Topic {i + 1}")
        elif count > target:
            # Truncate to target
            logger.warning(f"Outline has {count} topics, truncating to {target}")
            v = v[:target]

        return v


class SufficiencyJudgment(BaseModel):
    """Result from context_retriever - judges if Notion context is sufficient."""
    sufficient: bool
    missing: list[str]  # topics not covered by Notion context


class SlideSpec(BaseModel):
    """Specification for a single slide."""
    heading: str
    bullets: list[str]
    image_prompt: str | None = None  # populated only in pro/max
    image_path: str | None = None    # filled after image generation


class DeckSpec(BaseModel):
    """Complete deck specification from ppt_generator agent."""
    title: str
    slides: list[SlideSpec]


class ClarifyingQuestions(BaseModel):
    """Clarifying questions from research agent (max mode only)."""
    questions: list[str]
