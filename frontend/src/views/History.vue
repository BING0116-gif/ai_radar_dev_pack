<script setup>
import { onMounted, ref } from 'vue'
import * as api from '../api'
import BriefReader from '../components/BriefReader.vue'

const briefs = ref([])
const loading = ref(true)
const error = ref('')
const selectedId = ref(null)
const detail = ref(null)
const detailLoading = ref(false)

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    briefs.value = await api.getBriefs()
    if (briefs.value.length && selectedId.value === null) {
      selectBrief(briefs.value[0].id)
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function statusLabel(status) {
  return { pending: '待审', rejected: '已打回', published: '已发布' }[status] || status
}

function statusClass(status) {
  if (status === 'pending') return 'warn'
  if (status === 'rejected') return 'fail'
  return ''
}

async function selectBrief(id) {
  selectedId.value = id
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await api.getBrief(id)
  } catch (err) {
    error.value = err.message
  } finally {
    detailLoading.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <div>
    <h2>历史简报</h2>
    <div v-if="error" class="error">{{ error }}</div>

    <div class="card">
      <p v-if="loading" class="hint">加载中…</p>
      <table v-else>
        <thead>
          <tr><th>日期</th><th>标题</th><th>状态</th><th>条数</th></tr>
        </thead>
        <tbody>
          <tr v-if="!briefs.length">
            <td colspan="4" class="hint">暂无简报</td>
          </tr>
          <tr
            v-for="brief in briefs"
            :key="brief.id"
            :class="{ selected: brief.id === selectedId }"
            class="clickable"
            @click="selectBrief(brief.id)"
          >
            <td>{{ brief.brief_date }}</td>
            <td>{{ brief.title }}</td>
            <td>
              <span
                v-if="brief.status && brief.status !== 'published'"
                class="chip"
                :class="statusClass(brief.status)"
              >{{ statusLabel(brief.status) }}</span>
              <span v-else class="hint">已发布</span>
            </td>
            <td>{{ brief.item_count }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="detailLoading" class="card hint">加载详情…</div>
    <div v-else-if="detail" class="card">
      <h3 class="section-title">{{ detail.title }}</h3>
      <div class="hint" style="margin-bottom: 12px">
        {{ detail.brief_date }} · {{ detail.item_count }} 条 · run #{{ detail.run_id }}
      </div>
      <BriefReader :brief="detail" />
    </div>
  </div>
</template>