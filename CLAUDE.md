# CLAUDE.md — Project Rules (read this first, every time)

This file defines how to work in this repo. Follow it exactly. When a prompt and this
file conflict, ask before proceeding. The detailed build spec lives in `SPECS.md` —
read it before writing code.

---

## What this project is

An **agentic AI application that generates Slidev presentations**, grounded in a
**Notion page** as the context layer. The agent pipeline is built on **LangGraph**.
There are three modes — **fast**, **pro**, **max** — selected by the user and handled
entirely in the backend.

Stack:
- **AI layer:** Python, LangGraph, LangChain, `langchain-google-genai` (Gemini).
- **Backend:** FastAPI.
- **Frontend:** plain HTML/CSS/JS. **No TypeScript, no React, no build step.**
- **Slides:** Slidev (Node) — used as a *black box viewer*, see the hard rule below.

---

## Hard rules (these caused real failures — do not break them)

1. **NEVER touch the `slidev/` folder internals.** It is created once by
   `npm create slidev@latest` by a human. Do **not** add/edit `vite.config.*`, do
   **not** edit anything in `slidev/node_modules`, do **not** add a
   `pnpm-workspace.yaml`, do **not** reinstall or reconfigure it. The **only** file
   the app may write inside `slidev/` is `slidev/slides.md`. Treat everything else in
   `slidev/` as read-only.

2. **The project must NOT live in a OneDrive-synced path.** Assume it lives at
   `C:\dev\ppt_gen`. Never hardcode any absolute path (no `C:\Users\...`, no
   `C:\dev\...`) in code. Use paths relative to the project root or read them from
   `.env`.

3. **MOVE / EDIT existing working code; do not rewrite it from scratch.** When asked to
   refactor or relocate, preserve logic verbatim. Large regenerations corrupt files.

4. **One change at a time.** Do not combine a structural refactor with a feature
   change in the same step. After each change, report what changed and stop.

5. **Never create duplicate structures.** If you create a new file/folder that replaces
   an old one, delete the old one in the same step (after confirming nothing imports
   it). The repo must never contain two copies of the same module.

6. **Do not run `npm`, dev servers, or interactive scaffolds yourself.** Document the
   command for the human to run. You may run non-interactive Python checks
   (e.g. `python -c "import backend.main"`).

7. **No extra report files.** Do not generate `IMPLEMENTATION_STATUS.md`,
   `VERIFICATION_REPORT.txt`, etc. The only docs are `README.md`, `CLAUDE.md`,
   `SPECS.md`.

---

## Directory structure (authoritative)

```
ppt_gen/                      # project root (C:\dev\ppt_gen) — single venv at root
  ai/
    __init__.py
    llm.py                    # get_llm() factory (backend switch)
    config.yaml               # models, slide counts, per-mode agent/tool map
    src/
      __init__.py
      graph.py                # builds the LangGraph StateGraph per mode
      state.py                # GraphState TypedDict
      schemas.py              # all Pydantic models
    agents/
      __init__.py
      intent_detector.py      # input guardrail (see SPECS)
      manager.py
      context_retriever.py
      web_search.py
      ppt_generator.py
      image_generator.py      # stub until pro
      research.py             # stub until max
    agents_prompts/           # one .txt system prompt per agent
      intent_detector.txt
      manager.txt
      context_retriever.txt
      web_search.txt
      ppt_generator.txt
    tools/
      __init__.py
      notion_reader.py        # PORT existing working code, do not rewrite behavior
      web_search_tool.py
      slides_writer.py        # DeckSpec -> ./slidev/slides.md
      image_gen.py            # stub until pro
    utils/
      __init__.py
      logger.py               # the ONE shared logger
      prompt_loader.py        # loads agents_prompts/*.txt
  backend/
    __init__.py
    main.py                   # FastAPI app + endpoints + global exception handler
    mode_handler.py           # mode -> ModeConfig; entry point the API calls
  frontend/
    index.html
    style.css
    app.js
  slidev/                     # pristine, human-created, DO NOT TOUCH except slides.md
    slides.md
  logs/                       # logger writes here (gitignored)
  .env
  .gitignore
  requirements.txt
  README.md
  CLAUDE.md
  SPECS.md
```

Run the backend from the project root: `uvicorn backend.main:app --reload`.

---

## LLM setup

- Use `ChatGoogleGenerativeAI` from `langchain-google-genai` (>=4.0.0).
  **Do NOT use the deprecated `ChatVertexAI`, `AgentExecutor`, or
  `create_tool_calling_agent`.**
- `ai/llm.py` exposes `get_llm(model_name, temperature=0.3)`. It reads `USE_VERTEX`
  from `.env`:
  - `USE_VERTEX=true` → `ChatGoogleGenerativeAI(model=..., vertexai=True)` (uses
    `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` + ADC).
  - `USE_VERTEX=false` → `ChatGoogleGenerativeAI(model=...)` with `GEMINI_API_KEY`.
  Same function both ways — the backend switch is one env var.
- Models: `gemini-2.5-flash` and `gemini-2.5-pro` (names from `config.yaml`).
- **Google Search grounding** = bind a plain dict, no import:
  `get_llm("gemini-2.5-pro").bind_tools([{"google_search": {}}])`.
  **Never** combine `google_search` with `with_structured_output` in one call — keep
  the search node and the structured-output nodes separate.
- **Image generation** (pro/max) uses `gemini-2.5-flash-image` via the same SDK — a
  standalone `generate_content` call, **no** tools, **no** structured output.

---

## LangGraph patterns

- Use the low-level API: `from langgraph.graph import StateGraph, START, END`.
- State is a single `TypedDict` (`ai/src/state.py`). Each node is a plain function
  `def node(state) -> dict` returning a partial state update.
- Routing uses `add_conditional_edges`. No agent-executor harnesses, no hidden loops.
- Structured outputs via `llm.with_structured_output(PydanticModel)` — never parse
  JSON by hand.

---

## Logging & exceptions (non-negotiable — silent failures wasted a full day)

- **One logger:** `ai/utils/logger.py` exposes `get_logger(name)`. It attaches a
  `RotatingFileHandler` writing to `logs/app.log` **and** a console handler. Format:
  `%(asctime)s | %(levelname)s | %(name)s | %(message)s`. Level from `LOG_LEVEL` env
  (default INFO).
- **Every node and every tool** logs at entry (mode, query length, inputs) and exit
  (what it produced: # slides, context length, sufficiency result, etc.).
- **Wrap node/tool bodies in try/except**, log `logger.exception(...)` (full
  traceback), then raise a custom `AppError` (defined in `ai/utils`) carrying a
  human-readable message and the originating component.
- **FastAPI global handlers** in `main.py`: one for `AppError`, one catch-all for
  `Exception`. Both log the full traceback and return JSON
  `{"error": "<short>", "detail": "<message>"}` with status 500. Never return a bare
  500 with no body.

---

## Build discipline

Build in the phase order defined in `SPECS.md`. **fast mode must work end-to-end and be
committed before pro or max is started.** pro = fast + images; max = pro + clarifying
questions. They are supersets of fast.

**Commit (git) after every phase that works.** A working commit is the rollback point.

---

## Environment configuration

`.env` is loaded once via `ai/config_env.py`, which must be imported first by all entry
points and modules that read environment variables:

- Entry points: `ai/llm.py`, `ai/tools/notion_reader.py`, `backend/main.py`
- Test scripts: `test_llm.py`, `test_notion.py`

Pattern:
```python
# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

import os
# ... rest of imports
```

**Never** read `os.getenv()` before importing `config_env`. **Never** call `load_dotenv()`
directly in modules — it is centralized in `config_env.py`.

NEVER make a test accommodate a bug. If a test reveals a name/contract mismatch (env var, schema field, function signature), fix the SOURCE to match the spec — do not edit the test to accept both the right and wrong versions. Tests assert the spec; they don't bend to the code.

Before importing or calling a function/attribute from an existing module, READ that module to confirm the exact name. Do not assume naming conventions (e.g. a `.node` attribute, an `original_error` kwarg). Mismatched names cause AttributeError/TypeError.