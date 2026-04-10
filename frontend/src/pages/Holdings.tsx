import styled from '@emotion/styled'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portfolioApi, tradingApi } from '../api/endpoints'
import DataTable from '../components/DataTable'
import type { Column } from '../components/DataTable'
import type { Holding, Transaction } from '../api/types'
import { colors, spacing, fontSize, radius } from '../theme'
import { fmtCurrency } from '../lib/format'

const holdingColumns: Column<Holding>[] = [
  { key: 'ticker', header: 'Ticker' },
  { key: 'market', header: 'Market' },
  { key: 'shares', header: 'Qty', align: 'right' },
  { key: 'avg_price', header: 'Avg Price', align: 'right', render: r => fmtCurrency(r.avg_price, r.currency) },
  { key: 'current_price', header: 'Current', align: 'right', render: r => r.current_price != null ? fmtCurrency(r.current_price, r.currency) : '—' },
  { key: 'market_value', header: 'Market Value', align: 'right', render: r => r.market_value != null ? fmtCurrency(r.market_value, r.currency) : '—' },
  {
    key: 'pnl',
    header: 'P&L',
    align: 'right',
    render: r => {
      if (r.pnl == null) return '—'
      const color = r.pnl >= 0 ? colors.positive : colors.negative
      return <span style={{ color }}>{fmtCurrency(r.pnl, r.currency, r.pnl >= 0)}</span>
    },
  },
  {
    key: 'pnl_pct',
    header: 'P&L %',
    align: 'right',
    render: r => {
      if (r.pnl_pct == null) return '—'
      const color = r.pnl_pct >= 0 ? colors.positive : colors.negative
      return <span style={{ color }}>{(r.pnl_pct >= 0 ? '+' : '') + r.pnl_pct.toFixed(2)}%</span>
    },
  },
]

const txColumns: Column<Transaction>[] = [
  { key: 'executed_at', header: 'Date', render: r => r.executed_at.slice(0, 10) },
  { key: 'ticker', header: 'Ticker' },
  {
    key: 'action',
    header: 'Type',
    render: r => (
      <span style={{ color: r.action === 'buy' ? colors.positive : colors.negative, fontWeight: 600 }}>
        {r.action.toUpperCase()}
      </span>
    ),
  },
  { key: 'shares', header: 'Qty', align: 'right' },
  { key: 'price', header: 'Price', align: 'right', render: r => fmtCurrency(r.price, r.currency) },
  { key: 'total', header: 'Total', align: 'right', render: r => fmtCurrency(r.total, r.currency) },
]

export default function Holdings() {
  const qc = useQueryClient()

  const { data: account } = useQuery({
    queryKey: ['account'],
    queryFn: tradingApi.account,
    staleTime: 60_000,
  })

  const { data: holdings, isLoading: holdingsLoading } = useQuery({
    queryKey: ['holdings'],
    queryFn: portfolioApi.holdings,
    staleTime: 30_000,
  })

  const { data: transactions, isLoading: txLoading, isError: txError } = useQuery({
    queryKey: ['transactions'],
    queryFn: () => portfolioApi.transactions(50),
    staleTime: 30_000,
  })

  const syncMutation = useMutation({
    mutationFn: portfolioApi.sync,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['holdings'] })
      void qc.invalidateQueries({ queryKey: ['portfolio'] })
    },
  })

  return (
    <Page>
      <Header>
        <PageTitle>Holdings</PageTitle>
        <SyncBtn
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? '동기화 중...' : 'KIS 동기화'}
        </SyncBtn>
      </Header>

      {account?.is_paper && (
        <Banner type="info">
          모의투자 모드 — 실제 자금을 사용하지 않습니다. 국내 및 해외(미국) 주식 모두 지원됩니다.
        </Banner>
      )}

      {syncMutation.isSuccess && (
        <Banner type="success">
          동기화 완료 — {syncMutation.data?.synced ?? 0}개 포지션 업데이트됨
        </Banner>
      )}
      {syncMutation.isError && (
        <Banner type="error">
          동기화 실패: {String(syncMutation.error)}
        </Banner>
      )}

      <Section>
        <SectionTitle>보유 종목 {holdingsLoading ? '(로딩 중...)' : `(${holdings?.length ?? 0})`}</SectionTitle>
        <DataTable<Holding>
          columns={holdingColumns}
          data={holdings ?? []}
          emptyMessage="보유 종목 없음"
        />
      </Section>

      <Section>
        <SectionTitle>최근 거래내역 {txLoading ? '(로딩 중...)' : `(${transactions?.length ?? 0})`}</SectionTitle>
        {txError ? (
          <Banner type="error">KIS 주문 이력 조회 실패 — Settings 페이지에서 API 키를 확인해 주세요.</Banner>
        ) : (
          <DataTable<Transaction>
            columns={txColumns}
            data={transactions ?? []}
            emptyMessage="거래 내역 없음"
          />
        )}
      </Section>
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

const SyncBtn = styled.button`
  background: ${colors.primary};
  color: white;
  border: none;
  border-radius: ${radius.sm};
  padding: ${spacing.sm} ${spacing.lg};
  font-size: ${fontSize.sm};
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;

  &:hover:not(:disabled) { background: ${colors.primaryHover}; }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
`

const bannerColor = {
  success: colors.success,
  error: colors.danger,
  info: colors.primary,
}

const Banner = styled.div<{ type: 'success' | 'error' | 'info' }>`
  padding: ${spacing.md};
  border-radius: ${radius.sm};
  font-size: ${fontSize.sm};
  margin-bottom: ${spacing.lg};
  background: ${({ type }) => bannerColor[type]}22;
  border: 1px solid ${({ type }) => bannerColor[type]}44;
  color: ${({ type }) => bannerColor[type]};
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
