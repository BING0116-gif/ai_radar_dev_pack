<script setup>
import { ref } from 'vue'
import Dashboard from './views/Dashboard.vue'
import Settings from './views/Settings.vue'

const activeTab = ref('dashboard')
</script>

<template>
  <div class="app">
    <header class="topbar">
      <span class="brand">AI Radar</span>
      <nav>
        <button :class="{ active: activeTab === 'dashboard' }" @click="activeTab = 'dashboard'">
          Dashboard
        </button>
        <button :class="{ active: activeTab === 'settings' }" @click="activeTab = 'settings'">
          设置
        </button>
      </nav>
    </header>
    <main>
      <Dashboard v-if="activeTab === 'dashboard'" />
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

.app {
  max-width: 980px;
  margin: 0 auto;
  padding: 0 20px 60px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}

.brand {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

nav button {
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 15px;
  padding: 8px 14px;
  border-radius: 8px;
  cursor: pointer;
}

nav button.active {
  background: #eef3ef;
  color: var(--pine);
  font-weight: 600;
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
</style>