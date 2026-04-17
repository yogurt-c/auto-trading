import { useState } from 'react'
import styled from '@emotion/styled'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { performanceApi } from '../api/endpoints'
import MetricCard from '../components/MetricCard'
import { colors, spacing, fontSize, radius, shadow } from '../theme'
import { fmt, fmtCurrency } from '../lib/format'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function offsetDate(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}


// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Preset = '7D' | '30D' | '90D' | '1Y' | 'All' | 'custom'

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Performance() {
  const [preset, setPreset] = useState<Preset>('30D')
  const [groupBy, setGroupBy] = useState<'day' | 'month'>('day')
  const [startDate, setStartDate] = useState(() => offsetDate(-30))
  const [endDate, setEndDate] = useState(() => today())

  function applyPreset(p: Preset) {
    setPreset(p)
    const t = today()
    if (p === '7D')  { setStartDate(offsetDate(-7));   setEndDate(t); setGroupBy('day') }
    if (p === '30D') { setStartDate(offsetDate(-30));  setEndDate(t); setGroupBy('day') }
    if (p === '90D') { setStartDate(offsetDate(-90));  setEndDate(t); setGroupBy('day') }
    if (p === '1Y')  { setStartDate(offsetDate(-365)); setEndDate(t); setGroupBy('month') }
    if (p === 'All') { setStartDate('2000-01-01');      setEndDate(t); setGroupBy('month') }
  }

  const enabled = !!startDate && !!endDate && startDate <= endDate

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['performance', startDate, endDate, groupBy],
    queryFn: () => performanceApi.get({ start_date: startDate, end_date: endDate, group_by: groupBy }),
    enabled,
    staleTime: 60_000,
  })

  const krSummary = data?.by_currency.find(c => c.currency === 'KRW')
  const usSummary = data?.by_currency.find(c => c.currency === 'USD')
  const periodKrData = (data?.by_period ?? []).filter(p => p.currency === 'KRW')
  const periodUsData = (data?.by_period ?? []).filter(p => p.currency === 'USD')

  return (
    <Page>
      {/* ── Header ── */}
      <Header>
        <PageTitle>Performance</PageTitle>
        <Controls>
          <PresetGroup>
            {(['7D', '30D', '90D', '1Y', 'All'] as Preset[]).map(p => (
              <PresetBtn key={p} active={preset === p} onClick={() => applyPreset(p)}>
                {p}
              </PresetBtn>
            ))}
          </PresetGroup>
          <GroupByToggle>
            <ToggleBtn active={groupBy === 'day'} onClick={() => { setGroupBy('day'); setPreset('custom') }}>
              Day
            </ToggleBtn>
            <ToggleBtn active={groupBy === 'month'} onClick={() => { setGroupBy('month'); setPreset('custom') }}>
              Month
            </ToggleBtn>
          </GroupByToggle>
          <DateRange>
            <DateInput
              type="date"
              value={startDate}
              onChange={e => { setStartDate(e.target.value); setPreset('custom') }}
            />
            <DateSep>~</DateSep>
            <DateInput
              type="date"
              value={endDate}
              onChange={e => { setEndDate(e.target.value); setPreset('custom') }}
            />
          </DateRange>
          <RefreshBtn onClick={() => void refetch()} disabled={isLoading}>
            {isLoading ? '로딩 중...' : '새로고침'}
          </RefreshBtn>
        </Controls>
      </Header>

      {error && <ErrorMsg>데이터를 불러오는 중 오류가 발생했습니다.</ErrorMsg>}
      {!enabled && <ErrorMsg>start_date는 end_date보다 이전이어야 합니다.</ErrorMsg>}

      {/* ── Summary Metrics ── */}
      <SectionLabel>국내 (KRW)</SectionLabel>
      <MetricsRow>
        <MetricCard
          title="Realized P&L (KRW)"
          value={krSummary ? fmtCurrency(krSummary.total_realized_pnl, 'KRW', krSummary.total_realized_pnl >= 0) : '—'}
          subtitle={krSummary ? (krSummary.total_realized_pnl >= 0 ? '수익' : '손실') : undefined}
        />
        <MetricCard title="거래 수" value={krSummary ? String(krSummary.total_trade_count) : '—'} />
        <MetricCard title="승률" value={krSummary ? `${fmt(krSummary.win_rate, 1)}%` : '—'} />
        <MetricCard
          title="이익 / 전체"
          value={krSummary ? `${krSummary.win_count} / ${krSummary.total_trade_count}` : '—'}
        />
      </MetricsRow>

      <SectionLabel>해외 (USD)</SectionLabel>
      <MetricsRow>
        <MetricCard
          title="Realized P&L (USD)"
          value={usSummary ? fmtCurrency(usSummary.total_realized_pnl, 'USD', usSummary.total_realized_pnl >= 0) : '—'}
          subtitle={usSummary ? (usSummary.total_realized_pnl >= 0 ? '수익' : '손실') : undefined}
        />
        <MetricCard title="거래 수" value={usSummary ? String(usSummary.total_trade_count) : '—'} />
        <MetricCard title="승률" value={usSummary ? `${fmt(usSummary.win_rate, 1)}%` : '—'} />
        <MetricCard
          title="이익 / 전체"
          value={usSummary ? `${usSummary.win_count} / ${usSummary.total_trade_count}` : '—'}
        />
      </MetricsRow>

      {/* ── Period P&L Bar Charts (KRW / USD) ── */}
      <ChartsRow>
          {periodKrData.length > 0 ? (
            <Card>
              <CardTitle>기간별 손익 (KRW)</CardTitle>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={periodKrData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                  <XAxis dataKey="period" tick={{ fill: colors.textMuted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.border }} />
                  <YAxis tick={{ fill: colors.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={v => v.toLocaleString()} />
                  <Tooltip
                    contentStyle={{ background: colors.bgCard, border: `1px solid ${colors.border}`, borderRadius: radius.md }}
                    labelStyle={{ color: colors.text }}
                    formatter={(value: number) => [fmtCurrency(value, 'KRW'), 'Realized P&L']}
                  />
                  <Bar dataKey="realized_pnl" radius={[4, 4, 0, 0]}>
                    {periodKrData.map((entry, i) => (
                      <Cell key={i} fill={entry.realized_pnl >= 0 ? colors.positive : colors.negative} fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <Card>
              <CardTitle>기간별 손익 (KRW)</CardTitle>
              <EmptyMsg>데이터 없음</EmptyMsg>
            </Card>
          )}
          {periodUsData.length > 0 ? (
            <Card>
              <CardTitle>기간별 손익 (USD)</CardTitle>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={periodUsData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                  <XAxis dataKey="period" tick={{ fill: colors.textMuted, fontSize: 11 }} tickLine={false} axisLine={{ stroke: colors.border }} />
                  <YAxis tick={{ fill: colors.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={v => v.toLocaleString()} />
                  <Tooltip
                    contentStyle={{ background: colors.bgCard, border: `1px solid ${colors.border}`, borderRadius: radius.md }}
                    labelStyle={{ color: colors.text }}
                    formatter={(value: number) => [fmtCurrency(value, 'USD'), 'Realized P&L']}
                  />
                  <Bar dataKey="realized_pnl" radius={[4, 4, 0, 0]}>
                    {periodUsData.map((entry, i) => (
                      <Cell key={i} fill={entry.realized_pnl >= 0 ? colors.positive : colors.negative} fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          ) : (
            <Card>
              <CardTitle>기간별 손익 (USD)</CardTitle>
              <EmptyMsg>데이터 없음</EmptyMsg>
            </Card>
          )}
        </ChartsRow>

      {/* ── Bottom: Strategy Table + Trade History ── */}
      <BottomGrid>
        {/* 전략별 성과 */}
        <Card>
          <CardTitle>전략별 성과</CardTitle>
          {data && data.by_strategy.length > 0 ? (
            <Table>
              <thead>
                <tr>
                  <Th>전략</Th>
                  <Th>통화</Th>
                  <Th align="right">Realized P&L</Th>
                  <Th align="right">거래 수</Th>
                  <Th align="right">승률</Th>
                </tr>
              </thead>
              <tbody>
                {data.by_strategy.map((s, i) => (
                  <tr key={i}>
                    <Td>{s.strategy_name}</Td>
                    <Td><CurrencyBadge krw={s.currency === 'KRW'}>{s.currency}</CurrencyBadge></Td>
                    <Td align="right" positive={s.realized_pnl >= 0}>
                      {fmtCurrency(s.realized_pnl, s.currency, s.realized_pnl >= 0)}
                    </Td>
                    <Td align="right">{s.trade_count}</Td>
                    <Td align="right" positive={s.win_rate >= 50}>
                      {fmt(s.win_rate, 1)}%
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <EmptyMsg>데이터 없음</EmptyMsg>
          )}
        </Card>

        {/* 거래 내역 */}
        <Card>
          <CardTitle>거래 내역</CardTitle>
          {data && data.trades.length > 0 ? (
            <Table>
              <thead>
                <tr>
                  <Th>체결일</Th>
                  <Th>Ticker</Th>
                  <Th align="right">Qty</Th>
                  <Th align="right">매도가</Th>
                  <Th align="right">평균단가</Th>
                  <Th align="right">Realized P&L</Th>
                  <Th>전략</Th>
                </tr>
              </thead>
              <tbody>
                {data.trades.map(t => (
                  <tr key={t.id}>
                    <Td>{t.executed_at.slice(0, 10)}</Td>
                    <Td><TickerBadge>{t.ticker}</TickerBadge></Td>
                    <Td align="right">{t.qty}</Td>
                    <Td align="right">{fmtCurrency(t.sell_price, t.currency)}</Td>
                    <Td align="right">{fmtCurrency(t.avg_cost, t.currency)}</Td>
                    <Td align="right" positive={t.realized_pnl >= 0}>
                      {fmtCurrency(t.realized_pnl, t.currency, t.realized_pnl >= 0)}
                      <PctBadge positive={t.realized_pnl >= 0}>
                        ({t.realized_pnl >= 0 ? '+' : ''}{fmt(t.realized_pnl_pct, 1)}%)
                      </PctBadge>
                    </Td>
                    <Td>{t.strategy_name ?? '—'}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <EmptyMsg>데이터 없음</EmptyMsg>
          )}
        </Card>
      </BottomGrid>
    </Page>
  )
}

// ---------------------------------------------------------------------------
// Styled components
// ---------------------------------------------------------------------------

const Page = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${spacing.lg};
`

const Header = styled.div`
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: ${spacing.md};
  justify-content: space-between;
`

const PageTitle = styled.h1`
  font-size: ${fontSize.xl};
  font-weight: 700;
  color: ${colors.text};
  margin: 0;
`

const Controls = styled.div`
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: ${spacing.sm};
`

const PresetGroup = styled.div`
  display: flex;
  gap: 4px;
`

const PresetBtn = styled.button<{ active?: boolean }>`
  padding: 6px 12px;
  border-radius: ${radius.sm};
  border: 1px solid ${({ active }) => active ? colors.primary : colors.border};
  background: ${({ active }) => active ? colors.primary + '22' : 'transparent'};
  color: ${({ active }) => active ? colors.primary : colors.textMuted};
  font-size: ${fontSize.sm};
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: ${colors.primary};
    color: ${colors.primary};
  }
`

const GroupByToggle = styled.div`
  display: flex;
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  overflow: hidden;
`

const ToggleBtn = styled.button<{ active?: boolean }>`
  padding: 6px 12px;
  border: none;
  background: ${({ active }) => active ? colors.primary : 'transparent'};
  color: ${({ active }) => active ? '#fff' : colors.textMuted};
  font-size: ${fontSize.sm};
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: ${({ active }) => active ? colors.primary : colors.bgHover};
    color: ${colors.text};
  }
`

const DateRange = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.xs};
`

const DateInput = styled.input`
  background: ${colors.bgSurface};
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  color: ${colors.text};
  font-size: ${fontSize.sm};
  padding: 5px 10px;
  outline: none;

  &:focus {
    border-color: ${colors.primary};
  }
`

const DateSep = styled.span`
  color: ${colors.textMuted};
  font-size: ${fontSize.sm};
`

const RefreshBtn = styled.button`
  padding: 6px 14px;
  border-radius: ${radius.sm};
  border: 1px solid ${colors.border};
  background: transparent;
  color: ${colors.textMuted};
  font-size: ${fontSize.sm};
  cursor: pointer;
  transition: all 0.15s;

  &:hover:not(:disabled) {
    border-color: ${colors.primary};
    color: ${colors.primary};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`

const ErrorMsg = styled.div`
  color: ${colors.negative};
  font-size: ${fontSize.sm};
  padding: ${spacing.sm} ${spacing.md};
  background: ${colors.negative}18;
  border-radius: ${radius.md};
  border: 1px solid ${colors.negative}44;
`

const SectionLabel = styled.h2`
  font-size: ${fontSize.sm};
  font-weight: 600;
  color: ${colors.textMuted};
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
`

const MetricsRow = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: ${spacing.md};
`

const Card = styled.div`
  background: ${colors.bgCard};
  border: 1px solid ${colors.border};
  border-radius: ${radius.lg};
  padding: ${spacing.lg};
  box-shadow: ${shadow.sm};
`

const CardTitle = styled.h2`
  font-size: ${fontSize.md};
  font-weight: 600;
  color: ${colors.text};
  margin: 0 0 ${spacing.md} 0;
`

const ChartsRow = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: ${spacing.md};
`

const BottomGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: ${spacing.md};

  @media (max-width: 1100px) {
    grid-template-columns: 1fr;
  }
`

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${fontSize.sm};
`

const Th = styled.th<{ align?: string }>`
  text-align: ${({ align }) => align ?? 'left'};
  color: ${colors.textMuted};
  font-weight: 500;
  padding: ${spacing.sm};
  border-bottom: 1px solid ${colors.border};
  white-space: nowrap;
`

const Td = styled.td<{ align?: string; positive?: boolean }>`
  text-align: ${({ align }) => align ?? 'left'};
  color: ${({ positive }) =>
    positive === true ? colors.positive :
    positive === false ? colors.negative :
    colors.text};
  padding: ${spacing.sm};
  border-bottom: 1px solid ${colors.border}44;
  vertical-align: middle;
`

const TickerBadge = styled.span`
  background: ${colors.primary}22;
  color: ${colors.primary};
  border-radius: ${radius.sm};
  padding: 2px 7px;
  font-size: ${fontSize.xs};
  font-weight: 600;
`

const CurrencyBadge = styled.span<{ krw?: boolean }>`
  background: ${({ krw }) => krw ? '#3b82f622' : '#8b5cf622'};
  color: ${({ krw }) => krw ? '#3b82f6' : '#8b5cf6'};
  border-radius: ${radius.sm};
  padding: 2px 7px;
  font-size: ${fontSize.xs};
  font-weight: 600;
`

const PctBadge = styled.span<{ positive?: boolean }>`
  margin-left: 4px;
  font-size: ${fontSize.xs};
  color: ${({ positive }) => positive ? colors.positive : colors.negative};
  opacity: 0.8;
`

const EmptyMsg = styled.div`
  color: ${colors.textMuted};
  font-size: ${fontSize.sm};
  padding: ${spacing.lg} 0;
  text-align: center;
`
