/**
 * 숫자를 로케일 형식의 문자열로 포맷합니다.
 * null/undefined이면 '—'를 반환합니다.
 */
export function fmt(n: number | null | undefined, decimals = 2, prefix = ''): string {
  if (n == null) return '—'
  return prefix + n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}
