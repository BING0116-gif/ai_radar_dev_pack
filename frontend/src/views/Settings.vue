<script setup>
import { onMounted, ref } from 'vue'
import * as api from '../api'

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const saved = ref(false)

const form = ref({
  role: '',
  max_items: 5,
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  notification_channel: 'none',
})
const topicsText = ref('')
const keywordsText = ref('')
const excludedText = ref('')

function toList(text) {
  return text
    .split(/[,，\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

function fromList(arr) {
  return (arr || []).join(', ')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.getSubscription()
    form.value = {
      role: data.role || '',
      max_items: data.max_items,
      language: data.language || 'zh-CN',
      timezone: data.timezone || 'Asia/Shanghai',
      notification_channel: data.notification_channel || 'none',
    }
    topicsText.value = fromList(data.topics)
    keywordsText.value = fromList(data.keywords)
    excludedText.value = fromList(data.excluded_keywords)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    await api.saveSubscription({
      role: form.value.role,
      topics: toList(topicsText.value),
      keywords: toList(keywordsText.value),
      excluded_keywords: toList(excludedText.value),
      max_items: form.value.max_items,
      language: form.value.language,
      timezone: form.value.timezone,
      notification_channel: form.value.notification_channel,
    })
    saved.value = true
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h2>订阅设置</h2>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="saved" class="success">设置已保存。</div>

    <div class="card">
      <p v-if="loading" class="hint">加载中…</p>
      <template v-else>
        <div class="grid">
          <label class="field">
            <span>身份（role）</span>
            <input v-model="form.role" type="text" placeholder="如：Agent Developer" />
          </label>

          <label class="field">
            <span>关注主题（topics，逗号分隔）</span>
            <textarea v-model="topicsText" rows="2" placeholder="AI Coding, MCP"></textarea>
          </label>

          <label class="field">
            <span>关键词（keywords，逗号分隔）</span>
            <textarea v-model="keywordsText" rows="2" placeholder="Claude, Agent"></textarea>
          </label>

          <label class="field">
            <span>排除关键词（excluded keywords）</span>
            <textarea v-model="excludedText" rows="2" placeholder="spam"></textarea>
          </label>

          <label class="field">
            <span>每期条数（1–20）</span>
            <input v-model.number="form.max_items" type="number" min="1" max="20" />
          </label>

          <label class="field">
            <span>语言</span>
            <select v-model="form.language">
              <option value="zh-CN">中文（简体）</option>
              <option value="en">English</option>
            </select>
          </label>

          <label class="field">
            <span>通知渠道</span>
            <select v-model="form.notification_channel">
              <option value="none">不通知</option>
              <option value="console">Console</option>
              <option value="email">Email（需配置）</option>
            </select>
          </label>
        </div>

        <button class="btn" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存设置' }}
        </button>
      </template>
    </div>
  </div>
</template>