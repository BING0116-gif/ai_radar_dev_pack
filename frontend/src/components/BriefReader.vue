<script setup>
// 简报正文阅读器：优先渲染结构化 items 为可读卡片；
// 旧数据（无 items）退回 markdown-it 渲染（纯展示、不注入 HTML）。
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  brief: { type: Object, required: true },
  // item_key -> verdict（like/dislike/read），来自 GET /api/feedback
  feedbackMap: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['feedback'])

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const items = computed(() => (Array.isArray(props.brief.items) ? props.brief.items : []))
const hasItems = computed(() => items.value.length > 0)

const renderedMarkdown = computed(() => md.render(props.brief.content_markdown || ''))

function itemKey(item) {
  // 稳定标识优先用来源 URL（已持久化 items 必有），无则回退标题
  return item.source_url || String(item.title || '').trim()
}

function currentVerdict(item) {
  return props.feedbackMap[itemKey(item)] || null
}

function setVerdict(item, verdict) {
  const key = itemKey(item)
  const active = currentVerdict(item)
  // 再次点击同一按钮 = 取消反馈
  const next = active === verdict ? null : verdict
  emit('feedback', { item_key: key, item_title: item.title || '', verdict: next })
}
</script>

<template>
  <div>
    <div v-if="hasItems" class="brief-items">
      <article v-for="(item, i) in items" :key="i" class="news-card">
        <div class="news-top">
          <h4 class="news-title">{{ item.title }}</h4>
          <span v-if="item.source_name" class="source">{{ item.source_name }}</span>
        </div>

        <div class="news-meta">
          <span v-if="item.published_at" class="meta-item">🕓 {{ item.published_at }}</span>
          <div v-if="item.topics && item.topics.length" class="topics">
            <span v-for="(t, ti) in item.topics" :key="ti" class="topic">{{ t }}</span>
          </div>
        </div>

        <p v-if="item.summary" class="summary">{{ item.summary }}</p>

        <div v-if="item.why_it_matters" class="why">
          <span class="why-label">为什么重要</span>
          <span>{{ item.why_it_matters }}</span>
        </div>

        <div class="news-actions">
          <a v-if="item.source_url" class="read-link" :href="item.source_url" target="_blank" rel="noopener noreferrer">
            阅读原文 ↗
          </a>

          <div class="feedbacks">
            <button
              class="fb" :class="{ active: currentVerdict(item) === 'like' }"
              title="想继续看这类内容" @click="setVerdict(item, 'like')"
            >赞</button>
            <button
              class="fb" :class="{ active: currentVerdict(item) === 'dislike' }"
              title="不再想看这类内容" @click="setVerdict(item, 'dislike')"
            >不感兴趣</button>
            <button
              class="fb" :class="{ active: currentVerdict(item) === 'read' }"
              title="标记为已读" @click="setVerdict(item, 'read')"
            >已读</button>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="md-wrap" v-html="renderedMarkdown"></div>
  </div>
</template>

<style scoped>
.brief-items {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.news-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  background: #fff;
}

.news-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.news-title {
  margin: 0;
  font-size: 15px;
  line-height: 1.5;
}

.source {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--pine);
  background: #eef3ef;
  border-radius: 6px;
  padding: 2px 8px;
  white-space: nowrap;
}

.news-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin: 8px 0;
}

.meta-item {
  font-size: 12px;
  color: var(--muted);
}

.topics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.topic {
  font-size: 12px;
  color: #8a6d1a;
  background: #f5eedd;
  border-radius: 999px;
  padding: 1px 8px;
}

.summary {
  margin: 0 0 10px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--ink);
}

.why {
  display: flex;
  gap: 8px;
  align-items: baseline;
  font-size: 13px;
  line-height: 1.6;
  color: #4a4a4a;
  background: #faf6ef;
  border-left: 3px solid #c9b98a;
  border-radius: 0 6px 6px 0;
  padding: 8px 12px;
}

.why-label {
  flex-shrink: 0;
  font-weight: 600;
  color: #8a6d1a;
}

.news-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.read-link {
  display: inline-block;
  margin-top: 10px;
  font-size: 13px;
  color: var(--pine);
  text-decoration: none;
  font-weight: 600;
}

.read-link:hover {
  text-decoration: underline;
}

.feedbacks {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}

.fb {
  border: 1px solid var(--border);
  background: #faf8f4;
  color: var(--muted, #8a8378);
  font-size: 12px;
  border-radius: 999px;
  padding: 2px 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.fb:hover {
  border-color: var(--pine);
  color: var(--pine);
}

.fb.active {
  background: #eef3ef;
  border-color: var(--pine);
  color: var(--pine);
  font-weight: 600;
}

/* markdown 兜底（仅旧数据） */
.md-wrap :deep(h1) {
  font-size: 17px;
  margin: 0 0 10px;
}

.md-wrap :deep(h2) {
  font-size: 15px;
  margin: 14px 0 6px;
}

.md-wrap :deep(p) {
  margin: 6px 0;
  font-size: 13.5px;
  line-height: 1.65;
}

.md-wrap :deep(a) {
  color: var(--pine);
  word-break: break-all;
}

.md-wrap {
  line-height: 1.6;
  font-size: 14px;
}
</style>