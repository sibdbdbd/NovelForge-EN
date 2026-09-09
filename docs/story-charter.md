# Story Charter: the author's requirements, kept alive for the whole novel

The Novel Bible answers *what is true about the world*. Story Memory answers
*what has happened on the page so far*. The **Story Charter** answers the
question those two cannot: **what did the author ask for?**

## The problem it solves

Before the Charter, the Create Novel form's options (genre, tags, protagonist
name, romance level, ending preference, the free-text summary, …) were read by
storyline ideation and, weakly, by the architecture stage — and then never
consulted again. Chapter planning, chapter drafting, repair passes and every
manual Forge run received **zero** author requirements. A novel could be asked
to have "no love triangle" and grow one by chapter 40, because nothing between
the form and the drafting prompt carried the instruction.

The Charter is a single, persistent, author-editable record of requirements
that is rendered into **every** planning and generation prompt, scoped to what
each prompt can act on.

## The record

One singleton `Story Charter` card per project (`StoryCharter` schema in
`app/schemas/story_charter.py`; no migration — it is a card like any other and
travels with card export/import):

| Field | Meaning |
| --- | --- |
| `brief` | The author's own description, verbatim. **Never rewritten by the system.** |
| `working_title`, `one_line_pitch`, `audience`, `language`, `target_chapters`, `words_per_chapter` | Framing the planner needs |
| `requirements[]` | Things the novel must / should do. Each has `strength` (`must` \| `prefer`), `scope` (`whole_novel`, `planning`, `characters`, `world`, `prose`, `ending`, `chapter`), a `category`, and `source` |
| `open_choices[]` | Things the author **deliberately left undecided** — with `decide_by` (`author` \| `planner` \| `either`) and optional guidance on how the story may explore them without settling them |
| `boundaries[]` | Content that must never appear (`hard` blocks, `soft` is avoided) |
| `reference` | How an imported reference novel may inform this one — structure and rhythm only; names, settings, scenes and phrasing are always in `never_reuse` |
| `questions_for_author[]`, `interpretation_notes` | What the system inferred and what it would like to know; the author answers by adding entries, never by being blocked |

Every entry carries `source ∈ {author, interpreted, imported}` so the UI can show
what the author typed versus what the system inferred. Author entries are never
touched by re-interpretation; interpreted entries are replaced.

## How it is filled

1. **Create Novel** — the free-text brief is now the primary input; the
   preference grid is optional. On job creation `CharterService.ensure_from_job`
   seeds the Charter from whatever the author filled in (`charter_from_job_options`
   turns each chosen option into a scoped requirement). An existing, non-empty
   Charter is authoritative and left untouched.
2. **Interpret brief** (one model call, `Story Charter Interpretation` prompt,
   `CharterInterpretation` schema) — turns the brief into requirements, open
   choices, boundaries, a pitch and up to five questions. The model is told what
   the author has already fixed so it only adds what the brief adds. Inferred
   entries are tagged *inferred* in the UI and are editable or deletable.
3. **The author** — the Novel Bible → *Story Charter* section is a full editor.
   Saving is the author's word: `PUT /api/story-charter` replaces the record.

## How it reaches prompts

`render_charter(charter, consumer=…)` produces a deterministic, budgeted block.
`CONSUMER_SCOPES` decides which scopes each consumer sees (`whole_novel` always):

| consumer | scopes | where it is injected |
| --- | --- | --- |
| `storylines` | planning, characters, world, ending, structure | `autonomous/storylines.source_brief` — *outranks the reference* |
| `architecture` | + relationships | `autonomous/architecture.build_prompt` |
| `chapter_plan` | planning, structure, pacing, chapter, ending | `autonomous/chapter_plan.build_prompt` (every blueprint batch) |
| `draft` | prose, chapter, characters, planning, world | Forge compiler section `story_charter`, **priority 0, mandatory**; hard boundaries are also added to the compiled prohibited list; carried unchanged into repair prompts |
| `review` | prose, chapter, characters, planning, ending | available to critics/reviewers |

Open choices are rendered with an explicit instruction: *do not turn these into
permanent facts unless the author allowed it*. `GET /api/story-charter/render?consumer=…`
returns exactly what a consumer receives; the panel shows it under *What the
prompts receive*.

## Deterministic conflict scan

`POST /api/story-charter/check` scans a text against hard boundaries and
negatively phrased requirements ("no …", "never …") and returns a
`CharterCheckReport` (`clean | review | block`) with cited spans. It uses no
model and is safe to run on every draft.

## Prompts are product, not code

The pipeline system prompts used to be Python string literals with a hardcoded
sub-genre voice ("aristocratic protagonist secretly a genius") baked into every
chapter regardless of genre. They now live as `Prompt` rows seeded from
`backend/app/bootstrap/prompts/` and are editable in the Prompt Workshop:

- `Forge - Chapter Draft`, `Forge - Chapter Repair`
- `Autonomous - Storyline Ideation`, `Autonomous - Novel Architecture`, `Autonomous - Chapter Plan`
- `Story Charter Interpretation`

`app/services/ai/prompt_registry.py` resolves them by name and appends a
code-owned **output contract** (the JSON/marker format the parser depends on),
so an author can rewrite the voice and the rules without being able to break
structured parsing. Genre, tone and style now come from the Charter and the
Bible, not from the prompt.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/story-charter?project_id=` | Charter + summary (empty charter when none exists) |
| `PUT` | `/api/story-charter` | Save (author edits are authoritative) |
| `POST` | `/api/story-charter/interpret` | Interpret the brief with a chosen model |
| `GET` | `/api/story-charter/render?project_id=&consumer=` | Exactly what a consumer receives |
| `POST` | `/api/story-charter/check` | Deterministic conflict scan of a text |
| `GET` | `/api/story-charter/meta` | Vocabulary for editors (scopes, categories, consumers) |

## Tests

`backend/tests/test_story_charter.py`: seeding from job options, scope-aware
rendering and budget, interpretation merge (author entries preserved,
interpreted replaced, duplicates skipped, ids assigned server-side), the
interpret endpoint with a stubbed model, presence of the charter block in every
prompt builder, and the conflict scan. `test_autonomous_pipeline.py` asserts
the charter is seeded on job creation and reaches the chapter planner;
`test_forge_pipeline.py` asserts the compiled context carries the
`story_charter` section. `useStoryCharter.test.ts` covers the editor model.
