import type { ChatMessage } from './types'

const API_BASE = (import.meta.env['VITE_API_BASE_URL'] as string | undefined) ?? '/api'

export type StreamChunk =
  | { type: 'content'; text: string }
  | { type: 'status'; text: string }

/**
 * SSE 스트리밍 채팅 — 서버에서 `data: {"content"|"status": "..."}` 형식으로 전송
 */
export async function* streamChat(
  message: string,
  history: ChatMessage[]
): AsyncGenerator<StreamChunk> {
  const token = sessionStorage.getItem('auth_token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // 3분 타임아웃 — subagent(strategy-advisor 등)가 여러 번 API 호출을 수행하므로
  // 충분한 여유를 두되, 무한 대기는 방지한다.
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 180_000)

  let response: Response
  try {
    response = await fetch(`${API_BASE}/agent/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message, history }),
      signal: controller.signal,
    })
  } catch (e) {
    clearTimeout(timeoutId)
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new Error('응답 시간이 초과되었습니다. 다시 시도해 주세요.')
    }
    throw e
  }

  if (!response.ok) {
    clearTimeout(timeoutId)
    throw new Error(`SSE request failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    clearTimeout(timeoutId)
    throw new Error('Response body is not readable')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        // SSE comment lines (": keepalive") — 연결 유지용, 무시
        if (trimmed.startsWith(':')) continue
        if (!trimmed.startsWith('data:')) continue

        const jsonStr = trimmed.slice(5).trim()
        if (!jsonStr || jsonStr === '[DONE]') continue

        try {
          const parsed = JSON.parse(jsonStr) as { content?: string; status?: string; error?: string }
          if (parsed.error) throw new Error(parsed.error)
          if (parsed.status) yield { type: 'status', text: parsed.status }
          if (parsed.content) yield { type: 'content', text: parsed.content }
        } catch (e) {
          if (e instanceof SyntaxError) continue  // non-JSON SSE line 무시
          throw e
        }
      }
    }
  } finally {
    clearTimeout(timeoutId)
    reader.releaseLock()
  }
}
