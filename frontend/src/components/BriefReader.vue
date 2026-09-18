<script setup>
// 简报正文阅读器：优先渲染结构化 items 为可读卡片；
// 旧数据（无 items）退回 markdown-it 渲染（纯展示、不注入 HTML）。
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  brief: { type: Object, required: true },
})

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const items = computed(() => (Array.isArray(props.brief.items) ? props.brief.items : []))
const hasItems = computed(() => items.value.length > 0)

const renderedMarkdown = computed(() => md.render(props.brief.content_markdown || ''))
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

        <a v-if="item.source_url" class="read-link" :href="item.source_url" target="_blank" rel="noopener noreferrer">
          阅读原文 ↗
        </a>
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