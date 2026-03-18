import styled from '@emotion/styled'
import { colors, spacing, fontSize, radius } from '../theme'

interface Props {
  page: number        // 1-indexed
  totalPages: number
  onPageChange: (page: number) => void
}

export default function Pagination({ page, totalPages, onPageChange }: Props) {
  if (totalPages <= 1) return null

  return (
    <Container>
      <NavBtn
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        aria-label="이전 페이지"
      >
        ‹
      </NavBtn>
      <PageInfo>
        {page} / {totalPages}
      </PageInfo>
      <NavBtn
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="다음 페이지"
      >
        ›
      </NavBtn>
    </Container>
  )
}

const Container = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: ${spacing.sm};
  margin-top: ${spacing.md};
`

const NavBtn = styled.button`
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid ${colors.border};
  border-radius: ${radius.sm};
  color: ${colors.textMuted};
  font-size: ${fontSize.md};
  line-height: 1;
  cursor: pointer;
  transition: all 0.15s;

  &:hover:not(:disabled) {
    border-color: ${colors.primary};
    color: ${colors.primary};
  }

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
`

const PageInfo = styled.span`
  font-size: ${fontSize.sm};
  color: ${colors.textMuted};
  min-width: 60px;
  text-align: center;
`
