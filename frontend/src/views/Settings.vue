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
  notification_channel: 'email',
  require_approval: false,
})
const topicsText = ref('')
const keywordsText = ref('')
const excludedText = ref('')

// 邮件推送 SMTP 配置
const emailForm = ref({
  host: '',
  port: 465,
  user: '',
  password: '',
  sender: '',
  recipient: '',
})
const emailConfigured = ref(false)
const emailSaving = ref(false)
const emailTesting = ref(false)
const emailMsg = ref('')
const emailMsgOk = ref(true)

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
    const [data, email] = await Promise.all([api.getSubscription(), api.getEmailConfig()])
    form.value = {
      role: data.role || '',
      max_items: data.max_items,
      language: data.language || 'zh-CN',
      timezone: data.timezone || 'Asia/Shanghai',
      notification_channel: data.notification_channel || 'email',
      require_approval: data.require_approval || false,
    }
    topicsText.value = fromList(data.topics)
    keywordsText.value = fromList(data.keywords)
    excludedText.value = fromList(data.excluded_keywords)
    emailForm.value = {
      host: email.host || '',
      port: email.port || 465,
      user: email.user || '',
      password: '', // 不回显
      sender: email.sender || '',
      recipient: email.recipient || '',
    }
    emailConfigured.value = email.configured === true
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function saveEmail() {
  emailSaving.value = true
  emailMsg.value = ''
  try {
    const res = await api.saveEmailConfig(emailForm.value)
    emailConfigured.value = res.configured === true
    emailMsg.value = res.configured ? '邮件配置已保存并生效，后续简报会真实发送到收件箱。' : '已保存（尚未配置完整，仍为演示模式）。'
    emailMsgOk.value = true
  } catch (err) {
    emailMsg.value = err.message
    emailMsgOk.value = false
  } finally {
    emailSaving.value = false
  }
}

async function sendTestEmail() {
  emailTesting.value = true
  emailMsg.value = ''
  try {
    const res = await api.testEmailConfig(emailForm.value)
    emailMsg.value = res.detail
    emailMsgOk.value = res.sent === true
    emailConfigured.value = res.mode === 'smtp'
  } catch (err) {
    emailMsg.value = err.message
    emailMsgOk.value = false
  } finally {
    emailTesting.value = false
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
      require_approval: form.value.require_approval,
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
            <span>推送渠道</span>
            <select v-model="form.notification_channel">
              <option value="email">Email（默认；未配置将写入 workspace/emails 供查看）</option>
              <option value="console">Console</option>
              <option value="none">不推送</option>
            </select>
          </label>

          <label class="field switch-field">
            <span>先审后发（HITL）</span>
            <span class="switch-row">
              <input v-model="form.require_approval" type="checkbox" class="switch" />
              <span class="hint">开启后，生成的简报先进入「待审」队列，你确认后才发布并通知</span>
            </span>
          </label>
        </div>

        <button class="btn" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存设置' }}
        </button>
      </template>
    </div>

    <!-- 邮件推送 SMTP 配置 -->
    <div class="card">
      <div class="row-card" style="align-items: baseline; margin-bottom: 4px">
        <h3 class="section-title" style="margin: 0">邮件推送配置</h3>
        <span class="chip" :class="emailConfigured ? 'ok' : 'warn'">
          {{ emailConfigured ? '已配置 · 真实 SMTP' : '演示模式 · 未配置' }}
        </span>
      </div>
      <p class="hint" style="margin-top: 4px">
        填好 SMTP 后保存即生效，简报会自动发到收件箱。凭据保存在容器数据卷的本地文件（不入库、不入 Git）；生产可用 EMAIL_* 环境变量。密码不回显，留空表示保留已保存的密码。
      </p>
      <div class="grid">
        <label class="field">
          <span>SMTP 服务器（host）</span>
          <input v-model="emailForm.host" type="text" placeholder="如 smtp.qq.com" />
        </label>
        <label class="field">
          <span>端口（port）</span>
          <input v-model.number="emailForm.port" type="number" min="1" max="65535" placeholder="465" />
        </label>
        <label class="field">
          <span>账号（user）</span>
          <input v-model="emailForm.user" type="text" placeholder="发件邮箱账号" />
        </label>
        <label class="field">
          <span>授权码 / 密码</span>
          <input v-model="emailForm.password" type="password" placeholder="留空保留已保存的值" autocomplete="new-password" />
        </label>
        <label class="field">
          <span>发件人邮箱（sender）</span>
          <input v-model="emailForm.sender" type="email" placeholder="如 sender@qq.com" />
        </label>
        <label class="field">
          <span>收件人邮箱（recipient，可多个逗号分隔）</span>
          <input v-model="emailForm.recipient" type="text" placeholder="你要收到简报的邮箱" />
        </label>
      </div>
      <div style="display: flex; gap: 10px; flex-wrap: wrap">
        <button class="btn" :disabled="emailSaving" @click="saveEmail">
          {{ emailSaving ? '保存中…' : '保存配置' }}
        </button>
        <button class="btn btn-soft" :disabled="emailTesting" @click="sendTestEmail">
          {{ emailTesting ? '发送中…' : '发送测试邮件' }}
        </button>
      </div>
      <div v-if="emailMsg" class="email-msg" :class="emailMsgOk ? 'success' : 'error'" style="margin-top: 14px">
        {{ emailMsg }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.switch-field {
  grid-column: 1 / -1;
}

.switch-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.switch {
  width: 16px;
  height: 16px;
  accent-color: var(--pine);
  cursor: pointer;
}
</style>