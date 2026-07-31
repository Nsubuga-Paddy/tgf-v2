import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { Moon, Play, Search, Sun, X } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { HELP_CATEGORIES, youtubeEmbed, youtubeThumb } from '../data/helpCenterData'
import { apiRequest } from '../lib/api'
import mcsLogo from '../../mcs-logo2.png'

function VideoModal({ video, categories, onClose }) {
  useEffect(() => {
    if (!video) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [video, onClose])

  if (!video) return null

  const categoryLabel =
    categories.find((c) => c.id === video.category)?.label ?? video.category

  return createPortal(
    <div className="help-modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="help-modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-video-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="help-modal-header">
          <div>
            <small>{categoryLabel}</small>
            <h2 id="help-video-title">{video.title}</h2>
          </div>
          <button type="button" className="modal-close" aria-label="Close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="help-modal-player">
          <iframe
            title={video.title}
            src={video.embedUrl || youtubeEmbed(video.youtubeId)}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
        <p className="help-modal-desc">{video.description}</p>
      </div>
    </div>,
    document.body,
  )
}

function HelpBody({
  query,
  setQuery,
  category,
  setCategory,
  categories,
  filtered,
  loading,
  error,
  setActiveVideo,
  showGuestBadge,
}) {
  return (
    <main className="help-wrap">
      <section className="help-hero">
        {showGuestBadge ? <span className="help-hero-badge">No login required</span> : null}
        <h1>Video tutorials for every MCS project</h1>
        <p>
          Watch guides on signup, your profile, savings, farming projects, and cooperative
          shares — available before and after you create an account.
        </p>
      </section>

      <section className="help-toolbar">
        <div className="help-search-row">
          <label className="help-search-field">
            <Search size={16} />
            <input
              type="search"
              placeholder="Search tutorials…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          {query || category !== 'all' ? (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                setQuery('')
                setCategory('all')
              }}
            >
              Clear
            </button>
          ) : null}
        </div>

        <div className="help-filter-label">Categories</div>
        <div className="help-category-pills">
          {categories.map((cat) => (
            <button
              key={cat.id}
              type="button"
              className={`help-category-pill ${category === cat.id ? 'active' : ''}`}
              onClick={() => setCategory(cat.id)}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </section>

      <div className="help-results-meta">
        <span>
          {filtered.length} tutorial{filtered.length === 1 ? '' : 's'}
          {category !== 'all' ? ` · ${categories.find((c) => c.id === category)?.label}` : ''}
        </span>
      </div>

      {loading ? (
        <div className="help-empty">
          <h3>Loading tutorials…</h3>
          <p>Fetching Help Center videos from the database.</p>
        </div>
      ) : error ? (
        <div className="help-empty">
          <h3>Could not load tutorials</h3>
          <p>{error}</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="help-empty">
          <h3>No matching tutorials</h3>
          <p>No published tutorials match your search yet.</p>
        </div>
      ) : (
        <div className="help-video-grid">
          {filtered.map((video) => {
            const categoryLabel =
              categories.find((c) => c.id === video.category)?.label ?? video.category
            return (
              <button
                key={video.id}
                type="button"
                className="help-video-card"
                onClick={() => setActiveVideo(video)}
              >
                <div className="help-thumb">
                  <img
                    src={video.thumbnailUrl || youtubeThumb(video.youtubeId)}
                    alt=""
                    loading="lazy"
                  />
                  <span className="help-play-overlay">
                    <span className="help-play-btn">
                      <Play size={18} fill="currentColor" />
                    </span>
                  </span>
                </div>
                <div className="help-card-body">
                  <span className="help-card-category">{categoryLabel}</span>
                  <b className="help-card-title">{video.title}</b>
                  <p className="help-card-desc">{video.description}</p>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </main>
  )
}

export default function HelpCenter() {
  const { isAuthenticated, user } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')
  const [activeVideo, setActiveVideo] = useState(null)
  const [categories, setCategories] = useState(HELP_CATEGORIES)
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const isMemberSession = Boolean(isAuthenticated)
  const isVerifiedMember = isMemberSession && user?.is_verified !== false

  useEffect(() => {
    let alive = true
    apiRequest('/api/help/videos/')
      .then((data) => {
        if (!alive) return
        setCategories(data.categories?.length ? data.categories : HELP_CATEGORIES)
        setVideos(data.videos || [])
      })
      .catch((err) => {
        if (!alive) return
        setError(err.message || 'Could not load help videos.')
        setVideos([])
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return videos.filter((video) => {
      const catOk = category === 'all' || video.category === category
      if (!catOk) return false
      if (!q) return true
      return (
        video.title.toLowerCase().includes(q) ||
        video.description.toLowerCase().includes(q)
      )
    })
  }, [query, category, videos])

  const body = (
    <HelpBody
      query={query}
      setQuery={setQuery}
      category={category}
      setCategory={setCategory}
      categories={categories}
      filtered={filtered}
      loading={loading}
      error={error}
      setActiveVideo={setActiveVideo}
      showGuestBadge={!isMemberSession}
    />
  )

  const modal = (
    <VideoModal
      video={activeVideo}
      categories={categories}
      onClose={() => setActiveVideo(null)}
    />
  )

  if (isVerifiedMember) {
    return (
      <AppShell title="Help Center">
        <div className="help-page help-page-in-shell">{body}</div>
        {modal}
      </AppShell>
    )
  }

  return (
    <div className="help-page">
      <header className="help-header">
        <div className="help-header-inner">
          <Link to={isMemberSession ? '/verification-pending' : '/'} className="help-logo">
            <img src={mcsLogo} alt="MCS logo" />
            <span>MCS Help Center</span>
          </Link>

          <div className="help-guest-nav">
            <button
              type="button"
              className="help-theme-btn"
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              onClick={toggleTheme}
            >
              {isDark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            {isMemberSession ? (
              <Link to="/verification-pending" className="help-guest-btn primary">
                Back to account status
              </Link>
            ) : (
              <>
                <Link to="/login" className="help-guest-btn">
                  Login
                </Link>
                <Link to="/signup" className="help-guest-btn primary">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {body}
      {modal}
    </div>
  )
}
