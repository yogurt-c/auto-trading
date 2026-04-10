import { useState } from 'react'
import type { ChatMessage } from '../api/types'

const STORAGE_KEY = 'chat_history'
const MAX_MESSAGES = 100

export function useChatHistory() {
  const [history, setHistoryState] = useState<ChatMessage[]>(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY)
      return stored ? (JSON.parse(stored) as ChatMessage[]) : []
    } catch {
      return []
    }
  })

  const setHistory = (updater: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[]), persist = true) => {
    setHistoryState(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      const capped = next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next
      if (persist) {
        try {
          sessionStorage.setItem(STORAGE_KEY, JSON.stringify(capped))
        } catch { /* storage quota exceeded */ }
      }
      return capped
    })
  }

  // 스트리밍 완료 후 명시적으로 호출 — 스트리밍 중에는 persist=false로 상태만 업데이트
  const persistHistory = (messages: ChatMessage[]) => {
    const capped = messages.length > MAX_MESSAGES ? messages.slice(-MAX_MESSAGES) : messages
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(capped))
    } catch { /* storage quota exceeded */ }
  }

  const clearHistory = () => {
    sessionStorage.removeItem(STORAGE_KEY)
    setHistoryState([])
  }

  return { history, setHistory, persistHistory, clearHistory }
}
