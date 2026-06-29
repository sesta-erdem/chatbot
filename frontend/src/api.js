// Tüm REST + WS adresleri tek yerde.
// Prod: aynı origin (FastAPI derlenmiş SPA'yı servis eder → CORS yok).
// Dev: frontend/.env içindeki VITE_API_BASE (http://127.0.0.1:8000) kullanılır.
export const API_BASE = import.meta.env.VITE_API_BASE || ''

function httpBase() {
  return API_BASE || window.location.origin
}

async function authRequest(path, email, password) {
  const r = await fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.detail || 'İşlem başarısız')
  return data.access_token
}

export const login = (email, password) => authRequest('/auth/login', email, password)
export const register = (email, password) => authRequest('/auth/register', email, password)

export async function uploadDocument(file, token) {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch(API_BASE + '/documents/upload', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + token },
    body: fd,
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.detail || 'Yükleme başarısız')
  return data
}

export async function getAdminStats(token) {
  const r = await fetch(API_BASE + '/admin/stats', {
    headers: { Authorization: 'Bearer ' + token },
  })
  if (!r.ok) throw new Error(r.status === 403 ? 'Bu sayfa yalnız admin içindir' : 'Hata')
  return r.json()
}

export function wsUrl(token, conversationId) {
  const base = httpBase().replace(/^http/, 'ws')
  let url = `${base}/ws?token=${encodeURIComponent(token)}`
  if (conversationId) url += `&conversation_id=${encodeURIComponent(conversationId)}`
  return url
}
