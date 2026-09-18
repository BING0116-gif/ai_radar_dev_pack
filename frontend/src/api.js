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

// HITL 审批流
export function getReviews() {
  return request('/api/reviews')
}

export function approveReview(briefId) {
  return request(`/api/reviews/${briefId}/approve`, { method: 'POST' })
}

export function rejectReview(briefId) {
  return request(`/api/reviews/${briefId}/reject`, { method: 'POST' })
}

// 单条新闻反馈（个性化信号）
export function getFeedback() {
  return request('/api/feedback')
}

export function submitFeedback(payload) {
  return request('/api/feedback', { method: 'POST', body: JSON.stringify(payload) })
}

export function deleteFeedback(itemKey) {
  // item_key 可能是含 / 的来源 URL，必须走 query 参数（路径段会截断）
  return request(`/api/feedback?item_key=${encodeURIComponent(itemKey)}`, { method: 'DELETE' })
}