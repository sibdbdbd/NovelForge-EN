import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import type { AuthorDirective, AutonomousJob, WebnovelStyleProfile } from '@renderer/api/autonomous'
import { directiveProblem, directiveRange, linesToList, listToLines, stylePatch, useDirector, webnovelParams, type DirectorApi } from '../useDirector'

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
function directive(id: string, over: Partial<AuthorDirective> = {}): AuthorDirective {
  return { id, scope: 'novel', chapter_from: 0, chapter_to: 0, kind: 'must', text: `note ${id}`, applies_to: ['planning', 'drafting'], created_at: '', consumed_by_chapters: [], active: true, ...over }
}
function makeApi(over: Partial<DirectorApi> = {}): DirectorApi {
  let rows: AuthorDirective[] = [directive('dir-1')]
  return {
    listSubgenres: vi.fn(async () => [{ key: 'hunter_gate', label: 'Hunter / Gate' }, { key: 'regression', label: 'Regression' }, { key: 'platform:novelpia', label: 'novelpia', note: 'short paragraphs' }]),
    getStyle: vi.fn(async () => profile()),
    patchStyle: vi.fn(async (_id, patch) => profile({ ...(patch as Partial<WebnovelStyleProfile>), derived_from: 'author' })),
    getStylePreview: vi.fn(async () => ({ drafting: 'D', planning: 'P', critic: 'C' })),
    listDirectives: vi.fn(async () => rows),
    addDirective: vi.fn(async (_id, body) => { const row = directive(`dir-${rows.length + 1}`, body as Partial<AuthorDirective>); rows = [...rows, row]; return row }),
    patchDirective: vi.fn(async (_id, did, patch) => { rows = rows.map((r) => (r.id === did ? { ...r, ...patch } : r)); return rows.find((r) => r.id === did)! }),
    deleteDirective: vi.fn(async (_id, did) => { rows = rows.filter((r) => r.id !== did); return { removed: did } }),
    getRedoPlan: vi.fn(async (_id, from) => ({ from_chapter: from, latest_committed: 12, chapters_discarded: [from, 12].filter((n, i, a) => a.indexOf(n) === i), chapters_kept: from - 1, will_replan: true, job_stage: 'CHAPTER_GENERATION_LOOP', job_status: 'paused' })),
    redoFromChapter: vi.fn(async (_id, body) => ({ job: job({ status: 'queued', chapters_committed: body.from_chapter - 1 }), active: true })),
    getChapterQuality: vi.fn(async (_id, n) => ({ chapter: n, run_id: n, model_calls: 3, repair_attempts: 0, webnovel_after: { version: 'v', scores: { rhythm: 8 }, overall: 8, metrics: {}, findings: [], passed: true } })),
    ...over,
  }
}

describe('directive helpers', () => {
  it('formats chapter ranges', () => {
    expect(directiveRange({ scope: 'novel', chapter_from: 0, chapter_to: 0 })).toBe('all')
    expect(directiveRange({ scope: 'chapter', chapter_from: 12, chapter_to: 0 })).toBe('12')
    expect(directiveRange({ scope: 'arc', chapter_from: 12, chapter_to: 15 })).toBe('12–15')
  })
  it('validates like the backend', () => {
    expect(directiveProblem({ scope: 'novel', kind: 'must', text: '  ' }, 30)).toBe('text')
    expect(directiveProblem({ scope: 'chapter', kind: 'must', text: 'x' }, 30)).toBe('chapter_from')
    expect(directiveProblem({ scope: 'chapter', kind: 'must', text: 'x', chapter_from: 31 }, 30)).toBe('beyond_count')
    expect(directiveProblem({ scope: 'arc', kind: 'must', text: 'x', chapter_from: 5, chapter_to: 3 }, 30)).toBe('chapter_to')
    expect(directiveProblem({ scope: 'arc', kind: 'must', text: 'x', chapter_from: 5, chapter_to: 9 }, 30)).toBeNull()
    expect(directiveProblem({ scope: 'chapter', kind: 'must', text: 'x', chapter_from: 5 }, 0)).toBeNull() // count unknown before selection
  })
  it('computes a minimal deep patch and round-trips list fields', () => {
    const base = profile()
    const draft = profile({ narrator_register: 'grim_survivor', banned_moves: ['recap'] })
    draft.engine = { ...draft.engine, subgenre: 'regression' }
    draft.reader = { ...draft.reader, comedy_level: 'dry' } // unchanged nested value
    expect(stylePatch(base, draft)).toEqual({ narrator_register: 'grim_survivor', banned_moves: ['recap'], engine: { subgenre: 'regression' } })
    expect(stylePatch(base, profile())).toEqual({})
    expect(linesToList(listToLines(['F', ' E ', '', 'S']))).toEqual(['F', 'E', 'S'])
  })
  it('turns the Create Novel webnovel card into request params, omitting "let the engine decide"', () => {
    const empty = { platform: '', subgenre: '', perspective: '', narrator_register: '', thought_style: '', status_windows: 'auto' as const, comedy_level: '', directives_text: '', auto_start: true }
    expect(webnovelParams(empty)).toEqual({})
    expect(webnovelParams({ ...empty, status_windows: 'off', subgenre: 'regression', directives_text: ' The hero never begs. \n\nNo love triangle.', auto_start: false })).toEqual({
      subgenre: 'regression', status_windows: false, auto_start: false,
      directives: [{ scope: 'novel', kind: 'must', text: 'The hero never begs.' }, { scope: 'novel', kind: 'must', text: 'No love triangle.' }],
    })
    expect(webnovelParams({ ...empty, status_windows: 'on', platform: 'munpia', narrator_register: 'grim_survivor' })).toEqual({ platform: 'munpia', narrator_register: 'grim_survivor', status_windows: true })
  })
})

describe('useDirector', () => {
  it('loads style, subgenres and directives for the job and splits platform notes from templates', async () => {
    const api = makeApi()
    const d = useDirector(api, ref(job()))
    await d.load()
    expect(d.style.value?.engine.subgenre).toBe('hunter_gate')
    expect(d.subgenreTemplates.value.map((s) => s.key)).toEqual(['hunter_gate', 'regression'])
    expect(d.platformNotes.value.novelpia).toBe('short paragraphs')
    expect(d.directives.value.map((x) => x.id)).toEqual(['dir-1'])
    expect(d.hasProject.value).toBe(true)
  })

  it('patches the style and refreshes the preview only once it was opened', async () => {
    const api = makeApi()
    const d = useDirector(api, ref(job()))
    await d.saveStyle({ narrator_register: 'grim_survivor' })
    expect(api.patchStyle).toHaveBeenCalledWith(7, { narrator_register: 'grim_survivor' })
    expect(d.style.value?.derived_from).toBe('author')
    expect(api.getStylePreview).not.toHaveBeenCalled()
    await d.loadPreview()
    await d.applySubgenre('regression')
    expect(api.patchStyle).toHaveBeenLastCalledWith(7, { engine: { subgenre: 'regression' } })
    expect(api.getStylePreview).toHaveBeenCalledTimes(2)
  })

  it('adds, toggles and removes directives and rejects invalid ones client-side', async () => {
    const api = makeApi()
    const d = useDirector(api, ref(job()))
    await d.loadDirectives()
    expect(await d.addDirective({ scope: 'chapter', kind: 'must', text: 'x' })).toBeNull()
    expect(d.error.value).toBe('directive:chapter_from')
    expect(api.addDirective).not.toHaveBeenCalled()
    const row = await d.addDirective({ scope: 'arc', kind: 'prefer', text: '  Keep the assessor.  ', chapter_from: 13, chapter_to: 15 })
    expect(row?.text).toBe('Keep the assessor.')
    expect(d.directives.value).toHaveLength(2)
    await d.toggleDirective('dir-1')
    expect(d.directives.value[0].active).toBe(false)
    expect(d.activeDirectives.value.map((x) => x.id)).toEqual(['dir-2'])
    expect(await d.removeDirective('dir-1')).toBe(true)
    expect(d.directives.value.map((x) => x.id)).toEqual(['dir-2'])
  })

  it('gates redo on a paused job with committed chapters and forwards the note', async () => {
    const api = makeApi()
    const j = ref(job({ status: 'running' }))
    const d = useDirector(api, j)
    expect(d.canRedo.value).toBe(false)
    j.value = job({ status: 'paused' })
    expect(d.canRedo.value).toBe(true)
    await d.loadQuality(12)
    await d.loadQuality(3)
    expect(Object.keys(d.quality.value)).toEqual(['3', '12'])
    await d.planRedo(10)
    expect(d.redoPlan.value?.chapters_kept).toBe(9)
    const res = await d.redo({ from_chapter: 10, note: '  Open at the desk.  ' })
    expect(api.redoFromChapter).toHaveBeenCalledWith(7, expect.objectContaining({ from_chapter: 10, note: 'Open at the desk.', replan: true, auto_start: true }))
    expect(res?.job.chapters_committed).toBe(9)
    expect(d.redoPlan.value).toBeNull()
    expect(Object.keys(d.quality.value)).toEqual(['3']) // stale scores for discarded chapters are dropped
    expect(api.listDirectives).toHaveBeenCalled()
  })

  it('does nothing without a job and surfaces API errors', async () => {
    const api = makeApi({ getStyle: vi.fn(async () => { throw new Error('boom') }) })
    const d = useDirector(api, ref(null))
    expect(await d.loadStyle()).toBeNull()
    expect(api.getStyle).not.toHaveBeenCalled()
    const d2 = useDirector(api, ref(job()))
    expect(await d2.loadStyle()).toBeNull()
    expect(d2.error.value).toBe('boom')
    expect(d2.busy.value).toBeNull()
  })
})
