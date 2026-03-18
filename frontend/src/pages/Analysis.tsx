import { useState, useRef, useEffect } from 'react'
import styled from '@emotion/styled'
import { streamChat } from '../api/sseClient'
import type { ChatMessage } from '../api/types'
import { useChatHistory } from '../hooks/useChatHistory'
import { colors, spacing, fontSize, radius, shadow } from '../theme'
import MarkdownContent from '../components/MarkdownContent'

const QUICK_PROMPTS = [
  '현재 포트폴리오 전체 분석해줘',
  '리스크 높은 종목 알려줘',
  '다음 매수 추천 전략은?',
]

export default function Analysis() {
  const { history, setHistory, clearHistory } = useChatHistory()
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  const send = async (msg: string) => {
    if (!msg.trim() || streaming) return
    setError(null)

    const userMsg: ChatMessage = { role: 'user', content: msg }
    const nextHistory = [...history, userMsg]
    setHistory(nextHistory)
    setInput('')
    setStreaming(true)

    const assistantMsg: ChatMessage = { role: 'assistant', content: '' }
    setHistory([...nextHistory, assistantMsg])

    try {
      for await (const chunk of streamChat(msg, history)) {
        if (chunk.type === 'status') {
          setStatusMsg(chunk.text)
        } else {
          setStatusMsg(null)
          setHistory(prev => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last && last.role === 'assistant') {
              copy[copy.length - 1] = { ...last, content: last.content + chunk.text }
            }
            return copy
          })
        }
      }
    } catch (e) {
      setError(String(e))
      setHistory(prev => prev.slice(0, -1))
    } finally {
      setStreaming(false)
      setStatusMsg(null)
    }
  }

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send(input)
    }
  }

  return (
    <Page>
      <Header>
        <PageTitle>AI Analysis</PageTitle>
        <ClearBtn onClick={clearHistory} disabled={streaming || history.length === 0}>
          기록 초기화
        </ClearBtn>
      </Header>

      <ChatArea>
        {history.length === 0 && (
          <WelcomeBox>
            <WelcomeTitle>Portfolio AI 어시스턴트</WelcomeTitle>
            <WelcomeSub>포트폴리오에 대해 무엇이든 물어보세요</WelcomeSub>
            <QuickRow>
              {QUICK_PROMPTS.map(p => (
                <QuickBtn key={p} onClick={() => void send(p)} disabled={streaming}>
                  {p}
                </QuickBtn>
              ))}
            </QuickRow>
          </WelcomeBox>
        )}

        {history.map((msg, i) => {
          const isLastStreaming = streaming && i === history.length - 1
          return (
            <Bubble key={i} role={msg.role}>
              <BubbleLabel>{msg.role === 'user' ? '나' : 'AI'}</BubbleLabel>
              {msg.role === 'assistant' ? (
                <MarkdownContent>
                  {msg.content || (isLastStreaming && !statusMsg ? '▋' : '')}
                </MarkdownContent>
              ) : (
                <BubbleContent>{msg.content}</BubbleContent>
              )}
              {isLastStreaming && statusMsg && (
                <ToolStatusLine>{statusMsg}</ToolStatusLine>
              )}
            </Bubble>
          )
        })}

        {error && <ErrorMsg>{error}</ErrorMsg>}
        <div ref={bottomRef} />
      </ChatArea>

      <InputRow>
        <Textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="메시지를 입력하세요 (Shift+Enter: 줄바꿈)"
          disabled={streaming}
          rows={2}
        />
        <SendBtn onClick={() => void send(input)} disabled={streaming || !input.trim()}>
          {streaming ? '생성 중...' : '전송'}
        </SendBtn>
      </InputRow>
    </Page>
  )
}

const Page = styled.div`
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px);
`

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: ${spacing.lg};
  flex-shrink: 0;
`

const PageTitle = styled.h1`
  font-size: ${fontSize.xl};
  font-weight: 700;
  margin: 0;
  color: ${colors.text};
`

const ClearBtn = styled.button`
  background: transparent;
  border: 1px solid ${colors.border};
  color: ${colors.textMuted};
  border-radius: ${radius.sm};
  padding: ${spacing.xs} ${spacing.md};
  font-size: ${fontSize.sm};
  cursor: pointer;
  transition: all 0.15s;

  &:hover:not(:disabled) { border-color: ${colors.danger}; color: ${colors.danger}; }
  &:disabled { opacity: 0.4; cursor: not-allowed; }
`

const ChatArea = styled.div`
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: ${spacing.md};
  padding-bottom: ${spacing.md};
`

const WelcomeBox = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  padding: ${spacing.xxl};
`

const WelcomeTitle = styled.h2`
  font-size: ${fontSize.xl};
  font-weight: 700;
  color: ${colors.text};
  margin: 0 0 ${spacing.sm};
`

const WelcomeSub = styled.p`
  color: ${colors.textMuted};
  font-size: ${fontSize.md};
  margin: 0 0 ${spacing.xl};
`

const QuickRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${spacing.sm};
  justify-content: center;
`

const QuickBtn = styled.button`
  background: ${colors.bgCard};
  border: 1px solid ${colors.border};
  color: ${colors.textMuted};
  border-radius: ${radius.full};
  padding: ${spacing.sm} ${spacing.md};
  font-size: ${fontSize.sm};
  cursor: pointer;
  transition: all 0.15s;

  &:hover:not(:disabled) {
    border-color: ${colors.primary};
    color: ${colors.primary};
  }

  &:disabled { opacity: 0.4; }
`

const Bubble = styled.div<{ role: 'user' | 'assistant' }>`
  max-width: 80%;
  align-self: ${({ role }) => (role === 'user' ? 'flex-end' : 'flex-start')};
  background: ${({ role }) => (role === 'user' ? colors.primary + '33' : colors.bgCard)};
  border: 1px solid ${({ role }) => (role === 'user' ? colors.primary + '55' : colors.border)};
  border-radius: ${radius.md};
  padding: ${spacing.sm} ${spacing.md};
  box-shadow: ${shadow.sm};
`

const BubbleLabel = styled.div`
  font-size: ${fontSize.xs};
  font-weight: 600;
  color: ${colors.textMuted};
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`

const BubbleContent = styled.div`
  font-size: ${fontSize.sm};
  color: ${colors.text};
  white-space: pre-wrap;
  line-height: 1.6;
`

const ToolStatusLine = styled.div`
  margin-top: ${spacing.xs};
  font-size: ${fontSize.xs};
  color: ${colors.primary};
  opacity: 0.8;
  display: flex;
  align-items: center;
  gap: 6px;

  &::before {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${colors.primary};
    animation: pulse 1.2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.7); }
  }
`

const ErrorMsg = styled.div`
  background: ${colors.danger}22;
  border: 1px solid ${colors.danger}44;
  color: ${colors.danger};
  padding: ${spacing.md};
  border-radius: ${radius.sm};
  font-size: ${fontSize.sm};
`

const InputRow = styled.div`
  display: flex;
  gap: ${spacing.sm};
  padding-top: ${spacing.md};
  border-top: 1px solid ${colors.border};
  flex-shrink: 0;
`

const Textarea = styled.textarea`
  flex: 1;
  background: ${colors.bgSurface};
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  padding: ${spacing.sm} ${spacing.md};
  color: ${colors.text};
  font-size: ${fontSize.sm};
  resize: none;
  outline: none;
  font-family: inherit;
  line-height: 1.5;

  &:focus { border-color: ${colors.primary}; }
  &::placeholder { color: ${colors.textDim}; }
  &:disabled { opacity: 0.5; }
`

const SendBtn = styled.button`
  background: ${colors.primary};
  color: white;
  border: none;
  border-radius: ${radius.sm};
  padding: ${spacing.sm} ${spacing.xl};
  font-size: ${fontSize.sm};
  font-weight: 600;
  cursor: pointer;
  align-self: flex-end;
  transition: background 0.15s;
  white-space: nowrap;

  &:hover:not(:disabled) { background: ${colors.primaryHover}; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`
