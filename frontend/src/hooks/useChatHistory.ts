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

  const setHistory = (updater: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => {
    setHistoryState(prev => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      const capped = next.length > MAX_MESSAGES ? next.slice(-MAX_MESSAGES) : next
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(capped))
      } catch { /* storage quota exceeded */ }
      return capped
    })
  }

  const clearHistory = () => {
    sessionStorage.removeItem(STORAGE_KEY)
    setHistoryState([])
  }

  return { history, setHistory, clearHistory }
}
