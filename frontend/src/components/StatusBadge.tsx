import styled from '@emotion/styled'
import { colors, radius, fontSize, spacing } from '../theme'

type Status = 'active' | 'filled' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'pending' | string

interface Props {
  status: Status
  label?: string
}

function getColor(status: Status): string {
  switch (status.toLowerCase()) {
    case 'active':
    case 'filled':
    case 'success':
      return colors.success
    case 'failed':
    case 'error':
    case 'cancelled':
      return colors.danger
    case 'pending':
    case 'paused':
      return colors.warning
    case 'completed':
      return colors.info
    default:
      return colors.neutral
  }
}

export default function StatusBadge({ status, label }: Props) {
  const color = getColor(status)
  return <Badge color={color}>{label ?? status}</Badge>
}

const Badge = styled.span<{ color: string }>`
  display: inline-block;
  padding: 2px ${spacing.sm};
  border-radius: ${radius.full};
  font-size: ${fontSize.xs};
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: ${({ color }) => color};
  background: ${({ color }) => color}22;
  border: 1px solid ${({ color }) => color}44;
`
