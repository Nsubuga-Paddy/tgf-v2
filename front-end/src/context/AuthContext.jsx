import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { apiRequest } from '../lib/api'

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

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() =>
    typeof window === 'undefined' ? null : readStoredAuth(),
  )

  const saveSession = useCallback((next) => {
    setSession(next)
    writeStoredAuth(next)
  }, [])

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
      const next = {
        access: data.access,
        refresh: data.refresh,
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
        const next = {
          access: data.access,
          refresh: data.refresh,
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

  const updateUser = useCallback(
    (patch) => {
      setSession((prev) => {
        if (!prev) return prev
        const next = { ...prev, user: { ...(prev.user || {}), ...patch } }
        writeStoredAuth(next)
        return next
      })
    },
    [],
  )

  const refreshAccess = useCallback(async () => {
    if (!session?.refresh) throw new Error('No refresh token available')
    const data = await apiRequest('/api/auth/token/refresh/', {
      method: 'POST',
      body: { refresh: session.refresh },
    })
    const next = {
      ...session,
      access: data.access,
      refresh: data.refresh || session.refresh,
    }
    saveSession(next)
    return next.access
  }, [saveSession, session])

  const authFetch = useCallback(
    async (path, options = {}) => {
      if (!session?.access) throw new Error('You must be logged in to continue.')
      try {
        return await apiRequest(path, { ...options, token: session.access })
      } catch (error) {
        if (error.status !== 401 || !session?.refresh) throw error
        const access = await refreshAccess()
        return apiRequest(path, { ...options, token: access })
      }
    },
    [refreshAccess, session],
  )

  const logout = useCallback(async () => {
    const refresh = session?.refresh
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
  }, [saveSession, session])

  const value = useMemo(
    () => ({
      accessToken: session?.access || '',
      refreshToken: session?.refresh || '',
      user: session?.user || null,
      isAuthenticated: Boolean(session?.access),
      login,
      signup,
      requestPasswordReset,
      confirmPasswordReset,
      logout,
      authFetch,
      refreshAccess,
      updateUser,
    }),
    [
      authFetch,
      confirmPasswordReset,
      login,
      logout,
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
