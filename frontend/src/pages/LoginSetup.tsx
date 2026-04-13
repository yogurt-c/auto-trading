import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import styled from '@emotion/styled'
import { authApi } from '../api/endpoints'
import { useAuth } from '../contexts/AuthContext'
import { colors, spacing, fontSize, radius, shadow } from '../theme'

type Mode = 'loading' | 'setup' | 'login'

export default function LoginSetup() {
  const navigate = useNavigate()
  const { login, setSession, isAuthenticated } = useAuth()

  const [mode, setMode] = useState<Mode>('loading')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // 이미 인증된 경우 대시보드로
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, navigate])

  // 설정 여부 확인 (sessionStorage 캐시 우선)
  useEffect(() => {
    const cached = sessionStorage.getItem('app_configured')
    if (cached === 'true') {
      setMode('login')
      return
    }
    authApi
      .status()
      .then(({ configured }) => {
        if (configured) {
          sessionStorage.setItem('app_configured', 'true')
          setMode('login')
        } else {
          setMode('setup')
        }
      })
      .catch(() => setMode('login')) // 네트워크 오류 시 로그인 폼 기본값
  }, [])

  const handleSetup = async () => {
    setError(null)
    if (!password.trim()) {
      setError('비밀번호를 입력해 주세요')
      return
    }
    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다')
      return
    }
    if (password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다')
      return
    }
    setIsSubmitting(true)
    try {
      const data = await authApi.setup(password)
      setSession(data.access_token)
      navigate('/dashboard', { replace: true })
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? '설정에 실패했습니다')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleLogin = async () => {
    setError(null)
    if (!password.trim()) {
      setError('비밀번호를 입력해 주세요')
      return
    }
    setIsSubmitting(true)
    try {
      await login(password)
      navigate('/dashboard', { replace: true })
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? '로그인에 실패했습니다')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (mode === 'loading') {
    return (
      <Page>
        <Card>
          <LoadingText>로딩 중...</LoadingText>
        </Card>
      </Page>
    )
  }

  return (
    <Page>
      <Card>
        <Logo>Portfolio</Logo>
        <LogoSub>AI Manager</LogoSub>

        {mode === 'setup' ? (
          <>
            <Title>초기 설정</Title>
            <Description>앱을 보호할 비밀번호를 설정하세요</Description>
            <Field>
              <Label>비밀번호 (8자 이상)</Label>
              <Input
                type="password"
                placeholder="새 비밀번호"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && void handleSetup()}
                autoFocus
              />
            </Field>
            <Field>
              <Label>비밀번호 확인</Label>
              <Input
                type="password"
                placeholder="비밀번호 재입력"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && void handleSetup()}
              />
            </Field>
            {error && <ErrorMsg>{error}</ErrorMsg>}
            <SubmitBtn onClick={() => void handleSetup()} disabled={isSubmitting}>
              {isSubmitting ? '설정 중...' : '비밀번호 설정'}
            </SubmitBtn>
          </>
        ) : (
          <>
            <Title>로그인</Title>
            <Description>비밀번호를 입력하여 접속하세요</Description>
            <Field>
              <Label>비밀번호</Label>
              <Input
                type="password"
                placeholder="비밀번호"
                value={password}
                onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && void handleLogin()}
                autoFocus
              />
            </Field>
            {error && <ErrorMsg>{error}</ErrorMsg>}
            <SubmitBtn onClick={() => void handleLogin()} disabled={isSubmitting}>
              {isSubmitting ? '로그인 중...' : '로그인'}
            </SubmitBtn>
          </>
        )}
      </Card>
    </Page>
  )
}

const Page = styled.div`
  min-height: 100vh;
  background: ${colors.bg};
  display: flex;
  align-items: center;
  justify-content: center;
`

const Card = styled.div`
  background: ${colors.bgCard};
  border: 1px solid ${colors.border};
  border-radius: ${radius.lg};
  padding: ${spacing.xxl};
  width: 100%;
  max-width: 400px;
  box-shadow: ${shadow.lg};
  display: flex;
  flex-direction: column;
  gap: ${spacing.md};
`

const Logo = styled.div`
  font-size: ${fontSize.xl};
  font-weight: 700;
  color: ${colors.primary};
  letter-spacing: -0.5px;
  text-align: center;
`

const LogoSub = styled.div`
  font-size: ${fontSize.xs};
  color: ${colors.textMuted};
  text-align: center;
  margin-top: -${spacing.sm};
`

const Title = styled.h1`
  font-size: ${fontSize.lg};
  font-weight: 700;
  color: ${colors.text};
  margin: 0;
  margin-top: ${spacing.sm};
`

const Description = styled.p`
  font-size: ${fontSize.sm};
  color: ${colors.textMuted};
  margin: 0;
`

const Field = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.xs};
`

const Label = styled.label`
  font-size: ${fontSize.sm};
  font-weight: 500;
  color: ${colors.textMuted};
`

const Input = styled.input`
  background: ${colors.bgSurface};
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  padding: ${spacing.sm} ${spacing.md};
  color: ${colors.text};
  font-size: ${fontSize.sm};
  outline: none;
  transition: border-color 0.15s;

  &:focus {
    border-color: ${colors.primary};
  }

  &::placeholder {
    color: ${colors.textDim};
  }
`

const ErrorMsg = styled.div`
  font-size: ${fontSize.sm};
  color: ${colors.danger};
  padding: ${spacing.sm} ${spacing.md};
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid ${colors.danger};
  border-radius: ${radius.sm};
`

const SubmitBtn = styled.button`
  background: ${colors.primary};
  color: white;
  border: none;
  border-radius: ${radius.sm};
  padding: ${spacing.sm} ${spacing.md};
  font-size: ${fontSize.sm};
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: ${spacing.sm};

  &:hover:not(:disabled) {
    background: ${colors.primaryHover};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`

const LoadingText = styled.div`
  color: ${colors.textMuted};
  font-size: ${fontSize.sm};
  text-align: center;
  padding: ${spacing.xl} 0;
`
