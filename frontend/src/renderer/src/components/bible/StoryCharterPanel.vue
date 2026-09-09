<template>
  <div class="charter" data-testid="story-charter-panel">
    <div class="charter-head">
      <div>
        <h3 class="title">{{ t('charter.title') }}</h3>
        <p class="muted">{{ t('charter.subtitle') }}</p>
      </div>
      <div class="head-actions">
        <el-tag v-if="summary?.exists" size="small" effect="plain" type="success">{{ t('charter.counts', { musts: summary.musts, prefers: summary.prefers, open: summary.open_choices, never: summary.boundaries }) }}</el-tag>
        <el-tag v-else size="small" effect="plain" type="info">{{ t('charter.notYet') }}</el-tag>
        <el-button size="small" :loading="loading" @click="load">{{ t('bible.refresh') }}</el-button>
        <el-button size="small" type="primary" :loading="saving" :disabled="!dirty" data-testid="charter-save" @click="save">{{ t('charter.save') }}</el-button>
      </div>
    </div>

    <el-alert v-if="error" type="error" :closable="true" show-icon :title="error" @close="error = ''" />
    <el-alert v-if="summary?.brief_changed_since_interpretation" type="warning" :closable="false" show-icon :title="t('charter.briefChanged')" data-testid="charter-brief-changed" />

    <!-- Brief + identity -->
    <el-card shadow="never" class="block">
      <template #header><b>{{ t('charter.briefTitle') }}</b><span class="muted hint">{{ t('charter.briefHint') }}</span></template>
      <div class="grid2">
        <el-form-item :label="t('charter.workingTitle')"><el-input v-model="charter.working_title" @input="touch" /></el-form-item>
        <el-form-item :label="t('charter.pitch')"><el-input v-model="charter.one_line_pitch" @input="touch" /></el-form-item>
        <el-form-item :label="t('charter.audience')"><el-input v-model="charter.audience" :placeholder="t('charter.audiencePlaceholder')" @input="touch" /></el-form-item>
        <div class="grid2 tight">
          <el-form-item :label="t('charter.targetChapters')"><el-input-number v-model="charter.target_chapters" :min="1" :max="2000" @change="touch" /></el-form-item>
          <el-form-item :label="t('charter.wordsPerChapter')"><el-input-number v-model="charter.words_per_chapter" :min="300" :max="20000" :step="100" @change="touch" /></el-form-item>
        </div>
      </div>
      <el-form-item :label="t('charter.brief')">
        <el-input v-model="charter.brief" type="textarea" :autosize="{ minRows: 4, maxRows: 16 }" :placeholder="t('charter.briefPlaceholder')" data-testid="charter-brief" @input="touch" />
      </el-form-item>
      <div class="interpret-row">
        <el-select v-model="llmConfigId" filterable size="small" class="model" :placeholder="t('bible.selectModel')">
          <el-option v-for="c in llmConfigs" :key="c.id" :label="c.display_name || c.model_name" :value="Number(c.id)" />
        </el-select>
        <el-button size="small" type="primary" plain :disabled="!llmConfigId || !charter.brief.trim()" :loading="interpreting" data-testid="charter-interpret" @click="interpret">{{ t('charter.interpret') }}</el-button>
        <span class="muted">{{ t('charter.interpretHint') }}</span>
      </div>
      <div v-if="charter.interpretation_notes" class="notes" data-testid="charter-notes">
        <b>{{ t('charter.interpretationNotes') }}</b>
        <p>{{ charter.interpretation_notes }}</p>
      </div>
      <div v-if="charter.questions_for_author.length" class="questions" data-testid="charter-questions">
        <b>{{ t('charter.questions') }}</b>
        <ul><li v-for="(q, i) in charter.questions_for_author" :key="i">{{ q }}</li></ul>
        <span class="muted">{{ t('charter.questionsHint') }}</span>
      </div>
    </el-card>

    <!-- Requirements -->
    <el-card shadow="never" class="block" data-testid="charter-requirements">
      <template #header>
        <b>{{ t('charter.requirements') }}</b><span class="muted hint">{{ t('charter.requirementsHint') }}</span>
        <el-button size="small" text type="primary" class="add" @click="addRequirement">{{ t('charter.add') }}</el-button>
      </template>
      <el-empty v-if="!charter.requirements.length" :description="t('charter.noRequirements')" :image-size="50" />
      <div v-for="(r, i) in charter.requirements" :key="r.id" class="entry" :class="{ interpreted: r.source === 'interpreted' }">
        <div class="entry-main">
          <el-input v-model="r.text" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" :placeholder="t('charter.requirementPlaceholder')" @input="touch" />
          <p v-if="r.rationale" class="muted rationale">{{ t('charter.because') }} {{ r.rationale }}</p>
        </div>
        <div class="entry-side">
          <el-select v-model="r.strength" size="small" class="w110" @change="touch">
            <el-option value="must" :label="t('charter.strength.must')" />
            <el-option value="prefer" :label="t('charter.strength.prefer')" />
          </el-select>
          <el-select v-model="r.scope" size="small" class="w130" @change="touch">
            <el-option v-for="s in meta.scopes" :key="s" :value="s" :label="t('charter.scope.' + s, s)" />
          </el-select>
          <el-select v-model="r.category" size="small" class="w130" @change="touch">
            <el-option v-for="c in meta.categories" :key="c" :value="c" :label="t('charter.category.' + c, c)" />
          </el-select>
          <el-tag size="small" effect="plain" :type="r.source === 'author' ? 'success' : 'warning'" :title="t('charter.sourceHint.' + r.source)">{{ t('charter.source.' + r.source) }}</el-tag>
          <el-button size="small" text type="danger" @click="remove(charter.requirements, i)">✕</el-button>
        </div>
      </div>
    </el-card>

    <!-- Open choices -->
    <el-card shadow="never" class="block" data-testid="charter-open-choices">
      <template #header>
        <b>{{ t('charter.openChoices') }}</b><span class="muted hint">{{ t('charter.openChoicesHint') }}</span>
        <el-button size="small" text type="primary" class="add" @click="addOpenChoice">{{ t('charter.add') }}</el-button>
      </template>
      <el-empty v-if="!charter.open_choices.length" :description="t('charter.noOpenChoices')" :image-size="50" />
      <div v-for="(o, i) in charter.open_choices" :key="o.id" class="entry" :class="{ interpreted: o.source === 'interpreted' }">
        <div class="entry-main">
          <el-input v-model="o.topic" :placeholder="t('charter.openTopicPlaceholder')" @input="touch" />
          <el-input v-model="o.guidance" size="small" class="sub" :placeholder="t('charter.openGuidancePlaceholder')" @input="touch" />
        </div>
        <div class="entry-side">
          <el-select v-model="o.decide_by" size="small" class="w170" @change="touch">
            <el-option value="author" :label="t('charter.decideBy.author')" />
            <el-option value="planner" :label="t('charter.decideBy.planner')" />
            <el-option value="either" :label="t('charter.decideBy.either')" />
          </el-select>
          <el-tag size="small" effect="plain" :type="o.source === 'author' ? 'success' : 'warning'">{{ t('charter.source.' + o.source) }}</el-tag>
          <el-button size="small" text type="danger" @click="remove(charter.open_choices, i)">✕</el-button>
        </div>
      </div>
    </el-card>

    <!-- Boundaries -->
    <el-card shadow="never" class="block" data-testid="charter-boundaries">
      <template #header>
        <b>{{ t('charter.boundaries') }}</b><span class="muted hint">{{ t('charter.boundariesHint') }}</span>
        <el-button size="small" text type="primary" class="add" @click="addBoundary">{{ t('charter.add') }}</el-button>
      </template>
      <el-empty v-if="!charter.boundaries.length" :description="t('charter.noBoundaries')" :image-size="50" />
      <div v-for="(b, i) in charter.boundaries" :key="b.id" class="entry" :class="{ interpreted: b.source === 'interpreted' }">
        <div class="entry-main"><el-input v-model="b.text" :placeholder="t('charter.boundaryPlaceholder')" @input="touch" /></div>
        <div class="entry-side">
          <el-select v-model="b.severity" size="small" class="w110" @change="touch">
            <el-option value="hard" :label="t('charter.severity.hard')" />
            <el-option value="soft" :label="t('charter.severity.soft')" />
          </el-select>
          <el-tag size="small" effect="plain" :type="b.source === 'author' ? 'success' : 'warning'">{{ t('charter.source.' + b.source) }}</el-tag>
          <el-button size="small" text type="danger" @click="remove(charter.boundaries, i)">✕</el-button>
        </div>
      </div>
    </el-card>

    <!-- What the model sees -->
    <el-card shadow="never" class="block" data-testid="charter-preview">
      <template #header>
        <b>{{ t('charter.previewTitle') }}</b><span class="muted hint">{{ t('charter.previewHint') }}</span>
        <el-radio-group v-model="consumer" size="small" class="add" @change="loadPreview">
          <el-radio-button v-for="c in consumers" :key="c" :value="c">{{ t('charter.consumer.' + c, c) }}</el-radio-button>
        </el-radio-group>
      </template>
      <pre v-if="preview" class="preview">{{ preview }}</pre>
      <p v-else class="muted">{{ dirty ? t('charter.previewSaveFirst') : t('charter.previewEmpty') }}</p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, toRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { getAIConfigOptions } from '@renderer/api/ai'
import { getStoryCharter, getStoryCharterMeta, interpretStoryCharter, renderStoryCharter, saveStoryCharter, type CharterSummary } from '@renderer/api/storyCharter'
import { CHARTER_CONSUMERS, useStoryCharter } from '@renderer/composables/useStoryCharter'

const props = defineProps<{ projectId: number }>()
const emit = defineEmits<{ (e: 'saved', summary: CharterSummary): void }>()
const { t } = useI18n()

const state = useStoryCharter({ get: getStoryCharter, save: saveStoryCharter, interpret: interpretStoryCharter, render: renderStoryCharter }, toRef(props, 'projectId'))
const { charter, summary, consumer, preview, loading, saving, interpreting, dirty, error, touch, remove, addRequirement, addOpenChoice, addBoundary, load, loadPreview } = state
const consumers = CHARTER_CONSUMERS

const meta = reactive<{ scopes: string[]; categories: string[] }>({ scopes: [], categories: [] })
const llmConfigs = ref<any[]>([])
const llmConfigId = ref<number | undefined>(undefined)

async function save() {
  const s = await state.save()
  if (s) {
    emit('saved', s)
    ElMessage.success(t('charter.saved'))
  }
}

async function interpret() {
  if (!llmConfigId.value) return
  const s = await state.interpret(llmConfigId.value)
  if (s) {
    emit('saved', s)
    ElMessage.success(t('charter.interpreted', { n: state.interpretedCount.value }))
  }
}

watch(() => props.projectId, load)
onMounted(async () => {
  try { const m = await getStoryCharterMeta(); meta.scopes = m.scopes; meta.categories = m.categories } catch { /* defaults below */ }
  if (!meta.scopes.length) meta.scopes = ['whole_novel', 'planning', 'characters', 'world', 'prose', 'ending', 'chapter']
  if (!meta.categories.length) meta.categories = ['premise', 'protagonist', 'cast', 'world', 'progression', 'relationships', 'romance', 'tone', 'theme', 'structure', 'pacing', 'prose', 'content', 'length', 'ending', 'other']
  try { const o = await getAIConfigOptions(); llmConfigs.value = (o as any)?.llm_configs || []; if (llmConfigs.value.length && !llmConfigId.value) llmConfigId.value = Number(llmConfigs.value[0].id) } catch { /* ignore */ }
  await load()
})
</script>

<style scoped>
.charter { display: flex; flex-direction: column; gap: 12px; }
.charter-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.title { margin: 0; font-size: 16px; }
.muted { color: var(--el-text-color-secondary); font-size: 12px; margin: 2px 0 0; }
.hint { margin-left: 8px; font-weight: normal; }
.head-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.block :deep(.el-card__header) { display: flex; align-items: center; padding: 10px 14px; }
.block :deep(.el-card__body) { padding: 12px 14px; }
.add { margin-left: auto; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0 14px; }
.grid2.tight { grid-template-columns: 1fr 1fr; }
.interpret-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.model { width: 260px; }
.notes, .questions { margin-top: 10px; padding: 8px 10px; border-radius: 6px; background: var(--el-fill-color-light); font-size: 13px; }
.notes p { margin: 4px 0 0; white-space: pre-wrap; }
.questions ul { margin: 4px 0; padding-left: 18px; }
.entry { display: flex; flex-direction: column; gap: 6px; padding: 8px 0; border-bottom: 1px dashed var(--el-border-color-lighter); }
.entry:last-child { border-bottom: none; }
.entry.interpreted { border-left: 3px solid var(--el-color-warning-light-5); padding-left: 8px; }
.entry-main { min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.entry-side { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.entry-side .el-button { margin-left: auto; }
.rationale { margin: 0; }
.sub { margin-top: 2px; }
.w110 { width: 110px; } .w130 { width: 130px; } .w170 { width: 170px; }
.preview { white-space: pre-wrap; font-family: inherit; font-size: 12.5px; line-height: 1.45; margin: 0; max-height: 420px; overflow: auto; color: var(--el-text-color-regular); }
</style>
