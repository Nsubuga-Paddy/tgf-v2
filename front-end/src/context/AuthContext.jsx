import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { apiRequest } from '../lib/api'
import {
  SESSION_ABSOLUTE_MS,
  SESSION_ACTIVITY_THROTTLE_MS,
  SESSION_IDLE_MS,
  SESSION_TIMEOUT_REASON,
  SESSION_WARNING_BEFORE_MS,
} from '../lib/sessionPolicy'

const STORAGE_KEY = 'mcs-auth'

const AuthContext = createContext(null)

function readStoredAuth() {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || 'null')
  } catch {
    return null
  }
}

function writeStoredAuth(value) {
  if (!value) {
    window.localStorage.removeItem(STORAGE_KEY)
    return
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
}

function withSessionMeta(session) {
  if (!session) return null
  return {
    ...session,
    startedAt: session.startedAt || Date.now(),
    lastActiveAt: session.lastActiveAt || Date.now(),
  }
}

export function AuthProvider({ children }) {
  const navigate = useNavigate()
  const [session, setSession] = useState(() =>
    typeof window === 'undefined' ? null : withSessionMeta(readStoredAuth()),
  )
  const [idleWarning, setIdleWarning] = useState(false)

  const sessionRef = useRef(session)
  const idleTimerRef = useRef(null)
  const warningTimerRef = useRef(null)
  const absoluteTimerRef = useRef(null)
  const lastActivityRef = useRef(Date.now())
  const endingRef = useRef(false)

  useEffect(() => {
    sessionRef.current = session
  }, [session])

  const saveSession = useCallback((next) => {
    const normalized = withSessionMeta(next)
    setSession(normalized)
    writeStoredAuth(normalized)
  }, [])

  const clearTimers = useCallback(() => {
    if (idleTimerRef.current) {
      window.clearTimeout(idleTimerRef.current)
      idleTimerRef.current = null
    }
    if (warningTimerRef.current) {
      window.clearTimeout(warningTimerRef.current)
      warningTimerRef.current = null
    }
    if (absoluteTimerRef.current) {
      window.clearTimeout(absoluteTimerRef.current)
      absoluteTimerRef.current = null
    }
  }, [])

  const endSession = useCallback(
    async (reason = 'logout') => {
      if (endingRef.current) return
      endingRef.current = true
      clearTimers()
      setIdleWarning(false)
      const refresh = sessionRef.current?.refresh
      saveSession(null)
      if (refresh) {
        try {
          await apiRequest('/api/auth/logout/', {
            method: 'POST',
            body: { refresh },
          })
        } catch {
          // Local logout should not be blocked by an expired refresh token.
        }
      }
      endingRef.current = false
      if (reason === SESSION_TIMEOUT_REASON) {
        navigate(`/login?reason=${SESSION_TIMEOUT_REASON}`, { replace: true })
      }
    },
    [clearTimers, navigate, saveSession],
  )

  const logoutForTimeout = useCallback(() => endSession(SESSION_TIMEOUT_REASON), [endSession])

  const scheduleIdleTimers = useCallback(() => {
    clearTimers()
    if (!sessionRef.current?.access) return

    const startedAt = sessionRef.current.startedAt || Date.now()
    const absoluteRemaining = SESSION_ABSOLUTE_MS - (Date.now() - startedAt)
    if (absoluteRemaining <= 0) {
      endSession(SESSION_TIMEOUT_REASON)
      return
    }

    absoluteTimerRef.current = window.setTimeout(() => {
      endSession(SESSION_TIMEOUT_REASON)
    }, absoluteRemaining)

    const warningDelay = Math.max(SESSION_IDLE_MS - SESSION_WARNING_BEFORE_MS, 0)
    warningTimerRef.current = window.setTimeout(() => {
      setIdleWarning(true)
    }, warningDelay)

    idleTimerRef.current = window.setTimeout(() => {
      endSession(SESSION_TIMEOUT_REASON)
    }, SESSION_IDLE_MS)
  }, [clearTimers, endSession])

  const markActivity = useCallback(() => {
    if (!sessionRef.current?.access) return
    const now = Date.now()
    if (now - lastActivityRef.current < SESSION_ACTIVITY_THROTTLE_MS) return
    lastActivityRef.current = now
    setIdleWarning(false)
    setSession((prev) => {
      if (!prev) return prev
      const next = { ...prev, lastActiveAt: now }
      writeStoredAuth(next)
      return next
    })
    scheduleIdleTimers()
  }, [scheduleIdleTimers])

  const dismissIdleWarning = useCallback(() => {
    markActivity()
  }, [markActivity])

  useEffect(() => {
    if (!session?.access) {
      clearTimers()
      setIdleWarning(false)
      return undefined
    }

    lastActivityRef.current = Date.now()
    scheduleIdleTimers()

    // Intentional interaction only — ignore bare mousemove so idle expiry is reliable.
    const events = ['mousedown', 'keydown', 'touchstart', 'scroll', 'click']
    const onActivity = () => markActivity()
    events.forEach((eventName) =>
      window.addEventListener(eventName, onActivity, { passive: true }),
    )

    const onVisibility = () => {
      if (document.visibilityState === 'visible') markActivity()
    }
    document.addEventListener('visibilitychange', onVisibility)

    return () => {
      clearTimers()
      events.forEach((eventName) => window.removeEventListener(eventName, onActivity))
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [session?.access, clearTimers, markActivity, scheduleIdleTimers])

  const login = useCallback(
    async ({ username, password }) => {
      const data = await apiRequest('/api/auth/login/', {
        method: 'POST',
        body: { username, password },
      })
      if (!data?.access || !data?.refresh) {
        throw new Error(
          'Login succeeded but no access token was returned. Please confirm the /api/auth/login/ endpoint is reachable.',
        )
      }
      const now = Date.now()
      const next = {
        access: data.access,
        refresh: data.refresh,
        startedAt: now,
        lastActiveAt: now,
        user: data.user || {
          username,
          first_name: '',
          last_name: '',
          email: '',
          is_verified: true,
        },
      }
      saveSession(next)
      return next
    },
    [saveSession],
  )

  const signup = useCallback(
    async (payload) => {
      const data = await apiRequest('/api/auth/signup/', {
        method: 'POST',
        body: payload,
      })
      if (data?.access && data?.refresh) {
        const now = Date.now()
        const next = {
          access: data.access,
          refresh: data.refresh,
          startedAt: now,
          lastActiveAt: now,
          user: data.user || {
            username: payload.username,
            first_name: payload.first_name || '',
            last_name: payload.last_name || '',
            email: payload.email || '',
            is_verified: false,
          },
        }
        saveSession(next)
      }
      return data
    },
    [saveSession],
  )

  const requestPasswordReset = useCallback(async (email) => {
    return apiRequest('/api/auth/forgot-password/', {
      method: 'POST',
      body: { email },
    })
  }, [])

  const confirmPasswordReset = useCallback(async (payload) => {
    return apiRequest('/api/auth/reset-password/', {
      method: 'POST',
      body: payload,
    })
  }, [])

  const updateUser = useCallback((patch) => {
    setSession((prev) => {
      if (!prev) return prev
      const next = { ...prev, user: { ...(prev.user || {}), ...patch } }
      writeStoredAuth(next)
      return next
    })
  }, [])

  const refreshAccess = useCallback(async () => {
    const current = sessionRef.current
    if (!current?.refresh) throw new Error('No refresh token available')
    const data = await apiRequest('/api/auth/token/refresh/', {
      method: 'POST',
      body: { refresh: current.refresh },
    })
    const next = {
      ...current,
      access: data.access,
      refresh: data.refresh || current.refresh,
      lastActiveAt: Date.now(),
    }
    saveSession(next)
    return next.access
  }, [saveSession])

  const authFetch = useCallback(
    async (path, options = {}) => {
      if (!sessionRef.current?.access) throw new Error('You must be logged in to continue.')
      try {
        return await apiRequest(path, {
          ...options,
          token: sessionRef.current.access,
        })
      } catch (error) {
        if (error.status !== 401 || !sessionRef.current?.refresh) throw error
        try {
          const access = await refreshAccess()
          return apiRequest(path, { ...options, token: access })
        } catch (refreshError) {
          await endSession(SESSION_TIMEOUT_REASON)
          throw refreshError
        }
      }
    },
    [endSession, refreshAccess],
  )

  const logout = useCallback(async () => {
    await endSession('logout')
  }, [endSession])

  const value = useMemo(
    () => ({
      accessToken: session?.access || '',
      refreshToken: session?.refresh || '',
      user: session?.user || null,
      isAuthenticated: Boolean(session?.access),
      idleWarning,
      login,
      signup,
      requestPasswordReset,
      confirmPasswordReset,
      logout,
      logoutForTimeout,
      dismissIdleWarning,
      authFetch,
      refreshAccess,
      updateUser,
    }),
    [
      authFetch,
      confirmPasswordReset,
      dismissIdleWarning,
      idleWarning,
      login,
      logout,
      logoutForTimeout,
      refreshAccess,
      requestPasswordReset,
      session,
      signup,
      updateUser,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
