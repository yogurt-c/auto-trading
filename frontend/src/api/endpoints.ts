import api from './client'
import type {
  PortfolioResponse,
  Holding,
  Transaction,
  Strategy,
  StrategyStatus,
  TradeLog,
  AccountInfo,
  Position,
  SchedulerStatus,
  SchedulerRun,
  PaginatedLogs,
  PaginatedRuns,
  Settings,
} from './types'

// ── Portfolio ──────────────────────────────────────────────────────────────

export const portfolioApi = {
  get: () =>
    api.get<any>('/portfolio').then(r => {
      const d = r.data
      return {
        holdings: (d.holdings ?? []).map((h: any) => ({
          symbol: h.ticker,
          quantity: h.shares,
          avg_cost: h.avg_price,
          current_price: h.current_price ?? null,
          market_value: h.market_value ?? null,
          unrealized_pnl: h.pnl ?? null,
          unrealized_pnl_pct: h.pnl_pct ?? null,
        })),
        summary: {
          total_market_value: d.summary?.total_market_value ?? 0,
          total_cost_basis: d.summary?.total_cost_basis ?? 0,
          total_unrealized_pnl: d.summary?.total_pnl ?? 0,
          total_unrealized_pnl_pct: d.summary?.total_pnl_pct ?? 0,
          holding_count: d.count ?? 0,
        },
        fetch_errors: d.failed_tickers ?? [],
      } as PortfolioResponse
    }),

  sync: () =>
    api.post<any>('/portfolio/sync').then(r => ({
      synced: r.data.synced_count ?? 0,
    })),

  holdings: () =>
    api.get<any>('/portfolio').then(r =>
      (r.data.holdings ?? []).map((h: any): Holding => ({
        symbol: h.ticker,
        quantity: h.shares,
        avg_cost: h.avg_price,
        current_price: h.current_price ?? null,
        market_value: h.market_value ?? null,
        unrealized_pnl: h.pnl ?? null,
        unrealized_pnl_pct: h.pnl_pct ?? null,
      }))
    ),

  transactions: (limit = 50) =>
    api
      .get<any>('/portfolio/transactions', { params: { limit } })
      .then(r =>
        (r.data.transactions ?? []).map((t: any): Transaction => ({
          id: t.id,
          symbol: t.ticker,
          transaction_type: String(t.action).toUpperCase() as 'BUY' | 'SELL',
          quantity: t.shares,
          price: t.price,
          total_amount: t.total,
          transaction_date: t.executed_at,
          notes: t.notes ?? null,
        }))
      ),

  addTransaction: (data: {
    symbol: string
    transaction_type: 'BUY' | 'SELL'
    quantity: number
    price: number
    transaction_date: string
    notes?: string
  }) =>
    api
      .post<any>('/portfolio/transactions', {
        ticker: data.symbol,
        action: data.transaction_type.toLowerCase(),
        shares: data.quantity,
        price: data.price,
        executed_at: data.transaction_date,
        notes: data.notes,
      })
      .then(r => r.data as Transaction),
}

// ── Strategies ─────────────────────────────────────────────────────────────

export const strategiesApi = {
  list: () =>
    api.get<any>('/strategies').then(r => {
      const rows: any[] = Array.isArray(r.data) ? r.data : []
      return rows.map((s): Strategy => ({
        id: s.id,
        name: s.name,
        symbol: s.ticker ?? '',
        strategy_type: s.strategy_type,
        description: s.description ?? '',
        ai_rationale: s.ai_rationale ?? null,
        status: s.status as StrategyStatus,
        parameters: {
          entry_price_drop_pct: s.entry_price_drop_pct,
          entry_rsi_below: s.entry_rsi_below,
          take_profit_pct: s.take_profit_pct,
          stop_loss_pct: s.stop_loss_pct,
          sell_ratio: s.sell_ratio,
          dca_amount_usd: s.dca_amount_usd,
          dca_frequency_days: s.dca_frequency_days,
          max_position_usd: s.max_position_usd,
        },
        created_at: s.created_at,
        last_checked_at: s.last_checked_at ?? null,
        last_run_at: s.last_triggered_at ?? null,
      }))
    }),

  updateStatus: (id: number, status: StrategyStatus) =>
    api.patch<any>(`/strategies/${id}/status`, { status }).then(r => r.data as Strategy),

  delete: (id: number) => api.delete(`/strategies/${id}`).then(r => r.data),
}

// ── Trading ────────────────────────────────────────────────────────────────

export const tradingApi = {
  account: () =>
    api.get<any>('/trading/account').then(r => (r.data.account ?? r.data) as AccountInfo),

  positions: () =>
    api.get<any>('/trading/positions').then(r =>
      (Array.isArray(r.data) ? r.data : r.data.positions ?? []) as Position[]
    ),

  logs: (limit = 10, offset = 0) =>
    api.get<any>('/trading/logs', { params: { limit, offset } }).then(r => ({
      logs: (r.data.logs ?? []).map((l: any): TradeLog => ({
        id: l.id,
        strategy_id: l.strategy_id ?? null,
        symbol: l.ticker,
        action: l.side,
        quantity: l.qty,
        price: l.price ?? 0,
        status: l.status,
        error_message: l.error_message ?? null,
        executed_at: l.executed_at,
      })),
      total: r.data.total ?? 0,
      limit: r.data.limit ?? limit,
      offset: r.data.offset ?? offset,
    } as PaginatedLogs)),
}

// ── Scheduler ──────────────────────────────────────────────────────────────

export const schedulerApi = {
  status: () => api.get<SchedulerStatus>('/scheduler/status').then(r => r.data),

  runs: (limit = 10, offset = 0) =>
    api.get<any>('/scheduler/runs', { params: { limit, offset } }).then(r => ({
      runs: (r.data.runs ?? []).map((run: any): SchedulerRun => ({
        id: run.id,
        started_at: run.started_at,
        finished_at: run.finished_at ?? null,
        status: run.status,
        strategies_run: run.strategies_checked ?? 0,
        trades_executed: run.orders_placed ?? 0,
        error_message: run.error_message ?? null,
        summary: run.summary ?? null,
      })),
      total: r.data.total ?? 0,
      limit: r.data.limit ?? limit,
      offset: r.data.offset ?? offset,
    } as PaginatedRuns)),

  trigger: () => api.post<{ message: string }>('/scheduler/trigger').then(r => r.data),
}

// ── Auth ───────────────────────────────────────────────────────────────────

export const authApi = {
  status: () =>
    api.get<{ configured: boolean }>('/auth/status').then(r => r.data),

  setup: (password: string) =>
    api
      .post<{ access_token: string; token_type: string }>('/auth/setup', { password })
      .then(r => r.data),

  login: (password: string) =>
    api
      .post<{ access_token: string; token_type: string }>('/auth/login', { password })
      .then(r => r.data),

  changePassword: (current_password: string, new_password: string) =>
    api
      .post<{ success: boolean }>('/auth/change-password', { current_password, new_password })
      .then(r => r.data),

  me: () =>
    api.get<{ sub: string }>('/auth/me').then(r => r.data),
}

// ── Settings ───────────────────────────────────────────────────────────────

export const settingsApi = {
  getAll: () =>
    api.get<any>('/settings').then(r => (r.data.settings ?? r.data) as Settings),

  set: (key: string, value: string) =>
    api.put<{ key: string; value: string }>(`/settings/${key}`, { value }).then(r => r.data),

  status: () =>
    api.get<{ ok: boolean; reason: 'ok' | 'missing' | 'invalid'; message: string }>('/settings/status').then(r => r.data),
}
