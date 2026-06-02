"""
Centralized environment configuration loader.
This module MUST be imported first by all entry points to ensure .env is loaded.

Import this at the top of:
- ai/llm.py
- ai/tools/notion_reader.py
- backend/main.py
- Any test scripts
"""
from dotenv import load_dotenv

# Load .env file once at module import time
load_dotenv()
