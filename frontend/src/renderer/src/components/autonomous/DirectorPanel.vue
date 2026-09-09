<template>
  <el-card shadow="never" class="director" data-testid="director-panel">
    <template #header>
      <div class="head">
        <div>
          <b>{{ t('director.title') }}</b>
          <p class="muted sub">{{ t('director.subtitle') }}</p>
        </div>
        <el-button size="small" @click="emit('close')">{{ t('director.close') }}</el-button>
      </div>
    </template>

    <el-alert v-if="director.error.value" type="error" :closable="true" show-icon :title="errorText" @close="director.error.value = null" />
    <el-alert v-if="!director.hasProject.value" type="info" :closable="false" show-icon :title="t('director.pendingNote')" class="note" data-testid="director-pending" />
    <el-alert v-else-if="director.isRunning.value" type="info" :closable="false" show-icon :title="t('director.runningNote')" class="note" />

    <el-tabs v-model="tab">
      <!-- ------------------------------------------------------------ style -->
      <el-tab-pane :label="t('director.tabs.style')" name="style">
        <div v-if="!draft" class="muted">…</div>
        <template v-else>
          <div class="toolbar">
            <el-tag size="small" effect="plain" :type="draft.derived_from === 'author' ? 'success' : 'info'" data-testid="style-derived">{{ t('director.style.derived.' + draft.derived_from) }}</el-tag>
            <el-tag v-if="styleDirty" size="small" type="warning" effect="plain">{{ t('director.style.dirty') }}</el-tag>
            <span class="spacer" />
            <el-button size="small" @click="togglePreview">{{ t('director.style.preview') }}</el-button>
            <el-button size="small" type="primary" :disabled="!styleDirty" :loading="director.busy.value === 'style-save'" data-testid="style-save" @click="saveStyle">{{ t('director.style.save') }}</el-button>
          </div>
          <el-collapse v-if="draft.detection_notes" class="notes">
            <el-collapse-item :title="t('director.style.detectionNotes')"><pre class="pre">{{ draft.detection_notes }}</pre></el-collapse-item>
          </el-collapse>

          <el-card v-if="director.preview.value && showPreview" shadow="never" class="block" data-testid="style-preview">
            <template #header><b>{{ t('director.style.previewTitle') }}</b></template>
            <el-tabs>
              <el-tab-pane :label="t('director.style.previewDrafting')"><pre class="pre">{{ director.preview.value.drafting }}</pre></el-tab-pane>
              <el-tab-pane :label="t('director.style.previewPlanning')"><pre class="pre">{{ director.preview.value.planning }}</pre></el-tab-pane>
              <el-tab-pane :label="t('director.style.previewCritic')"><pre class="pre">{{ director.preview.value.critic }}</pre></el-tab-pane>
            </el-tabs>
          </el-card>

          <el-form label-position="top" size="small">
            <el-card shadow="never" class="block">
              <template #header><b>{{ t('director.style.identity') }}</b></template>
              <div class="grid">
                <el-form-item :label="t('director.style.platform')">
                  <el-select v-model="draft.platform" data-testid="style-platform">
                    <el-option v-for="p in WEBNOVEL_PLATFORMS" :key="p" :value="p" :label="t('autonomous.webnovel.platforms.' + p)" />
                  </el-select>
                  <div v-if="director.platformNotes.value[draft.platform]" class="field-hint">{{ director.platformNotes.value[draft.platform] }}</div>
                </el-form-item>
                <el-form-item :label="t('director.style.subgenre')">
                  <el-select v-model="draft.engine.subgenre" filterable data-testid="style-subgenre">
                    <el-option v-for="s in director.subgenreTemplates.value" :key="s.key" :value="s.key" :label="s.label" />
                  </el-select>
                  <div class="field-hint">{{ t('director.style.subgenreHint') }}</div>
                </el-form-item>
                <el-form-item :label="t('director.style.perspective')">
                  <el-select v-model="draft.perspective"><el-option v-for="p in WEBNOVEL_PERSPECTIVES" :key="p" :value="p" :label="t('autonomous.webnovel.perspectives.' + p)" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.register')">
                  <el-select v-model="draft.narrator_register" data-testid="style-register"><el-option v-for="r in WEBNOVEL_REGISTERS" :key="r" :value="r" :label="t('autonomous.webnovel.registers.' + r)" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.distance')">
                  <el-select v-model="draft.narrative_distance"><el-option v-for="v in ['very_close', 'close', 'medium']" :key="v" :value="v" :label="v.replace('_', ' ')" /></el-select>
                </el-form-item>
              </div>
            </el-card>

            <el-card shadow="never" class="block">
              <template #header><b>{{ t('director.style.narration') }}</b></template>
              <div class="grid">
                <el-form-item :label="t('director.style.thoughtStyle')">
                  <el-select v-model="draft.narration.thought_style"><el-option v-for="v in THOUGHT_STYLES" :key="v" :value="v" :label="t('autonomous.webnovel.thoughtStyles.' + v)" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.thoughtDensity')">
                  <el-select v-model="draft.narration.thought_density"><el-option v-for="v in ['sparse', 'regular', 'dense']" :key="v" :value="v" :label="v" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.windows')"><el-switch v-model="draft.narration.windows_enabled" data-testid="style-windows" /></el-form-item>
                <el-form-item :label="t('director.style.windowStyle')">
                  <el-select v-model="draft.narration.window_style" :disabled="!draft.narration.windows_enabled"><el-option v-for="v in ['square_brackets', 'angle_brackets', 'none']" :key="v" :value="v" :label="v.replace('_', ' ')" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.sfx')">
                  <el-select v-model="draft.narration.sfx_style"><el-option v-for="v in ['em_dash', 'bare', 'none']" :key="v" :value="v" :label="v.replace('_', ' ')" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.sfxDensity')">
                  <el-select v-model="draft.narration.sfx_density"><el-option v-for="v in ['none', 'light', 'regular']" :key="v" :value="v" :label="v" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.address')">
                  <el-select v-model="draft.narration.address"><el-option v-for="v in ['korean_honorifics', 'western_titles', 'mixed', 'minimal']" :key="v" :value="v" :label="v.replace('_', ' ')" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.rhythm')">
                  <el-select v-model="draft.narration.paragraph_rhythm"><el-option v-for="v in ['one_line', 'short', 'mixed']" :key="v" :value="v" :label="v.replace('_', ' ')" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.lineBreakBeats')"><el-switch v-model="draft.narration.line_break_beats" /></el-form-item>
                <el-form-item :label="t('director.style.titleStyle')">
                  <el-select v-model="draft.narration.chapter_title_style"><el-option v-for="v in ['numbered_only', 'numbered_with_title', 'title_only', 'episode']" :key="v" :value="v" :label="v.replace(/_/g, ' ')" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.tense')">
                  <el-radio-group v-model="draft.narration.tense"><el-radio-button value="past">past</el-radio-button><el-radio-button value="present">present</el-radio-button></el-radio-group>
                </el-form-item>
              </div>
            </el-card>

            <el-card shadow="never" class="block">
              <template #header><b>{{ t('director.style.engine') }}</b></template>
              <div class="grid">
                <el-form-item :label="t('director.style.progressionAxis')"><el-input v-model="draft.engine.progression_axis" /></el-form-item>
                <el-form-item :label="t('director.style.knowledgeAdvantage')"><el-input v-model="draft.engine.knowledge_advantage" /></el-form-item>
                <el-form-item :label="t('director.style.faceSlap')">
                  <el-select v-model="draft.engine.face_slap_cadence"><el-option v-for="v in ['none', 'occasional', 'regular', 'every_arc']" :key="v" :value="v" :label="v.replace('_', ' ')" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.arcShape')"><el-input v-model="draft.engine.typical_arc_shape" /></el-form-item>
              </div>
              <div class="grid">
                <el-form-item :label="t('director.style.tierLadder')"><el-input :model-value="listToLines(draft.engine.tier_ladder)" type="textarea" :rows="4" data-testid="style-tiers" @update:model-value="draft!.engine.tier_ladder = linesToList($event)" /><div class="field-hint">{{ t('director.style.listHint') }}</div></el-form-item>
                <el-form-item :label="t('director.style.rewardTypes')"><el-input :model-value="listToLines(draft.engine.reward_types)" type="textarea" :rows="4" @update:model-value="draft!.engine.reward_types = linesToList($event)" /></el-form-item>
                <el-form-item :label="t('director.style.worldHooks')"><el-input :model-value="listToLines(draft.engine.world_hooks)" type="textarea" :rows="4" @update:model-value="draft!.engine.world_hooks = linesToList($event)" /></el-form-item>
                <el-form-item :label="t('director.style.vocabulary')"><el-input :model-value="listToLines(draft.engine.genre_vocabulary)" type="textarea" :rows="4" @update:model-value="draft!.engine.genre_vocabulary = linesToList($event)" /></el-form-item>
              </div>
            </el-card>

            <el-card shadow="never" class="block">
              <template #header><b>{{ t('director.style.reader') }}</b></template>
              <div class="grid">
                <el-form-item :label="t('director.style.coreFantasy')"><el-input v-model="draft.reader.core_fantasy" /></el-form-item>
                <el-form-item :label="t('director.style.comedy')">
                  <el-select v-model="draft.reader.comedy_level"><el-option v-for="v in COMEDY_LEVELS" :key="v" :value="v" :label="t('autonomous.webnovel.comedy.' + v)" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.romance')">
                  <el-select v-model="draft.reader.romance_mode"><el-option v-for="v in ['none', 'slow_burn_subplot', 'central', 'harem_adjacent_no', 'found_family']" :key="v" :value="v" :label="v.replace(/_/g, ' ')" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.violence')">
                  <el-select v-model="draft.reader.violence_level"><el-option v-for="v in ['low', 'moderate', 'high']" :key="v" :value="v" :label="v" /></el-select>
                </el-form-item>
                <el-form-item :label="t('director.style.dopamine')"><el-input-number v-model="draft.reader.dopamine_per_chapter" :min="0" :max="4" /></el-form-item>
                <el-form-item :label="t('director.style.rewardGap')"><el-input-number v-model="draft.reader.reward_gap_max_chapters" :min="1" :max="10" /></el-form-item>
                <el-form-item :label="t('director.style.interiority')"><el-slider v-model="draft.reader.interiority_share_target" :min="0.05" :max="0.6" :step="0.01" show-input :show-input-controls="false" /></el-form-item>
                <el-form-item :label="t('director.style.palette')"><el-input :model-value="listToLines(draft.reader.emotional_palette)" type="textarea" :rows="3" @update:model-value="draft!.reader.emotional_palette = linesToList($event)" /></el-form-item>
              </div>
            </el-card>

            <el-card shadow="never" class="block">
              <template #header><b>{{ t('director.style.chapter') }}</b></template>
              <div class="grid">
                <el-form-item :label="t('director.style.wordsTarget')"><el-input-number v-model="draft.chapter.words_target" :min="600" :max="12000" :step="100" /></el-form-item>
                <el-form-item :label="t('director.style.scenes')">
                  <div class="row"><el-input-number v-model="draft.chapter.min_scenes" :min="1" :max="6" /><span>–</span><el-input-number v-model="draft.chapter.max_scenes" :min="1" :max="8" /></div>
                </el-form-item>
                <el-form-item :label="t('director.style.hookLastLine')"><el-switch v-model="draft.chapter.hook_in_last_line" /></el-form-item>
                <el-form-item :label="t('director.style.recap')"><el-switch v-model="draft.chapter.recap_allowed" /></el-form-item>
                <el-form-item :label="t('director.style.authorNote')">
                  <el-select v-model="draft.chapter.author_note_style"><el-option v-for="v in ['none', 'short', 'chatty']" :key="v" :value="v" :label="v" /></el-select>
                </el-form-item>
              </div>
              <el-form-item :label="t('director.style.openingRule')"><el-input v-model="draft.chapter.opening_rule" type="textarea" :rows="2" /></el-form-item>
              <el-form-item :label="t('director.style.endingRule')"><el-input v-model="draft.chapter.ending_rule" type="textarea" :rows="2" /></el-form-item>
            </el-card>

            <el-card shadow="never" class="block">
              <template #header><b>{{ t('director.style.moves') }}</b></template>
              <div class="grid">
                <el-form-item :label="t('director.style.signature')"><el-input :model-value="listToLines(draft.signature_moves)" type="textarea" :rows="5" @update:model-value="draft!.signature_moves = linesToList($event)" /></el-form-item>
                <el-form-item :label="t('director.style.banned')"><el-input :model-value="listToLines(draft.banned_moves)" type="textarea" :rows="5" @update:model-value="draft!.banned_moves = linesToList($event)" /></el-form-item>
              </div>
            </el-card>
          </el-form>
        </template>
      </el-tab-pane>

      <!-- ------------------------------------------------------- directives -->
      <el-tab-pane :label="t('director.tabs.directives') + (director.directives.value.length ? ` (${director.directives.value.length})` : '')" name="directives">
        <p class="muted">{{ t('director.directives.hint') }}</p>
        <el-card shadow="never" class="block" data-testid="directive-form">
          <el-form label-position="top" size="small">
            <div class="grid">
              <el-form-item :label="t('director.directives.scope')">
                <el-radio-group v-model="newDirective.scope" data-testid="directive-scope">
                  <el-radio-button v-for="s in DIRECTIVE_SCOPES" :key="s" :value="s">{{ t('director.directives.scopes.' + s) }}</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item :label="t('director.directives.kind')">
                <el-radio-group v-model="newDirective.kind">
                  <el-radio-button v-for="k in DIRECTIVE_KINDS" :key="k" :value="k">{{ t('director.directives.kinds.' + k) }}</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item v-if="newDirective.scope !== 'novel'" :label="t('director.directives.from')"><el-input-number v-model="newDirective.chapter_from" :min="1" :max="job.chapter_count || 2000" data-testid="directive-from" /></el-form-item>
              <el-form-item v-if="newDirective.scope === 'arc'" :label="t('director.directives.to')"><el-input-number v-model="newDirective.chapter_to" :min="newDirective.chapter_from || 1" :max="job.chapter_count || 2000" /></el-form-item>
            </div>
            <el-form-item :label="t('director.directives.text')">
              <el-input v-model="newDirective.text" type="textarea" :autosize="{ minRows: 2, maxRows: 8 }" :placeholder="t('director.directives.textPlaceholder')" data-testid="directive-text" />
            </el-form-item>
            <div class="row">
              <el-checkbox-group v-model="newDirective.applies_to" size="small">
                <el-checkbox-button v-for="a in ['planning', 'drafting', 'critic', 'export']" :key="a" :value="a">{{ a }}</el-checkbox-button>
              </el-checkbox-group>
              <span class="spacer" />
              <span v-if="newProblem" class="warn">{{ t('director.directives.problems.' + newProblem) }}</span>
              <el-button type="primary" size="small" :disabled="!!newProblem" :loading="director.busy.value === 'directive-add'" data-testid="directive-add" @click="addDirective">{{ t('director.directives.add') }}</el-button>
            </div>
          </el-form>
        </el-card>
        <el-empty v-if="!director.directives.value.length" :description="t('director.directives.empty')" :image-size="50" />
        <div v-for="d in director.directives.value" :key="d.id" class="directive" :class="{ off: !d.active }" :data-testid="`directive-${d.id}`">
          <div class="directive-head">
            <el-tag size="small" :type="kindType(d.kind)" effect="dark">{{ t('director.directives.kinds.' + d.kind) }}</el-tag>
            <el-tag size="small" effect="plain">{{ t('director.directives.scopes.' + d.scope) }} · {{ t('director.directives.range') }} {{ directiveRange(d) === 'all' ? t('director.directives.all') : directiveRange(d) }}</el-tag>
            <el-tag v-if="!d.active" size="small" type="info" effect="plain">{{ t('director.directives.inactive') }}</el-tag>
            <span class="muted small">{{ (d.consumed_by_chapters || []).length ? t('director.directives.consumed', { list: (d.consumed_by_chapters || []).join(', ') }) : t('director.directives.notConsumed') }}</span>
            <span class="spacer" />
            <el-switch :model-value="d.active" size="small" @change="director.toggleDirective(d.id)" />
            <el-button size="small" text type="danger" :data-testid="`directive-remove-${d.id}`" @click="director.removeDirective(d.id)">{{ t('common.delete', 'Delete') }}</el-button>
          </div>
          <el-input :model-value="d.text" type="textarea" :autosize="{ minRows: 1, maxRows: 6 }" class="directive-text" @change="(v: string) => v.trim() && v !== d.text && director.updateDirective(d.id, { text: v.trim() })" />
        </div>
      </el-tab-pane>

      <!-- ------------------------------------------------------------- redo -->
      <el-tab-pane :label="t('director.tabs.redo')" name="redo" :disabled="!director.hasProject.value">
        <p class="muted">{{ t('director.redo.hint') }}</p>
        <el-alert v-if="redoBlocker" type="warning" :closable="false" show-icon :title="t('director.redo.' + redoBlocker)" class="note" data-testid="redo-blocker" />
        <el-form label-position="top" size="small">
          <div class="grid">
            <el-form-item :label="t('director.redo.from')">
              <el-input-number v-model="redoForm.from_chapter" :min="1" :max="Math.max(1, job.chapters_committed || 1)" data-testid="redo-from" @change="director.redoPlan.value = null" />
            </el-form-item>
            <el-form-item :label="t('director.redo.noteKind')">
              <el-radio-group v-model="redoForm.note_kind"><el-radio-button v-for="k in DIRECTIVE_KINDS" :key="k" :value="k">{{ t('director.directives.kinds.' + k) }}</el-radio-button></el-radio-group>
            </el-form-item>
            <el-form-item><el-checkbox v-model="redoForm.replan">{{ t('director.redo.replan') }}</el-checkbox></el-form-item>
            <el-form-item><el-checkbox v-model="redoForm.auto_start">{{ t('director.redo.autoStart') }}</el-checkbox></el-form-item>
          </div>
          <el-form-item :label="t('director.redo.note')">
            <el-input v-model="redoForm.note" type="textarea" :autosize="{ minRows: 2, maxRows: 8 }" :placeholder="t('director.redo.notePlaceholder')" data-testid="redo-note" />
          </el-form-item>
          <div class="row">
            <el-button size="small" :disabled="!director.canRedo.value" :loading="director.busy.value === 'redo-plan'" data-testid="redo-preview" @click="director.planRedo(redoForm.from_chapter)">{{ t('director.redo.preview') }}</el-button>
            <span v-if="director.redoPlan.value" class="muted small" data-testid="redo-plan">{{ t('director.redo.plan', { kept: director.redoPlan.value.chapters_kept, discarded: discarded.length, list: discarded.join(', '), latest: director.redoPlan.value.latest_committed }) }}</span>
            <span class="spacer" />
            <el-popconfirm :title="t('director.redo.confirmBody', { list: discardedList, prev: redoForm.from_chapter - 1 })" :confirm-button-text="t('director.redo.confirm', { n: redoForm.from_chapter })" width="360" @confirm="doRedo">
              <template #reference>
                <el-button type="danger" size="small" :disabled="!director.canRedo.value" :loading="director.busy.value === 'redo'" data-testid="redo-btn">{{ t('director.redo.confirm', { n: redoForm.from_chapter }) }}</el-button>
              </template>
            </el-popconfirm>
          </div>
        </el-form>
        <el-collapse v-if="redoLog.length" class="notes">
          <el-collapse-item :title="t('director.redo.log')">
            <ul class="kv"><li v-for="(e, i) in redoLog" :key="i"><span>{{ t('director.redo.logEntry', { n: e.from_chapter, note: e.note ? t('director.redo.withNote') : '', when: e.at || '' }) }}</span></li></ul>
          </el-collapse-item>
        </el-collapse>
      </el-tab-pane>

      <!-- ---------------------------------------------------------- quality -->
      <el-tab-pane :label="t('director.tabs.quality')" name="quality" :disabled="!director.hasProject.value">
        <p class="muted">{{ t('director.quality.hint') }}</p>
        <div class="row">
          <el-input-number v-model="qualityChapter" :min="1" :max="Math.max(1, job.chapters_committed || 1)" size="small" data-testid="quality-chapter" />
          <el-button size="small" data-testid="quality-load" @click="director.loadQuality(qualityChapter, true)">{{ t('director.quality.load') }}</el-button>
        </div>
        <template v-if="q">
          <div class="scores" data-testid="quality-scores">
            <div class="score overall">
              <div class="muted small">{{ t('director.quality.overall') }}</div>
              <b>{{ q.webnovel_after?.overall?.toFixed(1) ?? '–' }}</b>
              <div class="muted small">{{ t('director.quality.before') }} {{ q.webnovel_before?.overall?.toFixed(1) ?? '–' }}</div>
            </div>
            <div v-for="dim in CONFORMANCE_DIMENSIONS" :key="dim" class="score">
              <div class="muted small">{{ t('director.quality.dims.' + dim) }}</div>
              <el-progress type="dashboard" :percentage="(q.webnovel_after?.scores?.[dim] ?? 0) * 10" :width="64" :stroke-width="6" :color="scoreColor(q.webnovel_after?.scores?.[dim] ?? 0)">
                <template #default><b>{{ q.webnovel_after?.scores?.[dim] ?? '–' }}</b></template>
              </el-progress>
              <div class="muted small">{{ t('director.quality.before') }} {{ q.webnovel_before?.scores?.[dim] ?? '–' }}</div>
            </div>
          </div>
          <div class="muted small">{{ t('director.quality.calls', { n: q.model_calls }) }} · {{ t('director.quality.repairs', { n: q.repair_attempts }) }}<template v-if="q.critic_after?.scores"> · {{ t('director.quality.critic') }}: {{ Object.entries(q.critic_after.scores).filter(([k]) => !k.startsWith('webnovel_')).map(([k, v]) => `${k} ${v}`).join(' · ') }}</template></div>
          <el-collapse v-if="findings.length" class="notes">
            <el-collapse-item :title="t('director.quality.findings', { n: findings.length })">
              <div v-for="(f, i) in findings" :key="i" class="finding">
                <el-tag size="small" :type="f.severity === 'critical' || f.severity === 'high' ? 'danger' : f.severity === 'medium' ? 'warning' : 'info'" effect="plain">{{ f.severity }}</el-tag>
                <span class="mono">{{ f.code }}</span>
                <span>{{ f.problem }}<template v-if="f.quote"> — <i>“{{ f.quote }}”</i></template><template v-if="f.fix"> → {{ f.fix }}</template></span>
              </div>
            </el-collapse-item>
          </el-collapse>
          <p v-else class="muted small">{{ t('director.quality.noFindings') }}</p>
        </template>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { COMEDY_LEVELS, DIRECTIVE_KINDS, DIRECTIVE_SCOPES, THOUGHT_STYLES, WEBNOVEL_PERSPECTIVES, WEBNOVEL_PLATFORMS, WEBNOVEL_REGISTERS, type AutonomousJob, type DirectiveKind, type DirectiveRequest, type JobResponse, type WebnovelStyleProfile } from '@renderer/api/autonomous'
import { CONFORMANCE_DIMENSIONS, directiveProblem, directiveRange, linesToList, listToLines, stylePatch, type Director } from '@renderer/composables/useDirector'

interface RedoLogEntry { from_chapter: number; note?: string; at?: string }
type TagType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

type DirectorTab = 'style' | 'directives' | 'redo' | 'quality'

const props = withDefaults(defineProps<{ job: AutonomousJob; director: Director; initialTab?: DirectorTab }>(), { initialTab: 'style' })
const emit = defineEmits<{ (e: 'close'): void; (e: 'job', res: JobResponse): void }>()
const { t } = useI18n()
const director = props.director

const tab = ref<DirectorTab>(props.initialTab)
const draft = ref<WebnovelStyleProfile | null>(null)
const showPreview = ref(false)
const qualityChapter = ref(Math.max(1, props.job.chapters_committed || 1))
const newDirective = reactive<DirectiveRequest>({ scope: 'novel', kind: 'must', text: '', chapter_from: 1, chapter_to: 0, applies_to: ['planning', 'drafting'], active: true })
const redoForm = reactive<{ from_chapter: number; note: string; note_kind: DirectiveKind; replan: boolean; auto_start: boolean }>({ from_chapter: Math.max(1, props.job.chapters_committed || 1), note: '', note_kind: 'must', replan: true, auto_start: true })

const styleDirty = computed(() => !!draft.value && !!director.style.value && Object.keys(stylePatch(director.style.value, draft.value)).length > 0)
const newProblem = computed(() => directiveProblem(newDirective, props.job.chapter_count || 0))
const q = computed(() => director.quality.value[qualityChapter.value])
// Backend payloads may omit list fields (older rows, chapters whose craft passes never ran); never let the template dereference them.
const findings = computed(() => q.value?.webnovel_after?.findings ?? [])
const redoLog = computed<RedoLogEntry[]>(() => (props.job.stage_results?.redo_log as RedoLogEntry[] | undefined) || [])
const discarded = computed<number[]>(() => director.redoPlan.value?.chapters_discarded ?? [])
const discardedList = computed(() => discarded.value.join(', ') || `${redoForm.from_chapter}–${props.job.chapters_committed}`)
const redoBlocker = computed<'needsPause' | 'needsChapters' | 'needsStage' | null>(() => {
  if (!director.hasProject.value) return null
  if (props.job.status === 'running' || props.job.status === 'queued') return 'needsPause'
  if (!(props.job.chapters_committed || 0)) return 'needsChapters'
  if (!director.canRedo.value) return 'needsStage'
  return null
})
const errorText = computed(() => {
  const e = director.error.value || ''
  return e.startsWith('directive:') ? t('director.directives.problems.' + e.slice('directive:'.length)) : e
})

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T
}
function kindType(k: DirectiveKind): TagType {
  return k === 'must' ? 'danger' : k === 'avoid' ? 'warning' : k === 'prefer' ? 'primary' : 'info'
}
function scoreColor(v: number): string {
  return v >= 8 ? 'var(--el-color-success)' : v >= 6 ? 'var(--el-color-primary)' : v >= 4 ? 'var(--el-color-warning)' : 'var(--el-color-danger)'
}

watch(() => director.style.value, (s) => { if (s) draft.value = clone(s) }, { immediate: true })
watch(() => props.job.chapters_committed, (n) => {
  const max = Math.max(1, n || 1)
  if (redoForm.from_chapter > max) redoForm.from_chapter = max
  if (qualityChapter.value > max) qualityChapter.value = max
})

async function saveStyle(): Promise<void> {
  if (!draft.value || !director.style.value) return
  const res = await director.saveStyle(stylePatch(director.style.value, draft.value))
  if (res) ElMessage.success(t('director.style.saved'))
}
async function togglePreview(): Promise<void> {
  showPreview.value = !showPreview.value
  if (showPreview.value) await director.loadPreview()
}
async function addDirective(): Promise<void> {
  const body: DirectiveRequest = { ...newDirective, text: newDirective.text.trim() }
  if (body.scope === 'novel') {
    body.chapter_from = 0
    body.chapter_to = 0
  }
  if (body.scope === 'chapter') body.chapter_to = 0
  const row = await director.addDirective(body)
  if (row) newDirective.text = ''
}
async function doRedo(): Promise<void> {
  const res = await director.redo({ from_chapter: redoForm.from_chapter, note: redoForm.note, note_kind: redoForm.note_kind, replan: redoForm.replan, auto_start: redoForm.auto_start })
  if (res) {
    ElMessage.success(t('director.redo.done', { prev: redoForm.from_chapter - 1, n: redoForm.from_chapter }))
    redoForm.note = ''
    emit('job', res)
  }
}

onMounted(() => { void director.load() })
</script>

<style scoped>
.director { border-color: var(--el-color-primary-light-5); }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.sub { margin: 4px 0 0; font-size: 12px; line-height: 1.4; max-width: 900px; }
.muted { color: var(--el-text-color-secondary); }
.small { font-size: 12px; }
.mono { font-family: monospace; font-size: 12px; }
.warn { color: var(--el-color-warning); font-size: 12px; }
.note { margin-bottom: 10px; }
.notes { margin: 8px 0; }
.toolbar, .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.toolbar { margin-bottom: 8px; }
.spacer { flex: 1; }
.block { margin-top: 10px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0 16px; }
.field-hint { font-size: 11px; color: var(--el-text-color-secondary); margin-top: 3px; line-height: 1.3; }
.pre { white-space: pre-wrap; font-family: inherit; font-size: 12px; color: var(--el-text-color-regular); max-height: 320px; overflow: auto; margin: 0; }
.directive { border: 1px solid var(--el-border-color-lighter); border-radius: 8px; padding: 8px 10px; margin-top: 8px; }
.directive.off { opacity: 0.6; }
.directive-head { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-bottom: 6px; }
.directive-text :deep(textarea) { font-size: 13px; }
.scores { display: flex; gap: 14px; flex-wrap: wrap; align-items: flex-end; margin: 10px 0; }
.score { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 72px; }
.score.overall b { font-size: 28px; line-height: 1.1; }
.finding { display: flex; gap: 8px; align-items: flex-start; font-size: 12px; padding: 3px 0; }
.kv { list-style: none; padding: 0; margin: 0; font-size: 12px; }
.kv li { padding: 3px 0; border-bottom: 1px dashed var(--el-border-color-lighter); }
</style>
