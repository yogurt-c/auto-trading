// ── Portfolio ──────────────────────────────────────────────────────────────

export interface Holding {
  symbol: string
  quantity: number
  avg_cost: number
  current_price: number | null
  market_value: number | null
  unrealized_pnl: number | null
  unrealized_pnl_pct: number | null
}

export interface Transaction {
  id: string
  symbol: string
  transaction_type: 'BUY' | 'SELL'
  quantity: number
  price: number
  total_amount: number
  transaction_date: string
  notes: string | null
}

export interface PortfolioSummary {
  total_market_value: number
  total_cost_basis: number
  total_unrealized_pnl: number
  total_unrealized_pnl_pct: number
  holding_count: number
}

export interface PortfolioResponse {
  holdings: Holding[]
  summary: PortfolioSummary
  fetch_errors: string[]
}

// ── Strategies ─────────────────────────────────────────────────────────────

export type StrategyStatus = 'active' | 'paused' | 'completed'
export type Market = 'KR' | 'US'
export type Currency = 'KRW' | 'USD'

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
  created_at: string
  last_checked_at: string | null
  last_triggered_at: string | null
  updated_at: string
}

// ── Trading ────────────────────────────────────────────────────────────────

export interface TradeLog {
  id: number
  strategy_id: number | null
  symbol: string
  action: string
  quantity: number
  price: number | null
  status: string
  error_message: string | null
  avg_cost_snapshot: number | null
  executed_at: string
}

export interface AccountInfo {
  buying_power: number
  portfolio_value: number
  cash: number
  equity: number
  last_equity: number
  long_market_value: number
  short_market_value: number
  initial_margin: number
  maintenance_margin: number
  daytrade_count: number
  currency: string
  status: string
}

export interface Position {
  symbol: string
  qty: number
  avg_entry_price: number
  market_value: number
  unrealized_pl: number
  unrealized_plpc: number
  current_price: number
  side: string
}

// ── Scheduler ──────────────────────────────────────────────────────────────

export interface SchedulerStatus {
  running: boolean
  next_run: string | null
  market_open: boolean
}

export interface SchedulerRun {
  id: number
  started_at: string
  finished_at: string | null
  status: string
  strategies_run: number
  trades_executed: number
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
  strategy_id: number | null
  strategy_name: string | null
  executed_at: string
}

export interface PeriodPnl {
  period: string
  realized_pnl: number
  trade_count: number
}

export interface StrategyPnl {
  strategy_id: number | null
  strategy_name: string
  realized_pnl: number
  trade_count: number
  win_count: number
  win_rate: number
}

export interface PerformanceSummary {
  period_start: string
  period_end: string
  total_realized_pnl: number
  total_trade_count: number
  win_count: number
  win_rate: number
  trades: RealizedTrade[]
  by_period: PeriodPnl[]
  by_strategy: StrategyPnl[]
}

// ── Chat ───────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
