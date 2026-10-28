import { useEffect, useState, useRef } from 'react'
import { api, streamChaptersAI } from './api.js'

const fmt = s => {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = Math.floor(s % 60)
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }
  return `${m}:${String(sec).padStart(2, '0')}`
}

const EMPTY_CH = { title: '', start_time: 0, end_time: 300, summary: '', key_concepts: '' }

function parseTimestamps(text, videoDurationSec) {
  if (!text) return []
  const entries = []
  const regex = /(?:\[|\()?\b(\d{1,2}:\d{2}(?::\d{2})?)\b(?:\]|\))?(?:\([^\)]*\))?\s*([^\n\r\[]+)/gi
  
  let match
  while ((match = regex.exec(text)) !== null) {
    const timeStr = match[1]
    let titleStr = match[2] || ''

    const parts = timeStr.split(':').map(Number)
    let secs = 0
    if (parts.length === 3) {
      secs = parts[0] * 3600 + parts[1] * 60 + parts[2]
    } else if (parts.length === 2) {
      secs = parts[0] * 60 + parts[1]
    }

    let cleanTitle = titleStr
      .replace(/https?:\/\/\S+/gi, '')
      .replace(/\[|\]|\(|\)/g, '')
      .replace(/^[\s⭐️✦•\-\d.)]+/, '')
      .trim()

    if (!cleanTitle) cleanTitle = `Chapter at ${timeStr}`
    if (cleanTitle.length < 3) cleanTitle = `${cleanTitle} Lecture`

    entries.push({ start_time: secs, title: cleanTitle })
  }

  if (entries.length === 0) return []

  entries.sort((a, b) => a.start_time - b.start_time)
  const unique = []
  for (const item of entries) {
    if (!unique.length || unique[unique.length - 1].start_time !== item.start_time) {
      unique.push(item)
    }
  }

  const lastSec = unique[unique.length - 1].start_time
  const totalDuration = videoDurationSec && videoDurationSec > lastSec ? videoDurationSec : lastSec + 300

  return unique.map((item, idx) => {
    let nextStart = idx < unique.length - 1 ? unique[idx + 1].start_time : totalDuration
    let endTime = nextStart > item.start_time ? nextStart - 1 : item.start_time + 60
    if (endTime <= item.start_time) endTime = item.start_time + 60

    return {
      title: item.title,
      start_time: item.start_time,
      end_time: endTime,
      summary: `Concepts and discussion covering ${item.title}`,
      key_concepts: item.title.toLowerCase().replace(/[^a-z0-9 ]/g, '').split(/\s+/).filter(w => w.length > 2).slice(0, 3).join(', '),
    }
  })
}

export default function Admin({ cfg, setCfg, videos = [], onVideoListChanged }) {
  const [hot, setHot] = useState([])
  const [chapters, setChapters] = useState([])
  const [note, setNote] = useState(null)
  const [vid, setVid] = useState({ title: '', url: '', description: '', duration_seconds: 1800 })
  const [existingChapters, setExistingChapters] = useState([])
  const [pasteText, setPasteText] = useState('')
  const [showPaste, setShowPaste] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)
  const abortCtrl = useRef(null)
  const v = cfg.videoId
  const say = (ok, text) => { setNote({ ok, text }); setTimeout(() => setNote(null), 8000) }

  const loadHotspots = () => v && api.hotspots(v).then(setHot).catch(() => setHot([]))
  const loadExisting = () => v && api.chapters(v).then(setExistingChapters).catch(() => setExistingChapters([]))

  useEffect(() => { 
    setHot([])
    setExistingChapters([])
    setChapters([])
    loadHotspots()
    loadExisting() 
  }, [v])

  async function createVideo(e) {
    e.preventDefault()
    try {
      const r = await api.createVideo({ ...vid, course_id: Number(cfg.courseId), duration_seconds: Number(vid.duration_seconds) })
      setCfg(c => ({ ...c, videoId: String(r.id), videoUrl: r.url, videoTitle: r.title }))
      say(true, `Video "${r.title}" created (ID #${r.id}) and auto-selected!`)
      if (onVideoListChanged) onVideoListChanged()
      setVid({ title: '', url: '', description: '', duration_seconds: 1800 })
    } catch (err) { say(false, err.message) }
  }

  async function deleteSelectedVideo(videoIdToDelete) {
    const id = videoIdToDelete || v
    if (!id) return
    const confirm = window.confirm(`Delete Video #${id} and its chapters?`)
    if (!confirm) return
    try {
      await api.deleteVideo(id)
      say(true, `Video #${id} deleted successfully.`)
      if (onVideoListChanged) onVideoListChanged()
    } catch (err) { say(false, err.message) }
  }

  const updateChapter = (i, field, value) => {
    setChapters(prev => prev.map((ch, idx) => idx === i ? { ...ch, [field]: value } : ch))
  }
  const addRow = () => {
    const last = chapters[chapters.length - 1]
    setChapters(prev => [...prev, {
      ...EMPTY_CH,
      start_time: last ? Number(last.end_time) + 1 : 0,
      end_time: last ? Number(last.end_time) + 301 : 300,
    }])
  }
  const removeRow = (i) => setChapters(prev => prev.filter((_, idx) => idx !== i))

  const parsePaste = () => {
    const dur = Number(vid.duration_seconds) || 12000
    const parsed = parseTimestamps(pasteText, dur)
    if (parsed.length === 0) {
      return say(false, 'Timestamps detect nahi hue!')
    }
    setChapters(parsed)
    say(true, `Parsed ${parsed.length} chapters! Ab "Save & Import Chapters" click karo.`)
  }

  // REAL-TIME SSE STREAMING CHAPTERS GENERATION
  const handleAutoChaptersStream = async () => {
    if (!v) return say(false, 'Select a video first!')
    setAiLoading(true)
    setExistingChapters([]) // Clean UI to stream live into it!
    say(true, "⚡ Connecting to AI Stream... Chapters will appear live in real-time as they generate!")
    
    abortCtrl.current = new AbortController()

    try {
      await streamChaptersAI(v, (newChapter) => {
        // Live append each chapter as it's streamed and saved to DB
        setExistingChapters(prev => [...prev, newChapter])
      }, abortCtrl.current.signal)

      await loadHotspots()
      say(true, "🎉 All chapters streamed and permanently saved to Database! Check Learn tab.")
    } catch (e) {
      say(false, "Streaming error: " + e.message)
      await loadExisting()
    } finally {
      setAiLoading(false)
    }
  }

  async function importChapters() {
    const cleaned = chapters
      .filter(ch => ch.title && ch.title.trim())
      .map(ch => {
        let t = ch.title.trim()
        if (t.length < 3) t = `${t} Topic`
        let s = (ch.summary || '').trim()
        if (s.length < 5) s = `Overview of ${t}`
        let st = Number(ch.start_time) || 0
        let et = Number(ch.end_time) || (st + 60)
        if (et <= st) et = st + 60

        return {
          title: t,
          start_time: st,
          end_time: et,
          summary: s,
          key_concepts: typeof ch.key_concepts === 'string'
            ? ch.key_concepts.split(',').map(k => k.trim()).filter(Boolean)
            : ch.key_concepts || [],
        }
      })

    cleaned.sort((a, b) => a.start_time - b.start_time)
    for (let i = 1; i < cleaned.length; i++) {
      if (cleaned[i].start_time < cleaned[i - 1].end_time) {
        cleaned[i - 1].end_time = cleaned[i].start_time - 1
      }
    }

    if (cleaned.length === 0) return say(false, 'Kam se kam ek chapter add karo!')

    try {
      await api.bulkChapters(v, cleaned)
      say(true, `Successfully saved ${cleaned.length} chapters into Video #${v}!`)
      loadExisting()
      loadHotspots()
      setChapters([])
    } catch (err) { 
      say(false, err.message) 
    }
  }

  const max = Math.max(1, ...hot.map(h => h.doubt_count))

  return (
    <main className="admin">
      {note && <div className={note.ok ? 'ok' : 'err'}>{note.text}</div>}

      {/* ---- Video Management & Delete ---- */}
      <section className="card">
        <h2>📂 Course {cfg.courseId} Videos ({videos.length})</h2>
        <div style={{ display: 'grid', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
          {videos.length === 0 && <p className="muted">No videos yet in this course.</p>}
          {videos.map(item => (
            <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#252932', padding: '8px 12px', borderRadius: '6px' }}>
              <div>
                <b>#{item.id}</b> {item.title}
                <div style={{ fontSize: '11px', color: '#888' }}>{item.url}</div>
              </div>
              <button 
                onClick={() => deleteSelectedVideo(item.id)}
                style={{ background: '#451a1a', color: '#f87171', border: '1px solid #7f1d1d', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}
                title="Delete Video"
              >
                Delete 🗑️
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* ---- Hotspots ---- */}
      <section className="card">
        <h2>🔥 Doubt Hotspots {v && <small>(Video #{v}: {cfg.videoTitle || ''})</small>}</h2>
        {!v && <p className="muted">Top se video select karo.</p>}
        {v && existingChapters.length === 0 && <p className="muted" style={{ color: '#f5a623' }}>⚠️ Is video me chapters nahi hain. Neeche se live stream karo.</p>}
        {v && existingChapters.length > 0 && hot.every(h => h.doubt_count === 0) && <p className="muted">Is video par abhi koi doubts nahi puche gaye hain.</p>}
        {hot.filter(h => h.doubt_count > 0).map(h => (
          <div key={h.chapter_id} className="hot">
            <div className="hl">
              <span>{h.title} <small>{fmt(h.start_time)}–{fmt(h.end_time)}</small></span>
              <span className={`tier ${h.difficulty_tier?.toLowerCase()}`}>{h.difficulty_tier} · {h.doubt_count}</span>
            </div>
            <div className="track"><i className={h.difficulty_tier?.toLowerCase()} style={{ width: `${(h.doubt_count / max) * 100}%` }} /></div>
          </div>
        ))}
      </section>

      {/* ---- Live Streamed Chapters (Permanent DB) ---- */}
      {v && (
        <section className="card wide">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <h2 style={{ margin: 0 }}>
              📋 Live Chapters in Database 
              <small>(Video #{v} · {existingChapters.length} Total)</small>
              {aiLoading && <span style={{ color: '#5eead4', fontSize: '12px', marginLeft: '10px' }}>⚡ Streaming in live...</span>}
            </h2>
            <button className="secondary" onClick={loadExisting}>🔄 Refresh</button>
          </div>
          {existingChapters.length === 0 ? (
            <p className="muted">No chapters saved in database yet. Click the purple button below to stream them live!</p>
          ) : (
            <div style={{ display: 'grid', gap: '6px', maxHeight: '250px', overflowY: 'auto' }}>
              {existingChapters.map(c => (
                <div key={c.id || c.start_time} style={{ display: 'flex', gap: '10px', alignItems: 'center', padding: '6px 12px', background: '#252932', borderRadius: '6px', fontSize: '13px' }}>
                  <b style={{ color: '#5eead4', minWidth: '95px' }}>{fmt(c.start_time)}–{fmt(c.end_time)}</b>
                  <span style={{ flex: 1, fontWeight: '500' }}>{c.title}</span>
                  {c.key_concepts?.length > 0 && <small style={{ color: '#888' }}>{Array.isArray(c.key_concepts) ? c.key_concepts.join(', ') : c.key_concepts}</small>}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ---- Add Video ---- */}
      <section className="card">
        <h2>➕ Add New Video to Course {cfg.courseId}</h2>
        <form onSubmit={createVideo} className="grid">
          <input required placeholder="Video Title (e.g. LangGraph 3hr Course)" value={vid.title} onChange={e => setVid({ ...vid, title: e.target.value })} />
          <input required placeholder="YouTube / MP4 URL" value={vid.url} onChange={e => setVid({ ...vid, url: e.target.value })} />
          <input placeholder="Short Description" value={vid.description} onChange={e => setVid({ ...vid, description: e.target.value })} />
          <input type="number" placeholder="Duration in Seconds (e.g. 11400 = 3+ Hours)" value={vid.duration_seconds} onChange={e => setVid({ ...vid, duration_seconds: e.target.value })} />
          <button className="primary">Create Video & Auto-Select</button>
        </form>
      </section>

      {/* ---- Chapter Builder ---- */}
      <section className="card wide">
        <h2>📑 Smart Chapters Importer {v && <small>for Video #{v}</small>}</h2>

        <div style={{ display: 'flex', gap: '10px', marginBottom: '14px', flexWrap: 'wrap' }}>
          {/* Main AI Streaming Button! */}
          <button 
            className="primary" 
            onClick={handleAutoChaptersStream}
            disabled={!v || aiLoading}
            style={{ background: 'linear-gradient(135deg, #6366f1, #a855f7)', color: '#fff', border: 'none', padding: '10px 18px', fontWeight: 'bold' }}
          >
            {aiLoading ? "⚡ Streaming Chapters Live..." : "✨ Live Stream Auto-Generate Chapters via AI"}
          </button>

          <button className="secondary" onClick={() => setShowPaste(!showPaste)}>
            📋 Paste YouTube Timestamps Manually
          </button>
          
          <button className="secondary" onClick={addRow}>+ Add Manual Row</button>
        </div>

        {showPaste && (
          <div style={{ marginBottom: '14px', padding: '14px', background: '#1e2530', borderRadius: '10px', border: '1px solid #3d4450' }}>
            <p style={{ margin: '0 0 8px', fontSize: '13px', color: '#5eead4', fontWeight: 'bold' }}>
              📋 Paste YouTube Timestamps Description here:
            </p>
            <textarea
              rows={5}
              value={pasteText}
              onChange={e => setPasteText(e.target.value)}
              placeholder="[0:00:00](...) Introduction&#10;[0:01:24](...) Type Annotations..."
              style={{ fontFamily: 'ui-monospace, monospace', fontSize: '13px' }}
              spellCheck={false}
            />
            <button className="primary" onClick={parsePaste} style={{ marginTop: '8px' }}>
              🚀 Parse Timestamps
            </button>
          </div>
        )}

        {chapters.length > 0 && (
          <>
            <p className="muted" style={{ margin: '0 0 8px', fontSize: '13px' }}>
              ⚡ <b>{chapters.length} Manual Draft Chapters</b>:
            </p>
            <div style={{ display: 'grid', gap: '6px', maxHeight: '350px', overflowY: 'auto', paddingRight: '4px' }}>
              {chapters.map((ch, i) => (
                <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 90px 90px 2fr 32px', gap: '6px', alignItems: 'center' }}>
                  <input placeholder="Chapter Title" value={ch.title} onChange={e => updateChapter(i, 'title', e.target.value)} />
                  <input type="number" placeholder="Start" value={ch.start_time} onChange={e => updateChapter(i, 'start_time', e.target.value)} style={{ textAlign: 'center', fontSize: '12px' }} title={fmt(ch.start_time)} />
                  <input type="number" placeholder="End" value={ch.end_time} onChange={e => updateChapter(i, 'end_time', e.target.value)} style={{ textAlign: 'center', fontSize: '12px' }} title={fmt(ch.end_time)} />
                  <input placeholder="Summary" value={ch.summary} onChange={e => updateChapter(i, 'summary', e.target.value)} />
                  <button onClick={() => removeRow(i)} style={{ background: 'transparent', color: '#f44', border: 'none', cursor: 'pointer', fontSize: '16px' }} title="Remove">✕</button>
                </div>
              ))}
            </div>

            <button className="primary" disabled={!v} onClick={importChapters} style={{ marginTop: '12px', width: '100%', fontSize: '15px' }}>
              {v ? `💾 Save All ${chapters.length} Chapters to Database` : 'Top se Video Select Karo'}
            </button>
          </>
        )}
      </section>
    </main>
  )
}
