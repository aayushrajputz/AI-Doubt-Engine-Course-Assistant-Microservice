import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'
import { api, streamDoubt } from './api.js'

const fmt = s => {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = Math.floor(s % 60)
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

const ytId = u => (u || '').match(/(?:v=|youtu\.be\/|embed\/)([\w-]{11})/)?.[1]

let ytReady
const loadYT = () => ytReady ||= new Promise(res => {
  if (window.YT?.Player) return res(window.YT)
  const s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api'; document.head.appendChild(s)
  window.onYouTubeIframeAPIReady = () => res(window.YT)
})

function Player({ url, onTime, seekRef }) {
  const id = ytId(url)
  const box = useRef(), vid = useRef()
  useEffect(() => {
    if (!id) { seekRef.current = t => { if (vid.current) { vid.current.currentTime = t; vid.current.play() } }; return }
    let p, timer, dead = false
    loadYT().then(YT => {
      if (dead) return
      p = new YT.Player(box.current, { videoId: id, width: '100%', height: '100%', playerVars: { rel: 0 } })
      seekRef.current = t => { p.seekTo(t, true); p.playVideo() }
      timer = setInterval(() => { try { onTime(p.getCurrentTime()) } catch {} }, 500)
    })
    return () => { dead = true; clearInterval(timer); p?.destroy?.() }
  }, [id])
  if (!url) return <div className="empty">Select a video from the course playlist on the left.</div>
  return id ? <div className="ratio"><div ref={box} /></div>
    : <video ref={vid} src={url} controls className="ratio" onTimeUpdate={e => onTime(e.target.currentTime)} />
}

export default function Student({ cfg, setCfg, videos = [] }) {
  const [time, setTime] = useState(0)
  const [chapters, setChapters] = useState([])
  const [msgs, setMsgs] = useState([])
  const [q, setQ] = useState('')
  const [attach, setAttach] = useState(true)
  const [busy, setBusy] = useState(false)
  const seekRef = useRef(() => {}), inputRef = useRef(), endRef = useRef(), abort = useRef()
  const secs = Math.floor(time)
  const hasVideo = !!cfg.videoId
  const active = chapters.find(c => secs >= c.start_time && secs <= c.end_time)

  useEffect(() => {
    setChapters([])
    if (cfg.videoId) api.chapters(cfg.videoId).then(setChapters).catch(() => {})
  }, [cfg.videoId])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const patch = (i, f) => setMsgs(m => m.map((x, j) => j === i ? { ...x, ...(typeof f === 'function' ? f(x) : f) } : x))

  async function send() {
    const question = q.trim()
    if (!question || busy) return
    const withVideo = attach && hasVideo
    const idx = msgs.length + 1
    setMsgs(m => [...m, { role: 'user', text: question, ts: withVideo ? secs : null }, { role: 'ai', text: '', pending: true }])
    setQ(''); setBusy(true)
    abort.current = new AbortController()
    try {
      const doubt = await api.createDoubt({
        user_id: Number(cfg.userId), course_id: Number(cfg.courseId),
        ...(withVideo ? { video_id: Number(cfg.videoId), timestamp: secs } : {}),
        title: withVideo ? 'Video Doubt' : 'General Doubt', question,
        tags: withVideo ? ['video'] : ['general'],
      })
      await streamDoubt(doubt.id, data => {
        const d = data.trim()
        if (d === '[DONE]') return
        if (d.startsWith('[EXACT CACHE HIT')) return patch(idx, { badge: { kind: 'exact', label: '⚡ Exact cache hit · 0ms / ₹0.00' } })
        if (d.startsWith('[FTS DICTIONARY CACHE HIT')) return patch(idx, { badge: { kind: 'fts', label: '📖 FTS Dictionary Hit · Postgres english · ₹0.00' } })
        const sem = d.match(/^\[SEMANTIC CACHE HIT\s*\(?([\d.]+%?)\)?\]/)
        if (sem) return patch(idx, { badge: { kind: 'semantic', label: `🧠 Semantic match ${sem[1]} · pgvector` } })
        if (d.startsWith('{') && d.includes('usage_metrics')) {
          try { return patch(idx, { metrics: JSON.parse(d) }) } catch {}
        }
        patch(idx, x => ({ text: x.text + data }))
      }, abort.current.signal)
    } catch (e) { patch(idx, { error: e.message }) }
    patch(idx, { pending: false }); setBusy(false)
  }

  const selectVideo = (v) => {
    setCfg(c => ({
      ...c,
      videoId: String(v.id),
      videoUrl: v.url,
      videoTitle: v.title
    }))
  }

  return (
    <main className="student-layout">
      {/* 1. LEFT PANE: Udemy / Coursera Style Course Playlist */}
      <aside className="playlist-sidebar">
        <div className="playlist-header">
          <h3>📚 Course Lectures</h3>
          <span className="badge">{videos.length} videos</span>
        </div>
        <div className="playlist-list">
          {videos.length === 0 && (
            <p className="muted" style={{ padding: '16px' }}>No videos in this course yet. Add them in Instructor tab.</p>
          )}
          {videos.map((v, i) => {
            const isCur = String(v.id) === String(cfg.videoId)
            return (
              <div 
                key={v.id} 
                className={`playlist-item ${isCur ? 'active' : ''}`}
                onClick={() => selectVideo(v)}
              >
                <div className="pl-index">{isCur ? '▶' : `${i + 1}`}</div>
                <div className="pl-info">
                  <div className="pl-title">{v.title}</div>
                  <div className="pl-meta">
                    {v.duration_seconds ? `${Math.round(v.duration_seconds / 60)} mins` : 'Video'}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </aside>

      {/* 2. MIDDLE PANE: Video Player + Chapters */}
      <section className="video-main">
        <Player url={cfg.videoUrl} onTime={setTime} seekRef={seekRef} />
        
        <div className="bar">
          <span className="clock">{fmt(time)} <small>/ {secs}s</small></span>
          {active && <span className="now">📍 {active.title}</span>}
          <button className="primary" onClick={() => { setAttach(true); inputRef.current?.focus() }}>
            Ask Doubt @ {fmt(time)}
          </button>
        </div>

        <div className="chapters-box">
          <h4>📑 Video Chapters ({chapters.length})</h4>
          {chapters.length === 0 && (
            <p className="muted">No chapters created for this video. Generate them in Instructor tab!</p>
          )}
          <div className="chapters-scroll">
            {chapters.map(c => (
              <button 
                key={c.id} 
                className={`chap ${active?.id === c.id ? 'on' : ''}`} 
                onClick={() => seekRef.current(c.start_time)}
              >
                <b>{fmt(c.start_time)}</b> 
                <span>{c.title}</span>
                {c.key_concepts?.length > 0 && (
                  <small>{Array.isArray(c.key_concepts) ? c.key_concepts.join(', ') : c.key_concepts}</small>
                )}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 3. RIGHT PANE: AI Doubt Assistant */}
      <aside className="chat">
        <div className="chat-header">
          <h3>💬 AI Tutor Assistant</h3>
          <span className="tag-live">Active</span>
        </div>
        <div className="log">
          {msgs.length === 0 && (
            <div className="empty-chat">
              <p>👋 <b>Welcome to your AI Doubt Desk!</b></p>
              <p className="muted">Ask any question in <b>English, Hindi, ya Hinglish</b>. AI will answer using the instructor's exact lecture context!</p>
            </div>
          )}
          {msgs.map((m, i) => m.role === 'user'
            ? <div key={i} className="bubble me">{m.text}{m.ts != null && <small>at {fmt(m.ts)} ({m.ts}s)</small>}</div>
            : <div key={i} className="bubble ai">
                {m.badge && <span className={`pill ${m.badge.kind}`}>{m.badge.label}</span>}
                <ReactMarkdown rehypePlugins={[rehypeHighlight]}>{m.text}</ReactMarkdown>
                {m.pending && !m.text && <span className="dots">Thinking…</span>}
                {m.error && <div className="err">{m.error}</div>}
                {m.metrics && <footer>Tokens: {m.metrics.total_tokens} | Cost: {m.metrics.cached ? '₹0.00 (Cache)' : `${m.metrics.cost_inr} (${m.metrics.cost_usd})`}</footer>}
              </div>)}
          <div ref={endRef} />
        </div>
        
        <div className="compose">
          <label className="toggle">
            <input type="checkbox" checked={attach && hasVideo} disabled={!hasVideo} onChange={e => setAttach(e.target.checked)} />
            Attach video context @ {fmt(time)} {!hasVideo && '(Select video first)'}
          </label>
          <div className="row">
            <textarea 
              ref={inputRef} 
              rows={2} 
              value={q} 
              placeholder="Poocho apna doubt (Hinglish / English)..." 
              onChange={e => setQ(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} 
            />
            <button className="primary" disabled={busy || !q.trim()} onClick={send}>
              {busy ? '…' : 'Send'}
            </button>
          </div>
        </div>
      </aside>
    </main>
  )
}
