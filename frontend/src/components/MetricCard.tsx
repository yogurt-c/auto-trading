import styled from '@emotion/styled'
import { colors, spacing, fontSize, radius, shadow } from '../theme'

interface Props {
  title: string
  value: string | number
  delta?: number | null
  deltaLabel?: string
  subtitle?: string
}

export default function MetricCard({ title, value, delta, deltaLabel, subtitle }: Props) {
  const isPositive = delta !== undefined && delta !== null && delta >= 0
  const hasData = delta !== undefined && delta !== null

  return (
    <Card>
      <Title>{title}</Title>
      <Value>{value}</Value>
      {hasData && (
        <Delta positive={isPositive}>
          {isPositive ? '▲' : '▼'} {Math.abs(delta!).toFixed(2)}%
          {deltaLabel && <span> {deltaLabel}</span>}
        </Delta>
      )}
      {subtitle && <Subtitle>{subtitle}</Subtitle>}
    </Card>
  )
}

const Card = styled.div`
  background: ${colors.bgCard};
  border: 1px solid ${colors.border};
  border-radius: ${radius.md};
  padding: ${spacing.lg};
  box-shadow: ${shadow.sm};
`

const Title = styled.div`
  font-size: ${fontSize.xs};
  color: ${colors.textMuted};
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: ${spacing.sm};
`

const Value = styled.div`
  font-size: ${fontSize.xl};
  font-weight: 700;
  color: ${colors.text};
  letter-spacing: -0.5px;
`

const Delta = styled.div<{ positive: boolean }>`
  margin-top: ${spacing.xs};
  font-size: ${fontSize.sm};
  font-weight: 600;
  color: ${({ positive }) => (positive ? colors.positive : colors.negative)};
`

const Subtitle = styled.div`
  margin-top: ${spacing.xs};
  font-size: ${fontSize.xs};
  color: ${colors.textDim};
`
