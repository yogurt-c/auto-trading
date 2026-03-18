import { useState } from 'react'
import styled from '@emotion/styled'
import { useQuery } from '@tanstack/react-query'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { portfolioApi } from '../api/endpoints'
import MetricCard from '../components/MetricCard'
import { colors, spacing, fontSize, radius, shadow } from '../theme'

const CHART_COLORS = [
  '#6c7cff', '#34d399', '#fbbf24', '#f87171', '#a78bfa',
  '#38bdf8', '#fb923c', '#4ade80', '#f472b6', '#94a3b8',
]

function fmt(n: number | null | undefined, decimals = 2, prefix = '') {
  if (n == null) return '—'
  return prefix + n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export default function Dashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['portfolio'],
    queryFn: portfolioApi.get,
    refetchInterval: 60_000,
  })

  const [manualPrices, setManualPrices] = useState<Record<string, string>>({})

  const holdings = data?.holdings ?? []
  const summary = data?.summary
  const fetchErrors = data?.fetch_errors ?? []

  // 수동 가격 재계산용
  const effectiveHoldings = holdings.map(h => {
    const manual = manualPrices[h.symbol]
    if (!manual || isNaN(parseFloat(manual))) return h
    const price = parseFloat(manual)
    const mv = price * h.quantity
    const pnl = mv - h.avg_cost * h.quantity
    const pnlPct = h.avg_cost > 0 ? (pnl / (h.avg_cost * h.quantity)) * 100 : 0
    return { ...h, current_price: price, market_value: mv, unrealized_pnl: pnl, unrealized_pnl_pct: pnlPct }
  })

  const pieData = effectiveHoldings
    .filter(h => h.market_value != null && h.market_value > 0)
    .map(h => ({ name: h.symbol, value: h.market_value! }))

  const barData = effectiveHoldings
    .filter(h => h.unrealized_pnl_pct != null)
    .map(h => ({ symbol: h.symbol, return: parseFloat((h.unrealized_pnl_pct ?? 0).toFixed(2)) }))
    .sort((a, b) => b.return - a.return)

  return (
    <Page>
      <Header>
        <PageTitle>Dashboard</PageTitle>
        <RefreshBtn onClick={() => void refetch()} disabled={isLoading}>
          {isLoading ? '로딩 중...' : '새로고침'}
        </RefreshBtn>
      </Header>

      {error && <ErrorBanner>데이터 로딩 실패: {String(error)}</ErrorBanner>}

      {/* 요약 메트릭 */}
      <MetricGrid>
        <MetricCard
          title="Market Value"
          value={fmt(summary?.total_market_value, 2, '$')}
        />
        <MetricCard
          title="Cost Basis"
          value={fmt(summary?.total_cost_basis, 2, '$')}
        />
        <MetricCard
          title="Unrealized P&L"
          value={fmt(summary?.total_unrealized_pnl, 2, summary && summary.total_unrealized_pnl >= 0 ? '+$' : '$')}
          delta={summary?.total_unrealized_pnl_pct ?? null}
        />
        <MetricCard
          title="보유 종목"
          value={summary?.holding_count ?? '—'}
        />
      </MetricGrid>

      {/* 가격 미수신 종목 수동 입력 */}
      {fetchErrors.length > 0 && (
        <Section>
          <SectionTitle>수동 가격 입력 필요</SectionTitle>
          <ManualGrid>
            {fetchErrors.map(sym => (
              <ManualField key={sym}>
                <ManualLabel>{sym}</ManualLabel>
                <ManualInput
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="현재가 입력"
                  value={manualPrices[sym] ?? ''}
                  onChange={e => setManualPrices(p => ({ ...p, [sym]: e.target.value }))}
                />
              </ManualField>
            ))}
          </ManualGrid>
        </Section>
      )}

      {/* 차트 */}
      <ChartGrid>
        <ChartCard>
          <SectionTitle>자산 배분</SectionTitle>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <Empty>보유 종목 없음</Empty>
          )}
        </ChartCard>

        <ChartCard>
          <SectionTitle>종목별 수익률 (%)</SectionTitle>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={barData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis dataKey="symbol" tick={{ fill: colors.textMuted, fontSize: 12 }} />
                <YAxis tick={{ fill: colors.textMuted, fontSize: 12 }} unit="%" />
                <Tooltip formatter={(v: number) => `${v.toFixed(2)}%`} />
                <Bar
                  dataKey="return"
                  radius={[4, 4, 0, 0]}
                  fill={colors.primary}
                  label={false}
                >
                  {barData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={entry.return >= 0 ? colors.positive : colors.negative}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty>수익률 데이터 없음</Empty>
          )}
        </ChartCard>
      </ChartGrid>
    </Page>
  )
}

const Page = styled.div``

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: ${spacing.xl};
`

const PageTitle = styled.h1`
  font-size: ${fontSize.xl};
  font-weight: 700;
  margin: 0;
  color: ${colors.text};
`

const RefreshBtn = styled.button`
  background: ${colors.bgSurface};
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  color: ${colors.textMuted};
  padding: ${spacing.xs} ${spacing.md};
  font-size: ${fontSize.sm};
  cursor: pointer;
  transition: all 0.15s;

  &:hover:not(:disabled) {
    border-color: ${colors.primary};
    color: ${colors.primary};
  }

  &:disabled { opacity: 0.5; cursor: not-allowed; }
`

const ErrorBanner = styled.div`
  background: ${colors.danger}22;
  border: 1px solid ${colors.danger}44;
  color: ${colors.danger};
  padding: ${spacing.md};
  border-radius: ${radius.sm};
  font-size: ${fontSize.sm};
  margin-bottom: ${spacing.lg};
`

const MetricGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: ${spacing.md};
  margin-bottom: ${spacing.xl};
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

const ManualGrid = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${spacing.md};
`

const ManualField = styled.div`
  display: flex;
  align-items: center;
  gap: ${spacing.sm};
`

const ManualLabel = styled.span`
  font-size: ${fontSize.sm};
  font-weight: 600;
  color: ${colors.text};
  min-width: 60px;
`

const ManualInput = styled.input`
  background: ${colors.bgSurface};
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  padding: 6px ${spacing.md};
  color: ${colors.text};
  font-size: ${fontSize.sm};
  width: 120px;
  outline: none;

  &:focus { border-color: ${colors.primary}; }
`

const ChartGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: ${spacing.lg};
`

const ChartCard = styled.div`
  background: ${colors.bgCard};
  border: 1px solid ${colors.border};
  border-radius: ${radius.md};
  padding: ${spacing.lg};
  box-shadow: ${shadow.sm};
`

const Empty = styled.div`
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${colors.textDim};
  font-size: ${fontSize.sm};
`
