/**
 * Story Charter editing state: load / edit / save / interpret, with dirty tracking and a
 * scope-filtered preview of exactly what each prompt consumer receives.
 *
 * The API is injected so the composable can be unit-tested without a backend.
 */
import { computed, reactive, ref, type Ref } from 'vue'
import type { components } from '@renderer/types/generated'
import { emptyCharter, newBoundary, newOpenChoice, newRequirement, toEditable, type EditableCharter, type StoryCharter } from '@renderer/services/charterModel'

type CharterReadResponse = components['schemas']['CharterReadResponse']
type CharterRenderResponse = components['schemas']['CharterRenderResponse']
type CharterSummary = components['schemas']['CharterSummary']

export interface StoryCharterApi {
  get: (projectId: number) => Promise<CharterReadResponse>
  save: (projectId: number, charter: StoryCharter) => Promise<CharterReadResponse>
  interpret: (body: { project_id: number; llm_config_id: number; brief?: string; replace_interpreted?: boolean }) => Promise<CharterReadResponse>
  render: (projectId: number, consumer: string) => Promise<CharterRenderResponse>
}

export const CHARTER_CONSUMERS = ['draft', 'chapter_plan', 'architecture', 'storylines'] as const

export function useStoryCharter(api: StoryCharterApi, projectId: Ref<number | undefined>) {
  const charter = reactive<EditableCharter>(emptyCharter())
  const summary = ref<CharterSummary | null>(null)
  const consumer = ref<string>('draft')
  const preview = ref('')
  const loading = ref(false)
  const saving = ref(false)
  const interpreting = ref(false)
  const dirty = ref(false)
  const error = ref('')

  const exists = computed(() => !!summary.value?.exists)
  const interpretedCount = computed(() => charter.requirements.filter((r) => r.source === 'interpreted').length)

  function assign(next: StoryCharter) {
    const full = toEditable(next)
    for (const k of Object.keys(full) as Array<keyof EditableCharter>) (charter as any)[k] = (full as any)[k]
    dirty.value = false
  }

  function touch() { dirty.value = true }
  function remove<T>(list: T[], i: number) { list.splice(i, 1); touch() }
  function addRequirement() { const r = newRequirement(charter.requirements); charter.requirements.push(r); touch(); return r }
  function addOpenChoice() { const o = newOpenChoice(charter.open_choices); charter.open_choices.push(o); touch(); return o }
  function addBoundary() { const b = newBoundary(charter.boundaries); charter.boundaries.push(b); touch(); return b }

  /** Entries without text are dropped before saving so a stray "+ Add" never persists an empty rule. */
  function cleaned(): StoryCharter {
    return {
      ...charter,
      requirements: charter.requirements.filter((r) => r.text.trim()),
      open_choices: charter.open_choices.filter((o) => o.topic.trim()),
      boundaries: charter.boundaries.filter((b) => b.text.trim())
    }
  }

  async function loadPreview() {
    if (!projectId.value || dirty.value) return
    try { preview.value = (await api.render(projectId.value, consumer.value)).text } catch { preview.value = '' }
  }

  async function load() {
    if (!projectId.value) return
    loading.value = true
    error.value = ''
    try {
      const res = await api.get(projectId.value)
      assign(res.charter)
      summary.value = res.summary
      await loadPreview()
    } catch (e: any) {
      error.value = e?.message || String(e)
    } finally {
      loading.value = false
    }
  }

  async function save(): Promise<CharterSummary | null> {
    if (!projectId.value) return null
    saving.value = true
    error.value = ''
    try {
      const res = await api.save(projectId.value, cleaned())
      assign(res.charter)
      summary.value = res.summary
      await loadPreview()
      return res.summary
    } catch (e: any) {
      error.value = e?.message || String(e)
      return null
    } finally {
      saving.value = false
    }
  }

  async function interpret(llmConfigId: number): Promise<CharterSummary | null> {
    if (!projectId.value || !charter.brief.trim()) return null
    interpreting.value = true
    error.value = ''
    try {
      if (dirty.value) await api.save(projectId.value, cleaned())
      const res = await api.interpret({ project_id: projectId.value, llm_config_id: llmConfigId, brief: charter.brief })
      assign(res.charter)
      summary.value = res.summary
      await loadPreview()
      return res.summary
    } catch (e: any) {
      error.value = e?.message || String(e)
      return null
    } finally {
      interpreting.value = false
    }
  }

  async function setConsumer(c: string) {
    consumer.value = c
    await loadPreview()
  }

  return { charter, summary, consumer, preview, loading, saving, interpreting, dirty, error, exists, interpretedCount, touch, remove, addRequirement, addOpenChoice, addBoundary, cleaned, load, save, interpret, setConsumer, loadPreview }
}
