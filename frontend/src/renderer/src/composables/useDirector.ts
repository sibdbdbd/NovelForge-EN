/**
 * Director: the author's live steering channel over an autonomous job.
 *
 * - Webnovel Style Profile: load / patch (deep-merge) / preview the rendered prompt blocks.
 * - Author directives: novel / arc / chapter scoped notes with add / edit / toggle / remove.
 * - Redo from chapter N with a note: preview what is discarded, then rewind + requeue.
 * - Per-chapter quality: critic + webnovel conformance for any committed chapter.
 *
 * Works before the novel project exists (edits are parked on the job and applied when the
 * project is created) and after it exists (edits land on the project immediately). Kept free
 * of Element Plus and injected with its API so the state logic is unit-testable.
 */
import { computed, ref, type ComputedRef, type Ref } from 'vue'
import type { AuthorDirective, AutonomousJob, ChapterQuality, DirectivePatch, DirectiveRequest, JobResponse, RedoPlan, RedoRequest, StylePatch, StylePreview, SubgenreTemplateInfo, WebnovelStyleProfile } from '@renderer/api/autonomous'

export interface DirectorApi {
  listSubgenres: () => Promise<SubgenreTemplateInfo[]>
  getStyle: (jobId: number) => Promise<WebnovelStyleProfile>
  patchStyle: (jobId: number, patch: StylePatch) => Promise<WebnovelStyleProfile>
  getStylePreview: (jobId: number) => Promise<StylePreview>
  listDirectives: (jobId: number) => Promise<AuthorDirective[]>
  addDirective: (jobId: number, body: DirectiveRequest) => Promise<AuthorDirective>
  patchDirective: (jobId: number, directiveId: string, body: DirectivePatch) => Promise<AuthorDirective>
  deleteDirective: (jobId: number, directiveId: string) => Promise<{ removed: string }>
  getRedoPlan: (jobId: number, fromChapter: number) => Promise<RedoPlan>
  redoFromChapter: (jobId: number, body: RedoRequest) => Promise<JobResponse>
  getChapterQuality: (jobId: number, chapterNumber: number) => Promise<ChapterQuality>
}

/** Stages at which "redo from chapter N" is meaningful (mirrors director.REDO_STAGES). */
export const REDO_STAGES = new Set(['CHAPTER_GENERATION_LOOP', 'WHOLE_NOVEL_AUDIT', 'GLOBAL_REPAIR', 'EXPORT', 'DONE'])
export const CONFORMANCE_DIMENSIONS = ['rhythm', 'inner_voice', 'conventions', 'momentum', 'reward', 'ending'] as const

export type ConformanceDimension = (typeof CONFORMANCE_DIMENSIONS)[number]
export type DirectiveProblem = 'text' | 'chapter_from' | 'chapter_to' | 'beyond_count'

interface HttpErrorLike { response?: { data?: { detail?: string | { message?: string; code?: string } } }; message?: string }

function errorMessage(e: unknown): string {
  const err = (e ?? {}) as HttpErrorLike
  const detail = err.response?.data?.detail
  if (detail && typeof detail === 'object') return detail.message || detail.code || JSON.stringify(detail)
  return detail || err.message || String(e)
}

/** A directive's chapter span for display: "all", "12" or "12–15". */
export function directiveRange(d: Pick<AuthorDirective, 'scope' | 'chapter_from' | 'chapter_to'>): string {
  if (d.scope === 'novel' || !d.chapter_from) return 'all'
  const to = d.chapter_to && d.chapter_to !== d.chapter_from ? d.chapter_to : 0
  return to ? `${d.chapter_from}–${to}` : String(d.chapter_from)
}

/** Validation mirroring the backend: chapter/arc notes need a start chapter; arcs end after they start. */
export function directiveProblem(d: DirectiveRequest, chapterCount: number): DirectiveProblem | null {
  if (!d.text.trim()) return 'text'
  if (d.scope !== 'novel') {
    if (!d.chapter_from || d.chapter_from < 1) return 'chapter_from'
    if (chapterCount && d.chapter_from > chapterCount) return 'beyond_count'
    if (d.scope === 'arc' && d.chapter_to && d.chapter_to < d.chapter_from) return 'chapter_to'
  }
  return null
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === 'object' && !Array.isArray(v)
}

/**
 * Minimal deep patch from `base` to `draft` (changed leaves only; arrays compared whole).
 * Sending only what changed lets the backend re-seed template-owned fields when the subgenre
 * changes instead of having them overwritten by stale values from the editor.
 */
export function stylePatch(base: WebnovelStyleProfile, draft: WebnovelStyleProfile): StylePatch {
  const out: Record<string, unknown> = {}
  for (const key of Object.keys(draft) as Array<keyof WebnovelStyleProfile>) {
    const a: unknown = base[key]
    const b: unknown = draft[key]
    if (isPlainObject(a) && isPlainObject(b)) {
      const nested: Record<string, unknown> = {}
      for (const k of Object.keys(b)) {
        if (JSON.stringify(a[k]) !== JSON.stringify(b[k])) nested[k] = b[k]
      }
      if (Object.keys(nested).length) out[key] = nested
    } else if (JSON.stringify(a) !== JSON.stringify(b)) {
      out[key] = b
    }
  }
  return out as StylePatch
}

/** Textarea helpers for list fields: one item per line. */
export function listToLines(list: string[] | undefined): string {
  return (list || []).join('\n')
}
export function linesToList(text: string): string[] {
  return text.split('\n').map((s) => s.trim()).filter(Boolean)
}

export interface WebnovelFormFields {
  platform: string
  subgenre: string
  perspective: string
  narrator_register: string
  thought_style: string
  status_windows: 'auto' | 'on' | 'off'
  comedy_level: string
  directives_text: string
  auto_start: boolean
}

/**
 * What the Create Novel "Korean webnovel style" card contributes to the job request.
 * Empty pickers are omitted so the engine detects them from the brief and the reference;
 * `status_windows` is tri-state because "no windows" is a real choice, not an absence.
 */
export function webnovelParams(f: WebnovelFormFields): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const k of ['platform', 'subgenre', 'perspective', 'narrator_register', 'thought_style', 'comedy_level'] as const) {
    if (f[k]) out[k] = f[k]
  }
  if (f.status_windows !== 'auto') out.status_windows = f.status_windows === 'on'
  const lines = linesToList(f.directives_text)
  if (lines.length) out.directives = lines.map((text) => ({ scope: 'novel', kind: 'must', text }))
  if (!f.auto_start) out.auto_start = false
  return out
}

export interface Director {
  style: Ref<WebnovelStyleProfile | null>
  preview: Ref<StylePreview | null>
  subgenres: Ref<SubgenreTemplateInfo[]>
  directives: Ref<AuthorDirective[]>
  redoPlan: Ref<RedoPlan | null>
  quality: Ref<Record<number, ChapterQuality>>
  busy: Ref<string | null>
  error: Ref<string | null>
  jobId: ComputedRef<number | null>
  hasProject: ComputedRef<boolean>
  isRunning: ComputedRef<boolean>
  canRedo: ComputedRef<boolean>
  activeDirectives: ComputedRef<AuthorDirective[]>
  subgenreTemplates: ComputedRef<SubgenreTemplateInfo[]>
  platformNotes: ComputedRef<Record<string, string>>
  load: () => Promise<void>
  loadSubgenres: () => Promise<SubgenreTemplateInfo[]>
  loadStyle: () => Promise<WebnovelStyleProfile | null>
  loadPreview: () => Promise<StylePreview | null>
  saveStyle: (patch: StylePatch) => Promise<WebnovelStyleProfile | null>
  applySubgenre: (subgenre: string) => Promise<WebnovelStyleProfile | null>
  loadDirectives: () => Promise<AuthorDirective[]>
  addDirective: (body: DirectiveRequest) => Promise<AuthorDirective | null>
  updateDirective: (id: string, patch: DirectivePatch) => Promise<AuthorDirective | null>
  toggleDirective: (id: string) => Promise<AuthorDirective | null>
  removeDirective: (id: string) => Promise<boolean>
  planRedo: (fromChapter: number) => Promise<RedoPlan | null>
  redo: (body: RedoRequest) => Promise<JobResponse | null>
  loadQuality: (chapterNumber: number, force?: boolean) => Promise<ChapterQuality | null>
  reset: () => void
}

export function useDirector(api: DirectorApi, job: Ref<AutonomousJob | null>): Director {
  const style = ref<WebnovelStyleProfile | null>(null)
  const preview = ref<StylePreview | null>(null)
  const subgenres = ref<SubgenreTemplateInfo[]>([])
  const directives = ref<AuthorDirective[]>([])
  const redoPlan = ref<RedoPlan | null>(null)
  const quality = ref<Record<number, ChapterQuality>>({})
  const busy = ref<string | null>(null)
  const error = ref<string | null>(null)

  const jobId = computed(() => job.value?.id ?? null)
  const hasProject = computed(() => !!job.value?.original_project_id)
  const isRunning = computed(() => job.value?.status === 'running' || job.value?.status === 'queued')
  /** Redo needs a novel project, committed chapters, a redo-able stage and a job that is not running. */
  const canRedo = computed(() => !!job.value && hasProject.value && (job.value.chapters_committed || 0) >= 1 && REDO_STAGES.has(job.value.stage) && !['running', 'cancelled'].includes(job.value.status))
  const activeDirectives = computed(() => directives.value.filter((d) => d.active))
  const subgenreTemplates = computed(() => subgenres.value.filter((s) => !s.key.startsWith('platform:')))
  const platformNotes = computed<Record<string, string>>(() => Object.fromEntries(subgenres.value.filter((s) => s.key.startsWith('platform:')).map((s) => [s.key.slice('platform:'.length), s.note || ''])))

  async function guard<T>(kind: string, fn: () => Promise<T>): Promise<T | null> {
    if (busy.value) return null
    busy.value = kind
    error.value = null
    try {
      return await fn()
    } catch (e) {
      error.value = errorMessage(e)
      return null
    } finally {
      busy.value = null
    }
  }

  async function loadSubgenres(): Promise<SubgenreTemplateInfo[]> {
    if (subgenres.value.length) return subgenres.value
    try {
      subgenres.value = await api.listSubgenres()
    } catch (e) {
      error.value = errorMessage(e)
    }
    return subgenres.value
  }

  async function loadStyle(): Promise<WebnovelStyleProfile | null> {
    if (!jobId.value) return null
    return guard('style', async () => {
      style.value = await api.getStyle(jobId.value!)
      return style.value
    })
  }

  async function loadPreview(): Promise<StylePreview | null> {
    if (!jobId.value) return null
    return guard('preview', async () => {
      preview.value = await api.getStylePreview(jobId.value!)
      return preview.value
    })
  }

  async function saveStyle(patch: StylePatch): Promise<WebnovelStyleProfile | null> {
    if (!jobId.value) return null
    return guard('style-save', async () => {
      style.value = await api.patchStyle(jobId.value!, patch)
      if (preview.value) preview.value = await api.getStylePreview(jobId.value!)
      return style.value
    })
  }

  /** Switch subgenre template: the backend re-seeds engine defaults for the new key while keeping author edits. */
  async function applySubgenre(subgenre: string): Promise<WebnovelStyleProfile | null> {
    return saveStyle({ engine: { subgenre } })
  }

  async function loadDirectives(): Promise<AuthorDirective[]> {
    if (!jobId.value) return []
    const out = await guard('directives', async () => {
      directives.value = await api.listDirectives(jobId.value!)
      return directives.value
    })
    return out || []
  }

  async function addDirective(body: DirectiveRequest): Promise<AuthorDirective | null> {
    if (!jobId.value) return null
    const problem = directiveProblem(body, job.value?.chapter_count || 0)
    if (problem) {
      error.value = `directive:${problem}`
      return null
    }
    return guard('directive-add', async () => {
      const row = await api.addDirective(jobId.value!, { ...body, text: body.text.trim() })
      directives.value = [...directives.value, row]
      return row
    })
  }

  async function updateDirective(id: string, patch: DirectivePatch): Promise<AuthorDirective | null> {
    if (!jobId.value) return null
    return guard('directive-edit', async () => {
      const row = await api.patchDirective(jobId.value!, id, patch)
      directives.value = directives.value.map((d) => (d.id === id ? row : d))
      return row
    })
  }

  async function toggleDirective(id: string): Promise<AuthorDirective | null> {
    const d = directives.value.find((x) => x.id === id)
    if (!d) return null
    return updateDirective(id, { active: !d.active })
  }

  async function removeDirective(id: string): Promise<boolean> {
    if (!jobId.value) return false
    const ok = await guard('directive-remove', async () => {
      await api.deleteDirective(jobId.value!, id)
      directives.value = directives.value.filter((d) => d.id !== id)
      return true
    })
    return !!ok
  }

  async function planRedo(fromChapter: number): Promise<RedoPlan | null> {
    if (!jobId.value) return null
    return guard('redo-plan', async () => {
      redoPlan.value = await api.getRedoPlan(jobId.value!, fromChapter)
      return redoPlan.value
    })
  }

  /** Rewind + requeue. Returns the job response so the caller can apply it to its own job state. */
  async function redo(body: RedoRequest): Promise<JobResponse | null> {
    if (!jobId.value || !canRedo.value) return null
    return guard('redo', async () => {
      const res = await api.redoFromChapter(jobId.value!, { replan: true, discard_texts: true, auto_start: true, ...body, note: body.note?.trim() || undefined })
      redoPlan.value = null
      quality.value = Object.fromEntries(Object.entries(quality.value).filter(([n]) => Number(n) < body.from_chapter))
      // The note became a chapter-scoped directive; reload inside the same busy window.
      directives.value = await api.listDirectives(jobId.value!)
      return res
    })
  }

  async function loadQuality(chapterNumber: number, force = false): Promise<ChapterQuality | null> {
    if (!jobId.value) return null
    if (!force && quality.value[chapterNumber]) return quality.value[chapterNumber]
    try {
      const q = await api.getChapterQuality(jobId.value, chapterNumber)
      quality.value = { ...quality.value, [chapterNumber]: q }
      return q
    } catch (e) {
      error.value = errorMessage(e)
      return null
    }
  }

  /** Everything the Director panel needs for the current job, loaded once per open. */
  async function load(): Promise<void> {
    if (!jobId.value) return
    await loadSubgenres()
    await loadStyle()
    await loadDirectives()
  }

  function reset(): void {
    style.value = null
    preview.value = null
    directives.value = []
    redoPlan.value = null
    quality.value = {}
    error.value = null
  }

  return {
    style, preview, subgenres, directives, redoPlan, quality, busy, error,
    jobId, hasProject, isRunning, canRedo, activeDirectives, subgenreTemplates, platformNotes,
    load, loadSubgenres, loadStyle, loadPreview, saveStyle, applySubgenre, loadDirectives, addDirective, updateDirective, toggleDirective, removeDirective, planRedo, redo, loadQuality, reset,
  }
}
