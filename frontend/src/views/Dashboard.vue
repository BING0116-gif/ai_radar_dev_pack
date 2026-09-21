<script setup>
import { computed, onMounted, ref } from 'vue'
import MarkdownIt from 'markdown-it'
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
const pendingBriefs = ref([])
const feedbackMap = ref({})
const reviewing = ref(false)

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const latest = computed(() => briefs.value[0] || null)

// 首页只展示最近 5 次运行，完整列表在「运行轨迹」页
const recentRuns = computed(() => runs.value.slice(0, 5))

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

const renderedChat = computed(() => md.render(chatAnswer.value || ''))

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [briefList, runList, reviewList, feedbackRows] = await Promise.all([
      api.getBriefs(),
      api.getRuns(),
      api.getReviews(),
      api.getFeedback(),
    ])
    briefs.value = briefList
    runs.value = runList
    pendingBriefs.value = reviewList
    const map = {}
    for (const row of feedbackRows) map[row.item_key] = row.verdict
    feedbackMap.value = map
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
    const res = await api.createRun()
    await refresh()
    if (res && res.brief_status === 'pending') {
      scrollToReviewWorkbench()
    }
  } catch (err) {
    error.value = err.message
  } finally {
    generating.value = false
  }
}

async function decideReview(briefId, verdict) {
  reviewing.value = true
  error.value = ''
  try {
    if (verdict === 'approve') await api.approveReview(briefId)
    else await api.rejectReview(briefId)
    await refresh()
  } catch (err) {
    error.value = err.message
  } finally {
    reviewing.value = false
  }
}

async function onFeedback({ item_key, item_title, verdict }) {
  try {
    if (verdict === null) {
      await api.deleteFeedback(item_key)
    } else {
      await api.submitFeedback({ item_key, item_title, verdict })
    }
    const rows = await api.getFeedback()
    const map = {}
    for (const row of rows) map[row.item_key] = row.verdict
    feedbackMap.value = map
  } catch (err) {
    error.value = err.message
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

function fmtTs(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function statusLabel(status) {
  return { pending: '待审', rejected: '已打回', published: '已发布' }[status] || status
}

function scrollToReviewWorkbench() {
  const el = document.querySelector('.review-workbench')
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
        <div class="md-wrap" v-html="renderedChat"></div>
      </div>
    </div>

    <!-- A2: 待审简报工作台（HITL） -->
    <div v-if="pendingBriefs.length" class="card review-workbench">
      <div class="row-card" style="align-items: baseline">
        <h3 class="section-title" style="margin: 0">待审简报</h3>
        <span class="chip warn">{{ pendingBriefs.length }} 篇等待你确认发布</span>
      </div>
      <div
        v-for="brief in pendingBriefs"
        :key="brief.id"
        class="review-item"
      >
        <div class="review-body">
          <div class="review-title">{{ brief.title }}</div>
          <div class="hint" style="font-size: 12px">
            {{ brief.brief_date }} · {{ brief.item_count }} 条 · run #{{ brief.run_id }}
          </div>
        </div>
        <div class="review-actions">
          <button class="btn btn-sm btn-soft" :disabled="reviewing" @click="decideReview(brief.id, 'reject')">打回</button>
          <button class="btn btn-sm" :disabled="reviewing" @click="decideReview(brief.id, 'approve')">通过并发布</button>
        </div>
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
      <div v-if="loading" class="skeleton">
        <div class="sk sk-title"></div>
        <div class="sk sk-line"></div>
        <div class="sk sk-line short"></div>
        <div class="sk sk-card"></div>
        <div class="sk sk-card"></div>
      </div>
      <div v-else-if="detail">
        <div class="row-card" style="align-items: baseline">
          <h3 class="section-title">{{ detail.title }}</h3>
          <div class="row-card" style="gap: 8px">
            <span v-if="detail.status && detail.status !== 'published'" class="chip warn">{{ statusLabel(detail.status) }}</span>
            <span class="hint">
              {{ detail.brief_date }} · {{ detail.item_count }} 条 · run #{{ detail.run_id }}
            </span>
          </div>
        </div>
        <BriefReader :brief="detail" :feedback-map="feedbackMap" @feedback="onFeedback" />
      </div>
      <p v-else class="hint">暂无简报，点击「立即生成」开始。</p>
    </div>

    <h3 class="section-title" style="display: flex; justify-content: space-between; align-items: baseline; gap: 12px">
      <span>最近运行</span>
      <span class="hint" style="font-size: 12px">仅显示最近 5 次，完整列表见「运行轨迹」</span>
    </h3>
    <div class="card">
      <table>
        <thead>
          <tr><th>ID</th><th>状态</th><th>步数</th><th>输入 tokens</th><th>输出 tokens</th><th>开始时间</th></tr>
        </thead>
        <tbody>
          <tr v-if="!recentRuns.length">
            <td colspan="6" class="hint">暂无运行记录</td>
          </tr>
          <tr v-for="run in recentRuns" :key="run.id">
            <td>#{{ run.id }}</td>
            <td><span class="chip" :class="run.status === 'completed' ? 'ok' : run.status === 'failed' ? 'fail' : 'chip-gray'">{{ run.status }}</span></td>
            <td>{{ run.step_count }}</td>
            <td>{{ fmtTokens(run.token_input) }}</td>
            <td>{{ fmtTokens(run.token_output) }}</td>
            <td>{{ fmtTs(run.started_at) }}</td>
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

/* ---- markdown 回答排版（与 BriefReader 兜底一致） ---- */
.md-wrap {
  line-height: 1.7;
  font-size: 14px;
}

.md-wrap :deep(h1) {
  font-size: 17px;
  margin: 0 0 10px;
}

.md-wrap :deep(h2) {
  font-size: 15px;
  margin: 14px 0 6px;
}

.md-wrap :deep(h3) {
  font-size: 14px;
  margin: 12px 0 4px;
}

.md-wrap :deep(p) {
  margin: 8px 0;
}

.md-wrap :deep(a) {
  color: var(--pine);
  word-break: break-all;
}

.md-wrap :deep(ul), .md-wrap :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.md-wrap :deep(li) {
  margin: 4px 0;
}

.md-wrap :deep(code) {
  background: #f1eee8;
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 12.5px;
}

/* ---- 待审工作台 ---- */
.review-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--border);
  flex-wrap: wrap;
}

.review-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}

.review-actions {
  display: flex;
  gap: 8px;
}

.chip.warn {
  background: #f5eedd;
  color: #8a6d1a;
}

/* ---- 骨架屏 ---- */
.skeleton {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sk {
  border-radius: 8px;
  background: linear-gradient(90deg, #efece6 25%, #f7f4ee 37%, #efece6 63%);
  background-size: 400% 100%;
  animation: sk-shimmer 1.4s ease infinite;
}

.sk-title { height: 18px; width: 40%; }
.sk-line { height: 12px; width: 70%; }
.sk-line.short { width: 45%; }
.sk-card { height: 76px; }

@keyframes sk-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
</style>