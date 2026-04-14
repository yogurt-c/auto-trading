import { useState } from 'react'
import styled from '@emotion/styled'
import * as Switch from '@radix-ui/react-switch'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi, authApi } from '../api/endpoints'
import { colors, spacing, fontSize, radius, shadow } from '../theme'

const PAPER_FIELDS = [
  { key: 'KIS_PAPER_APP_KEY', label: 'App Key', type: 'password' },
  { key: 'KIS_PAPER_APP_SECRET', label: 'App Secret', type: 'password' },
  { key: 'KIS_PAPER_ACCOUNT_NO', label: '계좌번호 (8자리 숫자)', type: 'text' },
]

const REAL_FIELDS = [
  { key: 'KIS_REAL_APP_KEY', label: 'App Key', type: 'password' },
  { key: 'KIS_REAL_APP_SECRET', label: 'App Secret', type: 'password' },
  { key: 'KIS_REAL_ACCOUNT_NO', label: '계좌번호 (8자리 숫자)', type: 'text' },
]

export default function Settings() {
  const qc = useQueryClient()
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.getAll,
  })

  const [form, setForm] = useState<Record<string, string>>({})
  const [toast, setToast] = useState<string | null>(null)

  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' })
  const [pwError, setPwError] = useState<string | null>(null)

  const pwMutation = useMutation({
    mutationFn: () => authApi.changePassword(pwForm.current, pwForm.next),
    onSuccess: () => {
      setPwForm({ current: '', next: '', confirm: '' })
      setPwError(null)
      setToast('비밀번호가 변경되었습니다')
      setTimeout(() => setToast(null), 2500)
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setPwError(detail ?? '비밀번호 변경에 실패했습니다')
    },
  })

  const handleChangePassword = () => {
    setPwError(null)
    if (!pwForm.current.trim()) {
      setPwError('현재 비밀번호를 입력해 주세요')
      return
    }
    if (!pwForm.next.trim()) {
      setPwError('새 비밀번호를 입력해 주세요')
      return
    }
    if (pwForm.next.length < 8) {
      setPwError('새 비밀번호는 8자 이상이어야 합니다')
      return
    }
    if (pwForm.next !== pwForm.confirm) {
      setPwError('새 비밀번호가 일치하지 않습니다')
      return
    }
    pwMutation.mutate()
  }

  const isPaper = settings?.['KIS_PAPER'] !== 'false'

  const paperMutation = useMutation({
    mutationFn: (paper: boolean) =>
      settingsApi.set('KIS_PAPER', paper ? 'true' : 'false'),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['settings'] })
      setToast('거래 모드가 변경되었습니다')
      setTimeout(() => setToast(null), 2500)
    },
  })

  const mutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      settingsApi.set(key, value),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['settings'] })
      // settingsStatus 검증은 handleSave의 Promise.all 완료 후에만 실행
      // (개별 키 저장 완료 시 즉시 refetch 시 부분적으로 저장된 상태로 KIS 검증이 실행되는 버그 방지)
      setToast('저장되었습니다')
      setTimeout(() => setToast(null), 2500)
    },
  })

  const handleSave = async () => {
    const entries = Object.entries(form).filter(([, value]) => value.trim())
    if (entries.length === 0) return
    await Promise.all(entries.map(([key, value]) => mutation.mutateAsync({ key, value: value.trim() })))
    // 모든 키 저장 완료 후 settingsStatus 재검증
    void qc.invalidateQueries({ queryKey: ['settingsStatus'] })
  }

  const get = (key: string) => form[key] ?? ''

  return (
    <Page>
      <PageTitle>Settings</PageTitle>
      <Card>
        <Section>
          <SectionTitle>거래 모드</SectionTitle>
          <ModeRow>
            <ModeInfo>
              <ModeLabel>Paper Trading</ModeLabel>
              <ModeDesc>
                {isPaper
                  ? '모의 거래 모드 — 실제 자금을 사용하지 않습니다'
                  : '실거래 모드 — 실제 자금으로 주문이 실행됩니다'}
              </ModeDesc>
            </ModeInfo>
            <SwitchRoot
              checked={isPaper}
              onCheckedChange={checked => paperMutation.mutate(checked)}
              disabled={paperMutation.isPending || isLoading}
            >
              <SwitchThumb />
            </SwitchRoot>
          </ModeRow>
          {!isPaper && (
            <LiveWarning>⚠ 실거래 모드: 실제 자금으로 주문이 즉시 실행됩니다.</LiveWarning>
          )}
        </Section>

        <Section>
          <SectionTitle>KIS API Keys</SectionTitle>
          <CredentialGrid>
            <CredentialBlock active={isPaper}>
              <CredentialBlockTitle active={isPaper}>
                모의투자
                {isPaper && <ActiveBadge>활성</ActiveBadge>}
              </CredentialBlockTitle>
              {PAPER_FIELDS.map(field => (
                <Field key={field.key}>
                  <Label>{field.label}</Label>
                  <Input
                    type={field.type}
                    placeholder={
                      isLoading
                        ? '로딩 중...'
                        : settings?.[field.key]
                          ? '••••••••••••••••'
                          : '입력되지 않음'
                    }
                    value={get(field.key)}
                    onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                  />
                  {settings?.[field.key] && (
                    <Hint>현재 값 설정됨 — 새 값 입력 시 덮어씌워집니다</Hint>
                  )}
                </Field>
              ))}
            </CredentialBlock>

            <CredentialBlock active={!isPaper}>
              <CredentialBlockTitle active={!isPaper}>
                실전투자
                {!isPaper && <ActiveBadge live>활성</ActiveBadge>}
              </CredentialBlockTitle>
              {REAL_FIELDS.map(field => (
                <Field key={field.key}>
                  <Label>{field.label}</Label>
                  <Input
                    type={field.type}
                    placeholder={
                      isLoading
                        ? '로딩 중...'
                        : settings?.[field.key]
                          ? '••••••••••••••••'
                          : '입력되지 않음'
                    }
                    value={get(field.key)}
                    onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                  />
                  {settings?.[field.key] && (
                    <Hint>현재 값 설정됨 — 새 값 입력 시 덮어씌워집니다</Hint>
                  )}
                </Field>
              ))}
            </CredentialBlock>
          </CredentialGrid>
        </Section>

        <Section>
          <SectionTitle>Anthropic API Key</SectionTitle>
          <Field>
            <Label>API Key</Label>
            <Input
              type="password"
              placeholder={
                isLoading
                  ? '로딩 중...'
                  : settings?.['ANTHROPIC_API_KEY']
                    ? '••••••••••••••••'
                    : '입력되지 않음'
              }
              value={get('ANTHROPIC_API_KEY')}
              onChange={e => setForm(f => ({ ...f, ANTHROPIC_API_KEY: e.target.value }))}
            />
            {settings?.['ANTHROPIC_API_KEY'] && (
              <Hint>현재 값 설정됨 — 새 값 입력 시 덮어씌워집니다</Hint>
            )}
          </Field>
        </Section>

        <SaveRow>
          <SaveBtn
            onClick={() => void handleSave()}
            disabled={mutation.isPending || Object.keys(form).every(k => !form[k]?.trim())}
          >
            {mutation.isPending ? '저장 중...' : '저장'}
          </SaveBtn>
        </SaveRow>
      </Card>

      <Card style={{ marginTop: spacing.xl }}>
        <Section>
          <SectionTitle>보안</SectionTitle>
          <Field>
            <Label>현재 비밀번호</Label>
            <Input
              type="password"
              placeholder="현재 비밀번호"
              value={pwForm.current}
              onChange={e => setPwForm(f => ({ ...f, current: e.target.value }))}
            />
          </Field>
          <Field>
            <Label>새 비밀번호 (8자 이상)</Label>
            <Input
              type="password"
              placeholder="새 비밀번호"
              value={pwForm.next}
              onChange={e => setPwForm(f => ({ ...f, next: e.target.value }))}
            />
          </Field>
          <Field>
            <Label>새 비밀번호 확인</Label>
            <Input
              type="password"
              placeholder="새 비밀번호 재입력"
              value={pwForm.confirm}
              onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))}
            />
          </Field>
          {pwError && <PwError>{pwError}</PwError>}
        </Section>
        <SaveRow>
          <SaveBtn
            onClick={handleChangePassword}
            disabled={pwMutation.isPending}
          >
            {pwMutation.isPending ? '변경 중...' : '비밀번호 변경'}
          </SaveBtn>
        </SaveRow>
      </Card>

      {toast && <Toast>{toast}</Toast>}
    </Page>
  )
}

const Page = styled.div`
  max-width: 640px;
`

const PageTitle = styled.h1`
  font-size: ${fontSize.xl};
  font-weight: 700;
  margin: 0 0 ${spacing.xl};
  color: ${colors.text};
`

const Card = styled.div`
  background: ${colors.bgCard};
  border: 1px solid ${colors.border};
  border-radius: ${radius.lg};
  padding: ${spacing.xl};
  box-shadow: ${shadow.sm};
`

const Section = styled.div`
  margin-bottom: ${spacing.xl};
`

const SectionTitle = styled.h2`
  font-size: ${fontSize.md};
  font-weight: 600;
  color: ${colors.text};
  margin: 0 0 ${spacing.lg};
`

const Field = styled.div`
  margin-bottom: ${spacing.lg};
`

const Label = styled.label`
  display: block;
  font-size: ${fontSize.sm};
  font-weight: 500;
  color: ${colors.textMuted};
  margin-bottom: ${spacing.xs};
`

const Input = styled.input`
  width: 100%;
  box-sizing: border-box;
  background: ${colors.bgSurface};
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  padding: ${spacing.sm} ${spacing.md};
  color: ${colors.text};
  font-size: ${fontSize.sm};
  outline: none;
  transition: border-color 0.15s;
  font-family: monospace;

  &:focus {
    border-color: ${colors.primary};
  }

  &::placeholder {
    color: ${colors.textDim};
  }
`

const Hint = styled.div`
  margin-top: 4px;
  font-size: ${fontSize.xs};
  color: ${colors.textDim};
`

const SaveRow = styled.div`
  display: flex;
  justify-content: flex-end;
  padding-top: ${spacing.lg};
  border-top: 1px solid ${colors.border};
`

const SaveBtn = styled.button`
  background: ${colors.primary};
  color: white;
  border: none;
  border-radius: ${radius.sm};
  padding: ${spacing.sm} ${spacing.xl};
  font-size: ${fontSize.sm};
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;

  &:hover:not(:disabled) {
    background: ${colors.primaryHover};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`

const ModeRow = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
`

const ModeInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`

const ModeLabel = styled.span`
  font-size: ${fontSize.sm};
  font-weight: 500;
  color: ${colors.text};
`

const ModeDesc = styled.span`
  font-size: ${fontSize.xs};
  color: ${colors.textMuted};
`

const SwitchRoot = styled(Switch.Root)`
  width: 44px;
  height: 24px;
  background: ${colors.border};
  border-radius: 12px;
  border: none;
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;

  &[data-state='checked'] {
    background: ${colors.primary};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`

const SwitchThumb = styled(Switch.Thumb)`
  display: block;
  width: 20px;
  height: 20px;
  background: white;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;

  &[data-state='checked'] {
    transform: translateX(20px);
  }
`

const PwError = styled.div`
  margin-top: ${spacing.sm};
  font-size: ${fontSize.sm};
  color: ${colors.danger};
  padding: ${spacing.sm} ${spacing.md};
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid ${colors.danger};
  border-radius: ${radius.sm};
`

const CredentialGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: ${spacing.lg};

  @media (max-width: 560px) {
    grid-template-columns: 1fr;
  }
`

const CredentialBlock = styled.div<{ active: boolean }>`
  border: 1px solid ${({ active }) => active ? colors.primary : colors.border};
  border-radius: ${radius.md};
  padding: ${spacing.lg};
  background: ${({ active }) => active ? 'rgba(108, 124, 255, 0.04)' : 'transparent'};
  transition: border-color 0.2s, background 0.2s;
`

const CredentialBlockTitle = styled.div<{ active: boolean }>`
  display: flex;
  align-items: center;
  gap: ${spacing.sm};
  font-size: ${fontSize.sm};
  font-weight: 600;
  color: ${({ active }) => active ? colors.primary : colors.textMuted};
  margin-bottom: ${spacing.lg};
`

const ActiveBadge = styled.span<{ live?: boolean }>`
  font-size: ${fontSize.xs};
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: ${({ live }) => live ? 'rgba(248, 113, 113, 0.15)' : 'rgba(108, 124, 255, 0.15)'};
  color: ${({ live }) => live ? colors.danger : colors.primary};
`

const LiveWarning = styled.div`
  margin-top: ${spacing.md};
  padding: ${spacing.sm} ${spacing.md};
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid ${colors.danger};
  border-radius: ${radius.sm};
  color: ${colors.danger};
  font-size: ${fontSize.sm};
  font-weight: 500;
`

const Toast = styled.div`
  position: fixed;
  bottom: ${spacing.xl};
  right: ${spacing.xl};
  background: ${colors.success};
  color: #000;
  padding: ${spacing.sm} ${spacing.lg};
  border-radius: ${radius.md};
  font-size: ${fontSize.sm};
  font-weight: 600;
  box-shadow: ${shadow.md};
  z-index: 1000;
`
