export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

const DEFAULT_TIMEOUT_MS = 20000

export class ApiError extends Error {
  constructor(message, { status, data } = {}) {
    super(typeof message === 'string' && message.trim() ? message : 'Something went wrong. Please try again.')
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

export function apiUrl(path) {
  if (/^https?:\/\//i.test(path)) return path
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

function errorText(value) {
  if (Array.isArray(value)) return value.map(errorText).filter(Boolean).join(' ')
  if (value && typeof value === 'object') {
    if (typeof value.string === 'string') return value.string
    return flattenApiErrors(value)
  }
  return String(value || '').trim()
}

export function flattenApiErrors(data) {
  if (!data) return ''
  if (typeof data === 'string') return data.trim()
  if (typeof data !== 'object') return String(data)

  const labels = {
    username: 'Username',
    first_name: 'First name',
    last_name: 'Last name',
    email: 'Email',
    whatsapp_number: 'WhatsApp number',
    password: 'Password',
    password1: 'Password',
    password2: 'Confirm password',
    non_field_errors: '',
    detail: '',
  }

  return Object.entries(data)
    .map(([field, value]) => {
      const text = errorText(value)
      if (!text) return ''
      const label = labels[field] ?? field
      return field === 'non_field_errors' || field === 'detail' || !label ? text : `${label}: ${text}`
    })
    .filter(Boolean)
    .join(' ')
}

function extractErrorMessage(data, status, path) {
  const isApiPath = String(path || '').includes('/api')
  if (status === 404 && isApiPath) {
    return 'Cannot reach the backend API. Please confirm the MCS backend is running and the frontend was restarted.'
  }

  if (typeof data === 'string' && data.trim()) {
    // Avoid dumping raw HTML pages into the UI.
    if (data.trim().startsWith('<')) {
      return `Request failed with status ${status}. Please confirm the backend API is reachable.`
    }
    return data.trim()
  }

  const fromBody = flattenApiErrors(data)
  if (fromBody) return fromBody

  if (status === 401) {
    return 'Invalid username or password. Please check your credentials and try again.'
  }
  if (status === 403) {
    return 'You do not have permission to perform this action.'
  }
  if (status >= 500) {
    return 'The server could not process this request. Please try again shortly.'
  }
  return `Request failed with status ${status}`
}

async function parseResponseBody(response) {
  const contentType = response.headers.get('content-type') || ''
  const raw = await response.text()
  if (!raw) return null

  if (contentType.includes('application/json') || raw.trim().startsWith('{') || raw.trim().startsWith('[')) {
    try {
      return JSON.parse(raw)
    } catch {
      return raw
    }
  }
  return raw
}

export async function apiRequest(path, { method = 'GET', body, token, headers = {}, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(apiUrl(path), {
      method,
      headers: {
        Accept: 'application/json',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    })

    const data = await parseResponseBody(response)

    if (!response.ok) {
      throw new ApiError(extractErrorMessage(data, response.status, path), {
        status: response.status,
        data,
      })
    }

    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error?.name === 'AbortError') {
      throw new ApiError('The server is taking too long to respond. Please confirm the MCS backend is running and try again.')
    }
    throw new ApiError('Cannot reach the backend server. Please confirm the MCS backend is running.')
  } finally {
    window.clearTimeout(timer)
  }
}
