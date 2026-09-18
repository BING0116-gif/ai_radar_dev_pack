<script setup>
import { computed, onMounted, ref } from 'vue'
import * as api from '../api'
import BriefReader from '../components/BriefReader.vue'

const briefs = ref([])
const runs = ref([])
const detail = ref(null)
const loading = ref(true)
const error = ref('')
const generating = ref(false)
const chatQuestion = ref('')
const chatAnswer = ref('')
const chatRun = ref(null)
const chatLoading = ref(false)

const latest = computed(() => briefs.value[0] || null)

const stats = computed(() => {
  const ok = runs.value.filter((r) => r.status === 'completed').length
  const total = runs.value.length
  return {
    briefs: briefs.value.length,
    runs: total,
    success: total ? Math.round((ok / total) * 100) : 0,
    last: total ? runs.value[0].started_at : '—',
    tokens: runs.value.reduce((sum, r) => sum + (r.token_input || 0) + (r.token_output || 0), 0),
  }
})

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [briefList, runList] = await Promise.all([api.getBriefs(), api.getRuns()])
    briefs.value = briefList
    runs.value = runList
    if (briefList.length) {
      detail.value = await api.getBrief(briefList[0].id)
    } else {
      detail.value = null
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function generateNow() {
  generating.value = true
  error.value = ''
  try {
    await api.createRun()
    await refresh()
  } catch (err) {
    error.value = err.message
  } finally {
    generating.value = false
  }
}

async function askAgent() {
  const task = chatQuestion.value.trim()
  if (!task || chatLoading.value) return
  chatLoading.value = true
  error.value = ''
  try {
    const res = await api.createRun({ task, mode: 'chat' })
    chatRun.value = res
    chatAnswer.value = res.content || '（Agent 未返回内容）'
    await refresh()
  } catch (err) {
    error.value = err.message
  } finally {
    chatLoading.value = false
  }
}

function fmtTokens(n) {
  return Number(n || 0).toLocaleString()
}

onMounted(refresh)
</script>

<template>
  <div>
    <div class="row-card" style="margin-bottom: 16px">
      <h2 style="margin: 0">今日简报</h2>
      <button class="btn" :disabled="generating" @click="generateNow">
        {{ generating ? '生成中…' : '立即生成' }}
      </button>
    </div>
    <div v-if="error" class="error">{{ error }}</div>

    <!-- A1: 向 Agent 提问（自由任务） -->
    <div class="card">
      <h3 class="section-title" style="margin-top: 0">向 Agent 提问</h3>
      <div class="chat-row">
        <textarea
          v-model="chatQuestion"
          class="chat-input"
          rows="2"
          placeholder="输入任意问题或任务，例如：查一下本周 DeepSeek 有什么新动态"
          @keydown.enter.exact.prevent="askAgent"
        ></textarea>
        <button class="btn" :disabled="chatLoading || !chatQuestion.trim()" @click="askAgent">
          {{ chatLoading ? '思考中…' : '提问' }}
        </button>
      </div>
      <div v-if="chatAnswer" class="chat-answer">
        <div class="chat-answer-head">
          <span class="hint">回答 · run #{{ chatRun.run_id }} · {{ fmtTokens(chatRun.token_input) }} 进 / {{ fmtTokens(chatRun.token_output) }} 出 tokens</span>
          <button class="link-btn" @click="chatQuestion = ''; chatAnswer = ''; chatRun = null">清空</button>
        </div>
        <p class="chat-text">{{ chatAnswer }}</p>
      </div>
    </div>

    <!-- KPI 指标卡 -->
    <div class="kpi-row">
      <div class="kpi">
        <div class="kpi-value">{{ stats.briefs }}</div>
        <div class="kpi-label">累计简报</div>
      </div>
      <div class="kpi">
        <div class="kpi-value">{{ stats.runs }}</div>
        <div class="kpi-label">运行次数</div>
      </div>
      <div class="kpi">
        <div class="kpi-value">{{ stats.tokens.toLocaleString() }}</div>
        <div class="kpi-label">累计 tokens</div>
      </div>
      <div class="kpi">
        <div class="kpi-value">{{ stats.success }}%</div>
        <div class="kpi-label">成功率</div>
      </div>
      <div class="kpi">
        <div class="kpi-value kpi-last">{{ stats.last }}</div>
        <div class="kpi-label">最近运行</div>
      </div>
    </div>

    <!-- 今日简报大卡 -->
    <div class="card">
      <p v-if="loading" class="hint">加载中…</p>
      <div v-else-if="detail">
        <div class="row-card" style="align-items: baseline">
          <h3 class="section-title">{{ detail.title }}</h3>
          <span class="hint">
            {{ detail.brief_date }} · {{ detail.item_count }} 条 · run #{{ detail.run_id }}
          </span>
        </div>
        <BriefReader :brief="detail" />
      </div>
      <p v-else class="hint">暂无简报，点击「立即生成」开始。</p>
    </div>

    <h3 class="section-title">最近运行</h3>
    <div class="card">
      <table>
        <thead>
          <tr><th>ID</th><th>状态</th><th>步数</th><th>输入 tokens</th><th>输出 tokens</th><th>开始时间</th></tr>
        </thead>
        <tbody>
          <tr v-if="!runs.length">
            <td colspan="6" class="hint">暂无运行记录</td>
          </tr>
          <tr v-for="run in runs" :key="run.id">
            <td>#{{ run.id }}</td>
            <td><span class="chip" :class="run.status === 'completed' ? 'ok' : run.status === 'failed' ? 'fail' : 'chip-gray'">{{ run.status }}</span></td>
            <td>{{ run.step_count }}</td>
            <td>{{ fmtTokens(run.token_input) }}</td>
            <td>{{ fmtTokens(run.token_output) }}</td>
            <td>{{ run.started_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.chat-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.chat-input {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  font: inherit;
  font-size: 14px;
  color: var(--ink);
  background: #fff;
  resize: vertical;
  min-height: 44px;
}

.chat-input:focus {
  outline: none;
  border-color: var(--pine);
  box-shadow: 0 0 0 2px rgba(62, 107, 90, 0.12);
}

.chat-answer {
  margin-top: 12px;
  border-top: 1px solid var(--border);
  padding-top: 12px;
}

.chat-answer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.chat-text {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  line-height: 1.7;
}

.link-btn {
  border: none;
  background: none;
  color: var(--muted, #8a8378);
  font-size: 12px;
  cursor: pointer;
  padding: 2px 4px;
}

.link-btn:hover {
  color: var(--pine);
}
</style>