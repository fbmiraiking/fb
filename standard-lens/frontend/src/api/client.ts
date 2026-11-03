const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const DEFAULT_TIMEOUT_MS = 8_000

export class ApiError extends Error {
  status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...init.headers,
      },
      signal: controller.signal,
    })

    if (!response.ok) {
      let message = `接口返回 HTTP ${response.status}`
      try {
        const payload: unknown = await response.json()
        if (payload && typeof payload === 'object' && 'detail' in payload) {
          const detail = (payload as { detail: unknown }).detail
          if (typeof detail === 'string' && detail.trim()) {
            message = detail
          } else if (Array.isArray(detail)) {
            const messages = detail
              .map((item) =>
                item && typeof item === 'object' && 'msg' in item
                  ? String((item as { msg: unknown }).msg)
                  : '',
              )
              .filter(Boolean)
            if (messages.length) {
              message = messages.join('；')
            }
          }
        }
      } catch {
        // Non-JSON error bodies fall back to the HTTP status message.
      }
      throw new ApiError(message, response.status)
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError('请求超时，请检查后端服务')
    }
    if (error instanceof TypeError) {
      throw new ApiError('无法连接后端服务')
    }
    throw error
  } finally {
    window.clearTimeout(timer)
  }
}
