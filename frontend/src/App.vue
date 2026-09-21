<script setup>
import { ref } from 'vue'
import Dashboard from './views/Dashboard.vue'
import History from './views/History.vue'
import Settings from './views/Settings.vue'
import Trace from './views/Trace.vue'

const activeTab = ref('dashboard')

const NAVS = [
  { key: 'dashboard', label: '简报' },
  { key: 'history', label: '历史' },
  { key: 'trace', label: '运行轨迹' },
  { key: 'settings', label: '设置' },
]
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-dot"></span>
        AI Radar
      </div>
      <nav class="side-nav">
        <button
          v-for="nav in NAVS"
          :key="nav.key"
          :class="{ active: activeTab === nav.key }"
          @click="activeTab = nav.key"
        >
          <span class="nav-label">{{ nav.label }}</span>
        </button>
      </nav>
      <div class="side-foot hint">A model-driven news agent</div>
    </aside>

    <main class="main">
      <Dashboard v-if="activeTab === 'dashboard'" />
      <History v-else-if="activeTab === 'history'" />
      <Trace v-else-if="activeTab === 'trace'" />
      <Settings v-else />
    </main>
  </div>
</template>

<style>
:root {
  --bg: #faf8f4;
  --ink: #2b2b2b;
  --muted: #6b6b6b;
  --pine: #3e6b5a;
  --border: #e4ded4;
  --danger: #b0413e;
  --success-bg: #eef4ee;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: system-ui, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 210px;
  flex-shrink: 0;
  border-right: 1px solid var(--border);
  background: #fdfbf7;
  padding: 24px 14px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  position: sticky;
  top: 0;
  height: 100vh;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 0 6px;
}

.brand-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--pine);
}

.side-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.side-nav button {
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 14.5px;
  text-align: left;
  padding: 9px 12px;
  border-radius: 8px;
  cursor: pointer;
}

.side-nav button:hover {
  background: #f4efe6;
}

.side-nav button.active {
  background: #eef3ef;
  color: var(--pine);
  font-weight: 600;
}

.side-foot {
  margin-top: auto;
  font-size: 12px;
}

.main {
  flex: 1;
  min-width: 0;
  max-width: 1080px;
  margin: 0 auto;
  padding: 28px 28px 60px;
  width: 100%;
}

h2 {
  font-size: 20px;
  margin: 0 0 16px;
}

.section-title {
  font-size: 16px;
  margin: 4px 0 12px;
}

.card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px;
  margin-bottom: 20px;
}

.row-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.btn {
  border: none;
  border-radius: 8px;
  background: var(--pine);
  color: #fff;
  padding: 10px 18px;
  font-size: 15px;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-sm {
  padding: 5px 12px;
  font-size: 13px;
}

.btn-soft {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--ink);
}

.btn-soft:hover:not(:disabled) {
  border-color: var(--pine);
  color: var(--pine);
}

.error {
  background: #fdf0ef;
  color: var(--danger);
  border: 1px solid #e9c3c0;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 14px;
}

.success {
  background: var(--success-bg);
  color: var(--pine);
  border: 1px solid #cddfd1;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 14px;
}

.hint {
  color: var(--muted);
  font-size: 13px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

th,
td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
}

th {
  color: var(--muted);
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 20px;
  margin-bottom: 16px;
}

.field {
  display: block;
  margin-bottom: 14px;
  font-size: 14px;
}

.field span {
  display: block;
  margin-bottom: 6px;
}

input,
select,
textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
  color: var(--ink);
}

textarea {
  resize: vertical;
}

.clickable {
  cursor: pointer;
}

.clickable:hover {
  background: #faf8f4;
}

.selected {
  background: #eef3ef;
}

/* KPI 指标卡 */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.kpi {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
}

.kpi-value {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 4px;
}

.kpi-last {
  font-size: 14px;
  font-weight: 600;
  color: var(--muted);
  word-break: break-all;
}

.kpi-label {
  font-size: 12px;
  color: var(--muted);
}

/* 状态徽标 */
.chip {
  display: inline-block;
  font-size: 12px;
  border-radius: 6px;
  padding: 2px 8px;
  white-space: nowrap;
}

.chip-gray { background: #f1eee8; color: #6b6b6b; }
.ok { background: #eef3ef; color: #3e6b5a; font-weight: 600; }
.fail { background: #fdf0ef; color: #b0413e; font-weight: 600; }
.warn { background: #f5eedd; color: #8a6d1a; font-weight: 600; }

@media (max-width: 760px) {
  .layout {
    flex-direction: column;
  }
  .sidebar {
    width: 100%;
    height: auto;
    position: static;
    flex-direction: row;
    align-items: center;
  }
  .side-nav {
    flex-direction: row;
  }
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>