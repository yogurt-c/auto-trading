import { useState } from 'react'
import styled from '@emotion/styled'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as Tabs from '@radix-ui/react-tabs'
import * as Switch from '@radix-ui/react-switch'
import * as Select from '@radix-ui/react-select'
import { strategiesApi, tradingApi, schedulerApi, settingsApi } from '../api/endpoints'
import MetricCard from '../components/MetricCard'
import DataTable from '../components/DataTable'
import type { Column } from '../components/DataTable'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import MarkdownContent from '../components/MarkdownContent'
import type { Strategy, TradeLog, PaginatedRuns } from '../api/types'
import { colors, spacing, fontSize, radius, shadow } from '../theme'

const INTERVAL_OPTIONS = ['5', '10', '15', '30', '60', '120', '240']

const LOG_PAGE_SIZE = 10
const RUN_PAGE_SIZE = 10

const STATUS_LABEL: Record<string, string> = {
  filled: '체결',
  partially_filled: '부분체결',
  pending: '대기',
  canceled: '취소',
  rejected: '거부',
  expired: '만료',
  failed: '실패',
}

const PARAM_LABELS: Record<string, string> = {
  entry_price_drop_pct: '진입 하락',
  entry_rsi_below: 'RSI 임계값',
  take_profit_pct: '익절',
  stop_loss_pct: '손절',
  sell_ratio: '매도 비율',
  dca_amount_usd: 'DCA 금액',
  dca_frequency_days: 'DCA 주기',
  max_position_usd: '최대 포지션',
}

function formatParamValue(key: string, value: unknown): string {
  if (value == null) return ''
  const n = Number(value)
  if (key.endsWith('_pct')) return `${n}%`
  if (key.endsWith('_usd')) return `$${n.toLocaleString()}`
  if (key === 'dca_frequency_days') return `${n}일`
  if (key === 'sell_ratio') return `${(n * 100).toFixed(0)}%`
  return String(value)
}

function fmt(n: number | null | undefined, decimals = 2, prefix = '') {
  if (n == null) return '—'
  return prefix + n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

const tradeLogColumns: Column<TradeLog>[] = [
  { key: 'executed_at', header: 'Time', render: r => r.executed_at.slice(0, 19).replace('T', ' ') },
  { key: 'symbol', header: 'Symbol' },
  { key: 'action', header: 'Action' },
  { key: 'quantity', header: 'Qty', align: 'right' },
  { key: 'price', header: 'Price', align: 'right', render: r => fmt(r.price, 2, '$') },
  { key: 'status', header: 'Status', render: r => <StatusBadge status={r.status} label={STATUS_LABEL[r.status] ?? r.status} /> },
  { key: 'error_message', header: 'Error', render: r => r.error_message ?? '' },
]

function formatDuration(startedAt: string, finishedAt: string | null): string {
  if (!finishedAt) return '실행 중'
  const s = Math.floor(
    (new Date(finishedAt).getTime() - new Date(startedAt).getTime()) / 1000
  )
  return s < 60 ? `${s}초` : `${Math.floor(s / 60)}분 ${s % 60}초`
}

export default function AutoTrading() {
  const qc = useQueryClient()
  const [expandedStrategy, setExpandedStrategy] = useState<number | null>(null)
  const [expandedRun, setExpandedRun] = useState<number | null>(null)
  const [logPage, setLogPage] = useState(1)
  const [runPage, setRunPage] = useState(1)

  const { data: strategies } = useQuery({ queryKey: ['strategies'], queryFn: strategiesApi.list })
  const { data: account } = useQuery({ queryKey: ['account'], queryFn: tradingApi.account })
  const { data: logsData } = useQuery({
    queryKey: ['tradeLogs', logPage],
    queryFn: () => tradingApi.logs(LOG_PAGE_SIZE, (logPage - 1) * LOG_PAGE_SIZE),
    placeholderData: (prev) => prev,
  })
  const { data: schedulerStatus } = useQuery({ queryKey: ['schedulerStatus'], queryFn: schedulerApi.status })
  const { data: runsData } = useQuery<PaginatedRuns>({
    queryKey: ['schedulerRuns', runPage],
    queryFn: () => schedulerApi.runs(RUN_PAGE_SIZE, (runPage - 1) * RUN_PAGE_SIZE),
    placeholderData: (prev) => prev,
  })
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: settingsApi.getAll })

  const updateStrategyMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: Strategy['status'] }) =>
      strategiesApi.updateStatus(id, status),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['strategies'] }),
  })

  const triggerMutation = useMutation({
    mutationFn: schedulerApi.trigger,
    onSuccess: () => {
      setRunPage(1)
      setLogPage(1)
      void qc.invalidateQueries({ queryKey: ['schedulerRuns'] })
      void qc.invalidateQueries({ queryKey: ['tradeLogs'] })
    },
  })

  const saveIntervalMutation = useMutation({
    mutationFn: (v: string) => settingsApi.set('scheduler_interval_minutes', v),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['settings'] }),
  })

  const saveEnabledMutation = useMutation({
    mutationFn: (v: string) => settingsApi.set('scheduler_enabled', v),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['settings'] }),
  })

  const active = (strategies ?? []).filter(s => s.status === 'active')
  const paused = (strategies ?? []).filter(s => s.status === 'paused')
  const completed = (strategies ?? []).filter(s => s.status === 'completed')

  const schedulerEnabled = settings?.['scheduler_enabled'] === 'true'
  const currentInterval = settings?.['scheduler_interval_minutes'] ?? '30'

  return (
    <Page>
      <PageTitle>Auto Trading</PageTitle>

      {/* 계좌 메트릭 */}
      <MetricGrid>
        <MetricCard title="Portfolio Value" value={fmt(account?.portfolio_value, 2, '$')} />
        <MetricCard title="Buying Power" value={fmt(account?.buying_power, 2, '$')} />
        <MetricCard title="Cash" value={fmt(account?.cash, 2, '$')} />
        <MetricCard title="Status" value={account?.status ?? '—'} />
      </MetricGrid>

      {/* 스케줄러 컨트롤 */}
      <ControlCard>
        <ControlRow>
          <ControlLabel>
            <span>자동 매매 활성화</span>
            {schedulerStatus?.next_run && (
              <ControlHint>
                다음 실행: {schedulerStatus.next_run.slice(0, 19).replace('T', ' ')}
                {schedulerStatus.market_open != null && (
                  <MarketStatus open={schedulerStatus.market_open}>
                    &nbsp;·&nbsp;{schedulerStatus.market_open ? '장 열림' : '장 마감'}
                  </MarketStatus>
                )}
              </ControlHint>
            )}
          </ControlLabel>
          <SwitchRoot
            checked={schedulerEnabled}
            onCheckedChange={v => saveEnabledMutation.mutate(v ? 'true' : 'false')}
          >
            <SwitchThumb />
          </SwitchRoot>
        </ControlRow>

        <ControlRow>
          <ControlLabel>
            <span>스케줄러 간격</span>
          </ControlLabel>
          <Select.Root
            value={currentInterval}
            onValueChange={v => saveIntervalMutation.mutate(v)}
          >
            <SelectTrigger>
              <Select.Value />
              <Select.Icon>▾</Select.Icon>
            </SelectTrigger>
            <Select.Portal>
              <SelectContent>
                <Select.Viewport>
                  {INTERVAL_OPTIONS.map(opt => (
                    <SelectItem key={opt} value={opt}>
                      <Select.ItemText>{opt}분</Select.ItemText>
                    </SelectItem>
                  ))}
                </Select.Viewport>
              </SelectContent>
            </Select.Portal>
          </Select.Root>
        </ControlRow>

        <TriggerBtn
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending}
        >
          {triggerMutation.isPending ? '실행 중...' : '지금 실행'}
        </TriggerBtn>
      </ControlCard>

      {/* 전략 탭 */}
      <Section>
        <SectionTitle>전략</SectionTitle>
        <StyledTabs defaultValue="active">
          <TabList>
            <TabTrigger value="active">활성 ({active.length})</TabTrigger>
            <TabTrigger value="paused">일시정지 ({paused.length})</TabTrigger>
            <TabTrigger value="completed">완료 ({completed.length})</TabTrigger>
          </TabList>

          {(['active', 'paused', 'completed'] as const).map((tab, ti) => {
            const list = [active, paused, completed][ti]
            return (
              <Tabs.Content key={tab} value={tab}>
                <StrategyList>
                  {list.length === 0 ? (
                    <Empty>전략 없음</Empty>
                  ) : (
                    list.map(s => (
                      <StrategyCard key={s.id}>
                        <StrategyHeader onClick={() => setExpandedStrategy(expandedStrategy === s.id ? null : s.id)}>
                          <StrategyInfo>
                            <StrategyName>{s.name}</StrategyName>
                            <StrategyMeta>{s.symbol} · {s.strategy_type}</StrategyMeta>
                            {s.description && <StrategyDescription>{s.description}</StrategyDescription>}
                          </StrategyInfo>
                          <StrategyActions onClick={e => e.stopPropagation()}>
                            {s.status !== 'completed' && (
                              <ActionBtn
                                onClick={() =>
                                  updateStrategyMutation.mutate({
                                    id: s.id,
                                    status: s.status === 'active' ? 'paused' : 'active',
                                  })
                                }
                              >
                                {s.status === 'active' ? '일시정지' : '활성화'}
                              </ActionBtn>
                            )}
                            <StatusBadge status={s.status} />
                          </StrategyActions>
                        </StrategyHeader>
                        {expandedStrategy === s.id && (
                          <StrategyDetail>
                            {s.last_checked_at && (
                              <DetailRow><DetailKey>마지막 평가</DetailKey><span>{s.last_checked_at.slice(0, 19).replace('T', ' ')}</span></DetailRow>
                            )}
                            <DetailRow><DetailKey>마지막 실행</DetailKey><span>{s.last_run_at?.slice(0, 19).replace('T', ' ') ?? '없음'}</span></DetailRow>
                            <DetailRow><DetailKey>생성일</DetailKey><span>{s.created_at.slice(0, 10)}</span></DetailRow>
                            {s.ai_rationale && (
                              <DetailRow><DetailKey>AI 근거</DetailKey><span>{s.ai_rationale}</span></DetailRow>
                            )}
                            <DetailRow>
                              <DetailKey>파라미터</DetailKey>
                              <ParamList>
                                {(() => {
                                  const entries = Object.entries(s.parameters).filter(([, v]) => v != null)
                                  if (entries.length === 0) return <span>없음</span>
                                  return entries.map(([k, v]) => (
                                    <ParamItem key={k}>
                                      <ParamLabel>{PARAM_LABELS[k] ?? k}</ParamLabel>
                                      <span>{formatParamValue(k, v)}</span>
                                    </ParamItem>
                                  ))
                                })()}
                              </ParamList>
                            </DetailRow>
                          </StrategyDetail>
                        )}
                      </StrategyCard>
                    ))
                  )}
                </StrategyList>
              </Tabs.Content>
            )
          })}
        </StyledTabs>
      </Section>

      {/* 스케줄러 실행 히스토리 */}
      <Section>
        <SectionTitle>스케줄러 실행 기록</SectionTitle>
        <StrategyList>
          {(runsData?.runs ?? []).length === 0 ? (
            <Empty>실행 기록 없음</Empty>
          ) : (
            (runsData?.runs ?? []).map(run => (
              <StrategyCard key={run.id}>
                <StrategyHeader onClick={() => setExpandedRun(expandedRun === run.id ? null : run.id)}>
                  <StrategyInfo>
                    <StrategyName>{run.started_at.slice(0, 19).replace('T', ' ')}</StrategyName>
                    <StrategyMeta>
                      {run.strategies_run}개 전략 · {run.trades_executed}회 거래 · {formatDuration(run.started_at, run.finished_at)}
                    </StrategyMeta>
                  </StrategyInfo>
                  <StrategyActions onClick={e => e.stopPropagation()}>
                    <StatusBadge status={run.status} />
                  </StrategyActions>
                </StrategyHeader>
                {expandedRun === run.id && (
                  <StrategyDetail>
                    {run.finished_at && (
                      <DetailRow>
                        <DetailKey>종료 시각</DetailKey>
                        <span>{run.finished_at.slice(0, 19).replace('T', ' ')}</span>
                      </DetailRow>
                    )}
                    <DetailRow>
                      <DetailKey>소요 시간</DetailKey>
                      <span>{formatDuration(run.started_at, run.finished_at)}</span>
                    </DetailRow>
                    {run.summary && (
                      <DetailRow style={{ flexDirection: 'column', gap: spacing.xs }}>
                        <DetailKey>AI 요약</DetailKey>
                        <MarkdownContent>{run.summary}</MarkdownContent>
                      </DetailRow>
                    )}
                    {run.error_message && (
                      <DetailRow>
                        <DetailKey>오류</DetailKey>
                        <RunError>{run.error_message}</RunError>
                      </DetailRow>
                    )}
                  </StrategyDetail>
                )}
              </StrategyCard>
            ))
          )}
        </StrategyList>
        <Pagination
          page={runPage}
          totalPages={Math.ceil((runsData?.total ?? 0) / RUN_PAGE_SIZE)}
          onPageChange={p => { setExpandedRun(null); setRunPage(p) }}
        />
      </Section>

      {/* 거래 로그 */}
      <Section>
        <SectionTitle>거래 로그</SectionTitle>
        <DataTable<TradeLog>
          columns={tradeLogColumns}
          data={logsData?.logs ?? []}
          emptyMessage="거래 로그 없음"
        />
        <Pagination
          page={logPage}
          totalPages={Math.ceil((logsData?.total ?? 0) / LOG_PAGE_SIZE)}
          onPageChange={setLogPage}
        />
      </Section>
    </Page>
  )
}

const Page = styled.div``

const PageTitle = styled.h1`
  font-size: ${fontSize.xl};
  font-weight: 700;
  margin: 0 0 ${spacing.xl};
  color: ${colors.text};
`

const MetricGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: ${spacing.md};
  margin-bottom: ${spacing.xl};
`

const ControlCard = styled.div`
  background: ${colors.bgCard};
  border: 1px solid ${colors.border};
  border-radius: ${radius.md};
  padding: ${spacing.lg};
  margin-bottom: ${spacing.xl};
  display: flex;
  flex-direction: column;
  gap: ${spacing.md};
  box-shadow: ${shadow.sm};
`

const ControlRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`

const ControlLabel = styled.div`
  font-size: ${fontSize.sm};
  color: ${colors.text};
  display: flex;
  flex-direction: column;
  gap: 2px;
`

const ControlHint = styled.span`
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

  &[data-state='checked'] {
    background: ${colors.primary};
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

const SelectTrigger = styled(Select.Trigger)`
  display: flex;
  align-items: center;
  gap: ${spacing.sm};
  background: ${colors.bgSurface};
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  padding: ${spacing.xs} ${spacing.md};
  color: ${colors.text};
  font-size: ${fontSize.sm};
  cursor: pointer;
  outline: none;

  &:hover { border-color: ${colors.primary}; }
`

const SelectContent = styled(Select.Content)`
  background: ${colors.bgSurface};
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  padding: 4px;
  z-index: 100;
  box-shadow: ${shadow.md};
`

const SelectItem = styled(Select.Item)`
  padding: ${spacing.xs} ${spacing.md};
  font-size: ${fontSize.sm};
  color: ${colors.text};
  cursor: pointer;
  border-radius: 4px;
  outline: none;

  &[data-highlighted] {
    background: ${colors.bgHover};
    color: ${colors.primary};
  }
`

const TriggerBtn = styled.button`
  background: ${colors.primary};
  color: white;
  border: none;
  border-radius: ${radius.sm};
  padding: ${spacing.sm} ${spacing.xl};
  font-size: ${fontSize.sm};
  font-weight: 600;
  cursor: pointer;
  align-self: flex-start;
  transition: background 0.15s;

  &:hover:not(:disabled) { background: ${colors.primaryHover}; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`

const Section = styled.div`
  margin-bottom: ${spacing.xl};
`

const SectionTitle = styled.h2`
  font-size: ${fontSize.md};
  font-weight: 600;
  color: ${colors.text};
  margin: 0 0 ${spacing.md};
`

const StyledTabs = styled(Tabs.Root)``

const TabList = styled(Tabs.List)`
  display: flex;
  border-bottom: 1px solid ${colors.border};
  margin-bottom: ${spacing.lg};
`

const TabTrigger = styled(Tabs.Trigger)`
  padding: ${spacing.sm} ${spacing.lg};
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: ${colors.textMuted};
  font-size: ${fontSize.sm};
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: -1px;

  &[data-state='active'] {
    color: ${colors.primary};
    border-bottom-color: ${colors.primary};
  }

  &:hover:not([data-state='active']) {
    color: ${colors.text};
  }
`

const StrategyList = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.sm};
`

const StrategyCard = styled.div`
  background: ${colors.bgCard};
  border: 1px solid ${colors.border};
  border-radius: ${radius.md};
  overflow: hidden;
`

const StrategyHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: ${spacing.md} ${spacing.lg};
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: ${colors.bgHover}; }
`

const StrategyInfo = styled.div``

const StrategyName = styled.div`
  font-size: ${fontSize.md};
  font-weight: 600;
  color: ${colors.text};
`

const StrategyMeta = styled.div`
  font-size: ${fontSize.xs};
  color: ${colors.textMuted};
  margin-top: 2px;
`

const StrategyDescription = styled.div`
  font-size: ${fontSize.xs};
  color: ${colors.textMuted};
  margin-top: 4px;
`

const StrategyActions = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.sm};
`

const ActionBtn = styled.button`
  background: transparent;
  border: 1px solid ${colors.border};
  color: ${colors.textMuted};
  border-radius: ${radius.sm};
  padding: 4px ${spacing.md};
  font-size: ${fontSize.xs};
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: ${colors.primary};
    color: ${colors.primary};
  }
`

const StrategyDetail = styled.div`
  padding: ${spacing.md} ${spacing.lg};
  border-top: 1px solid ${colors.border};
  background: ${colors.bgSurface};
  display: flex;
  flex-direction: column;
  gap: ${spacing.sm};
`

const DetailRow = styled.div`
  display: flex;
  gap: ${spacing.md};
  font-size: ${fontSize.sm};
  color: ${colors.text};
`

const DetailKey = styled.span`
  color: ${colors.textMuted};
  min-width: 100px;
`

const ParamList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`

const ParamItem = styled.div`
  display: flex;
  gap: ${spacing.md};
  font-size: ${fontSize.sm};
`

const ParamLabel = styled.span`
  color: ${colors.textMuted};
  min-width: 100px;
`

const Empty = styled.div`
  padding: ${spacing.xl};
  text-align: center;
  color: ${colors.textDim};
  font-size: ${fontSize.sm};
`

const MarketStatus = styled.span<{ open: boolean }>`
  color: ${({ open }) => (open ? colors.positive : colors.textMuted)};
`


const RunError = styled.span`
  color: ${colors.negative};
  white-space: pre-wrap;
`
