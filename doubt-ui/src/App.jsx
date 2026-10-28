import { useEffect, useState } from 'react'
import Student from './Student.jsx'
import Admin from './Admin.jsx'
import { api } from './api.js'

const KEY = 'doubt-ui-cfg'
const DEFAULTS = { userId: 1, courseId: 101, videoId: '', videoUrl: '', videoTitle: '' }

export default function App() {
  const [tab, setTab] = useState('student')
  const [videos, setVideos] = useState([])
  const [cfg, setCfg] = useState(() => {
    try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(KEY)) } } catch { return DEFAULTS }
  })

  // Load videos for this course automatically
  const loadVideos = async (cId) => {
    try {
      const list = await api.videosByCourse(cId || cfg.courseId)
      setVideos(list || [])
      if (list && list.length > 0) {
        const found = list.find(v => String(v.id) === String(cfg.videoId))
        if (!found) {
          setCfg(c => ({
            ...c,
            videoId: String(list[0].id),
            videoUrl: list[0].url,
            videoTitle: list[0].title
          }))
        } else {
          setCfg(c => ({ ...c, videoUrl: found.url, videoTitle: found.title }))
        }
      } else {
        setCfg(c => ({ ...c, videoId: '', videoUrl: '', videoTitle: '' }))
      }
    } catch {
      setVideos([])
    }
  }

  useEffect(() => {
    loadVideos(cfg.courseId)
  }, [cfg.courseId])

  useEffect(() => {
    try { localStorage.setItem(KEY, JSON.stringify(cfg)) } catch {}
  }, [cfg])

  const handleDeleteCurrentVideo = async () => {
    if (!cfg.videoId) return
    const confirmDelete = window.confirm(`Are you sure you want to delete Video #${cfg.videoId} ("${cfg.videoTitle}") and its chapters?`)
    if (!confirmDelete) return
    try {
      await api.deleteVideo(cfg.videoId)
      await loadVideos(cfg.courseId)
    } catch (e) {
      alert("Delete failed: " + e.message)
    }
  }

  return (
    <div className="app">
      <header className="top">
        <strong className="brand">🎓 LearnTube AI</strong>
        <nav>
          <button className={tab === 'student' ? 'on' : ''} onClick={() => setTab('student')}>Learn (Classroom)</button>
          <button className={tab === 'admin' ? 'on' : ''} onClick={() => setTab('admin')}>Instructor Studio</button>
        </nav>
        <div className="cfg">
          <label>Course 
            <input 
              type="number" 
              style={{ width: '70px' }}
              value={cfg.courseId} 
              onChange={e => {
                const newCourse = Number(e.target.value)
                setCfg(c => ({ ...c, courseId: newCourse, videoId: '', videoUrl: '' }))
              }} 
            />
          </label>

          {cfg.videoId && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: '#888' }}>
                Playing: <b style={{ color: '#fff' }}>#{cfg.videoId} {cfg.videoTitle}</b>
              </span>
              <button 
                onClick={handleDeleteCurrentVideo}
                title="Delete this video"
                style={{ background: '#3d1a1a', color: '#f87171', border: '1px solid #7f1d1d', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer', fontSize: '11px' }}
              >
                Delete 🗑️
              </button>
            </div>
          )}
        </div>
      </header>

      {tab === 'student' ? (
        <Student cfg={cfg} setCfg={setCfg} videos={videos} />
      ) : (
        <Admin 
          cfg={cfg} 
          setCfg={setCfg} 
          videos={videos}
          onVideoListChanged={() => loadVideos(cfg.courseId)} 
        />
      )}
    </div>
  )
}
