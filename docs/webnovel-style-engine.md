# Webnovel Style Engine & Director — Korean-webnovel prose in English

NovelForge writes English. The Webnovel Style Engine makes that English *read*
like a top-tier Korean serialized webnovel — Novelpia, Munpia, KakaoPage, Naver
Series — rather than like a Western literary novel that happens to have a
progression system. It exists because "write a hunter novel" produces adequate
fantasy prose but not the thing readers actually stay for: one-line rhythm on a
phone screen, the narrator's private verdict after every significant line,
`[Rank: F → E]` windows landing as beats, a face-slap paid on the page with the
doubter's reaction shot, and a last line that is a threat, a reveal or a
decision — never a moral.

The engine is three things that share one record:

1. a **Webnovel Style Profile** (`app/schemas/webnovel.py`) — the novel's
   platform, subgenre machinery, narration conventions, reader-experience
   targets and chapter shape;
2. a **prompt renderer + deterministic grader** that put that profile in front
   of every planner, drafter and critic and then measure whether the draft
   obeyed it (`app/services/forge/webnovel/`);
3. the **Director** (`app/services/autonomous/director.py`) — the author's
   live channel into a running Create Novel job: edit the profile, add standing
   notes, or *redo chapter N with this note*.

Token cost is not an optimization target here either; every profile-aware pass
also has a deterministic fallback, so a job never stalls on the engine.

```
Create Novel form ─┐                                        ┌──► storyline ideation   (GENRE ENGINE block)
                   ├─► detect_profile ─► Webnovel Style ────┼──► novel architecture   (+ AUTHOR DIRECTIVES, novel scope)
source fingerprint ┘   (author > brief > fingerprint >      ├──► chapter blueprints   (+ directives for the window)
                        template defaults)   Profile card   ├──► Forge compiler       (WEBNOVEL STYLE section, priority 2;
                                                            │                          AUTHOR DIRECTIVES, priority 0)
Director ◄──────────── PATCH /style, directives, redo ──────┤
                                                            └──► craft critic ◄── measure_conformance ──► polish / hook passes
                                                                                    │
                                                                    per-chapter webnovel_before / webnovel_after
                                                                    whole-novel audit `webnovel` in /report
```

## 1. The profile

`WebnovelStyleProfile` is a singleton **Webnovel Style Profile** card on the
generated novel project (`WebnovelStyleService`). Its groups map to the
decisions a Korean webnovel makes before the first line:

| Group | Fields | Why it exists |
|---|---|---|
| identity | `platform`, `perspective`, `narrative_distance`, `narrator_register` | Platform notes (`PLATFORM_NOTES`) carry front-page conventions — Novelpia's very short paragraphs and dense `'single-quote'` inner speech vs. Munpia's measured progression vs. KakaoPage's romance-friendly cinematic entries. Eight registers from `dry_cynical` to `earnest_underdog`. |
| `narration` | `thought_style`, `thought_density`, `windows_enabled`, `window_style`, `sfx_style`, `sfx_density`, `address`, `paragraph_rhythm`, `line_break_beats`, `chapter_title_style`, `tense`, `onomatopoeia_english` | The mechanics of the page: how inner speech is marked, whether `[System]` windows exist in this world at all, how SFX lines look (`Thud.` / `Crack—`), how Korean honorific logic is rendered in English (`Team Leader`, `Young Master`, `-nim` as a title word), one sentence per paragraph. |
| `engine` | `subgenre`, `progression_axis`, `tier_ladder`, `reward_types`, `face_slap_cadence`, `knowledge_advantage`, `world_hooks`, `typical_arc_shape`, `genre_vocabulary` | The machinery that manufactures episodes: what measurably grows, the named tiers, the kinds of dopamine the genre delivers, the protagonist's unfair edge, the world engines (gates, auctions, rankings, exams). |
| `reader` | `core_fantasy`, `dopamine_per_chapter`, `reward_gap_max_chapters`, `emotional_palette`, `comedy_level`, `romance_mode`, `violence_level`, `interiority_share_target` | The contract with the reader: minimum earned wins per chapter, the longest allowed drought, how much of the prose is the narrator's private processing. |
| `chapter` | `words_target`, `opening_rule`, `ending_rule`, `hook_in_last_line`, `min_scenes`, `max_scenes`, `recap_allowed`, `author_note_style` | Episode shape. Recap openings are off by default; the last paragraph is one or two lines. |
| moves | `signature_moves`, `banned_moves` | Free-text lists rendered verbatim into drafting and critic prompts. |
| system | `derived_from ∈ {author, detected, default}`, `detection_notes`, `updated_at` | Provenance the UI shows; author edits flip `derived_from` to `author`. |

### Subgenre templates

`templates.py` ships nineteen templates (`SUBGENRE_TEMPLATES`) plus `custom`:
regression, system apocalypse, hunter/gate, tower climb, dungeon, villainess
transmigration, academy, murim, cultivation, reincarnated noble, modern fantasy,
game/LitRPG, office life, romance fantasy (rofan), returnee, apocalypse
survival, sports, entertainment industry, historical transmigration. Each seeds
the `engine` and `reader` groups — the tier ladder, the reward types, the core
fantasy, the arc shape, the vocabulary the prose may use natively.
`guess_subgenre` maps cue words in the brief / genre / tags to a template, so
"a regressor who remembers the tower" lands on `regression` without the author
picking anything. Switching the subgenre later (Director → Style) re-seeds the
template machinery while keeping the author's other edits.

### Detection: how the profile is filled

`detect.detect_profile` runs when the novel project is created
(`JobRunner._style_profile` → `WebnovelStyleService.ensure`). Authority order,
highest first:

1. explicit Create Novel fields — `platform`, `subgenre`, `perspective`,
   `narrator_register`, `thought_style`, `status_windows`, `comedy_level`
   (every one defaults to *let the engine decide*);
2. cues in the author's brief / genre / tags;
3. measurable signals in the source **Narrative Fingerprint**
   (`fingerprint_signals`): POV, paragraph-length profile, inner-thought share,
   status-window presence, humour, reward cadence — plus the abstract scene
   function tags the analysis already produced;
4. the subgenre template defaults.

Nothing reads source *content*; only fingerprint numbers and function tags.
Every inference is written to `detection_notes` ("subgenre 'hunter_gate'
inferred from the author's brief / genre / tags") so the author can see what
was decided for them. A job with no author input still gets a complete,
internally consistent profile; a job with a two-page brief gets a profile that
obeys it.

## 2. Rendering into prompts

`render.py` produces three bounded blocks from one profile so every stage is
told the same thing at the level of detail it can use:

- `render_for_drafting` (≤3600 chars) — the full convention sheet: platform
  note, perspective and distance, register, inner-speech marking with the exact
  quote form, windows/SFX/address rules, paragraph rhythm, reward obligations,
  opening and ending rules, signature and banned moves.
- `render_for_planning` (≤2600 chars) — the **GENRE ENGINE**: progression
  axis, tier ladder, reward types, face-slap cadence, world hooks, arc shape,
  dopamine-per-chapter and drought limits. Storyline ideation gets it so every
  option is "architected for a serialized webnovel"; novel architecture and
  every chapter-blueprint window get it so the plan actually schedules rewards.
- `render_for_critic` (≤1800 chars) — the scorecard the adversarial editor
  grades against.

The Forge compiler adds a mandatory `webnovel_style` section (priority 2,
"outranks the fingerprint where they disagree") to every chapter context; the
craft passes read the profile directly (`CraftInputs.style_profile`). Both are
degradable: if the card is missing the section is simply absent and the chapter
drafts from the Charter, the Bible and the fingerprint as before.

## 3. Webnovel Conformance — the deterministic grader

`conformance.measure_conformance(prose, profile, language, closing_hook_plan)`
is a no-model pass that scores a draft 1–10 in six dimensions and cites every
problem with a quote and a fix:

| Dimension | What is measured | Typical finding codes |
|---|---|---|
| `rhythm` | paragraph-length profile vs. `paragraph_rhythm`, paragraph walls, dialogue buried in narration | `rhythm_long_paragraphs`, `rhythm_too_dense`, `paragraph_walls`, `dialogue_buried` |
| `inner_voice` | direct inner speech in the configured marker per 1000 words, private verdicts after dialogue lines | `inner_speech_missing`, `inner_speech_thin`, `inner_speech_marker`, `no_private_verdicts` |
| `conventions` | windows / SFX / address forms present when enabled and absent when disabled, recap openings, Western-literary metaphor stacking | `windows_absent`, `windows_forbidden`, `windows_spam`, `sfx_absent`, `sfx_forbidden`, `sfx_spam`, `recap_opening`, `metaphor_stacking`, `literary_register` |
| `momentum` | opening in motion, transition-marker hopping, exposition blocks | `weather_opening`, `transition_hopping`, `exposition_block`, `exposition_run` |
| `reward` | micro-payoffs on the page and reversals *with* the doubter's reaction shot | `reward_missing`, `reversal_without_reaction`, `want_stated_directly` |
| `ending` | hook class and strength of the final line, closing morals, long last paragraphs | `soft_ending`, `closing_moral`, `long_last_paragraph` |

`critic.merge_conformance` folds the result into the Prose Craft
`CriticReport`: shared dimensions take the **lower** score, the six webnovel
dimensions are added as `webnovel_*` scores, findings are appended
(`[webnovel/<code>] …`), and the chapter's overall becomes the mean of the
literary critic and the webnovel scorecard. A chapter that is clean English
prose but not a webnovel is therefore still sent to polish — and the polish
prompt receives the cited lines.

Every committed chapter stores `webnovel_before` and `webnovel_after`
(`validation_report.craft`), so the Director's *Chapter quality* tab and
`GET /jobs/{id}/chapters/{n}/quality` can show what the craft passes changed.
The whole-novel audit (`audit.webnovel_audit`) averages the dimensions across
chapters, lists chapters below the 6.5 floor, tracks the worst
**reward drought** against `reward_gap_max_chapters`, and flags three
consecutive soft endings; it surfaces as `webnovel` in `/report` and on the
finished screen.

## 4. Author Directives

`AuthorDirective` is the author's steering note in their own words:

- `scope ∈ {novel, arc, chapter}` with `chapter_from` / `chapter_to`;
- `kind ∈ {must, prefer, avoid, idea}`;
- `applies_to ⊆ {planning, drafting, critic, export}`;
- `consumed_by_chapters` — filled by the loop, so the author can see the note
  actually reached chapter 14;
- `active` — a soft delete that keeps the history.

Directives live in a singleton **Author Directives** card (`DirectiveService`)
and are rendered next to the Story Charter with the *same authority*: a
mandatory `author_directives` section at priority 0 in the Forge compiler,
an `[AUTHOR DIRECTIVES]` block in novel architecture (novel scope) and in every
chapter-blueprint batch (the window's scope). `directives_for(chapter, consumer)`
filters by scope and consumer; `render_directives` groups by kind and is
bounded.

**Before the project exists.** A job created with `auto_start=false` (or paused
during analysis) has no novel project yet, so the Director stores edits on the
job: `options.pending_directives` and `options.style_profile_override`. The
runner applies both the moment the project is created
(`director.apply_pending_directives`, `apply_style_override`) and then removes
them from `options`. Pending rows are shown with the full `AuthorDirective`
shape (`pending-1`, `pending-2`, …) so the UI does not need a second code path.

## 5. Redo from chapter N

`director.redo_from_chapter(job, from_chapter, note, note_kind, replan)` is the
author's "no — do chapter 14 like *this*". It requires a paused, waiting or
completed job at a redo-able stage (`CHAPTER_GENERATION_LOOP`,
`WHOLE_NOVEL_AUDIT`, `GLOBAL_REPAIR`, `EXPORT`, `DONE`). It then:

1. turns the note into a chapter-scoped directive for chapter N
   (`applies_to = planning, drafting, critic`);
2. rewinds canon and ledgers to N−1 (`rewind.rewind_to`, idempotent);
3. snapshots and discards Chapter Text cards and Chapter Digests ≥ N (outlines
   stay so the loop can regenerate) and marks their pipeline runs superseded;
4. resets the job to the chapter loop with `chapters_committed = N−1`, drops
   audit / repair / export results and the quality verdict, appends to
   `stage_results.redo_log`, and — when `replan` is on — sets
   `stage_results.replan_from = N`.

The chapter loop honours `replan_from` before drafting: the blueprint window
from N is re-planned under the note (`chapter_plan.replan_from`, reason
"author redo from chapter N") so the note can change *what happens*, not only
how it is written; the record lands in the chapter's `replan.pre_replan`.
`GET /jobs/{id}/redo/plan?from_chapter=N` previews what would be discarded.
`auto_start=false` leaves the job paused for more Director edits.

## 6. Export

`export.build_webnovel_text` produces a platform-ready plain-text artifact —
one episode per block with `episode_label` honouring `chapter_title_style`
(`Chapter 12 — The Bidding` / `Episode 12`), an optional author's note, and a
table of contents whose per-episode teaser is the chapter's final line (the
webnovel TOC convention). It ships alongside EPUB / DOCX / Markdown as
*Webnovel text (episodes)*.

## 7. API

All under `/api/autonomous`:

| Method & path | Purpose |
|---|---|
| `GET /subgenres` | Templates (`key`, `label`, `progression_axis`, `core_fantasy`) plus `platform:<name>` notes for the Create Novel form and the Director. |
| `GET /jobs/{id}/style` · `PATCH /jobs/{id}/style` | Read / deep-merge-patch the profile (or the pending override before the project exists). Unknown subgenres → 400. |
| `GET /jobs/{id}/style/preview` | The exact drafting / planning / critic blocks the prompts receive. |
| `GET/POST /jobs/{id}/directives` · `PATCH/DELETE /jobs/{id}/directives/{did}` | Directive CRUD (validation mirrors the UI: chapter/arc notes need a start chapter; arcs end after they start). |
| `GET /jobs/{id}/redo/plan?from_chapter=N` · `POST /jobs/{id}/redo` | Preview / perform a redo (`RedoRequest`: `note`, `note_kind`, `replan`, `discard_texts`, `auto_start`). A running job is paused first; 409 when the stage does not allow it. |
| `GET /jobs/{id}/chapters/{n}/quality` | Per-chapter craft report: `critic_before/after`, `webnovel_before/after`, passes, model calls, repairs. |

Create Novel (`POST /jobs`) accepts `platform`, `subgenre`, `perspective`,
`narrator_register`, `thought_style`, `status_windows`, `comedy_level` and a
`directives` list; `auto_start=false` creates the job paused for Director edits.

## 8. UI

- **Create Novel → Webnovel style** card: platform, subgenre template (with
  its core fantasy as hint), perspective, register, inner-speech marking,
  status windows, comedy level — each defaulting to *Let the engine decide* —
  plus a *Standing directives* textarea (one note per line) and a *Start
  immediately* switch.
- **Director** (button in the job bar, `DirectorPanel.vue`, `useDirector.ts`):
  - *Style profile* — every profile field grouped as above, with detection
    notes and a *What the prompts receive* preview; saving sends a minimal deep
    patch.
  - *Directives* — add / edit / toggle / delete, with consumed-by-chapter
    badges.
  - *Redo a chapter* — chapter, note kind, re-plan and resume switches, the
    note, a discard preview, a confirmation, and the redo history.
  - *Chapter quality* — the six webnovel dimensions before and after craft,
    the merged critic line, and the cited conformance findings.
- **Finished screen** — webnovel conformance overall, the worst reward
  drought, and a one-line style summary (platform · subgenre · perspective ·
  register) next to the audit verdict.

## 9. Tests

- `backend/tests/test_webnovel_engine.py` — templates cover every label and
  cue-guessing; detection from minimal and deep inputs; render blocks bounded
  and carrying conventions; conformance separates webnovel from literary prose;
  critic merge takes the lower shared score and adds webnovel dimensions;
  style/directive services persist on a project; compiled context carries
  style and directives into prompts; Director redo rewinds, requeues, re-plans
  and the note is consumed by the regenerated chapter — all against the fake
  pipeline client, no live model.
- `frontend/src/renderer/src/composables/__tests__/useDirector.test.ts` —
  composable state, validation, minimal patches, redo gating.
- `frontend/src/renderer/src/components/autonomous/__tests__/DirectorPanel.render.test.ts`
  — server-renders the real panel (Element Plus + i18n) against sparse and
  legacy payload shapes so a template `.length` on a missing list can never
  ship again.
