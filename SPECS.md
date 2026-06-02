# SPECS.md — Build Specification

Source of truth for *what* to build. Read alongside `CLAUDE.md` (the rules). Build in
the phase order at the bottom. Do not build ahead of the current phase.

---

## 1. Overview

User picks a **mode** (fast / pro / max) and types a **query** in the frontend. The
backend resolves the mode to a `ModeConfig`, runs a **LangGraph** pipeline, and writes a
**Slidev** deck (`slides.md`) grounded in a fixed **Notion page** (page ID from `.env`).

High-level flow:

```
POST /generate {mode, query}
  → mode_handler.resolve(mode) -> ModeConfig
  → build & run LangGraph:
        START → intent_detector (guardrail)
           ├─ invalid_query → END  (return polite user_message)
           └─ valid_query → manager → context_retriever
                                   ├─ sufficient → ppt_generator
                                   └─ insufficient → web_search → ppt_generator
                          → (pro/max: image_generator)
                          → slides_writer → END
  → response {valid, deck_id, markdown, slide_count}  (or {valid:false, user_message})
```

Notion page ID is **not** a request field — it is config (`NOTION_PAGE_ID` in `.env`).

---

## 2. Modes

Lite is removed. All three modes produce a 10-slide deck.

| Mode | Orchestration | Active agents | Images | Asks user first |
|------|---------------|---------------|--------|-----------------|
| fast | LangGraph | intent_detector, manager, context_retriever, web_search, ppt_generator | No | No |
| pro  | LangGraph | fast + image_generator | Yes | No |
| max  | LangGraph | pro + research | Yes | Yes (clarifying questions) |

Mode differences are **data**, not separate code paths or separate endpoints. The graph
is assembled per mode from `ModeConfig`; inactive nodes are simply not added.

---

## 3. API (backend/main.py)

Keep endpoints minimal — only what the frontend needs.

- `GET /health` → `{"status": "ok"}`.
- `GET /modes` → list of `{id, label, description}` for the frontend selector.
- `POST /generate` → body `{ "mode": "fast", "query": "..." }`
  - If guardrail rejects: `{ "valid": false, "user_message": "..." }` (HTTP 200).
  - On success: `{ "valid": true, "deck_id": "...", "markdown": "<slides.md text>",
    "slide_count": 10 }`.
- `GET /deck/{deck_id}` → `{ "markdown": "..." }` (re-fetch a generated deck).

`/generate` is **non-streaming** for v1. Streaming is a later phase (Phase 3) added as a
separate `POST /generate/stream` (SSE) — do not build it until fast works.

`max` mode is two-phase (Phase 5): `POST /max/questions {query}` →
`{questions: [...]}`; then `POST /generate {mode:"max", query, answers}`.

---

## 4. mode_handler.py (backend)

The single entry point the API calls. Responsibilities:
- `resolve(mode: str) -> ModeConfig` using `ai/config.yaml`.
- Build the LangGraph graph for that mode (`ai/src/graph.py:build_graph(mode_config)`).
- Invoke the graph with the initial state and return the final state.
- Catch `AppError`, log, re-raise for the global handler.

`ModeConfig` (dataclass or pydantic):
```
mode: str
model_fast: str          # e.g. gemini-2.5-flash  (intent_detector, manager)
model_pro: str           # e.g. gemini-2.5-pro     (retrieval judge, web, ppt)
slide_count: int         # 10
use_images: bool         # pro/max
research_first: bool     # max
active_agents: list[str]
```

---

## 5. Pydantic schemas (ai/src/schemas.py)

```python
class ValidationResult(BaseModel):
    valid_query: bool
    reason: str
    user_message: str        # shown to user when valid_query is False

class Outline(BaseModel):
    title: str
    slide_topics: list[str]  # length == slide_count

class SufficiencyJudgment(BaseModel):
    sufficient: bool
    missing: list[str]       # topics not covered by Notion context

class SlideSpec(BaseModel):
    heading: str
    bullets: list[str]
    image_prompt: str | None = None   # populated only in pro/max
    image_path: str | None = None     # filled after image generation

class DeckSpec(BaseModel):
    title: str
    slides: list[SlideSpec]

class ClarifyingQuestions(BaseModel):   # max mode
    questions: list[str]
```

One `DeckSpec` is shared across modes. Slide count is enforced by prompt + a validator,
not by separate per-mode classes.

---

## 6. Graph state (ai/src/state.py)

```python
class GraphState(TypedDict, total=False):
    mode: str
    query: str
    mode_config: dict
    valid_query: bool
    user_message: str
    outline: Outline
    notion_context: str
    sufficiency: SufficiencyJudgment
    web_context: str
    clarifying_questions: list[str]   # max
    answers: dict                     # max
    deck: DeckSpec
    deck_id: str
    deck_path: str
```

---

## 7. Agents (ai/agents/*.py) — each loads its prompt from agents_prompts/*.txt

**intent_detector** — *input guardrail, runs first.*
- Model: fast. `with_structured_output(ValidationResult)`.
- Rejects (sets `valid_query=False`) when the query is (a) harmful/hateful/violent, or
  (b) not a presentation request (e.g. "what is the capital of India" — a generic Q&A).
- On reject, sets a polite `user_message` like: "This is a presentation generator —
  tell me a topic you'd like a deck on." The manager is **never** reached.
- Conditional edge: `valid_query` False → END; True → manager.

**manager** — *plans the deck, holds the ModeConfig.*
- Model: fast. `with_structured_output(Outline)`.
- Produces `title` + exactly `slide_count` `slide_topics` from the query.

**context_retriever** — *Notion grounding + sufficiency judgment.*
- Calls `tools/notion_reader.read_page_context(NOTION_PAGE_ID)` → `notion_context`.
- Model: pro. `with_structured_output(SufficiencyJudgment)` comparing outline topics to
  the Notion context.
- Conditional edge: `sufficient` True → ppt_generator; False → web_search.
- **One escalation only** (no loops back).

**web_search** — *fills gaps when Notion is insufficient.*
- Model: pro, `bind_tools([{"google_search": {}}])` (no structured output here).
- Returns grounded text → `web_context`. Then → ppt_generator.

**ppt_generator** — *writes the deck.*
- Model: pro. `with_structured_output(DeckSpec)`.
- Inputs: outline + notion_context + web_context (+ answers in max).
- pro/max: also populate `image_prompt` per slide.
- Calls `tools/slides_writer.write_deck(deck, deck_id)`.

**image_generator** — *pro/max only; stub returns unchanged state until Phase 4.*
- Model: `gemini-2.5-flash-image`, standalone `generate_content`, no tools.
- One image per slide that has `image_prompt`; save PNG to
  `slidev/public/<deck_id>_<i>.png`; set `image_path`. Skip gracefully if no image part.

**research** — *max only; stub until Phase 5.*
- Model: pro. `with_structured_output(ClarifyingQuestions)`. Runs before manager;
  questions returned to user; answers merged into state on the second call.

---

## 8. Tools (ai/tools/*.py)

- **notion_reader.py** — PORT the existing working reader. `read_page_context(page_id)`:
  list block children with pagination, recurse into children, extract `plain_text` from
  paragraph / heading_1-3 / bulleted_list_item / numbered_list_item / quote / callout /
  code, join with newlines. Raise `AppError` with a clear "share the page with the
  integration" message on a not-found/permission error.
- **slides_writer.py** — `write_deck(deck: DeckSpec, deck_id: str) -> str`. Emits valid
  Slidev markdown to `slidev/slides.md` (the active deck) AND a copy to
  `slidev/decks/<deck_id>.md`. Returns the active path. **Writes only inside `slidev/`
  to `slides.md`, `decks/`, and `public/` — nothing else.**
- **web_search_tool.py** — wraps the grounded-LLM call used by the web_search agent.
- **image_gen.py** — stub until Phase 4.

### Slidev markdown format (slides_writer output)

```
---
theme: default
title: <deck.title>
---

# <deck.title>

---

## <slide.heading>

- <bullet>
- <bullet>

---
```
- First slide is the cover (deck title).
- Each `SlideSpec` → one slide: `## heading` then `- bullet` lines.
- If `image_path` is set: use a two-column layout
  (`---\nlayout: two-cols\n---`) with bullets on the left and
  `![](/<filename>.png)` on the right. Image files live in `slidev/public/`, referenced
  as `/<filename>.png`.
- Slides separated by `\n---\n` on its own line with blank lines around it.

---

## 9. config.yaml (ai/config.yaml)

```yaml
models:
  fast: gemini-2.5-flash
  pro: gemini-2.5-pro
  image: gemini-2.5-flash-image
slide_count: 10
modes:
  fast:
    use_images: false
    research_first: false
    active_agents: [intent_detector, manager, context_retriever, web_search, ppt_generator]
  pro:
    use_images: true
    research_first: false
    active_agents: [intent_detector, manager, context_retriever, web_search, ppt_generator, image_generator]
  max:
    use_images: true
    research_first: true
    active_agents: [research, intent_detector, manager, context_retriever, web_search, ppt_generator, image_generator]
```

---

## 10. .env

```
# Notion
NOTION_API_KEY=ntn_...
NOTION_PAGE_ID=223af9b35a0c807d9c3ce07b3e3926d5

# LLM backend switch
USE_VERTEX=true            # or false to use GEMINI_API_KEY
GOOGLE_CLOUD_PROJECT=gen-lang-client-0624934316
GOOGLE_CLOUD_LOCATION=us-central1
GEMINI_API_KEY=            # only needed if USE_VERTEX=false

# Paths / logging
SLIDEV_DIR=./slidev
LOG_LEVEL=INFO
```

---

## 11. Frontend (plain HTML/CSS/JS)

Single page. Mode selector (3 cards: fast/pro/max), a query textarea, a Generate button.
On submit, `fetch('/generate', {POST, json})`:
- If `valid:false` → show `user_message` in a notice.
- If success → render `markdown` in a styled `<pre>` (guaranteed view) **and** show an
  iframe to the Slidev dev server (`http://localhost:3030`) for the rendered deck. Add
  Copy and Download-`.md` buttons. The `<pre>` is the fallback if the Slidev server
  isn't running.
No framework, no build step. Keep `app.js` small and readable.

---

## 12. Build phases (do them in order; commit after each)

- **Phase 0 — Foundation.**
  1. Human runs `npm create slidev@latest slidev` and `npm run dev`; confirm it serves
     `localhost:3030` cleanly. Never touched again.
  2. Scaffold the Python structure, `logger.py`, `llm.py`, `.env`, requirements.
  3. Prove `get_llm(...).invoke("hi")` works (Vertex or key, per `USE_VERTEX`).
  4. Port `notion_reader`; confirm it prints the Notion page text.
  *Gate: LLM responds AND Notion text prints.*

- **Phase 1 — fast mode, no frontend, no streaming.**
  Build state, schemas, the five fast agents, the graph, mode_handler, `POST /generate`,
  global exception handlers, full logging. Test via `/docs` or curl. Confirm
  `slides.md` is written and renders in the already-running Slidev server.
  *Gate: a real query produces a 10-slide deck grounded in Notion, visible in Slidev.*
  **Commit.**

- **Phase 2 — minimal frontend.** index.html + style.css + app.js calling `/generate`;
  render `<pre>` + iframe. *Gate: end-to-end from the browser.* **Commit.**

- **Phase 3 — streaming.** Add `POST /generate/stream` (SSE) + a progress list in the
  frontend. Keep `/generate` working as the fallback. **Commit.**

- **Phase 4 — pro mode.** Implement `image_gen` + `image_generator` agent; activate via
  config. **Commit.**

- **Phase 5 — max mode.** Implement `research` agent + the two-phase questions flow.
  **Commit.**

Stop at the end of whatever phase the deadline allows — every phase boundary is a
complete, demoable submission.
