// Thin wrapper around the backend REST API (no mock data — always real calls).
// Responses use the {code, message, data} envelope; non-zero code -> Error.

const BASE = ''

async function request(path, options = {}) {
  let res
  try {
    res = await fetch(BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch {
    throw new Error('无法连接后端服务，请确认后端已启动')
  }
  let body = null
  try {
    body = await res.json()
  } catch {
    // ignore non-JSON bodies
  }
  if (!res.ok || (body && body.code !== 0)) {
    throw new Error((body && body.message) || `请求失败 (HTTP ${res.status})`)
  }
  return body.data
}

export function getSubscription() {
  return request('/api/subscription')
}

export function saveSubscription(payload) {
  return request('/api/subscription', { method: 'PUT', body: JSON.stringify(payload) })
}

export function getRuns() {
  return request('/api/runs')
}

export function getRunSteps(runId) {
  return request(`/api/runs/${runId}/steps`)
}

export function getBriefs() {
  return request('/api/briefs')
}

export function getBrief(briefId) {
  return request(`/api/briefs/${briefId}`)
}

export function createRun(payload = {}) {
  return request('/api/runs', { method: 'POST', body: JSON.stringify(payload) })
}