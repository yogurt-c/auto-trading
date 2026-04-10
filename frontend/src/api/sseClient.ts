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

  const response = await fetch(`${API_BASE}/agent/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, history }),
  })

  if (!response.ok) {
    throw new Error(`SSE request failed: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('Response body is not readable')

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
        if (!trimmed.startsWith('data:')) continue

        const json = trimmed.slice(5).trim()
        if (!json || json === '[DONE]') continue

        try {
          const parsed = JSON.parse(json) as { content?: string; status?: string; error?: string }
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
    reader.releaseLock()
  }
}
