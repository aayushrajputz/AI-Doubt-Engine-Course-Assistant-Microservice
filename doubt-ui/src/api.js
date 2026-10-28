const BASE = import.meta.env.VITE_API_URL || '/api'

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status }
}

const friendly = (status, detail) => {
  if (status === 404) return `Not found (404): ${detail || 'check the video or doubt ID.'}`
  if (status === 429) return 'Rate limited (429): wait a moment, then send again.'
  if (status === 422) return `Invalid input (422): ${detail}`
  if (status === 0) return 'Cannot reach the backend. Is it running on http://127.0.0.1:8000?'
  return `Request failed (${status}): ${detail || 'unexpected error'}`
}

async function parseError(res) {
  let detail = ''
  try {
    const j = await res.json()
    detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j)
  } catch { /* non-JSON body */ }
  return new ApiError(res.status, friendly(res.status, detail))
}

async function request(path, opts = {}) {
  let res
  try {
    res = await fetch(BASE + path, {
      ...opts,
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    })
  } catch { throw new ApiError(0, friendly(0)) }
  if (!res.ok) throw await parseError(res)
  return res.json()
}

export const api = {
  createVideo: body => request('/admin/videos/', { method: 'POST', body }),
  deleteVideo: id => request(`/admin/videos/${id}`, { method: 'DELETE' }),
  videosByCourse: courseId => request(`/admin/videos/course/${courseId}`),
  chapters: id => request(`/admin/videos/${id}/chapters`),
  bulkChapters: (id, chapters) => request(`/admin/videos/${id}/chapters/bulk`, { method: 'POST', body: chapters }),
  hotspots: id => request(`/admin/videos/${id}/hotspots`),
  createDoubt: body => request('/doubts/', { method: 'POST', body }),
}

/** REAL-TIME SSE STREAMING FOR CHAPTERS */
export async function streamChaptersAI(videoId, onChapter, signal) {
  let res
  try {
    res = await fetch(`${BASE}/admin/videos/${videoId}/auto-chapters-stream`, {
      method: 'POST',
      signal,
      headers: { Accept: 'text/event-stream' }
    })
  } catch (e) {
    if (e.name === 'AbortError') return
    throw new ApiError(0, friendly(0))
  }
  if (!res.ok) throw await parseError(res)

  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    const events = buf.split(/\r?\n\r?\n/)
    buf = events.pop()
    for (const ev of events) {
      const lines = ev.split(/\r?\n/).filter(l => l.startsWith('data:'))
      if (!lines.length) continue
      const dataStr = lines.map(l => l.slice(5).replace(/^ /, '')).join('\n').trim()
      if (dataStr === '[DONE]') return
      if (dataStr === '[STARTING_AI_TRANSCRIPTION]') continue
      try {
        const parsedChapter = JSON.parse(dataStr)
        onChapter(parsedChapter)
      } catch (err) {
        console.error("Error parsing streamed chapter:", err)
      }
    }
  }
}

/** POST + SSE via fetch ReadableStream for Doubts */
export async function streamDoubt(doubtId, onEvent, signal) {
  let res
  try {
    res = await fetch(`${BASE}/doubts/${doubtId}/stream`, { method: 'POST', signal, headers: { Accept: 'text/event-stream' } })
  } catch (e) { if (e.name === 'AbortError') return; throw new ApiError(0, friendly(0)) }
  if (!res.ok) throw await parseError(res)

  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    const events = buf.split(/\r?\n\r?\n/)
    buf = events.pop()
    for (const ev of events) {
      const lines = ev.split(/\r?\n/).filter(l => l.startsWith('data:'))
      if (!lines.length) continue
      onEvent(lines.map(l => l.slice(5).replace(/^ /, '')).join('\n'))
    }
  }
}
