import styled from '@emotion/styled'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portfolioApi } from '../api/endpoints'
import DataTable from '../components/DataTable'
import type { Column } from '../components/DataTable'
import type { Holding, Transaction } from '../api/types'
import { colors, spacing, fontSize, radius } from '../theme'

function fmt(n: number | null | undefined, decimals = 2, prefix = '') {
  if (n == null) return '—'
  return prefix + n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

const holdingColumns: Column<Holding>[] = [
  { key: 'symbol', header: 'Symbol' },
  { key: 'quantity', header: 'Qty', align: 'right' },
  { key: 'avg_cost', header: 'Avg Cost', align: 'right', render: r => fmt(r.avg_cost, 2, '$') },
  { key: 'current_price', header: 'Current', align: 'right', render: r => fmt(r.current_price, 2, '$') },
  { key: 'market_value', header: 'Market Value', align: 'right', render: r => fmt(r.market_value, 2, '$') },
  {
    key: 'unrealized_pnl',
    header: 'P&L',
    align: 'right',
    render: r => {
      if (r.unrealized_pnl == null) return '—'
      const color = r.unrealized_pnl >= 0 ? colors.positive : colors.negative
      return <span style={{ color }}>{fmt(r.unrealized_pnl, 2, r.unrealized_pnl >= 0 ? '+$' : '$')}</span>
    },
  },
  {
    key: 'unrealized_pnl_pct',
    header: 'P&L %',
    align: 'right',
    render: r => {
      if (r.unrealized_pnl_pct == null) return '—'
      const color = r.unrealized_pnl_pct >= 0 ? colors.positive : colors.negative
      return <span style={{ color }}>{(r.unrealized_pnl_pct >= 0 ? '+' : '') + r.unrealized_pnl_pct.toFixed(2)}%</span>
    },
  },
]

const txColumns: Column<Transaction>[] = [
  { key: 'transaction_date', header: 'Date', render: r => r.transaction_date.slice(0, 10) },
  { key: 'symbol', header: 'Symbol' },
  {
    key: 'transaction_type',
    header: 'Type',
    render: r => (
      <span style={{ color: r.transaction_type === 'BUY' ? colors.positive : colors.negative, fontWeight: 600 }}>
        {r.transaction_type}
      </span>
    ),
  },
  { key: 'quantity', header: 'Qty', align: 'right' },
  { key: 'price', header: 'Price', align: 'right', render: r => fmt(r.price, 2, '$') },
  { key: 'total_amount', header: 'Total', align: 'right', render: r => fmt(r.total_amount, 2, '$') },
  { key: 'notes', header: 'Notes', render: r => r.notes ?? '' },
]

export default function Holdings() {
  const qc = useQueryClient()

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
          {syncMutation.isPending ? '동기화 중...' : 'Alpaca 동기화'}
        </SyncBtn>
      </Header>

      {syncMutation.isSuccess && (
        <Banner success>
          동기화 완료 — {(syncMutation.data as { synced: number }).synced}개 포지션 업데이트됨
        </Banner>
      )}
      {syncMutation.isError && (
        <Banner success={false}>
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
          <Banner success={false}>Alpaca 주문 이력 조회 실패 — Settings 페이지에서 API 키를 확인해 주세요.</Banner>
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

const Banner = styled.div<{ success: boolean }>`
  padding: ${spacing.md};
  border-radius: ${radius.sm};
  font-size: ${fontSize.sm};
  margin-bottom: ${spacing.lg};
  background: ${({ success }) => (success ? colors.success : colors.danger)}22;
  border: 1px solid ${({ success }) => (success ? colors.success : colors.danger)}44;
  color: ${({ success }) => (success ? colors.success : colors.danger)};
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
