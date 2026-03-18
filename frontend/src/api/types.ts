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
  id: number
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

export interface Strategy {
  id: number
  name: string
  symbol: string
  strategy_type: string
  description: string
  ai_rationale: string | null
  status: StrategyStatus
  parameters: Record<string, unknown>
  created_at: string
  last_checked_at: string | null
  last_run_at: string | null
}

// ── Trading ────────────────────────────────────────────────────────────────

export interface TradeLog {
  id: number
  strategy_id: number | null
  symbol: string
  action: string
  quantity: number
  price: number
  status: string
  error_message: string | null
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

// ── Chat ───────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
