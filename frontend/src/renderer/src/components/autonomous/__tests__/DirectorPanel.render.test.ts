/**
 * Render-level regression test for the Director panel.
 *
 * Composable tests cover state transitions; this test renders the real SFC (Element Plus + i18n)
 * against the payload shapes the backend can legitimately return — sparse, null, or shaped by an older
 * server — and asserts the template never throws. A template `.length` on an undefined list is the
 * exact class of bug that unit tests missed and live QA caught.
 */
import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, defineComponent, h, nextTick, ref } from 'vue'
import { renderToString } from '@vue/server-renderer'
import ElementPlus, { ID_INJECTION_KEY, ZINDEX_INJECTION_KEY } from 'element-plus'
import { createI18n } from 'vue-i18n'
import type { AuthorDirective, AutonomousJob, ChapterQuality, WebnovelStyleProfile } from '@renderer/api/autonomous'
import { useDirector, type Director, type DirectorApi } from '@renderer/composables/useDirector'
import DirectorPanel from '../DirectorPanel.vue'
import en from '@renderer/locales/en/director.json'
import enAutonomous from '@renderer/locales/en/autonomous.json'
import enCommon from '@renderer/locales/en/common.json'

// The panel imports option constants from the API module, whose axios client reads browser globals at import time.
vi.mock('@renderer/api/request', () => ({ default: {}, API_BASE_URL: '', BASE_URL: '' }))

function job(over: Partial<AutonomousJob> = {}): AutonomousJob {
  return {
    id: 7, status: 'paused', stage: 'CHAPTER_GENERATION_LOOP', mode: 'fully_automatic', llm_config_id: 1, source_filename: 'book.epub', options: {}, original_project_id: 42, chapter_count: 30, chapters_committed: 12,
    progress_percent: 40, progress_message: '', stage_results: {}, warnings: [], model_calls: 0, input_tokens: 0, output_tokens: 0, attempts: [], stages: [], ...over,
  }
}
function profile(over: Partial<WebnovelStyleProfile> = {}): WebnovelStyleProfile {
  return {
    version: 'webnovel-style-1', platform: 'novelpia', perspective: 'first_person', narrative_distance: 'very_close', narrator_register: 'dry_cynical',
    narration: { thought_style: 'single_quotes', thought_density: 'dense', window_style: 'square_brackets', windows_enabled: true, sfx_style: 'em_dash', sfx_density: 'light', address: 'mixed', paragraph_rhythm: 'one_line', line_break_beats: true, chapter_title_style: 'numbered_with_title', tense: 'past', onomatopoeia_english: [] },
    engine: { subgenre: 'hunter_gate', progression_axis: 'Rank', tier_ladder: ['F', 'E', 'S'], reward_types: [], face_slap_cadence: 'regular', knowledge_advantage: '', world_hooks: [], typical_arc_shape: '', genre_vocabulary: [] },
    reader: { core_fantasy: '', dopamine_per_chapter: 1, reward_gap_max_chapters: 2, emotional_palette: [], comedy_level: 'dry', romance_mode: 'slow_burn_subplot', violence_level: 'moderate', interiority_share_target: 0.28 },
    chapter: { words_target: 2500, opening_rule: '', ending_rule: '', hook_in_last_line: true, min_scenes: 2, max_scenes: 4, recap_allowed: false, author_note_style: 'none' },
    banned_moves: [], signature_moves: [], derived_from: 'detected', detection_notes: '', updated_at: '', ...over,
  }
}

/** Directive rows as an older backend serialised them: no `consumed_by_chapters`, `applies_to`, `created_at` or `active`. */
function legacyDirective(id: string): AuthorDirective {
  return { id, scope: 'chapter', chapter_from: 3, chapter_to: 0, kind: 'must', text: 'Open at the desk.' } as AuthorDirective
}

function makeApi(over: Partial<DirectorApi> = {}): DirectorApi {
  return {
    listSubgenres: vi.fn(async () => [{ key: 'hunter_gate', label: 'Hunter / Gate' }, { key: 'platform:novelpia', label: 'novelpia', note: 'short paragraphs' }]),
    getStyle: vi.fn(async () => profile()),
    patchStyle: vi.fn(async () => profile()),
    getStylePreview: vi.fn(async () => ({ drafting: 'D', planning: 'P', critic: 'C' })),
    listDirectives: vi.fn(async () => [legacyDirective('pending-1')]),
    addDirective: vi.fn(async () => legacyDirective('pending-2')),
    patchDirective: vi.fn(async () => legacyDirective('pending-1')),
    deleteDirective: vi.fn(async () => ({ removed: 'pending-1' })),
    getRedoPlan: vi.fn(async (_id, from) => ({ from_chapter: from, latest_committed: 12, chapters_discarded: [], chapters_kept: from - 1, will_replan: true, job_stage: 'CHAPTER_GENERATION_LOOP', job_status: 'paused' })),
    redoFromChapter: vi.fn(async () => ({ job: job(), active: true })),
    // A committed chapter whose craft passes never ran: no webnovel/critic blocks at all.
    getChapterQuality: vi.fn(async (_id, n) => ({ chapter: n, run_id: n, model_calls: 1, repair_attempts: 0 }) as ChapterQuality),
    ...over,
  }
}

const i18n = createI18n({ legacy: false, locale: 'en', fallbackLocale: 'en', messages: { en: { ...en, ...enAutonomous, ...enCommon } } })

/** Server-render every tab of the panel once, returning the HTML; a template exception rejects the promise. */
async function renderPanel(director: Director, j: AutonomousJob, tab: 'style' | 'directives' | 'redo' | 'quality'): Promise<string> {
  const Root = defineComponent({
    setup() {
      return () => h(DirectorPanel, { job: j, director, initialTab: tab })
    },
  })
  const app = createSSRApp(Root)
  app.use(ElementPlus)
  app.use(i18n)
  // Element Plus SSR contract: provide the id / z-index contexts it would otherwise warn about.
  app.provide(ID_INJECTION_KEY, { prefix: 1, current: 0 })
  app.provide(ZINDEX_INJECTION_KEY, { current: 0 })
  app.config.warnHandler = () => undefined // SSR-only Element Plus warnings are not what this test is about
  const html = await renderToString(app)
  await nextTick()
  return html
}

describe('DirectorPanel renders defensively', () => {
  it('survives legacy directive rows, a chapter with no craft data, and an empty redo plan', async () => {
    const api = makeApi()
    const j = job()
    const director = useDirector(api, ref(j))
    await director.load()
    await director.loadQuality(12)
    await director.planRedo(4)
    expect(director.directives.value[0].consumed_by_chapters).toBeUndefined()
    expect(director.quality.value[12].webnovel_after).toBeUndefined()
    expect(director.redoPlan.value?.chapters_discarded).toEqual([])

    const directives = await renderPanel(director, j, 'directives')
    expect(directives).toContain('Not used yet')
    expect(directives).toContain('Directives (1)')

    const quality = await renderPanel(director, j, 'quality')
    expect(quality).toContain('No conformance findings.')
    expect(quality).toContain('data-testid="quality-scores"')

    const redo = await renderPanel(director, j, 'redo')
    expect(redo).toContain('0 discarded')
    expect(redo).toContain('data-testid="redo-btn"')
  })

  it('renders a job with no project yet (pending directives, disabled redo/quality tabs) and a completed job with a redo history', async () => {
    const pending = job({ original_project_id: undefined as unknown as number, chapters_committed: 0, stage: 'INGEST', status: 'paused' })
    const d1 = useDirector(makeApi(), ref(pending))
    await d1.load()
    const html = await renderPanel(d1, pending, 'style')
    expect(html).toContain('data-testid="director-pending"')
    expect(html).toContain('data-testid="style-derived"')

    const finished = job({ status: 'completed', stage: 'DONE', chapters_committed: 6, stage_results: { redo_log: [{ from_chapter: 4, note: 'harder face-slap', at: '2026-09-09T15:27:55' }, { from_chapter: 2 }] } })
    const d2 = useDirector(makeApi(), ref(finished))
    await d2.load()
    const redo = await renderPanel(d2, finished, 'redo')
    expect(redo).toContain('Redo history')
    expect(redo).toContain('From chapter 4 with a note · 2026-09-09T15:27:55')
    expect(redo).not.toContain('data-testid="redo-blocker"')
  })

  it('blocks redo with the right reason while the job is running or before any chapter is committed', async () => {
    const running = job({ status: 'running' })
    const d1 = useDirector(makeApi(), ref(running))
    await d1.load()
    expect(await renderPanel(d1, running, 'redo')).toContain('Pause the job first')

    const fresh = job({ status: 'paused', chapters_committed: 0 })
    const d2 = useDirector(makeApi(), ref(fresh))
    await d2.load()
    expect(await renderPanel(d2, fresh, 'redo')).toContain('No committed chapter to redo yet.')
  })
})
