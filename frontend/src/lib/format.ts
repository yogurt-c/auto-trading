import type { Currency } from '../api/types'

/**
 * 숫자를 로케일 형식의 문자열로 포맷합니다.
 * null/undefined이면 '—'를 반환합니다.
 */
export function fmt(n: number | null | undefined, decimals = 2, prefix = ''): string {
  if (n == null) return '—'
  return prefix + n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

/**
 * 통화 기반 금액 포맷.
 * KRW → '₩1,234,567' (소수점 없음, 한국 로케일)
 * USD → '$1,234.56'
 */
export function fmtCurrency(
  value: number | null | undefined,
  currency: Currency,
  showPositiveSign = false,
): string {
  if (value == null) return '—'
  const sign = showPositiveSign && value >= 0 ? '+' : ''
  if (currency === 'KRW') {
    return `${sign}₩${Math.round(value).toLocaleString('ko-KR')}`
  }
  return `${sign}$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
