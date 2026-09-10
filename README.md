<div align="center">

# NovelForge-EN

**Next-Generation Autonomous AI Novel Engineering Platform & Narrative Studio**

[![Repository](https://img.shields.io/badge/GitHub-Sigmaaaaa12343%2FNovelForge--EN-blue?logo=github)](https://github.com/Sigmaaaaa12343/NovelForge-EN/tree/main)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-purple.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.x-4FC08D.svg?logo=vuedotjs)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg?logo=typescript)](https://www.typescriptlang.org/)
[![Electron](https://img.shields.io/badge/Electron-30.x-47848F.svg?logo=electron)](https://www.electronjs.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite)](https://www.sqlite.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-Graph_DB-008CC1.svg?logo=neo4j)](https://neo4j.com/)

<p>
  <a href="#-table-of-contents">Contents</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-core-systems-deep-dive">Core Systems</a> •
  <a href="#-visual-tour--screenshots">Visual Tour</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-creation-modes">Creation Modes</a> •
  <a href="#-prose-craft-presets">Prose Craft</a> •
  <a href="#-api-reference">API Reference</a> •
  <a href="#-specialized-docs">Documentation</a>
</p>

<p align="center">
  <img src="docImgs/autonomous_studio.png" alt="NovelForge-EN Autonomous Studio" width="100%" style="border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,0.18);" />
</p>

</div>

---

## ℹ️ Repository Notice & English Fork Heritage

**NovelForge-EN** is the production-hardened English narrative engineering platform and autonomous novel generation system, maintaining active upstream synchronization with **[Sigmaaaaa12343/NovelForge-EN](https://github.com/Sigmaaaaa12343/NovelForge-EN/tree/main)**.

Originally forked from [RhythmicWave/NovelForge](https://github.com/RhythmicWave/NovelForge), this English distribution has evolved into a complete, enterprise-grade AI novel production suite:
- **Full English Localization & Hardened Architecture**: All backend services, data models, prompt templates, seed knowledge bases, and Vue 3 / Electron UI elements are natively localized and hardened.
- **Autonomous Novel Engine**: End-to-end reference EPUB deconstruction, narrative genome reverse-engineering, dynamic context-aware chapter beat planning, multi-pass scene drafting, and episodic publishing.
- **Webnovel Serialization Standards**: Built-in support for Korean webnovel prose dynamics (Novelpia, Munpia, KakaoPage, Naver Series, Royal Road) with deterministic conformance grading.
- **Author-Centric Reliability**: 65k context compiler, immutable server-side snapshots, live Director control room, and author field locks ensuring zero context drift or data loss.

---

<a id="-table-of-contents"></a>
## 📑 Table of Contents

- [🌟 Platform Overview](#-platform-overview)
- [🏗️ System Architecture](#-system-architecture)
- [⚡ 8 Core Systems Deep-Dive](#-core-systems-deep-dive)
  - [1. Autonomous Novel Pipeline (End-to-End)](#1-autonomous-novel-pipeline-end-to-end)
  - [2. Director Deep-Input & Live Control Room](#2-director-deep-input--live-control-room)
  - [3. Webnovel Style Engine & Conformance Grader](#3-webnovel-style-engine--conformance-grader)
  - [4. Prose Craft Multi-Pass Engine](#4-prose-craft-multi-pass-engine)
  - [5. 65k Context Compiler & Story Memory](#5-65k-context-compiler--story-memory)
  - [6. Novel Intelligence Studio (Novel Bible 2.0)](#6-novel-intelligence-studio-novel-bible-20)
  - [7. Studio Workbench, Cards & Workflow Automation](#7-studio-workbench-cards--workflow-automation)
  - [8. Enterprise Hardening & Manuscript Safety](#8-enterprise-hardening--manuscript-safety)
- [📸 Visual Tour & Screenshot Showcase](#-visual-tour--screenshots)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Windows Quick Start (One-Click)](#windows-quick-start-one-click)
  - [Linux / macOS Installation](#linux--macos-installation)
  - [LLM Provider Configuration](#llm-provider-configuration)
- [🎨 Creation Workflows](#-creation-modes)
- [✒️ Prose Craft Presets Comparison](#-prose-craft-presets)
- [🎭 19 Webnovel Subgenres & Platforms](#-webnovel-subgenres)
- [🔌 API & CLI Reference](#-api-reference)
- [📂 Project Directory Structure](#-project-directory-structure)
- [📚 Technical Documentation Index](#-specialized-docs)
- [🤝 Contributing & License](#-contributing--license)

---

<a id="-platform-overview"></a>
## 🌟 Platform Overview

Writing a coherent, commercially viable long-form novel (100,000 to 1,000,000+ words) using generic LLMs fails because:
1. **Context Drift**: Characters forget their injuries, items teleport across continents, and established magic costs vanish.
2. **AI Slop Prose**: Text fills with repetitive tropes, melodrama, therapy-speak, and cliché phrasing (*"a testament to"*, *"not X, but Y"*, *"a breath he didn't know he was holding"*).
3. **Pacing Collapse**: Early chapters rush through dopamine hits without narrative grounding, or middle chapters stall in endless repetitive dialogue loops.
4. **Lack of Mid-Flight Controllability**: The author cannot steer the direction without throwing away the entire manuscript or breaking canon.

**NovelForge-EN** resolves these architectural flaws through an interlocking suite of deterministic compilers, living ledgers, multi-pass craft engines, and real-time author control channels.

| Challenge in AI Novel Writing | How NovelForge-EN Solves It |
| :--- | :--- |
| **Context Amnesia** | **Living Story Memory**: Automatic Chapter Digests + Deterministic *Story So Far* compiler injecting tiered history and carry-forward world states into a 65k token budget. |
| **AI Slop & Repetitive Tics** | **Prose Craft & Tic Scrubbing**: Multi-pass scene drafting with subtext packets, protagonist voice profiles, and deterministic AI-tic catalogue elimination. |
| **Uncalibrated Dopamine & Rhythm** | **Webnovel Style Engine**: Platform conventions (Novelpia, KakaoPage), dynamic beat pacing (2–3 grounding beats in Ch 1 vs. 4–6 in climax), and 6-dimension conformance grading. |
| **Uncontrollable Generation** | **Director Control Room**: Live Directive Book (MUST / PREFER / AVOID / IDEA) and instant *Canon Rewind & Replan* from chapter N. |
| **Accidental Overwrites** | **Manuscript Safety Suite**: Automatic SQLite pre-migration backups, author field locks, and immutable server-side revision snapshots with full diff & restore. |

---

<a id="-system-architecture"></a>
## 🏗️ System Architecture

The following diagram illustrates the end-to-end narrative lifecycle within NovelForge-EN:

```mermaid
flowchart TD
    subgraph Ingestion ["1. Deconstruction & Ideation"]
        EPUB["Reference Manuscript (EPUB/TXT/DOCX)"] --> Deconstruct["Reverse-Engineering Lab"]
        Deconstruct --> Genome["Narrative Genome & Fingerprint"]
        Brief["Author Brief / Story Charter"] --> Ideation["Diversity-Gated Ideation"]
        Genome --> Ideation
        Ideation --> Architecture["Novel Architecture (Volumes & Acts)"]
    end

    subgraph StudioBible ["2. Novel Intelligence Studio"]
        Architecture --> BibleGen["11-Ledger Bible Generation"]
        BibleGen --> Ledgers["Living Ledgers (Characters, Rules, Threads, Promises, Power)"]
        Directives["Director Directive Book (MUST / PREFER / AVOID)"] --> Ledgers
    end

    subgraph ChapterPlanning ["3. Dynamic Planning & Context Compiler"]
        Ledgers --> Compiler["65k Context Compiler"]
        Memory["Story Memory (Digests & World State)"] --> Compiler
        Compiler --> BeatPlanner["Context-Aware Dynamic Beat Planner"]
        BeatPlanner --> Blueprints["Chapter Blueprints (Grounding / Progression / Climax)"]
    end

    subgraph ProseCraftLayer ["4. Prose Craft Multi-Pass Engine"]
        Blueprints --> SceneSplitter["Scene Decomposition"]
        SceneSplitter --> Subtext["Subtext Packets & Protagonist Voice"]
        Subtext --> SceneDraft["Scene-by-Scene Drafting with Boundary Stitching"]
        SceneDraft --> Conformance["Webnovel Conformance Grader"]
        Conformance --> Critic["Adversarial Critic & AI-Tic Elimination"]
        Critic --> HookSharpener["Hook Sharpener & Cliffhanger Engineering"]
    end

    subgraph ReviewAndExport ["5. Living Canon & Export"]
        HookSharpener --> Continuity["Continuity Guard & Story Digest"]
        Continuity --> Proposals["Bible Update Proposals"]
        Proposals --> Ledgers
        Continuity --> Export["Episodic Webnovel HTML / EPUB / Markdown"]
    end

    subgraph DirectorLoop ["Director Feedback Loop"]
        DirectorPanel["Director Control Room"] -.->|"Rewind to Ch N & Replan"| BeatPlanner
        DirectorPanel -.->|"Inject Real-time Directive"| Directives
    end
```

---

<a id="-core-systems-deep-dive"></a>
## ⚡ 8 Core Systems Deep-Dive

<a id="1-autonomous-novel-pipeline-end-to-end"></a>
### 1. Autonomous Novel Pipeline (End-to-End)
NovelForge-EN can autonomously transform a raw concept or a reference manuscript into a complete, publishable webnovel:
- **Narrative Deconstruction**: Ingests EPUB, TXT, Markdown, or DOCX files. Automatically detects chapters, extracts structural beats, isolates character relationship trajectories, and determines pacing rhythms.
- **Narrative Fingerprint**: Distills the source's narrative density, interiority share, dialogue-to-action ratio, and scene function patterns without copying any text, character names, or settings.
- **Diversity-Gated Storyline Ideation**: Formulates three radically distinct narrative premises adhering strictly to author-defined boundaries and anti-cliché diversity gates.
- **Dynamic Beat Planning**: Calibrates pacing based on chapter function:
  - *Early Chapters (Setup / Grounding)*: 2–3 expansive beats focused on orientation, sensory grounding, and protagonist interiority.
  - *Middle Progression*: 3–4 beats advancing conflicts and tactical progression.
  - *Escalation & Climax*: 4–6 rapid beats maximizing tension, reversals, and cliffhangers.
- **Whole-Novel Audit & Publishing**: Runs full continuity checks, reward drought audits, and exports clean EPUBs with embedded TOC, metadata, and webnovel episodic HTML.

<a id="2-director-deep-input--live-control-room"></a>
### 2. Director Deep-Input & Live Control Room
Never lose control of an autonomous generation run. The **Director Control Room** allows authors to intervene dynamically in real time:
- **Live Directive Book**: Submit standing instructions at three distinct scopes:
  - `novel`: Applies globally across all remaining volumes.
  - `arc`: Governs the current volume or major plot arc.
  - `chapter`: Injected strictly into the immediate next chapter.
  - Categorized by authority: `MUST` (strict requirement), `PREFER` (soft preference), `AVOID` (negative constraint), and `IDEA` (creative inspiration).
- **Dynamic Canon Rewind & Replan**: If chapter 14 takes an unintended turn:
  1. Author enters: *"Redo from chapter 14: Protagonist hides his identity from the guild master."*
  2. Canon and ledgers immediately roll back to chapter 13.
  3. Discarded chapters are preserved in an immutable history archive.
  4. The chapter blueprint window is dynamically re-planned under the new directive.
  5. Generation resumes seamlessly.

<a id="3-webnovel-style-engine--conformance-grader"></a>
### 3. Webnovel Style Engine & Conformance Grader
Traditional LLM prose sounds like dry Western literary fiction or academic summaries. The **Webnovel Style Engine** enforces authentic serialized webnovel craft:
- **Mobile-Optimized Rhythm**: Short, punchy 1–2 sentence paragraphs optimized for mobile reading.
- **Dual-Layer Interiority**: The protagonist's private commentary rendered in `'single quotes'` immediately following significant dialogue or high-stakes developments.
- **Status & System Windows**: Clean, bracketed status blocks (`[System]`, `[Skill Activated]`) treated as narrative beats rather than dumped text.
- **19 Subgenre Archetypes**: Instant calibration for Regression, System Apocalypse, Hunter/Gate, Tower Climb, Murim, Cultivation, Villainess Transmigration, Academy, and more.
- **Deterministic 6-Dimension Conformance Grader**: Analyzes every draft without model overhead:
  1. *Rhythm*: Paragraph lengths, sentence density, and line-break cadence.
  2. *Inner Voice*: Frequency and placement of protagonist private verdicts.
  3. *Conventions*: Status window formatting, SFX lines, and English-adapted address forms.
  4. *Momentum*: Forward narrative velocity and absence of recap bloat.
  5. *Reward Cadence*: Frequency of micro-payoffs, reputation shifts, and face-slaps.
  6. *Ending Hook*: Detection of cliffhanger strength vs. passive fade-outs.

<a id="4-prose-craft-multi-pass-engine"></a>
### 4. Prose Craft Multi-Pass Engine
Chapter generation is split into dedicated, specialized architectural passes:
- **Scene-by-Scene Decomposition**: Beats are grouped into 2–4 cohesive scenes. Each scene is drafted with a dedicated scene brief carrying forward the previous scene's *exact* ending lines, last speaker, physical coordinates, and carried tension.
- **Character Subtext Packets**: Before drafting dialogue, the engine compiles:
  - What each present character wants from the protagonist.
  - What they are actively suppressing or concealing.
  - Leverage, conversational tactics, and speech mannerisms.
  - What the protagonist is likely to misread.
- **Protagonist Voice Dossier**: Injects private humor, self-deception patterns, calculation styles, and cognitive biases.
- **Deterministic AI-Tic Elimination**: Identifies and scrubs over 50 mechanical AI prose habits:
  - *"Not X, but Y"* / *"Not merely X, but Y"*
  - *"A testament to..."* / *"A silent reminder of..."*
  - *"The man who..."* / *"The woman who..."*
  - *"A breath he didn't know he was holding"*
  - Emotional cocktail stacking (*"A mixture of fear, awe, and grudging respect"*)
  - Therapy-speak and anachronistic psychological jargon
- **Hook Sharpener**: Detects soft endings and rewrites the final lines into crisis, revelation, decision, or threat-arrival cliffhangers.

<a id="5-65k-context-compiler--story-memory"></a>
### 5. 65k Context Compiler & Story Memory
To take full advantage of long-context models like **Kimi K3** and **Gemini 2.5 Pro**, NovelForge-EN utilizes a **120,000 character (~30k+ token)** context compiler:
- **Structured Chapter Digests**: After every chapter, a background extraction isolates key events, persistent state changes, knowledge deltas, opened/closed hooks, promises, and physical endings.
- **Deterministic Story So Far Compiler**: Generates tiered recaps:
  - *Immediate Past (Last 3 Chapters)*: Full scene-level resolution.
  - *Current Arc (Chapters 4–15)*: Compressed beat summaries.
  - *Distant Canon*: Milestone summaries and permanent world alterations.
- **Carry-Forward World State**: Durably tracks who is injured, who holds specific key items, faction diplomatic states, and who is dead.
- **Continuity Guard**: Scans drafts for prohibited reveals, dead entities taking actions, teleporting characters, contradictory timelines, and dropped promises.

<a id="6-novel-intelligence-studio-novel-bible-20"></a>
### 6. Novel Intelligence Studio (Novel Bible 2.0)
The **Novel Bible** is a living, evidence-backed knowledge network composed of 11 interlocking ledgers:
1. **Story Foundation**: Premise, themes, philosophical conflict, narrative tone.
2. **Reader Contract**: Genre promises, dopamine cadence, taboos, and payoff timetables.
3. **Theme Map**: Visualized motif progression and symbolic stakes.
4. **Power System & Rules**: Tier ladders, hard costs, limits, backlash mechanics, and resource scarcity.
5. **Character Dossiers & Voices**: Aliases, speech patterns, private agendas, and consistency rules.
6. **Relationship Matrices**: Dynamic tracking of Trust, Affection, Fear, Dependency, and Resentment.
7. **Knowledge Facts Matrix**: Tracks who knows what, who suspects what, and who holds false beliefs.
8. **Plot Threads Ledger**: Active, dormant, and resolved plot arcs with overdue alerts.
9. **Promises & Payoffs**: Explicit setup-and-payoff contracts with chapter deadlines.
10. **World Rules & Timeline**: Immutable physical laws and chronological event history.
11. **Webnovel Style Profile**: Platform targets, POV mechanics, and genre engines.

- **Living Bible Proposal System**: As chapters are written, the engine proposes updates. Authors can accept, reject, edit, or tag entries as *plan-not-canon* or *unreliable narration*.
- **Author Field Locks**: Human edits are protected with author locks; automated background sync will never overwrite locked fields.

<a id="7-studio-workbench-cards--workflow-automation"></a>
### 7. Studio Workbench, Cards & Workflow Automation
For authors who prefer hands-on writing or hybrid collaboration:
- **Schema-First Card Modeling**: Define custom JSON Schemas for any entity type (`Settings → Card Types`) with inheritance, embedded records, and field-level validation.
- **Instruction-Streaming AI Card Generation**: Generate cards field-by-field in real time. Submit feedback to refine specific fields without regenerating the entire card.
- **Inspiration Assistant**: A dedicated conversational partner in the side panel equipped with ReAct tool-calling, cross-project card referencing, and thinking mode.
- **Ideas Workbench**: A scratchpad environment for brainstorming and collecting material that can be converted into formal project cards with one click.
- **Code-Style Workflow Studio**: Build deterministic or AI-assisted automation pipelines using Python-style execution syntax, with natural language generation via the **Workflow Agent**.
- **Dual Graph Engine**: Store entity relationships in SQLite or connect directly to local **Neo4j** instances.

<a id="8-enterprise-hardening--manuscript-safety"></a>
### 8. Enterprise Hardening & Manuscript Safety
NovelForge-EN is built with strict production guarantees:
- **Pre-Migration SQLite Backups**: Every schema migration automatically creates a timestamped database backup (`.pre-<rev>-<stamp>.bak`).
- **Server-Side Revision History**: Every overwrite (manual save, AI regeneration, or architecture upsert) creates an immutable server snapshot with diff viewing and one-click rollback.
- **Concurrency-Safe Budget Engine**: Distributed worker leases, repair-call reservations, and conservative charging of in-flight provider requests prevent budget overruns.
- **Credential Masking**: All LLM provider keys are masked in API responses (`••••last4`).
- **Zero Disruption Guarantee**: Zero system-wide VPN requirements; operates cleanly on standard network stacks with application-level proxy support.

---

<a id="-visual-tour--screenshots"></a>
## 📸 Visual Tour & Screenshot Showcase

### 1. Autonomous Novel Studio & Creation Wizard
Configure full autonomous pipeline runs: upload a reference manuscript, set quality presets, define the Story Charter brief, and choose your Webnovel Style Profile.

<p align="center">
  <img src="docImgs/autonomous_studio.png" alt="Autonomous Studio Creation Wizard" width="95%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

### 2. Project Bookshelf & Dashboard
Centralized management for all your creative projects, reverse-engineered reference bibles, and active manuscripts.

<p align="center">
  <img src="docImgs/dashboard_view.png" alt="NovelForge Project Bookshelf" width="95%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

### 3. Novel Intelligence Studio & Story Charter
The living command center for world lore, character dossiers, plot threads, and the foundational Story Charter.

<p align="center">
  <img src="docImgs/novel_bible_view.png" alt="Novel Intelligence Studio" width="95%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

### 4. Card Library, Card Hierarchy & Inspiration Assistant
Explore structured project cards, manage parent-child relationships, and brainstorm with the ReAct Inspiration Assistant.

<p align="center">
  <img src="docImgs/project_editor_view.png" alt="Card Library and Inspiration Assistant" width="95%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

### 5. Chapter Studio: Context Injection & Writing Environment
The core drafting environment with real-time entity context injection, word-count control, and quick contextual polishing.

<p align="center">
  <img src="docImgs/README/image-27.png" alt="Chapter Studio Drafting" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
  <img src="docImgs/README/image-8.png" alt="Contextual Polish and Rewrite" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

### 6. Streaming Field-Level AI Card Generation
Field-by-field interactive AI generation. Review, refine, and provide feedback on individual fields before committing.

<p align="center">
  <img src="docImgs/README/image-28.png" alt="Field-Level Streaming Generation" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
  <img src="docImgs/README/image-29.png" alt="Card Feedback and Confirmation" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

### 7. Workflow Studio & Natural Language Workflow Agent
Build automated pipeline workflows visually or via Python-style code, or let the natural language Workflow Agent construct them for you.

<p align="center">
  <img src="docImgs/README/image-24.png" alt="Visual Workflow Canvas" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
  <img src="docImgs/README/image-30.png" alt="Code-Style Workflow Editor" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

<p align="center">
  <img src="docImgs/README/image-35.png" alt="Workflow Agent Multi-Step Execution" width="95%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

### 8. Schema-First Studio & Knowledge Graph
Design dynamic card data schemas and explore entity relationship networks stored in SQLite or Neo4j.

<p align="center">
  <img src="docImgs/README/image-10.png" alt="Schema Studio Builder" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
  <img src="docImgs/README/image-5.png" alt="Knowledge Graph Entity Extraction" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

### 9. Ideas Workbench
A free-form creative scratchpad for capturing inspiration, cross-referencing lore, and migrating ideas into formal novel projects.

<p align="center">
  <img src="docImgs/README/image-21.png" alt="Ideas Workbench Canvas" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
  <img src="docImgs/README/image-22.png" alt="Cross-Project Card Migration" width="48%" style="border-radius: 6px; border: 1px solid #e1e4e8;" />
</p>

---

<a id="-getting-started"></a>
## 🚀 Getting Started

<a id="prerequisites"></a>
### Prerequisites
- **Python**: Version `3.11` or `3.12`
- **Node.js**: Version `18.x` or `20.x` with `npm`
- **Operating System**: Windows 10/11, macOS, or Linux (Ubuntu 20.04+)
- **Optional**: Neo4j Desktop 5.16+ (SQLite is enabled by default for graph relationships)

---

<a id="windows-quick-start-one-click"></a>
### Windows Quick Start (One-Click)

The repository root includes three automated batch scripts:

1. **Install Dependencies**:
   ```bat
   install.bat
   ```
   *Creates the Python virtual environment at `backend/venv`, installs backend requirements, and runs `npm install` for the frontend.*

2. **Start Backend Server**:
   ```bat
   run-backend.bat
   ```
   *Starts the FastAPI backend at `http://127.0.0.1:54321`.*

3. **Start Frontend Client**:
   ```bat
   run-frontend.bat
   ```
   *Launches the Electron desktop application and Vite dev server.*

---

<a id="linux--macos-installation"></a>
### Linux / macOS Installation

```bash
# 1. Clone the repository
git clone https://github.com/Sigmaaaaa12343/NovelForge-EN.git
cd NovelForge-EN

# 2. Setup Backend Environment
cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI backend
python3 main.py
```

In a second terminal:

```bash
# 3. Setup and Launch Frontend
cd NovelForge-EN/frontend
npm install

# Run as Electron desktop app:
npm run dev

# Or run in standard web browser mode:
npm run dev:web
```

Open your browser to `http://localhost:5173` if running in web mode.

---

<a id="llm-provider-configuration"></a>
### LLM Provider Configuration

Navigate to **Settings → LLM Config** in the app to configure your model credentials. NovelForge-EN supports all major AI providers:

- **Kimi K3 (Moonshot AI)**: Recommended for full 65k context compiler autonomous pipeline.
- **OpenAI**: GPT-4o, GPT-4o-mini, o1, o3-mini.
- **Anthropic**: Claude 3.5 Sonnet, Claude 3.7 Sonnet.
- **Google Gemini**: Gemini 1.5 Pro, Gemini 2.0 Flash, Gemini 2.5 Pro.
- **DeepSeek**: DeepSeek-V3, DeepSeek-R1 (via OpenAI-compatible endpoint).
- **Local / Self-Hosted**: Ollama, vLLM, LocalAI, LM Studio.

> [!NOTE]
> All API credentials are encrypted locally and masked in all UI displays and API responses (`••••last4`).

---

<a id="-creation-modes"></a>
## 🎨 Creation Workflows

NovelForge-EN offers three primary ways to write novels:

### Mode A: Fully Autonomous Pipeline
1. Click **Create Novel** in the top navigation.
2. Drop an existing EPUB/TXT manuscript or input a story brief into the **Story Charter**.
3. Select your target **Platform** and **Subgenre Template** (or let the engine auto-detect).
4. Choose your **Quality / Budget Preset** (`Economy`, `Balanced`, `Quality`).
5. Click **Start Generation**.
6. Monitor progress in real time. Use the **Director Control Room** to add directives or rewind chapters if necessary.
7. Export your finished novel to EPUB or episodic HTML.

### Mode B: Novel Intelligence Studio (Human-in-the-Loop)
1. Create a new project with the **Novel Intelligence Studio** template.
2. Fill out or AI-generate the 11 living ledgers (Foundation, Characters, Power System, World Rules, etc.).
3. Lock important canonical fields using **Author Locks**.
4. Generate volume and chapter blueprints.
5. In the Chapter Editor, trigger multi-pass drafting with context injection.
6. Review proposed Bible updates after each chapter to keep lore evergreen.

### Mode C: Snowflake Method & Visual Workflows
1. Create a project using the **Snowflake Method** template.
2. Expand your story step-by-step: One-Line Pitch → Story Outline → Worldview Setting → Core Blueprint → Volume Outlines → Stage Outlines → Chapter Outlines.
3. Use the **Inspiration Assistant** for targeted character development and scene troubleshooting.
4. Automate recurring tasks with custom visual workflows in the **Workflow Studio**.

---

<a id="-prose-craft-presets"></a>
## ✒️ Prose Craft Presets Comparison

NovelForge-EN provides four distinct quality presets for chapter drafting and polishing:

| Preset | Drafting Method | Subtext Packets | Protagonist Voice | AI-Tic Scrubbing | Hook Sharpener | Relative Cost | Best For |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`Legacy single-shot`** | Single LLM Call | ❌ | ❌ | ❌ | ❌ | 1.0x | Quick prototyping, background outlines |
| **`Single-shot + critic`** | Single Call + Review | ❌ | ❌ | Basic | Basic | 1.8x | Budget-conscious serialization |
| **`Scenes + polish`** | Scene Decomposition | ✅ | ✅ | Standard | ✅ | 3.2x | High-quality standard chapters |
| **`Elite multi-pass`** | Scene-by-Scene Multi-Pass | ✅ | ✅ | **Full Deterministic** | **Adversarial** | 5.5x | Flagship releases, premiere & climax chapters |

---

<a id="-webnovel-subgenres"></a>
## 🎭 19 Webnovel Subgenres & Platforms

### Supported Platforms
- **Novelpia**: Mobile-first cadence, frequent dopamine loops, system status windows, lighthearted inner monologues.
- **Munpia**: Traditional Korean fantasy/murim standards, disciplined progression, serious stakes, honorific conventions.
- **KakaoPage**: High-stakes cliffhangers, page-turner episodic structures, romance-fantasy / rofan tropes.
- **Naver Series**: Polished modern fantasy, returnee mechanics, corporate/hunter guild dynamics.
- **Royal Road**: Western progression fantasy, LitRPG mechanics, detailed statistical leveling, expansive worldbuilding.

### 19 Built-in Subgenre Archetypes
1. `regression` — Second chance, future knowledge advantage, vengeance or tragedy prevention.
2. `system_apocalypse` — Earth integration, tutorial survival, stat windows, skill acquisitions.
3. `hunter_gate` — Modern dungeon awakenings, hunter guilds, rank classifications, media spectacle.
4. `tower_climb` — Floor-by-floor trials, admin sponsors, shop systems, ruthless competition.
5. `dungeon` — Labyrinth ecology, monster drops, survival mechanics, territory building.
6. `villainess_transmigration` — Otome game villainess survival, death flag evasion, romantic subversion.
7. `academy` — Magic academy competitions, prodigy rivalries, mock battles, student rankings.
8. `murim` — Wuxia factions, qi cultivation, unorthodox sects, martial philosophy.
9. `cultivation` — Xianxia realms, heavenly tribulations, pill forging, face-slap progression.
10. `reincarnated_noble` — Weakest baron's son, territory development, political maneuvering.
11. `modern_fantasy` — Hidden occult societies, supernatural business, urban investigations.
12. `litrpg` — Explicit numbers, leveling math, class specializations, quest notifications.
13. `office_life` — Corporate warfare, modern workplace progression, dry salaryman humor.
14. `rofan` — Romance fantasy, high-society gossip, contractual marriages, imperial intrigue.
15. `returnee` — Conquering another realm, returning home to family, overwhelming power superiority.
16. `apocalypse_survival` — Resource scarcity, safe-zone construction, harsh moral choices.
17. `sports` — Athletic system, tactical playbooks, tournament climb, physical training arcs.
18. `entertainment_industry` — Actor/idol regression, method acting breakthroughs, box office success.
19. `historical_transmigration` — Modern technology introduced to ancient dynasties, military reforms.

---

<a id="-api-reference"></a>
## 🔌 API & CLI Reference

FastAPI exposes a complete, OpenAPI-compliant REST interface on `127.0.0.1:54321`:

### Core Endpoints

| Area | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Autonomous Jobs** | `POST` | `/api/autonomous/jobs` | Create and launch autonomous novel generation job |
| | `GET` | `/api/autonomous/jobs/{id}` | Inspect live job status, current stage, and token metrics |
| | `POST` | `/api/autonomous/jobs/{id}/pause` | Pause running job execution |
| | `POST` | `/api/autonomous/jobs/{id}/resume` | Resume paused or interrupted job |
| **Director Steering** | `GET` | `/api/autonomous/jobs/{id}/style` | Retrieve active Webnovel Style Profile |
| | `PATCH` | `/api/autonomous/jobs/{id}/style` | Live deep-merge update of style profile |
| | `POST` | `/api/autonomous/jobs/{id}/directives` | Append a MUST / PREFER / AVOID directive |
| | `GET` | `/api/autonomous/jobs/{id}/redo/plan` | Preview chapter rewind and discard plan |
| | `POST` | `/api/autonomous/jobs/{id}/redo` | Execute canon rewind to chapter N and replan |
| **Story Charter** | `GET` | `/api/story-charter/{project_id}` | Retrieve project Story Charter |
| | `POST` | `/api/story-charter/interpret` | AI interpretation of raw author brief |
| | `POST` | `/api/story-charter/check` | Deterministic conflict check against existing lore |
| **Prose Craft** | `POST` | `/api/craft/grade` | Instant deterministic webnovel craft grading |
| | `POST` | `/api/craft/polish` | Surgical line polish on cited spans |
| | `POST` | `/api/craft/hook-sharpen` | Adversarial cliffhanger hook rewrite |
| **Novel Bible** | `GET` | `/api/bible/{project_id}/summary` | Retrieve 11-ledger health and completeness summary |
| | `POST` | `/api/bible/{project_id}/proposals/review` | Accept or reject proposed chapter lore updates |
| | `POST` | `/api/bible/cards/{id}/locks` | Toggle author locks on specific Bible fields |

Interactive API documentation is accessible at `http://127.0.0.1:54321/docs` when the backend is running.

---

<a id="-project-directory-structure"></a>
## 📂 Project Directory Structure

```
NovelForge-EN/
├── install.bat                 # One-click Windows installer (Python venv + npm)
├── run-backend.bat             # One-click Windows backend runner
├── run-frontend.bat            # One-click Windows Electron/Vite runner
├── docImgs/                    # Visual assets, architecture diagrams, screenshots
├── docs/                       # Specialized operations & architecture guides
│   ├── ci.md                   # CI workflows, branch protection & ratchets
│   ├── kimi-k3.md              # Kimi K3 token budgets & preflight protocols
│   ├── live-qualification.md   # Live credentialed qualification procedures
│   ├── migrations.md           # Database migration policies & SQLite backups
│   ├── prose-craft.md          # Multi-pass scene drafting & AI-tic elimination
│   ├── security.md             # Local loopback security boundary & key masking
│   ├── setup.md                # Clean installation & troubleshooting guide
│   ├── story-charter.md        # Author brief interpretation & boundary scoping
│   ├── story-memory.md         # Chapter digests, Story So Far, continuity guard
│   └── webnovel-style-engine.md# 19 subgenres, platforms & conformance grader
├── backend/                    # FastAPI Core Backend
│   ├── app/
│   │   ├── api/                # REST endpoints (/autonomous, /craft, /bible, etc.)
│   │   ├── db/                 # SQLModel definitions & Alembic migrations
│   │   ├── schemas/            # Pydantic schemas for cards, bibles, and ledgers
│   │   └── services/           # Core business logic
│   │       ├── autonomous/     # End-to-end pipeline, beat planner, budget ledger
│   │       ├── forge/          # Context compiler, living memory, prose craft
│   │       └── webnovel/       # 19 subgenre templates, conformance grader
│   ├── tests/                  # Deterministic test suite (300+ pytest tests)
│   └── main.py                 # Application entry point (127.0.0.1:54321)
└── frontend/                   # Electron + Vue 3 Desktop Application
    ├── src/
    │   ├── main/               # Electron main process & IPC handlers
    │   ├── preload/            # Preload scripts & secure bridges
    │   └── renderer/           # Vue 3 Renderer Application
    │       ├── components/     # UI components (Director, Bible, Studio, Editor)
    │       ├── composables/    # Reactive Pinia composables
    │       ├── views/          # Views (Dashboard, Autonomous, Editor, Workflows)
    │       └── api/            # Typed backend client wrappers
    └── package.json            # Node dependencies and build scripts
```

---

<a id="-specialized-docs"></a>
## 📚 Technical Documentation Index

For in-depth operational and architectural specifications, consult the dedicated guides in [`docs/`](./docs):

- 🛠️ [**Setup & Installation Guide**](./docs/setup.md) — Detailed environment setup, dependencies, and troubleshooting.
- 📱 [**Webnovel Style Engine & Conformance**](./docs/webnovel-style-engine.md) — Subgenre mechanics, platform conventions, and rhythm grading.
- ✒️ [**Prose Craft Specification**](./docs/prose-craft.md) — Multi-pass scene drafting, subtext packets, voice dossiers, and AI-tic removal.
- 📜 [**Story Charter Guide**](./docs/story-charter.md) — Author briefs, boundary enforcement, and prompt injection precedence.
- 🧠 [**Story Memory & Living Canon**](./docs/story-memory.md) — Chapter digests, world state carry-forward, and continuity guards.
- 🤖 [**Kimi K3 Autonomous Pipeline**](./docs/kimi-k3.md) — 65k context budget allocation and structured output recovery.
- 🛡️ [**Security & Loopback Boundary**](./docs/security.md) — Local-only binding, credential masking, and isolation rules.
- 🗄️ [**Database Migrations & Safety**](./docs/migrations.md) — Forward schema migrations and automatic SQLite pre-migration backups.
- 🚦 [**CI & Branch Protection**](./docs/ci.md) — Deterministic testing gates and workflow ratchets.
- 🧪 [**Live Qualification Procedures**](./docs/live-qualification.md) — Step-by-step instructions for live-provider testing.

---

<a id="-contributing--license"></a>
## 🤝 Contributing & License

### Contributing
Contributions from both narrative designers and software engineers are warmly welcomed!
- Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for commit standards, pull request workflows, and test coverage requirements.
- Review [ROADMAP.md](./ROADMAP.md) to see upcoming milestones.

### Dual License Model
NovelForge-EN is released under a **dual-license model**:
- **Open Source**: By default, licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**. See [LICENSE](./LICENSE) for full details.
- **Commercial SaaS / Hosted Deployment**: Providing NovelForge-EN as a cloud-hosted backend or commercial SaaS to third parties requires a commercial license from the original authors.

---

<div align="center">
  <sub>Engineered with precision for authors, worldbuilders, and narrative architects.</sub>
</div>
