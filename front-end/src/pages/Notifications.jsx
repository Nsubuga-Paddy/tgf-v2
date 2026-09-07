import { useCallback, useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useParams } from 'react-router-dom'
import { Bell, CheckCheck, Inbox, X } from 'lucide-react'
import AppShell from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { formatNotifTime } from '../utils/notificationTime'

const MOBILE_QUERY = '(max-width: 900px)'

function useIsMobileNotifications() {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia(MOBILE_QUERY).matches
  })

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined
    const media = window.matchMedia(MOBILE_QUERY)
    const onChange = () => setIsMobile(media.matches)
    onChange()
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  return isMobile
}

function NotificationDetailContent({ notification }) {
  if (!notification) return null
  return (
    <article className="notifications-detail">
      <header className="notifications-detail-head">
        <div>
          <small>{notification.source === 'staff' ? 'Investor Notice' : 'System notice'}</small>
          <h2>{notification.title}</h2>
          <time dateTime={notification.createdAt}>{formatNotifTime(notification.createdAt)}</time>
        </div>
        {!notification.isRead ? <span className="notifications-unread-pill">Unread</span> : null}
      </header>
      <div className="notifications-detail-body">{notification.body}</div>
    </article>
  )
}

export default function Notifications() {
  const { notificationId } = useParams()
  const navigate = useNavigate()
  const { authFetch } = useAuth()
  const isMobile = useIsMobileNotifications()
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [markingAll, setMarkingAll] = useState(false)

  const selectedId = notificationId ? Number(notificationId) : null

  const loadNotifications = useCallback(async () => {
    setLoading(true)
    try {
      const payload = await authFetch('/api/notifications/?limit=200')
      setNotifications(payload.notifications || [])
      setUnreadCount(Number(payload.unreadCount || 0))
    } catch {
      // Keep prior list if refresh fails.
    } finally {
      setLoading(false)
    }
  }, [authFetch])

  useEffect(() => {
    loadNotifications()
  }, [loadNotifications])

  const selected = useMemo(
    () => notifications.find((item) => item.id === selectedId) || null,
    [notifications, selectedId],
  )

  const closeDetail = useCallback(() => {
    navigate('/notifications')
  }, [navigate])

  useEffect(() => {
    if (!selectedId || !authFetch) return
    const item = notifications.find((n) => n.id === selectedId)
    if (!item || item.isRead) return

    let cancelled = false
    ;(async () => {
      try {
        const payload = await authFetch(`/api/notifications/${selectedId}/read/`, {
          method: 'POST',
          body: { limit: 200 },
        })
        if (cancelled) return
        setNotifications(payload.notifications || [])
        setUnreadCount(Number(payload.unreadCount || 0))
      } catch {
        // ignore
      }
    })()

    return () => {
      cancelled = true
    }
  }, [authFetch, notifications, selectedId])

  useEffect(() => {
    if (!notificationId || loading) return
    if (notifications.length === 0) return
    if (!notifications.some((item) => item.id === selectedId)) {
      navigate('/notifications', { replace: true })
    }
  }, [loading, navigate, notificationId, notifications, selectedId])

  useEffect(() => {
    if (!isMobile || !selected) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') closeDetail()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [closeDetail, isMobile, selected])

  const openNotification = (item) => {
    navigate(`/notifications/${item.id}`)
  }

  const markAllRead = async () => {
    if (unreadCount === 0 || markingAll) return
    setMarkingAll(true)
    try {
      const payload = await authFetch('/api/notifications/read-all/', {
        method: 'POST',
        body: { limit: 200 },
      })
      setNotifications(payload.notifications || [])
      setUnreadCount(Number(payload.unreadCount || 0))
    } catch {
      // ignore
    } finally {
      setMarkingAll(false)
    }
  }

  const mobileDetailModal =
    isMobile && selected
      ? createPortal(
          <div className="modal-overlay" onClick={closeDetail} role="presentation">
            <div
              className="modal notif-detail-modal notifications-detail-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="notification-detail-title"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-head">
                <div className="modal-head-icon">
                  <Bell size={20} />
                </div>
                <div className="modal-head-text">
                  <b id="notification-detail-title">
                    {selected.source === 'staff' ? 'Investor Notice' : 'System notice'}
                  </b>
                  <span>{formatNotifTime(selected.createdAt)}</span>
                </div>
                <button type="button" className="modal-close" aria-label="Close" onClick={closeDetail}>
                  <X size={18} />
                </button>
              </div>
              <div className="modal-body notifications-detail-modal-body">
                <h2 className="notifications-detail-modal-title">{selected.title}</h2>
                {!selected.isRead ? (
                  <span className="notifications-unread-pill notifications-detail-modal-pill">Unread</span>
                ) : null}
                <div className="notif-detail-body notifications-detail-body">{selected.body}</div>
              </div>
              <div className="modal-foot">
                <button type="button" className="btn btn-outline" onClick={closeDetail}>
                  Close
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )
      : null

  return (
    <AppShell title="Notifications">
      <div className="notifications-page">
        <div className="notifications-toolbar">
          <div className="notifications-toolbar-copy">
            <Bell size={20} />
            <div>
              <strong>Your notifications</strong>
              <span>
                {unreadCount > 0
                  ? `${unreadCount} unread message${unreadCount === 1 ? '' : 's'}`
                  : 'All caught up'}
              </span>
            </div>
          </div>
          {unreadCount > 0 ? (
            <button
              type="button"
              className="btn-sm btn-outline notifications-mark-all"
              onClick={markAllRead}
              disabled={markingAll}
            >
              <CheckCheck size={16} />
              {markingAll ? 'Marking…' : 'Mark all read'}
            </button>
          ) : null}
        </div>

        <div className="notifications-layout">
          <aside className="notifications-list-panel" aria-label="Notification list">
            {loading ? (
              <p className="notifications-empty">Loading notifications…</p>
            ) : notifications.length === 0 ? (
              <div className="notifications-empty-state">
                <Inbox size={28} />
                <p>No notifications yet.</p>
                <span>Investor notices and updates will appear here.</span>
              </div>
            ) : (
              <ul className="notifications-list">
                {notifications.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className={`notifications-list-item ${
                        item.id === selectedId ? 'active' : ''
                      } ${item.isRead ? '' : 'unread'}`}
                      onClick={() => openNotification(item)}
                    >
                      <div className="notifications-list-item-head">
                        <b>{item.title}</b>
                        {!item.isRead ? <span className="notifications-unread-pill">New</span> : null}
                      </div>
                      <p>
                        {(item.body || '').slice(0, 140)}
                        {(item.body || '').length > 140 ? '…' : ''}
                      </p>
                      <small>{formatNotifTime(item.createdAt)}</small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          <section
            className="notifications-detail-panel notifications-detail-panel-desktop"
            aria-label="Notification detail"
          >
            {selected ? (
              <NotificationDetailContent notification={selected} />
            ) : (
              <div className="notifications-detail-placeholder">
                <Bell size={32} />
                <p>Select a notification to read it here.</p>
              </div>
            )}
          </section>
        </div>
      </div>
      {mobileDetailModal}
    </AppShell>
  )
}
