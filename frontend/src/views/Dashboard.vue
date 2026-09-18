<script setup>
import { onMounted, ref } from 'vue'
import * as api from '../api'

const briefs = ref([])
const runs = ref([])
const loading = ref(true)
const error = ref('')
const generating = ref(false)

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const [briefList, runList] = await Promise.all([api.getBriefs(), api.getRuns()])
    briefs.value = briefList
    runs.value = runList
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
    <h2>Dashboard</h2>
    <div v-if="error" class="error">{{ error }}</div>

    <div class="card row-card">
      <div>
        <strong>今日简报</strong>
        <template v-if="briefs.length">
          <div class="hint">
            最近一期：{{ briefs[0].title }}（{{ briefs[0].item_count }} 条，{{ briefs[0].brief_date }}）
          </div>
        </template>
        <div v-else-if="!loading" class="hint">暂无简报，点击「立即生成」开始。</div>
      </div>
      <button class="btn" :disabled="generating" @click="generateNow">
        {{ generating ? '生成中…' : '立即生成' }}
      </button>
    </div>

    <h3 class="section-title">最近运行</h3>
    <div class="card">
      <p v-if="loading" class="hint">加载中…</p>
      <table v-else>
        <thead>
          <tr><th>ID</th><th>状态</th><th>步数</th><th>开始时间</th></tr>
        </thead>
        <tbody>
          <tr v-if="!runs.length">
            <td colspan="4" class="hint">暂无运行记录</td>
          </tr>
          <tr v-for="run in runs" :key="run.id">
            <td>#{{ run.id }}</td>
            <td>{{ run.status }}</td>
            <td>{{ run.step_count }}</td>
            <td>{{ run.started_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>