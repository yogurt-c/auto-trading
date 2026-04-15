import styled from '@emotion/styled'
import { useQuery } from '@tanstack/react-query'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { portfolioApi } from '../api/endpoints'
import MetricCard from '../components/MetricCard'
import { colors, spacing, fontSize, radius, shadow } from '../theme'
import { fmtCurrency } from '../lib/format'

const CHART_COLORS = [
  '#6c7cff', '#34d399', '#fbbf24', '#f87171', '#a78bfa',
  '#38bdf8', '#fb923c', '#4ade80', '#f472b6', '#94a3b8',
]

export default function Dashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['portfolio'],
    queryFn: portfolioApi.get,
    refetchInterval: 60_000,
  })

  const holdings = data?.holdings ?? []
  const summary = data?.summary

  // 국내 / 해외 분리
  const krHoldings = holdings.filter(h => h.market === 'KR')
  const usHoldings = holdings.filter(h => h.market !== 'KR')

  const krPieData = krHoldings
    .filter(h => h.market_value != null && h.market_value > 0)
    .map(h => ({ name: h.ticker, value: h.market_value! }))

  const usPieData = usHoldings
    .filter(h => h.market_value != null && h.market_value > 0)
    .map(h => ({ name: h.ticker, value: h.market_value! }))

  const barData = holdings
    .filter(h => h.pnl_pct != null)
    .map(h => ({ symbol: h.ticker, return: parseFloat((h.pnl_pct ?? 0).toFixed(2)) }))
    .sort((a, b) => b.return - a.return)

  return (
    <Page>
      <Header>
        <PageTitle>Dashboard</PageTitle>
        <RefreshBtn onClick={() => void refetch()} disabled={isLoading}>
          {isLoading ? '로딩 중...' : '새로고침'}
        </RefreshBtn>
      </Header>

      {error && (
        <ErrorBanner>
          데이터 로딩 실패: {(error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '네트워크 오류가 발생했습니다'}
        </ErrorBanner>
      )}

      {/* 국내 포트폴리오 (KRW) */}
      <Section>
        <SectionTitle>국내 포트폴리오 (KRW)</SectionTitle>
        <MetricGrid>
          <MetricCard
            title="Market Value"
            value={summary?.kr ? fmtCurrency(summary.kr.total_market_value, 'KRW') : '—'}
          />
          <MetricCard
            title="Cost Basis"
            value={summary?.kr ? fmtCurrency(summary.kr.total_cost_basis, 'KRW') : '—'}
          />
          <MetricCard
            title="Unrealized P&L"
            value={summary?.kr ? fmtCurrency(summary.kr.total_pnl, 'KRW', summary.kr.total_pnl >= 0) : '—'}
            delta={summary?.kr?.total_pnl_pct}
          />
          <MetricCard
            title="보유 종목"
            value={summary?.kr?.holding_count ?? '—'}
          />
        </MetricGrid>
      </Section>

      {/* 해외 포트폴리오 (USD) */}
      <Section>
        <SectionTitle>해외 포트폴리오 (USD)</SectionTitle>
        <MetricGrid>
          <MetricCard
            title="Market Value"
            value={summary?.us ? fmtCurrency(summary.us.total_market_value, 'USD') : '—'}
          />
          <MetricCard
            title="Cost Basis"
            value={summary?.us ? fmtCurrency(summary.us.total_cost_basis, 'USD') : '—'}
          />
          <MetricCard
            title="Unrealized P&L"
            value={summary?.us ? fmtCurrency(summary.us.total_pnl, 'USD', summary.us.total_pnl >= 0) : '—'}
            delta={summary?.us?.total_pnl_pct}
          />
          <MetricCard
            title="보유 종목"
            value={summary?.us?.holding_count ?? '—'}
          />
        </MetricGrid>
      </Section>

      {/* 차트 */}
      <ChartGrid>
        {krPieData.length > 0 && (
          <ChartCard>
            <SectionTitle>국내 자산 배분</SectionTitle>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={krPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {krPieData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => fmtCurrency(v, 'KRW')} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {usPieData.length > 0 && (
          <ChartCard>
            <SectionTitle>해외 자산 배분</SectionTitle>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={usPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                  {usPieData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => fmtCurrency(v, 'USD')} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {barData.length > 0 && (
          <ChartCard>
            <SectionTitle>종목별 수익률 (%)</SectionTitle>
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
          </ChartCard>
        )}
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

const Section = styled.div`
  margin-bottom: ${spacing.xl};
`

const SectionTitle = styled.h2`
  font-size: ${fontSize.md};
  font-weight: 600;
  color: ${colors.text};
  margin: 0 0 ${spacing.md};
`

const MetricGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: ${spacing.md};
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
