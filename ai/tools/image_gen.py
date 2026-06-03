"""
Image generation tool using Gemini 2.5 Flash Image model.
Generates light-background images suitable for slide backgrounds.
Implements exact-match caching based on prompt hash.
"""
# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

import os
import hashlib
from pathlib import Path
from google import genai
from google.genai import types
from ai.utils import AppError
from ai.utils.logger import get_logger

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = get_logger(__name__)

# Image model name
IMAGE_MODEL = "gemini-2.5-flash-image"

# Style wrapper for light backgrounds with 16:9 aspect ratio
# NOTE: The robust guarantee for 16:9 display is on the CSS side (background-size: cover / object-fit: cover)
# so even if returned pixels aren't exactly 1920x1080, the slide background will fill correctly.
# This prompt instruction steers the model toward wide landscape composition.
LIGHT_BACKGROUND_STYLE = (
    "Very light, pale, desaturated, soft minimal abstract background. "
    "Lots of white/light space, low contrast, no text, suitable as a faint slide background "
    "behind dark text. Pastel colors only. "
    "Wide 16:9 landscape aspect ratio, high resolution, full-bleed composition suitable for a 1920x1080 slide background. "
)


def _get_cache_key(prompt: str) -> str:
    """
    Generate cache key from prompt using SHA256 hash.

    Args:
        prompt: The image generation prompt

    Returns:
        First 16 characters of SHA256 hex digest
    """
    return hashlib.sha256(prompt.encode('utf-8')).hexdigest()[:16]


def _get_genai_client() -> genai.Client:
    """
    Create a google.genai Client based on USE_VERTEX env var.
    Reuses the same auth pattern as get_llm.

    Returns:
        Configured genai.Client instance
    """
    use_vertex = os.getenv("USE_VERTEX", "false").lower() == "true"

    if use_vertex:
        # Vertex AI mode - use project and location
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION")

        if not project or not location:
            raise AppError(
                "USE_VERTEX=true requires GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION",
                component="image_gen"
            )

        logger.info(f"Creating genai Client for Vertex AI: project={project}, location={location}")
        return genai.Client(
            vertexai=True,
            project=project,
            location=location
        )
    else:
        # Gemini API mode - use API key
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise AppError(
                "USE_VERTEX=false requires GEMINI_API_KEY environment variable",
                component="image_gen"
            )

        logger.info("Creating genai Client for Gemini API")
        return genai.Client(api_key=api_key)


def generate_image(prompt: str) -> str:
    """
    Generate a light-background image suitable for slides.

    Uses exact-match caching: if an image with the same prompt hash exists,
    returns the cached path without generating a new image.

    Args:
        prompt: Subject/description for the image (style wrapper is auto-prepended)

    Returns:
        Relative path to the generated PNG (e.g., "public/images/abc123def456.png")
        Returns None if generation fails and no image is produced

    Raises:
        AppError: If generation fails due to system error
    """
    logger.info(f"Image generation requested | prompt_length={len(prompt)}")

    try:
        # Get images directory from env
        slidev_dir = Path(os.getenv("SLIDEV_DIR", "./slidev"))
        images_dir = slidev_dir / "public" / "images"

        # Create images directory if it doesn't exist
        images_dir.mkdir(parents=True, exist_ok=True)

        # Prepend light-background style wrapper
        full_prompt = LIGHT_BACKGROUND_STYLE + prompt
        logger.info(f"Full prompt (with style): {full_prompt}")

        # Check cache
        cache_key = _get_cache_key(full_prompt)
        cache_path = images_dir / f"{cache_key}.png"

        if cache_path.exists():
            logger.info(f"Cache HIT | key={cache_key} | path={cache_path}")
            # Return relative path from slidev directory
            relative_path = cache_path.relative_to(slidev_dir)
            return str(relative_path).replace('\\', '/')  # Use forward slashes for web

        logger.info(f"Cache MISS | key={cache_key} | generating new image")

        # Create genai client
        client = _get_genai_client()

        # Generate image with 16:9 aspect ratio via ImageConfig
        # Attempt to use official aspect_ratio config; fall back to prompt-only if unsupported
        logger.info(f"Calling {IMAGE_MODEL} to generate image")

        # Try with ImageConfig first
        response = None
        try:
            config = types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9")
            )
            logger.info("Attempting generation with ImageConfig(aspect_ratio='16:9')")
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[full_prompt],
                config=config
            )
            logger.info("Successfully generated with ImageConfig")
        except (AttributeError, TypeError, ValueError) as e:
            # ImageConfig or aspect_ratio not supported in this SDK version, or model rejected it
            logger.warning(f"ImageConfig aspect_ratio not supported or failed: {e}")
            logger.info("Retrying without ImageConfig (relying on prompt-based aspect ratio instruction)")
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[full_prompt]
            )
        except Exception as e:
            # Other API errors - retry without config
            logger.warning(f"Generation with ImageConfig failed: {e}")
            logger.info("Retrying without ImageConfig")
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[full_prompt]
            )

        # Extract image from response
        if not response.candidates or not response.candidates[0].content.parts:
            logger.warning("No candidates or parts in response - image generation may have failed")
            return None

        # Find the inline image part
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                image_bytes = part.inline_data.data
                break

        if not image_bytes:
            logger.warning("No inline image data in response parts")
            return None

        # Save PNG bytes
        cache_path.write_bytes(image_bytes)

        logger.info(f"Image generated and cached | key={cache_key} | size={len(image_bytes)} bytes | path={cache_path}")

        # Return relative path from slidev directory
        relative_path = cache_path.relative_to(slidev_dir)
        return str(relative_path).replace('\\', '/')  # Use forward slashes for web

    except AppError:
        raise
    except Exception as e:
        logger.exception(f"Image generation failed for prompt: {prompt[:100]}")
        raise AppError(
            f"Failed to generate image: {str(e)}",
            component="image_gen"
        )


if __name__ == "__main__":
    print("=" * 80)
    print("Testing Image Generation Tool")
    print("=" * 80)

    # Helper to check image dimensions
    def check_dimensions(rel_path):
        if not PIL_AVAILABLE:
            print("  (PIL not available - cannot check dimensions)")
            return
        if not rel_path:
            return
        slidev_dir = Path(os.getenv("SLIDEV_DIR", "./slidev"))
        full_path = slidev_dir / rel_path
        if full_path.exists():
            try:
                with Image.open(full_path) as img:
                    width, height = img.size
                    aspect = width / height if height > 0 else 0
                    print(f"  Dimensions: {width}x{height} (aspect ratio: {aspect:.2f}, target 16:9 = 1.78)")
                    if 1.7 <= aspect <= 1.85:
                        print(f"  ✓ Aspect ratio is approximately 16:9")
                    else:
                        print(f"  ⚠ Aspect ratio differs from 16:9")
            except Exception as e:
                print(f"  Error reading dimensions: {e}")

    # Test 1: Generate cover image
    print("\n[Test 1] Generating cover image: 'enterprise AI platform, futuristic network'")
    print("-" * 80)
    cover_prompt = "enterprise AI platform, futuristic network"
    cover_path = generate_image(cover_prompt)
    if cover_path:
        print(f"✓ Cover image generated: {cover_path}")
        check_dimensions(cover_path)
    else:
        print("✗ Cover image generation failed (returned None)")

    # Test 2: Same prompt again (should hit cache)
    print("\n[Test 2] Generating SAME cover image again (should hit cache)")
    print("-" * 80)
    cover_path_2 = generate_image(cover_prompt)
    if cover_path_2:
        print(f"✓ Cover image path: {cover_path_2}")
        if cover_path == cover_path_2:
            print("✓ Cache HIT confirmed - same path returned")
        else:
            print("✗ Cache MISS - different path returned (unexpected)")
    else:
        print("✗ Cover image generation failed (returned None)")

    # Test 3: Generate shared background image
    print("\n[Test 3] Generating shared background: 'abstract technology texture'")
    print("-" * 80)
    bg_prompt = "abstract technology texture"
    bg_path = generate_image(bg_prompt)
    if bg_path:
        print(f"✓ Background image generated: {bg_path}")
        check_dimensions(bg_path)
    else:
        print("✗ Background image generation failed (returned None)")

    # Summary
    print("\n" + "=" * 80)
    print("Image Generation Tests Complete")
    print("=" * 80)
    if cover_path and bg_path:
        print(f"\nGenerated images:")
        print(f"  1. Cover: slidev/{cover_path}")
        print(f"  2. Background: slidev/{bg_path}")
        print("\nOpen these PNG files to verify:")
        print("  - Light/pale colors suitable for backgrounds")
        print("  - Wide 16:9 landscape aspect ratio")
        if PIL_AVAILABLE:
            print("\nActual dimensions shown above.")
        else:
            print("\nNote: Install Pillow to see actual dimensions (pip install Pillow)")
    else:
        print("\n⚠ Some images failed to generate. Check logs for details.")
