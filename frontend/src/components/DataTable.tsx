import styled from '@emotion/styled'
import { colors, spacing, fontSize, radius } from '../theme'

export interface Column<T> {
  key: keyof T | string
  header: string
  render?: (row: T) => React.ReactNode
  align?: 'left' | 'right' | 'center'
}

interface Props<T> {
  columns: Column<T>[]
  data: T[]
  emptyMessage?: string
}

export default function DataTable<T>({
  columns,
  data,
  emptyMessage = '데이터 없음',
}: Props<T>) {
  return (
    <Wrapper>
      <Table>
        <thead>
          <tr>
            {columns.map(col => (
              <Th key={String(col.key)} align={col.align ?? 'left'}>
                {col.header}
              </Th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <EmptyCell colSpan={columns.length}>{emptyMessage}</EmptyCell>
            </tr>
          ) : (
            data.map((row, i) => (
              <Tr key={i}>
                {columns.map(col => (
                  <Td key={String(col.key)} align={col.align ?? 'left'}>
                    {col.render
                      ? col.render(row)
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      : String((row as Record<string, any>)[String(col.key)] ?? '')}
                  </Td>
                ))}
              </Tr>
            ))
          )}
        </tbody>
      </Table>
    </Wrapper>
  )
}

const Wrapper = styled.div`
  overflow-x: auto;
  border: 1px solid ${colors.border};
  border-radius: ${radius.md};
`

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${fontSize.sm};
`

const Th = styled.th<{ align: string }>`
  padding: ${spacing.sm} ${spacing.md};
  background: ${colors.bgSurface};
  color: ${colors.textMuted};
  font-weight: 600;
  text-align: ${({ align }) => align};
  font-size: ${fontSize.xs};
  text-transform: uppercase;
  letter-spacing: 0.6px;
  border-bottom: 1px solid ${colors.border};
  white-space: nowrap;
`

const Tr = styled.tr`
  border-bottom: 1px solid ${colors.border};
  transition: background 0.1s;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: ${colors.bgHover};
  }
`

const Td = styled.td<{ align: string }>`
  padding: ${spacing.sm} ${spacing.md};
  color: ${colors.text};
  text-align: ${({ align }) => align};
  white-space: nowrap;
`

const EmptyCell = styled.td`
  padding: ${spacing.xl};
  text-align: center;
  color: ${colors.textDim};
  font-size: ${fontSize.sm};
`
