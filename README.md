# PPT Generator - AI-Powered Slidev Presentation Builder

An agentic AI application that generates Slidev presentations grounded in Notion pages, built with LangGraph.

## Stack

- **AI layer:** Python, LangGraph, LangChain, ChatGoogleGenerativeAI (Gemini)
- **Backend:** FastAPI
- **Frontend:** Plain HTML/CSS/JS (no build step)
- **Slides:** Slidev (Node.js) - black box viewer

## Setup

### 1. Prerequisites

- Python 3.10+
- Node.js 18+
- Google Cloud project with Vertex AI enabled OR Gemini API key
- Notion integration and page access

### 2. Install Python Dependencies

```bash
# Create and activate virtual environment (if not already done)
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Unix/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

Edit `.env` with your credentials:

```bash
# Notion
NOTION_API_KEY=ntn_xxxxx  # Your Notion integration token
NOTION_PAGE_ID=xxxxx      # Your Notion page ID (32-char hex, no dashes)

# LLM backend switch
USE_VERTEX=true           # true for Vertex AI, false for Gemini API

# If USE_VERTEX=true:
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# If USE_VERTEX=false:
GEMINI_API_KEY=xxxxx

# Paths / logging
SLIDEV_DIR=./slidev
LOG_LEVEL=INFO
```

### 4. Set Up Slidev (One-time, manual)

```bash
# From project root
npm create slidev@latest slidev

# When prompted:
# - Project name: slidev
# - Install dependencies: Yes
# - Use pnpm: No (use npm)

# Start the Slidev dev server
cd slidev
npm run dev
```

Keep the Slidev server running at http://localhost:3030. **Never edit files in `slidev/` except `slides.md`.**

## Phase 0 - Foundation (Current)

### What's Built

1. ✓ Directory structure (`ai/`, `backend/`, `frontend/`, `logs/`)
2. ✓ Logger (`ai/utils/logger.py`) with file + console handlers
3. ✓ LLM factory (`ai/llm.py`) with Vertex/API backend switch
4. ✓ Notion reader (`ai/tools/notion_reader.py`) with pagination
5. ✓ Configuration files (`.env`, `config.yaml`, `requirements.txt`, `.gitignore`)

### Phase 0 Gate: Verification Tests

**Test 1: LLM Connection**

```bash
python test_llm.py
```

Expected: LLM responds with "WORKING" ✓

**Test 2: Notion Reader**

```bash
python test_notion.py
```

Expected: Prints text content from your Notion page ✓

**Both tests must pass to proceed to Phase 1.**

## Project Structure

```
ppt_gen/
  ai/
    __init__.py
    llm.py                    # LLM factory (Vertex/API switch)
    config.yaml               # Models, slide counts, per-mode config
    src/
      (Phase 1+: graph.py, state.py, schemas.py)
    agents/
      (Phase 1+: agent modules)
    agents_prompts/
      (Phase 1+: system prompt .txt files)
    tools/
      __init__.py
      notion_reader.py        # ✓ Notion page context reader
      (Phase 1+: web_search_tool.py, slides_writer.py, image_gen.py)
    utils/
      __init__.py             # AppError exception class
      logger.py               # ✓ Shared logger
      (Phase 1+: prompt_loader.py)
  backend/
    (Phase 1+: main.py, mode_handler.py)
  frontend/
    (Phase 2+: index.html, style.css, app.js)
  slidev/                     # DO NOT TOUCH (except slides.md)
  logs/                       # Auto-generated logs (gitignored)
  .env                        # ✓ Environment variables
  .gitignore                  # ✓
  requirements.txt            # ✓
  test_llm.py                 # ✓ Phase 0 verification
  test_notion.py              # ✓ Phase 0 verification
  CLAUDE.md                   # Project rules
  SPECS.md                    # Build specification
  README.md                   # This file
```

## Development Phases

- **Phase 0** ✓ Foundation (current - LLM + Notion work)
- **Phase 1** - Fast mode, no frontend (5 agents, LangGraph, FastAPI)
- **Phase 2** - Minimal frontend (HTML/CSS/JS UI)
- **Phase 3** - Streaming (SSE progress)
- **Phase 4** - Pro mode (image generation)
- **Phase 5** - Max mode (clarifying questions)

Each phase is a complete, demoable submission. Commit after each phase passes.

## Running the Backend (Phase 1+)

```bash
# From project root, with .venv activated
uvicorn backend.main:app --reload
```

API will be at http://localhost:8000

## Rules

- Read `CLAUDE.md` and `SPECS.md` before making changes
- One change at a time, commit after working phases
- Never touch `slidev/` internals (except `slides.md`)
- Use relative paths only, no hardcoded absolute paths
- Never create duplicate structures
