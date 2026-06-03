"""
Image generator agent - generates background images for pro/max modes.
Creates two images: cover image and shared content background.
"""
from ai.src.state import GraphState
from ai.tools.image_gen import generate_image
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def image_generator(state: GraphState) -> dict:
    """
    Generate background images for the presentation.

    Generates exactly TWO images:
    1. Cover image - derived from deck title
    2. Background image - shared subtle background for content slides

    Args:
        state: Current graph state with "outline" field

    Returns:
        Partial state update with "cover_image" and "bg_image" (relative paths from slidev/public/)

    Raises:
        AppError: If image generation fails
    """
    outline = state.get("outline")
    if not outline:
        raise AppError("No outline found in state", component="image_generator")

    logger.info(f"Image generator: creating images for '{outline.title}'")

    try:
        # Generate cover image from deck title
        cover_prompt = f"{outline.title}, professional, abstract"
        logger.info(f"Generating cover image: {cover_prompt}")
        cover_image_path = generate_image(cover_prompt)

        if not cover_image_path:
            logger.warning("Cover image generation returned None")
            cover_image_path = None

        # Generate shared background for content slides (very subtle)
        bg_prompt = "abstract technology texture, minimal, professional"
        logger.info(f"Generating background image: {bg_prompt}")
        bg_image_path = generate_image(bg_prompt)

        if not bg_image_path:
            logger.warning("Background image generation returned None")
            bg_image_path = None

        logger.info(
            f"Image generation complete | cover={cover_image_path} | bg={bg_image_path}"
        )

        return {
            "cover_image": cover_image_path,
            "bg_image": bg_image_path
        }

    except Exception as e:
        logger.exception("Image generator failed")
        raise AppError(
            f"Failed to generate images: {str(e)}",
            component="image_generator"
        )


# Test block
if __name__ == "__main__":
    from ai import config_env  # Load .env first
    from ai.agents.manager import manager

    print("=" * 80)
    print("Testing Image Generator Agent")
    print("=" * 80)

    # Step 1: Generate outline using manager
    query = "Meridian's Aurora Nexus enterprise AI platform"
    print(f"\n1. Generating outline for: '{query}'")
    print("-" * 80)

    manager_state = {"query": query}
    manager_result = manager(manager_state)
    outline = manager_result["outline"]

    print(f"Outline Title: {outline.title}")

    # Step 2: Run image generator
    print(f"\n2. Generating cover and background images...")
    print("-" * 80)

    generator_state = {"outline": outline}
    result = image_generator(generator_state)

    # Step 3: Display results
    print(f"\n" + "=" * 80)
    print("IMAGE GENERATION COMPLETE")
    print("=" * 80)
    print(f"Cover image: {result.get('cover_image') or 'None'}")
    print(f"Background image: {result.get('bg_image') or 'None'}")

    if result.get('cover_image') and result.get('bg_image'):
        print("\n✓ Both images generated successfully")
        print(f"\nOpen these images to verify they are light and suitable for backgrounds:")
        print(f"  slidev/{result['cover_image']}")
        print(f"  slidev/{result['bg_image']}")
    else:
        print("\n⚠ Some images failed to generate")

    print("\n" + "=" * 80)
    print("Image Generator Test Complete")
    print("=" * 80)
