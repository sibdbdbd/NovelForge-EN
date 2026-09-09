import request from './request'
import type { components } from '@renderer/types/generated'

// Backend-generated types (single source of truth)
export type CharterSummary = components['schemas']['CharterSummary']
export type CharterReadResponse = components['schemas']['CharterReadResponse']
export type CharterRenderResponse = components['schemas']['CharterRenderResponse']
export type CharterCheckReport = components['schemas']['CharterCheckReport']
export type CharterConflict = components['schemas']['CharterConflict']
export type { CharterBoundary, CharterRequirement, EditableCharter, OpenChoice, StoryCharter } from '@renderer/services/charterModel'
export { emptyCharter, newBoundary, newOpenChoice, newRequirement, toEditable } from '@renderer/services/charterModel'

import type { StoryCharter } from '@renderer/services/charterModel'

export interface CharterMeta {
  card_type: string
  scopes: string[]
  categories: string[]
  consumers: Record<string, string[]>
}

const opts = { showLoading: false }

export function getStoryCharter(projectId: number): Promise<CharterReadResponse> {
  return request.get('/story-charter', { project_id: projectId }, '/api', opts)
}

export function saveStoryCharter(projectId: number, charter: StoryCharter): Promise<CharterReadResponse> {
  return request.put('/story-charter', { project_id: projectId, charter }, '/api', opts)
}

export function interpretStoryCharter(body: { project_id: number; llm_config_id: number; brief?: string; replace_interpreted?: boolean }): Promise<CharterReadResponse> {
  return request.post('/story-charter/interpret', body, '/api', opts)
}

export function renderStoryCharter(projectId: number, consumer: string): Promise<CharterRenderResponse> {
  return request.get('/story-charter/render', { project_id: projectId, consumer }, '/api', opts)
}

export function checkStoryCharter(body: { project_id: number; text: string; chapter_number?: number }): Promise<CharterCheckReport> {
  return request.post('/story-charter/check', body, '/api', opts)
}

export function getStoryCharterMeta(): Promise<CharterMeta> {
  return request.get('/story-charter/meta', undefined, '/api', opts)
}
