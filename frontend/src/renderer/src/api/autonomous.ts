import request from './request'
import { API_BASE_URL } from './request'
import { artifactDownloadPath } from '@renderer/composables/useAutonomousNovel'

export type AutonomousMode = 'fully_automatic' | 'approval_gates' | 'manual'

export interface BudgetSpec {
  max_calls?: number
  max_input_tokens?: number
  max_output_tokens?: number
  max_total_tokens?: number
  max_repair_calls?: number
  max_cost_usd?: number
  price_per_million?: { input?: number; output?: number }
  prices?: Record<string, { input?: number; output?: number }>
}

export interface CreateJobRequest {
  filename: string
  content_base64: string
  llm_config_id: number
  mode?: AutonomousMode
  role_llm_config_ids?: Record<string, number>
  title?: string
  author?: string
  genre?: string
  genre_intensity?: string
  content_rating?: string
  ending_preference?: string
  romance_level?: string
  words_per_chapter?: number
  total_words?: number
  target_chapters?: number
  target_arcs?: number
  quality_preset?: 'economy' | 'balanced' | 'quality'
  craft_preset?: string
  storyline_count?: number
  fallback_llm_config_id?: number
  notes?: string
  protagonist_name?: string
  summary?: string
  tags?: string
  similarity_to_original?: string
  budget?: BudgetSpec
  idempotency_key?: string
  preflight_acknowledged?: boolean
  // Webnovel Style Engine — everything optional; empty fields are detected from the brief and the reference.
  platform?: WebnovelPlatform
  subgenre?: string
  perspective?: WebnovelPerspective
  narrator_register?: WebnovelRegister
  thought_style?: ThoughtStyle
  status_windows?: boolean
  comedy_level?: ComedyLevel
  directives?: Array<Pick<AuthorDirective, 'scope' | 'kind' | 'text'> & Partial<Pick<AuthorDirective, 'chapter_from' | 'chapter_to' | 'applies_to' | 'active'>>>
  auto_start?: boolean
}

// ------------------------------------------------------------------ webnovel style engine (mirrors backend/app/schemas/webnovel.py)
export type WebnovelPlatform = 'novelpia' | 'munpia' | 'kakaopage' | 'naver_series' | 'royalroad' | 'generic'
export type WebnovelPerspective = 'first_person' | 'third_limited' | 'third_close_alternating'
export type WebnovelRegister = 'dry_cynical' | 'deadpan_pragmatic' | 'cold_calculating' | 'warm_wry' | 'manic_comic' | 'grim_survivor' | 'sardonic_noble' | 'earnest_underdog'
export type ThoughtStyle = 'single_quotes' | 'italics' | 'em_dash' | 'plain'
export type ComedyLevel = 'none' | 'dry' | 'regular' | 'high'
export type DirectiveScope = 'novel' | 'arc' | 'chapter'
export type DirectiveKind = 'must' | 'prefer' | 'avoid' | 'idea'

export const WEBNOVEL_PLATFORMS: WebnovelPlatform[] = ['novelpia', 'munpia', 'kakaopage', 'naver_series', 'royalroad', 'generic']
export const WEBNOVEL_PERSPECTIVES: WebnovelPerspective[] = ['first_person', 'third_limited', 'third_close_alternating']
export const WEBNOVEL_REGISTERS: WebnovelRegister[] = ['dry_cynical', 'deadpan_pragmatic', 'cold_calculating', 'warm_wry', 'manic_comic', 'grim_survivor', 'sardonic_noble', 'earnest_underdog']
export const THOUGHT_STYLES: ThoughtStyle[] = ['single_quotes', 'italics', 'em_dash', 'plain']
export const COMEDY_LEVELS: ComedyLevel[] = ['none', 'dry', 'regular', 'high']
export const DIRECTIVE_SCOPES: DirectiveScope[] = ['novel', 'arc', 'chapter']
export const DIRECTIVE_KINDS: DirectiveKind[] = ['must', 'prefer', 'avoid', 'idea']

export interface NarrationConventions {
  thought_style: ThoughtStyle
  thought_density: 'sparse' | 'regular' | 'dense'
  window_style: 'square_brackets' | 'angle_brackets' | 'none'
  windows_enabled: boolean
  sfx_style: 'em_dash' | 'bare' | 'none'
  sfx_density: 'none' | 'light' | 'regular'
  address: 'korean_honorifics' | 'western_titles' | 'mixed' | 'minimal'
  paragraph_rhythm: 'one_line' | 'short' | 'mixed'
  line_break_beats: boolean
  chapter_title_style: 'numbered_only' | 'numbered_with_title' | 'title_only' | 'episode'
  tense: 'past' | 'present'
  onomatopoeia_english: string[]
}

export interface GenreEngine {
  subgenre: string
  progression_axis: string
  tier_ladder: string[]
  reward_types: string[]
  face_slap_cadence: 'none' | 'occasional' | 'regular' | 'every_arc'
  knowledge_advantage: string
  world_hooks: string[]
  typical_arc_shape: string
  genre_vocabulary: string[]
}

export interface ReaderExperience {
  core_fantasy: string
  dopamine_per_chapter: number
  reward_gap_max_chapters: number
  emotional_palette: string[]
  comedy_level: ComedyLevel
  romance_mode: 'none' | 'slow_burn_subplot' | 'central' | 'harem_adjacent_no' | 'found_family'
  violence_level: 'low' | 'moderate' | 'high'
  interiority_share_target: number
}

export interface ChapterShape {
  words_target: number
  opening_rule: string
  ending_rule: string
  hook_in_last_line: boolean
  min_scenes: number
  max_scenes: number
  recap_allowed: boolean
  author_note_style: 'none' | 'short' | 'chatty'
}

export interface WebnovelStyleProfile {
  version: string
  platform: WebnovelPlatform
  perspective: WebnovelPerspective
  narrative_distance: 'very_close' | 'close' | 'medium'
  narrator_register: WebnovelRegister
  narration: NarrationConventions
  engine: GenreEngine
  reader: ReaderExperience
  chapter: ChapterShape
  banned_moves: string[]
  signature_moves: string[]
  derived_from: 'author' | 'detected' | 'default'
  detection_notes: string
  updated_at: string
}

/** Recursive partial used for PATCH /style (the backend deep-merges). */
export type StylePatch = { [K in keyof WebnovelStyleProfile]?: WebnovelStyleProfile[K] extends object ? (WebnovelStyleProfile[K] extends unknown[] ? WebnovelStyleProfile[K] : Partial<WebnovelStyleProfile[K]>) : WebnovelStyleProfile[K] }

export interface StylePreview { drafting: string; planning: string; critic: string }

export interface SubgenreTemplateInfo { key: string; label: string; progression_axis?: string; core_fantasy?: string; windows?: boolean; register?: string; note?: string }

export interface AuthorDirective {
  id: string
  scope: DirectiveScope
  chapter_from: number
  chapter_to: number
  kind: DirectiveKind
  text: string
  applies_to: Array<'planning' | 'drafting' | 'critic' | 'export'>
  created_at: string
  consumed_by_chapters: number[]
  active: boolean
}

export type DirectiveRequest = Pick<AuthorDirective, 'scope' | 'kind' | 'text'> & Partial<Pick<AuthorDirective, 'chapter_from' | 'chapter_to' | 'applies_to' | 'active'>>
export type DirectivePatch = Partial<Pick<AuthorDirective, 'scope' | 'chapter_from' | 'chapter_to' | 'kind' | 'text' | 'applies_to' | 'active'>>

export interface RedoPlan { from_chapter: number; latest_committed: number; chapters_discarded: number[]; chapters_kept: number; will_replan: boolean; job_stage: string; job_status: string }
export interface RedoRequest { from_chapter: number; note?: string; note_kind?: DirectiveKind; replan?: boolean; discard_texts?: boolean; auto_start?: boolean }

export interface ConformanceFinding { code: string; severity: 'critical' | 'high' | 'medium' | 'low'; quote: string; problem: string; fix: string }
export interface WebnovelConformance { version: string; scores: Record<string, number>; overall: number; metrics: Record<string, number>; findings: ConformanceFinding[]; passed: boolean }
/** Mirrors `app.schemas.craft.CriticReport`; webnovel dimensions arrive prefixed `webnovel_` once merged. */
export interface CriticReport { scores: Record<string, number>; overall: number; verdict: 'accept' | 'polish' | 'rewrite'; strongest_moment?: string; findings?: Array<Record<string, unknown>>; source?: 'deterministic' | 'model' | 'merged'; tic_count?: number }
/** Whole-novel webnovel conformance summary from `audit.webnovel_audit` (surfaces in `/report` as `webnovel`). */
export interface WebnovelAudit {
  profile: { platform: string; subgenre: string; perspective: string; register: string }
  overall: number
  dimensions: Record<string, number>
  chapters: Array<{ chapter: number; overall: number; scores: Record<string, number>; metrics?: Record<string, number> }>
  below_floor: number[]
  worst_reward_drought: number
}

export interface ChapterQuality {
  chapter: number
  run_id: number
  model_calls: number
  repair_attempts: number
  validation_passed?: boolean | null
  style?: Record<string, unknown> | null
  critic_before?: CriticReport | null
  critic_after?: CriticReport | null
  webnovel_before?: WebnovelConformance | null
  webnovel_after?: WebnovelConformance | null
  passes?: Array<Record<string, unknown>> | null
  hook_after?: Record<string, unknown> | null
  mode?: string | null
}

export interface PreflightRequest {
  llm_config_id: number
  fallback_llm_config_id?: number
  timeout_seconds?: number
  check_fallback?: boolean
}

export interface PreflightCheck {
  name: string
  passed: boolean
  skipped: boolean
  advisory: boolean
  latency_ms?: number | null
  category?: string | null
  diagnostic?: string | null
}

export interface PreflightResult {
  passed: boolean
  llm_config_id: number
  provider: string
  model: string
  endpoint_class: string
  latency_ms: number
  model_availability?: PreflightCheck | null
  text_check?: PreflightCheck | null
  structured_check?: PreflightCheck | null
  usage_reporting: 'reported' | 'missing' | 'unknown'
  fallback_checked: boolean
  fallback?: PreflightResult | null
  warnings: string[]
  failure_category?: string | null
  diagnostic?: string | null
  checks: PreflightCheck[]
  timestamp: string
}

export interface BudgetCounter { used: number; reserved?: number; limit: number }
export interface BudgetSnapshot {
  calls: BudgetCounter
  input_tokens: BudgetCounter
  output_tokens: BudgetCounter
  total_tokens: BudgetCounter
  repair_calls: BudgetCounter
  cost_usd: { known: number | null; reserved: number; limit: number; unknown_calls: number; status: 'unknown' | 'estimated' | 'reported' }
  usage_estimated_calls: number
  estimated_cost_usd: number | null
}

export interface RecoveryEntry {
  id: number
  stage: string
  stage_attempt: number
  failure_category: string
  action: string
  reason: string
  success: boolean
  original_model?: string
  selected_model?: string
}

export interface StageAttempt {
  stage: string
  attempt: number
  status: string
  failure_category?: string | null
  recovery_action?: string | null
  started_at?: string | null
  finished_at?: string | null
}

export interface AutonomousJob {
  id: number
  status: 'queued' | 'running' | 'waiting_for_user' | 'paused' | 'failed' | 'cancelled' | 'completed'
  stage: string
  mode: AutonomousMode
  source_project_id?: number | null
  original_project_id?: number | null
  llm_config_id: number
  source_filename: string
  options: Record<string, unknown>
  selected_storyline_id?: number | null
  chapter_count: number
  chapters_committed: number
  progress_percent: number
  progress_message: string
  stage_results: Record<string, any>
  warnings: Array<Record<string, unknown>>
  error?: { category: string; message: string; detail?: Record<string, unknown> } | null
  model_calls: number
  input_tokens: number
  output_tokens: number
  waiting_for?: 'storyline_selection' | 'plan_approval' | 'manuscript_approval' | 'manual_mode' | 'approval' | 'budget_exhausted' | 'provider_unavailable' | 'manual_review_required' | 'quality_gate_failed' | 'paused' | null
  quality_status?: 'completed' | 'completed_with_warnings' | 'quality_gate_failed' | 'manual_review_required' | null
  quality_summary?: Record<string, unknown> | null
  budget?: BudgetSnapshot
  lease?: { owner: string | null; generation: number; expires_at: string | null; heartbeat_at: string | null }
  recovery?: RecoveryEntry[]
  created_at?: string | null
  updated_at?: string | null
  started_at?: string | null
  finished_at?: string | null
  attempts: StageAttempt[]
  stages: string[]
}

export interface JobResponse { job: AutonomousJob; active: boolean }

export interface StorylineOption {
  id: number
  job_id: number
  option_index: number
  title: string
  content: Record<string, any>
  originality_score: number
  originality_report: Record<string, any>
  similarity_to_others: Record<string, number>
  recommended_chapters_min: number
  recommended_chapters_max: number
  rejected: boolean
  rejection_reason?: string | null
  selected: boolean
}

export interface ExportArtifactInfo { id: number; kind: string; filename: string; media_type: string; size_bytes: number; content_hash: string; created_at: string }

export interface ChapterPreviewInfo { chapter_number: number; title?: string | null; words: number; summary?: string | null; sync_status?: string | null; validation_passed?: boolean | null; card_id: number; preview: string }

const opts = { showLoading: false }

export function createJob(body: CreateJobRequest): Promise<JobResponse> {
  return (request as any).request({ method: 'POST', url: '/api/autonomous/jobs', data: body, showLoading: false, timeout: 300_000 })
}
export function runPreflight(body: PreflightRequest): Promise<PreflightResult> {
  return (request as any).request({ method: 'POST', url: '/api/autonomous/preflight', data: body, showLoading: false, timeout: 320_000 })
}
export function listJobs(limit = 20): Promise<Array<AutonomousJob & { active: boolean }>> {
  return request.get('/autonomous/jobs', { limit }, '/api', opts)
}
export function getJob(jobId: number): Promise<JobResponse> {
  return request.get(`/autonomous/jobs/${jobId}`, undefined, '/api', opts)
}
export function listStorylines(jobId: number, includeRejected = false): Promise<StorylineOption[]> {
  return request.get(`/autonomous/jobs/${jobId}/storylines`, { include_rejected: includeRejected }, '/api', opts)
}
export function selectStoryline(jobId: number, body: { storyline_id: number; chapter_count: number; words_per_chapter?: number; title?: string }): Promise<JobResponse> {
  return (request as any).request({ method: 'POST', url: `/api/autonomous/jobs/${jobId}/select`, data: body, showLoading: false, timeout: 60_000 })
}
export function approveJob(jobId: number): Promise<JobResponse> {
  return (request as any).request({ method: 'POST', url: `/api/autonomous/jobs/${jobId}/approve`, showLoading: false })
}
export function pauseJob(jobId: number): Promise<JobResponse> {
  return (request as any).request({ method: 'POST', url: `/api/autonomous/jobs/${jobId}/pause`, showLoading: false })
}
export function resumeJob(jobId: number): Promise<JobResponse> {
  return (request as any).request({ method: 'POST', url: `/api/autonomous/jobs/${jobId}/resume`, showLoading: false })
}
export function cancelJob(jobId: number): Promise<JobResponse> {
  return (request as any).request({ method: 'POST', url: `/api/autonomous/jobs/${jobId}/cancel`, showLoading: false })
}
export function listChapters(jobId: number): Promise<ChapterPreviewInfo[]> {
  return request.get(`/autonomous/jobs/${jobId}/chapters`, undefined, '/api', opts)
}
export function listArtifacts(jobId: number): Promise<ExportArtifactInfo[]> {
  return request.get(`/autonomous/jobs/${jobId}/artifacts`, undefined, '/api', opts)
}
export function getReport(jobId: number): Promise<Record<string, any>> {
  return request.get(`/autonomous/jobs/${jobId}/report`, undefined, '/api', opts)
}
export function artifactDownloadUrl(artifactId: number, jobId?: number): string {
  // Job-scoped route; the unscoped legacy path only redirects here.
  if (jobId != null) return `${API_BASE_URL}${artifactDownloadPath(artifactId, jobId)}`
  return `${API_BASE_URL}/autonomous/artifacts/${artifactId}/download`
}

// ------------------------------------------------------------------ Director (style profile, directives, redo)
export function listSubgenres(): Promise<SubgenreTemplateInfo[]> {
  return request.get('/autonomous/subgenres', undefined, '/api', opts)
}
export function getStyle(jobId: number): Promise<WebnovelStyleProfile> {
  return request.get(`/autonomous/jobs/${jobId}/style`, undefined, '/api', opts)
}
export function patchStyle(jobId: number, patch: StylePatch): Promise<WebnovelStyleProfile> {
  return request.request<WebnovelStyleProfile>({ method: 'PATCH', url: `/api/autonomous/jobs/${jobId}/style`, data: patch, ...opts })
}
export function getStylePreview(jobId: number): Promise<StylePreview> {
  return request.get(`/autonomous/jobs/${jobId}/style/preview`, undefined, '/api', opts)
}
export function listDirectives(jobId: number): Promise<AuthorDirective[]> {
  return request.get(`/autonomous/jobs/${jobId}/directives`, undefined, '/api', opts)
}
export function addDirective(jobId: number, body: DirectiveRequest): Promise<AuthorDirective> {
  return request.post(`/autonomous/jobs/${jobId}/directives`, body, '/api', opts)
}
export function patchDirective(jobId: number, directiveId: string, body: DirectivePatch): Promise<AuthorDirective> {
  return request.request<AuthorDirective>({ method: 'PATCH', url: `/api/autonomous/jobs/${jobId}/directives/${encodeURIComponent(directiveId)}`, data: body, ...opts })
}
export function deleteDirective(jobId: number, directiveId: string): Promise<{ removed: string }> {
  return request.delete(`/autonomous/jobs/${jobId}/directives/${encodeURIComponent(directiveId)}`, undefined, '/api', opts)
}
export function getRedoPlan(jobId: number, fromChapter: number): Promise<RedoPlan> {
  return request.get(`/autonomous/jobs/${jobId}/redo/plan`, { from_chapter: fromChapter }, '/api', opts)
}
export function redoFromChapter(jobId: number, body: RedoRequest): Promise<JobResponse> {
  return request.request<JobResponse>({ method: 'POST', url: `/api/autonomous/jobs/${jobId}/redo`, data: body, timeout: 120_000, ...opts })
}
export function getChapterQuality(jobId: number, chapterNumber: number): Promise<ChapterQuality> {
  return request.get(`/autonomous/jobs/${jobId}/chapters/${chapterNumber}/quality`, undefined, '/api', opts)
}
