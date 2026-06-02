# Agentic Slidev Presentation Generator

An agentic AI application that generates [Slidev](https://sli.dev) presentations grounded
in a Notion knowledge base. A user picks a generation mode and a topic; a multi-agent
pipeline plans, retrieves grounding context from Notion, optionally fills gaps via web
search, and writes a complete Slidev deck (`slides.md`) — which is then rendered as a real
Slidev presentation.

---

## What it does

Given a query like *"Meridian Aurora Nexus enterprise AI platform"*, the system:

1. Validates the request (a guardrail rejects harmful or non-presentation queries).
2. Plans a 10-slide outline.
3. Retrieves grounding content from a configured Notion page and judges whether it
   sufficiently covers the outline.
4. If gaps remain, escalates to Google Search grounding to fill them.
5. Generates a fully grounded 10-slide Slidev deck, using specific facts and figures from
   the source rather than invented content.
6. Renders the deck as a real Slidev static site for viewing.

---

## Architecture

The design principle is **one shared tool layer; modes are configuration over it.** All
modes use the same agents and tools — a mode simply decides which agents are active, which
model is used, and what extra capabilities (images, clarifying questions) are switched on.

### The agent pipeline (LangGraph)

```
START
  → intent_detector        (input guardrail: valid presentation request?)
       ├─ invalid → END     (returns a polite message; no generation)
       └─ valid → manager   (plans title + 10 slide topics)
                → context_retriever   (reads Notion; judges sufficiency)
                     ├─ sufficient   → ppt_generator
                     └─ insufficient → web_search → ppt_generator
                → ppt_generator       (writes grounded DeckSpec → slides.md)
                → END
```

Each agent is a plain function node in a LangGraph `StateGraph`, with structured outputs
enforced via Pydantic models (`with_structured_output`). Web search uses Gemini's built-in
Google Search grounding. No content is parsed from free-form JSON — every inter-agent
contract is a typed schema.

### Modes

| Mode | Agents | Model | Slides | Extra |
|------|--------|-------|--------|-------|
| fast | guardrail → manager → context → (web) → ppt | Flash + Pro | 10 | — |
| pro  | fast + image generation | Flash + Pro | 10 | AI-generated slide images |
| max  | pro + research | Flash + Pro | 10 | asks clarifying questions first |

(`fast` is fully implemented; `pro` and `max` build on it as supersets.)

### Project layout

```
ai/
  llm.py              # LLM factory: Vertex AI or Gemini API via one env switch
  config.yaml         # models, slide count, per-mode agent/tool map
  config_env.py       # loads .env once, imported first by all entry points
  src/
    graph.py          # builds & runs the LangGraph pipeline
    state.py          # GraphState (typed graph state)
    schemas.py        # all Pydantic models
  agents/             # one file per agent (intent_detector, manager, ...)
  agents_prompts/     # one system prompt (.txt) per agent
  tools/              # notion_reader, slides_writer, web_search, image_gen
  utils/              # logger, prompt loader, AppError
backend/
  main.py             # FastAPI app + endpoints + global exception handlers
  mode_handler.py     # resolves a mode and runs the right pipeline
  render_fallback.py  # non-Slidev HTML viewer (see Known Issues)
frontend/             # plain HTML/CSS/JS UI
slidev/               # pristine Slidev project; only slides.md is written by the app
logs/                 # rotating application logs
```

---

## Three design decisions

1. **Slidev as the output format.** The app generates a Markdown `slides.md`, not a binary
   `.pptx`. This keeps generation simple and version-controllable, makes the agent's output
   directly inspectable, and lets Slidev render a polished deck and export to PDF/PPTX.

2. **Notion as the context layer.** Generation is grounded in a Notion page rather than the
   model's general knowledge. The `context_retriever` reads the page and judges coverage; if
   the source is insufficient, the pipeline escalates to web search. This makes output
   factual and verifiable — every figure in a generated slide traces back to the source.

3. **LangGraph for agentic orchestration.** A typed `StateGraph` with conditional edges
   gives explicit, debuggable control flow (the guardrail short-circuit and the
   sufficiency-based web-search escalation are real branches), rather than an opaque
   agent-executor loop.

---

## Setup

### Prerequisites
- Python 3.12, Node.js **20 or 22 LTS** (see Known Issues re: Node 24)
- A Google Cloud project with Vertex AI enabled (or a Gemini API key)
- A Notion integration token and a shared Notion page

### 1. Python environment
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt
```

### 2. Environment variables (`.env`)
```
NOTION_API_KEY=ntn_...
NOTION_PAGE_ID=<your page id>

# LLM backend switch
USE_VERTEX=true
GOOGLE_CLOUD_PROJECT=<project id>
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_API_KEY=                     # only if USE_VERTEX=false

SLIDEV_DIR=./slidev
LOG_LEVEL=INFO
```
For Vertex, authenticate once: `gcloud auth application-default login`.
Share your Notion page with the integration (page → ••• → Connections → add it).

### 3. Slidev project
```bash
npm create slidev@latest slidev      # one-time scaffold; do not edit its internals
cd slidev && npm install
```

### 4. Run
```bash
# backend (from project root)
uvicorn backend.main:app --reload

# frontend (separate terminal)
cd frontend && python -m http.server 3000
# open http://localhost:3000
```

Enter a topic, generate, and render the Slidev deck.

---

## Known issues

- **Slidev dev server / `slidev export` fail on the development machine** with a Vite
  path-resolution error (`Failed to resolve import .../conditional-styles`). This is an
  environment-specific Windows + Vite bug (reproduced on a clean scaffold under both Node 22
  and Node 24), **not** a problem with generated decks: the produced `slides.md` is valid
  Slidev and renders correctly elsewhere.
  - **Rendering path that works here:** `slidev build` (static build) succeeds and is what
    the app uses to render decks for viewing.
  - **Fallbacks:** `backend/render_fallback.py` produces a dependency-free HTML view of any
    deck; the deck also renders normally in Slidev on Linux/WSL or a clean environment.