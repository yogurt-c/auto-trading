import { useState } from 'react'
import styled from '@emotion/styled'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi } from '../api/endpoints'
import { colors, spacing, fontSize, radius, shadow } from '../theme'

const SETTING_FIELDS = [
  { key: 'ALPACA_API_KEY', label: 'Alpaca API Key', type: 'password' },
  { key: 'ALPACA_SECRET_KEY', label: 'Alpaca Secret Key', type: 'password' },
  { key: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key', type: 'password' },
]

export default function Settings() {
  const qc = useQueryClient()
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.getAll,
  })

  const [form, setForm] = useState<Record<string, string>>({})
  const [toast, setToast] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      settingsApi.set(key, value),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['settings'] })
      void qc.invalidateQueries({ queryKey: ['settingsStatus'] })
      setToast('저장되었습니다')
      setTimeout(() => setToast(null), 2500)
    },
  })

  const handleSave = async () => {
    for (const [key, value] of Object.entries(form)) {
      if (value.trim()) {
        await mutation.mutateAsync({ key, value: value.trim() })
      }
    }
  }

  const get = (key: string) => form[key] ?? ''

  return (
    <Page>
      <PageTitle>Settings</PageTitle>
      <Card>
        <Section>
          <SectionTitle>API Keys</SectionTitle>
          {SETTING_FIELDS.map(field => (
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
