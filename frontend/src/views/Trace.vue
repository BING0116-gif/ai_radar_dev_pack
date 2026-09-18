<script setup>
import { onMounted, ref } from 'vue'
import * as api from '../api'

const runs = ref([])
const steps = ref([])
const loading = ref(true)
const error = ref('')
const selectedRunId = ref(null)

const EVENT_META = {
  run_start: { label: '开始', dot: 'dot-gray' },
  llm_turn: { label: '模型决策', dot: 'dot-llm' },
  tool_call: { label: '调用工具', dot: 'dot-tool' },
  tool_result: { label: '工具结果', dot: 'dot-result' },
  run_error: { label: '出错', dot: 'dot-fail' },
  run_finish: { label: '结束', dot: 'dot-gray' },
}

function meta(eventType) {
  return EVENT_META[eventType] || { label: eventType, dot: 'dot-gray' }
}

const KIND = { run_start: 'gray', run_finish: 'gray', llm_turn: 'llm', tool_call: 'tool', tool_result: 'result', run_error: 'fail' }
function kindClass(eventType) {
  return 'kind-' + (KIND[eventType] || 'gray')
}

function inputPreview(step) {
  try {
    return JSON.stringify(step.tool_input).slice(0, 240)
  } catch {
    return String(step.tool_input || '')
  }
}

function fmtTokens(n) {
  return Number(n || 0).toLocaleString()
}

function turnInfo(step) {
  const t = step.tool_input || {}
  return `调用工具 ${t.tool_calls || 0} 次 · 输入 ${fmtTokens(t.token_input)} / 输出 ${fmtTokens(t.token_output)} tokens`
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    runs.value = await api.getRuns()
    if (runs.value.length && selectedRunId.value === null) {
      selectRun(runs.value[0].id)
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function selectRun(id) {
  selectedRunId.value = id
  loading.value = true
  error.value = ''
  try {
    steps.value = await api.getRunSteps(id)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <div>
    <h2>Agent 运行轨迹</h2>
    <p class="hint" style="margin-top: -8px">
      每一步都由模型自主决策：调用哪个工具、调用几次、何时停止 —— 这是「工具调用顺序由 LLM 决定」的直接证据。
    </p>
    <div v-if="error" class="error">{{ error }}</div>

    <div class="card">
      <p class="hint" style="margin-top: 0">选择一次运行：</p>
      <div class="run-pills">
        <button
          v-for="run in runs"
          :key="run.id"
          class="pill"
          :class="{ active: run.id === selectedRunId }"
          @click="selectRun(run.id)"
        >
          #{{ run.id }} · {{ run.status }}
        </button>
        <span v-if="!runs.length" class="hint">暂无运行记录</span>
      </div>
    </div>

    <div class="card">
      <p v-if="loading" class="hint">加载中…</p>
      <div v-else-if="!steps.length" class="hint">该运行暂无步骤</div>

      <ol v-else class="timeline">
        <li v-for="step in steps" :key="step.step_no" class="tl-item">
          <div class="tl-dot">
            <span class="dot" :class="meta(step.event_type).dot"></span>
          </div>
          <div class="tl-body">
            <div class="tl-head">
              <span class="tl-no">#{{ step.step_no }}</span>
              <span class="tl-kind" :class="kindClass(step.event_type)">{{ meta(step.event_type).label }}</span>
              <span v-if="step.event_type === 'tool_result'" class="chip" :class="step.success ? 'ok' : 'fail'">
                {{ step.success ? '成功' : '失败' }}
              </span>
              <span v-if="step.duration_ms" class="hint" style="font-size: 12px">{{ step.duration_ms }} ms</span>
            </div>

            <div v-if="step.event_type === 'llm_turn'" class="tl-code">{{ turnInfo(step) }}</div>
            <div v-if="step.event_type === 'tool_call' || step.event_type === 'tool_result'">
              <div v-if="step.tool_name" class="tl-code">工具：{{ step.tool_name }}</div>
              <div v-if="step.tool_input" class="tl-code">{{ inputPreview(step) }}</div>
            </div>
            <div v-if="step.tool_output_preview" class="tl-code out">{{ step.tool_output_preview }}</div>
          </div>
        </li>
      </ol>
    </div>
  </div>
</template>

<style scoped>
.run-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  border: 1px solid var(--border);
  background: #fff;
  color: var(--ink);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 13px;
  cursor: pointer;
}

.pill.active {
  background: var(--pine);
  border-color: var(--pine);
  color: #fff;
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
}

.tl-item {
  display: flex;
  gap: 12px;
  position: relative;
  padding-bottom: 14px;
}

.tl-item::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 18px;
  bottom: 0;
  width: 2px;
  background: var(--border);
}

.tl-item:last-child::before {
  display: none;
}

.tl-dot {
  width: 12px;
  flex-shrink: 0;
  padding-top: 4px;
}

.dot {
  display: block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px var(--border);
}

.dot-gray { background: #c4c4c4; }
.dot-llm { background: #4a86b8; }
.dot-tool { background: #c9a53c; }
.dot-result { background: #3e6b5a; }
.dot-fail { background: #b0413e; }

.tl-body {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  background: #fff;
}

.tl-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tl-no {
  font-size: 12px;
  color: var(--muted);
}

.tl-kind {
  font-size: 12px;
  border-radius: 6px;
  padding: 1px 8px;
}

.kind-gray { background: #f1eee8; color: #6b6b6b; }
.kind-llm { background: #e8eff4; color: #2f5f7a; }
.kind-tool { background: #f5eedd; color: #8a6d1a; }
.kind-result { background: #eef3ef; color: #3e6b5a; }
.kind-fail { background: #fdf0ef; color: #b0413e; }

.tl-code {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
  color: #4a4a4a;
  background: #faf8f4;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
  margin-top: 8px;
  word-break: break-all;
  white-space: pre-wrap;
}

.tl-code.out {
  background: #f4f7f4;
}
</style>