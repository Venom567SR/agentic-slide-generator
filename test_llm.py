"""
Test script to verify LLM connection works.
Phase 0 gate: LLM must respond successfully.
"""
# Load .env first
from ai import config_env

import os
from ai.llm import get_llm
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def test_llm():
    """Test that LLM connection works with a simple invoke."""
    try:
        print("=" * 60)
        print("Testing LLM Connection")
        print("=" * 60)

        # Read configuration
        use_vertex = os.getenv("USE_VERTEX", "false").lower() == "true"
        print(f"\nMode: {'Vertex AI' if use_vertex else 'Gemini API'}")

        # Test with gemini-2.5-flash (fast model)
        print("\nInitializing LLM (gemini-2.5-flash)...")
        llm = get_llm("gemini-2.5-flash", temperature=0.3)

        print("Sending test message: 'Hi, respond with just the word WORKING'")
        response = llm.invoke("Hi, respond with just the word WORKING")

        print("\n" + "=" * 60)
        print("LLM Response:")
        print("=" * 60)
        print(response.content)
        print("=" * 60)

        print("\n✓ LLM connection successful!")
        return True

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ LLM connection FAILED")
        print("=" * 60)
        logger.exception("LLM test failed")
        print(f"\nError: {e}")
        print("\nPlease check:")
        if os.getenv("USE_VERTEX", "false").lower() == "true":
            print("  - GOOGLE_CLOUD_PROJECT is set correctly")
            print("  - GOOGLE_CLOUD_LOCATION is set correctly")
            print("  - Application Default Credentials (ADC) are configured")
            print("    Run: gcloud auth application-default login")
        else:
            print("  - GEMINI_API_KEY is set correctly")
            print("  - API key is valid and active")
        return False


if __name__ == "__main__":
    success = test_llm()
    exit(0 if success else 1)
