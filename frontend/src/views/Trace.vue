<script setup>
import { onMounted, ref } from 'vue'
import * as api from '../api'

const runs = ref([])
const steps = ref([])
const loading = ref(true)
const error = ref('')
const selectedRunId = ref(null)

const EVENT_CHIP = {
  run_start: 'chip-gray',
  run_finish: 'chip-gray',
  llm_turn: 'chip-llm',
  tool_call: 'chip-tool',
  tool_result: 'chip-result',
  run_error: 'chip-fail',
}

function chipClass(eventType) {
  return EVENT_CHIP[eventType] || 'chip-gray'
}

function inputPreview(step) {
  try {
    return JSON.stringify(step.tool_input).slice(0, 240)
  } catch {
    return String(step.tool_input || '')
  }
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
    <div v-if="error" class="error">{{ error }}</div>

    <div class="card">
      <p class="hint" style="margin-top: 0">选择一次运行（点击按钮切换）：</p>
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
      <table v-else>
        <thead>
          <tr>
            <th>#</th><th>事件</th><th>工具</th><th>输入</th><th>输出</th><th>耗时</th><th>结果</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!steps.length">
            <td colspan="7" class="hint">该运行暂无步骤</td>
          </tr>
          <tr v-for="step in steps" :key="step.step_no">
            <td>{{ step.step_no }}</td>
            <td><span class="chip" :class="chipClass(step.event_type)">{{ step.event_type }}</span></td>
            <td>{{ step.tool_name || '—' }}</td>
            <td class="preview">{{ step.tool_input ? inputPreview(step) : '—' }}</td>
            <td class="preview">{{ step.tool_output_preview || '—' }}</td>
            <td>{{ step.duration_ms }} ms</td>
            <td>
              <span v-if="step.event_type === 'tool_result'" class="chip" :class="step.success ? 'ok' : 'fail'">
                {{ step.success ? '成功' : '失败' }}
              </span>
              <span v-else>—</span>
            </td>
          </tr>
        </tbody>
      </table>
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

.chip {
  display: inline-block;
  font-size: 12px;
  border-radius: 6px;
  padding: 2px 8px;
  white-space: nowrap;
}

.chip-gray { background: #f1eee8; color: #6b6b6b; }
.chip-llm { background: #e8eff4; color: #2f5f7a; }
.chip-tool { background: #f5eedd; color: #8a6d1a; }
.chip-result { background: #eef3ef; color: #3e6b5a; }
.chip-fail { background: #fdf0ef; color: #b0413e; }
.ok { background: #eef3ef; color: #3e6b5a; font-weight: 600; }
.fail { background: #fdf0ef; color: #b0413e; font-weight: 600; }

.preview {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
  color: #4a4a4a;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>