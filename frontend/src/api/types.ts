// ── Portfolio ──────────────────────────────────────────────────────────────

export type Market = 'KR' | 'US'
export type Currency = 'KRW' | 'USD'

export interface Holding {
  ticker: string
  shares: number
  avg_price: number
  current_price: number | null
  market_value: number | null
  pnl: number | null
  pnl_pct: number | null
  market: Market
  currency: Currency
}

export interface Transaction {
  id: string
  ticker: string
  action: 'buy' | 'sell'
  side: 'buy' | 'sell'
  shares: number
  price: number
  total: number
  executed_at: string
  currency: Currency
  market: Market
  strategy_id: number | null
}

export interface ReconcileResult {
  db_repaired: number
  kr_synced: number
  us_synced: number
  pending_resolved: number
  pending_remaining: number
  errors: Array<{ source?: string; trade_log_id?: number; broker_order_id?: string; ticker?: string; market?: string; error: string }>
}

export interface MarketSummary {
  total_market_value: number
  total_cost_basis: number
  total_pnl: number
  total_pnl_pct: number
  holding_count: number
  currency: Currency
}

export interface PortfolioResponse {
  holdings: Holding[]
  summary: {
    kr: MarketSummary | null
    us: MarketSummary | null
  }
  failed_tickers: string[]
}

// ── Strategies ─────────────────────────────────────────────────────────────

export type StrategyStatus = 'active' | 'paused' | 'completed'

export interface Strategy {
  id: number
  name: string
  ticker: string | null
  strategy_type: string
  description: string
  ai_rationale: string | null
  market: Market
  currency: Currency
  status: StrategyStatus
  entry_price_drop_pct: number | null
  entry_rsi_below: number | null
  take_profit_pct: number | null
  stop_loss_pct: number | null
  sell_ratio: number | null
  dca_amount: number | null
  dca_frequency_days: number | null
  max_position: number | null
  // 기술지표 기반 진입 조건
  entry_bb_lower_touch: boolean | null
  entry_macd_hist_positive: boolean | null
  entry_disparity_below: number | null
  entry_volume_surge: number | null
  entry_sma_cross: number | null
  created_at: string
  last_checked_at: string | null
  last_triggered_at: string | null
  updated_at: string
}

export interface EvaluationCondition {
  triggered: boolean
  [key: string]: unknown
}

export interface EvaluationResult {
  ticker: string
  current_price: number
  entry_triggered: boolean
  exit_triggered: boolean
  signal_score: number | null
  conditions: Record<string, EvaluationCondition>
  holding_avg_price: number | null
  current_pnl_pct: number | null
  note: string | null
}

export interface StrategyPreset {
  name: string
  strategy_type: string
  description: string
  risk: 'low' | 'medium' | 'high'
  entry_rsi_below?: number
  entry_bb_lower_touch?: boolean
  entry_macd_hist_positive?: boolean
  entry_disparity_below?: number
  entry_volume_surge?: number
  entry_sma_cross?: number
  take_profit_pct?: number
  stop_loss_pct?: number
  dca_frequency_days?: number
}

// ── Trading ────────────────────────────────────────────────────────────────

export interface TradeLog {
  id: number
  strategy_id: number | null
  ticker: string
  side: string
  qty: number
  order_type: string
  limit_price: number | null
  filled_price: number | null
  status: string
  broker_order_id: string | null
  market: Market
  currency: Currency
  ai_reasoning: string | null
  avg_cost_snapshot: number | null
  executed_at: string
}

export interface AccountInfo {
  kr_cash: number
  kr_portfolio_value: number
  kr_buying_power: number
  us_cash: number
  us_portfolio_value: number
  us_buying_power: number
  status: string
  is_paper: boolean
}

export interface Position {
  ticker: string
  qty: number
  avg_entry_price: number
  current_price: number
  market_value: number
  unrealized_pl: number
  unrealized_plpc: number
  market: Market
  currency: Currency
}

// ── Scheduler ──────────────────────────────────────────────────────────────

export interface SchedulerStatus {
  running: boolean
  next_run: string | null
  krx_open: boolean
  nyse_open: boolean
}

export interface SchedulerRun {
  id: number
  started_at: string
  finished_at: string | null
  status: string
  strategies_checked: number
  orders_placed: number
  error_message: string | null
  summary: string | null
}

// ── Paginated responses ─────────────────────────────────────────────────────

export interface PaginatedLogs {
  logs: TradeLog[]
  total: number
  limit: number
  offset: number
}

export interface PaginatedRuns {
  runs: SchedulerRun[]
  total: number
  limit: number
  offset: number
}

// ── Settings ───────────────────────────────────────────────────────────────

export type Settings = Record<string, string>

// ── Performance ────────────────────────────────────────────────────────────

export interface RealizedTrade {
  id: number
  trade_log_id: number
  ticker: string
  qty: number
  sell_price: number
  avg_cost: number
  realized_pnl: number
  realized_pnl_pct: number
  currency: Currency
  strategy_id: number | null
  strategy_name: string | null
  executed_at: string
}

export interface PeriodPnl {
  period: string
  currency: Currency
  realized_pnl: number
  trade_count: number
}

export interface CurrencySummary {
  currency: Currency
  total_realized_pnl: number
  total_trade_count: number
  win_count: number
  win_rate: number
}

export interface StrategyPnl {
  strategy_id: number | null
  strategy_name: string
  currency: Currency
  realized_pnl: number
  trade_count: number
  win_count: number
  win_rate: number
}

export interface PerformanceSummary {
  period_start: string
  period_end: string
  by_currency: CurrencySummary[]
  trades: RealizedTrade[]
  by_period: PeriodPnl[]
  by_strategy: StrategyPnl[]
}

// ── Chat ───────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
