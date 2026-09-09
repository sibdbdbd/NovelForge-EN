/**
 * Pure helpers for the Story Charter editor (no network, no i18n) so composables and tests can
 * import them without pulling in the HTTP client.
 */
import type { components } from '@renderer/types/generated'

export type StoryCharter = components['schemas']['StoryCharter']
export type CharterRequirement = components['schemas']['CharterRequirement']
export type OpenChoice = components['schemas']['OpenChoice']
export type CharterBoundary = components['schemas']['CharterBoundary']

/** Editor-side charter: every list is present (the API marks them optional because they default server-side). */
export type EditableCharter = Omit<StoryCharter, 'requirements' | 'open_choices' | 'boundaries' | 'questions_for_author'> & {
  requirements: CharterRequirement[]
  open_choices: OpenChoice[]
  boundaries: CharterBoundary[]
  questions_for_author: string[]
}

export function emptyCharter(): EditableCharter {
  return {
    version: 'story-charter-1',
    working_title: '',
    one_line_pitch: '',
    brief: '',
    audience: '',
    language: 'English',
    target_chapters: null,
    words_per_chapter: null,
    reference: null,
    requirements: [],
    open_choices: [],
    boundaries: [],
    questions_for_author: [],
    interpretation_notes: '',
    updated_at: '',
    interpreted_at: '',
    interpreted_brief_hash: '',
    source_job_id: null
  }
}

export function toEditable(c: StoryCharter): EditableCharter {
  return { ...emptyCharter(), ...c, requirements: c.requirements ?? [], open_choices: c.open_choices ?? [], boundaries: c.boundaries ?? [], questions_for_author: c.questions_for_author ?? [] }
}

function nextId(prefix: string, items: Array<{ id: string }>): string {
  const used = new Set(items.map((x) => x.id))
  let n = 1
  while (used.has(`${prefix}-${n}`)) n += 1
  return `${prefix}-${n}`
}

export function newRequirement(items: CharterRequirement[]): CharterRequirement {
  return { id: nextId('req', items), text: '', category: 'other', strength: 'must', scope: 'whole_novel', source: 'author', rationale: '', locked: true }
}

export function newOpenChoice(items: OpenChoice[]): OpenChoice {
  return { id: nextId('open', items), topic: '', options: [], guidance: '', decide_by: 'author', source: 'author' }
}

export function newBoundary(items: CharterBoundary[]): CharterBoundary {
  return { id: nextId('no', items), text: '', severity: 'hard', source: 'author' }
}
