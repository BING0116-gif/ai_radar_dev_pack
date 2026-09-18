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

const latest = computed(() => briefs.value[0] || null)

const stats = computed(() => {
  const ok = runs.value.filter((r) => r.status === 'completed').length
  const total = runs.value.length
  return {
    briefs: briefs.value.length,
    runs: total,
    success: total ? Math.round((ok / total) * 100) : 0,
    last: total ? runs.value[0].started_at : '—',
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
          <tr><th>ID</th><th>状态</th><th>步数</th><th>开始时间</th></tr>
        </thead>
        <tbody>
          <tr v-if="!runs.length">
            <td colspan="4" class="hint">暂无运行记录</td>
          </tr>
          <tr v-for="run in runs" :key="run.id">
            <td>#{{ run.id }}</td>
            <td><span class="chip" :class="run.status === 'completed' ? 'ok' : run.status === 'failed' ? 'fail' : 'chip-gray'">{{ run.status }}</span></td>
            <td>{{ run.step_count }}</td>
            <td>{{ run.started_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>