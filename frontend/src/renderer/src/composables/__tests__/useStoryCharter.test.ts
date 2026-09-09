import { describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useStoryCharter, type StoryCharterApi } from '../useStoryCharter'
import { emptyCharter, newBoundary, newOpenChoice, newRequirement, toEditable, type StoryCharter } from '@renderer/services/charterModel'
import type { components } from '@renderer/types/generated'

type CharterReadResponse = components['schemas']['CharterReadResponse']

function response(charter: Partial<StoryCharter>, exists = true): CharterReadResponse {
  const full = { ...emptyCharter(), ...charter } as StoryCharter
  return {
    project_id: 7,
    card_id: exists ? 42 : null,
    charter: full,
    summary: {
      project_id: 7, exists, working_title: full.working_title ?? '', one_line_pitch: full.one_line_pitch ?? '',
      musts: (full.requirements ?? []).filter((r) => r.strength === 'must').length, prefers: (full.requirements ?? []).filter((r) => r.strength === 'prefer').length,
      open_choices: (full.open_choices ?? []).length, boundaries: (full.boundaries ?? []).length, interpreted: !!full.interpreted_at, brief_changed_since_interpretation: false, questions_for_author: full.questions_for_author ?? [], categories: {}
    }
  }
}

function makeApi(over: Partial<StoryCharterApi> = {}): StoryCharterApi {
  return {
    get: vi.fn(async () => response({ brief: 'A brief.', requirements: [{ id: 'req-1', text: 'Fixed rule', category: 'other', strength: 'must', scope: 'whole_novel', source: 'author', rationale: '', locked: true }] })),
    save: vi.fn(async (_pid, charter) => response(charter)),
    interpret: vi.fn(async () => response({ brief: 'A brief.', interpreted_at: '2026-09-08T00:00:00', requirements: [
      { id: 'req-1', text: 'Fixed rule', category: 'other', strength: 'must', scope: 'whole_novel', source: 'author', rationale: '', locked: true },
      { id: 'req-2', text: 'Inferred rule', category: 'prose', strength: 'prefer', scope: 'prose', source: 'interpreted', rationale: "brief says 'wry'", locked: false }
    ], open_choices: [{ id: 'open-1', topic: 'the ending', options: [], guidance: '', decide_by: 'author', source: 'interpreted' }] })),
    render: vi.fn(async (_pid, consumer) => ({ project_id: 7, consumer, text: `[${consumer}] rendered`, chars: 10, consumers: ['draft'] })),
    ...over
  }
}

describe('useStoryCharter', () => {
  it('loads the charter, normalises optional lists and previews the draft consumer', async () => {
    const api = makeApi()
    const s = useStoryCharter(api, ref(7))
    await s.load()
    expect(s.charter.brief).toBe('A brief.')
    expect(s.charter.requirements).toHaveLength(1)
    expect(s.charter.open_choices).toEqual([])
    expect(s.exists.value).toBe(true)
    expect(s.dirty.value).toBe(false)
    expect(s.preview.value).toBe('[draft] rendered')
    expect(api.render).toHaveBeenCalledWith(7, 'draft')
  })

  it('tracks edits, drops empty entries on save and refreshes the preview only when clean', async () => {
    const api = makeApi()
    const s = useStoryCharter(api, ref(7))
    await s.load()
    s.addRequirement() // empty: must not persist
    const r = s.addRequirement()
    r.text = 'No love triangle'
    r.strength = 'prefer'
    s.addBoundary().text = 'No gore'
    s.addOpenChoice() // empty topic: dropped
    expect(s.dirty.value).toBe(true)
    ;(api.render as any).mockClear()
    await s.loadPreview() // dirty: preview is not refreshed from a stale server copy
    expect(api.render).not.toHaveBeenCalled()
    const summary = await s.save()
    const saved = (api.save as any).mock.calls[0][1] as StoryCharter
    expect(saved.requirements!.map((x) => x.text)).toEqual(['Fixed rule', 'No love triangle'])
    expect(saved.boundaries!.map((x) => x.text)).toEqual(['No gore'])
    expect(saved.open_choices).toEqual([])
    expect(summary?.musts).toBe(1)
    expect(summary?.prefers).toBe(1)
    expect(summary?.boundaries).toBe(1)
    expect(s.dirty.value).toBe(false)
    expect(api.render).toHaveBeenCalled()
  })

  it('interpret saves pending edits first, then merges inferred entries and reports how many were added', async () => {
    const api = makeApi()
    const s = useStoryCharter(api, ref(7))
    await s.load()
    s.charter.brief = 'A brief. I want a wry voice.'
    s.touch()
    const summary = await s.interpret(3)
    expect(api.save).toHaveBeenCalledTimes(1) // pending brief edit persisted before interpreting
    expect(api.interpret).toHaveBeenCalledWith({ project_id: 7, llm_config_id: 3, brief: 'A brief. I want a wry voice.' })
    expect(s.interpretedCount.value).toBe(1)
    expect(s.charter.open_choices[0].topic).toBe('the ending')
    expect(summary?.interpreted).toBe(true)
    expect(s.dirty.value).toBe(false)
  })

  it('does not interpret an empty brief and surfaces API errors without throwing', async () => {
    const api = makeApi({ get: vi.fn(async () => response({}, false)), save: vi.fn(async () => { throw new Error('boom') }) })
    const s = useStoryCharter(api, ref(7))
    await s.load()
    expect(s.exists.value).toBe(false)
    expect(await s.interpret(3)).toBeNull()
    expect(api.interpret).not.toHaveBeenCalled()
    s.charter.working_title = 'X'
    s.touch()
    expect(await s.save()).toBeNull()
    expect(s.error.value).toContain('boom')
    expect(s.dirty.value).toBe(true) // unsaved edits are kept after a failure
  })

  it('switching the consumer re-renders the scope-filtered preview', async () => {
    const api = makeApi()
    const s = useStoryCharter(api, ref(7))
    await s.load()
    await s.setConsumer('architecture')
    expect(s.preview.value).toBe('[architecture] rendered')
  })

  it('id helpers never collide with existing entries', () => {
    const reqs = [newRequirement([])]
    reqs.push(newRequirement(reqs))
    expect(reqs.map((r) => r.id)).toEqual(['req-1', 'req-2'])
    const opens = [newOpenChoice([])]
    expect(newOpenChoice(opens).id).toBe('open-2')
    expect(newBoundary([{ id: 'no-1', text: '', severity: 'hard', source: 'author' }]).id).toBe('no-2')
    const e = toEditable({ ...emptyCharter(), requirements: undefined, open_choices: undefined, boundaries: undefined, questions_for_author: undefined } as any)
    expect(e.requirements).toEqual([])
    expect(e.questions_for_author).toEqual([])
  })
})
