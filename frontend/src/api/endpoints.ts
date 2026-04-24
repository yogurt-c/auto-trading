import api from './client'
import type {
  PortfolioResponse,
  MarketSummary,
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
  PerformanceSummary,
  RealizedTrade,
  Currency,
  Market,
  EvaluationResult,
  StrategyPreset,
  ReconcileResult,
} from './types'

// ── Portfolio ──────────────────────────────────────────────────────────────

const parseHolding = (h: any): Holding => ({
  ticker: h.ticker,
  shares: h.shares,
  avg_price: h.avg_price,
  current_price: h.current_price ?? null,
  market_value: h.market_value ?? null,
  pnl: h.pnl ?? null,
  pnl_pct: h.pnl_pct ?? null,
  market: h.market ?? 'US',
  currency: (h.currency ?? 'USD') as Currency,
})

const parseMarketSummary = (s: any): MarketSummary | null =>
  s
    ? {
        total_market_value: s.total_market_value ?? 0,
        total_cost_basis: s.total_cost_basis ?? 0,
        total_pnl: s.total_pnl ?? 0,
        total_pnl_pct: s.total_pnl_pct ?? 0,
        holding_count: s.holding_count ?? 0,
        currency: (s.currency ?? 'USD') as Currency,
      }
    : null

export const portfolioApi = {
  get: () =>
    api.get<any>('/portfolio').then(r => {
      const d = r.data
      return {
        holdings: (d.holdings ?? []).map(parseHolding),
        summary: {
          kr: parseMarketSummary(d.summary?.kr),
          us: parseMarketSummary(d.summary?.us),
        },
        failed_tickers: d.failed_tickers ?? [],
      } as PortfolioResponse
    }),

  sync: () =>
    api.post<any>('/portfolio/sync').then(r => ({
      synced: r.data.synced_count ?? 0,
    })),

  holdings: () =>
    api.get<any>('/portfolio').then(r =>
      (r.data.holdings ?? []).map(parseHolding)
    ),

  transactions: (limit = 50, market?: 'KR' | 'US') =>
    api
      .get<any>('/portfolio/transactions', { params: { limit, market } })
      .then(r =>
        (r.data.transactions ?? []).map((t: any): Transaction => ({
          id: t.id,
          ticker: t.ticker,
          action: (t.action ?? t.side) as 'buy' | 'sell',
          side: (t.side ?? t.action) as 'buy' | 'sell',
          shares: t.shares,
          price: t.price,
          total: t.total,
          executed_at: t.executed_at,
          currency: (t.currency ?? 'KRW') as Currency,
          market: (t.market ?? 'KR') as Market,
          strategy_id: t.strategy_id ?? null,
        }))
      ),

  reconcile: (lookback_days = 30) =>
    api
      .post<ReconcileResult>('/portfolio/reconcile', null, { params: { lookback_days } })
      .then(r => r.data),
}

// ── Strategies ─────────────────────────────────────────────────────────────

export const strategiesApi = {
  list: () =>
    api.get<any>('/strategies').then(r => {
      const rows: any[] = Array.isArray(r.data) ? r.data : []
      return rows.map((s): Strategy => ({
        id: s.id,
        name: s.name,
        ticker: s.ticker ?? null,
        strategy_type: s.strategy_type,
        description: s.description ?? '',
        ai_rationale: s.ai_rationale ?? null,
        market: s.market ?? 'US',
        currency: s.currency ?? 'USD',
        status: s.status as StrategyStatus,
        entry_price_drop_pct: s.entry_price_drop_pct ?? null,
        entry_rsi_below: s.entry_rsi_below ?? null,
        take_profit_pct: s.take_profit_pct ?? null,
        stop_loss_pct: s.stop_loss_pct ?? null,
        sell_ratio: s.sell_ratio ?? null,
        dca_amount: s.dca_amount ?? null,
        dca_frequency_days: s.dca_frequency_days ?? null,
        max_position: s.max_position ?? null,
        entry_bb_lower_touch: s.entry_bb_lower_touch ?? null,
        entry_macd_hist_positive: s.entry_macd_hist_positive ?? null,
        entry_disparity_below: s.entry_disparity_below ?? null,
        entry_volume_surge: s.entry_volume_surge ?? null,
        entry_sma_cross: s.entry_sma_cross ?? null,
        created_at: s.created_at,
        last_checked_at: s.last_checked_at ?? null,
        last_triggered_at: s.last_triggered_at ?? null,
        updated_at: s.updated_at ?? '',
      }))
    }),

  evaluate: (id: number) =>
    api.get<EvaluationResult>(`/strategies/${id}/evaluate`).then(r => r.data),

  presets: () =>
    api.get<StrategyPreset[]>('/strategies/presets').then(r => r.data),

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
        ticker: l.ticker,
        side: l.side,
        qty: l.qty,
        order_type: l.order_type,
        limit_price: l.limit_price ?? null,
        filled_price: l.filled_price ?? null,
        status: l.status,
        broker_order_id: l.broker_order_id ?? null,
        market: l.market ?? 'US',
        currency: l.currency ?? 'USD',
        ai_reasoning: l.ai_reasoning ?? null,
        avg_cost_snapshot: l.avg_cost_snapshot ?? null,
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
        strategies_checked: run.strategies_checked ?? 0,
        orders_placed: run.orders_placed ?? 0,
        error_message: run.error_message ?? null,
        summary: run.summary ?? null,
      })),
      total: r.data.total ?? 0,
      limit: r.data.limit ?? limit,
      offset: r.data.offset ?? offset,
    } as PaginatedRuns)),

  trigger: () => api.post<{ message: string }>('/scheduler/trigger').then(r => r.data),
}

// ── Performance ────────────────────────────────────────────────────────────

export const performanceApi = {
  get: (params?: { start_date?: string; end_date?: string; group_by?: 'day' | 'month' }) =>
    api
      .get<any>('/portfolio/performance', { params })
      .then(r => {
        const d = r.data
        return {
          ...d,
          trades: (d.trades ?? []).map((t: any): RealizedTrade => ({
            ...t,
            currency: (t.currency ?? 'USD') as Currency,
          })),
        } as PerformanceSummary
      }),
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
