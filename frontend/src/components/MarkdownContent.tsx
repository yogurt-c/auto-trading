import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import styled from '@emotion/styled'
import { colors, spacing, fontSize, radius } from '../theme'

const Wrapper = styled.div`
  color: ${colors.text};
  font-size: ${fontSize.sm};
  line-height: 1.7;
  width: 100%;

  h1, h2, h3, h4 {
    font-size: ${fontSize.md};
    font-weight: 600;
    color: ${colors.text};
    border-bottom: 1px solid ${colors.border};
    padding-bottom: ${spacing.xs};
    margin: ${spacing.md} 0 ${spacing.sm};
  }

  h1:first-child, h2:first-child, h3:first-child {
    margin-top: 0;
  }

  p {
    margin: ${spacing.xs} 0;
  }

  ul, ol {
    padding-left: ${spacing.lg};
    margin: ${spacing.xs} 0;
  }

  li {
    margin: 2px 0;
  }

  strong {
    font-weight: 600;
    color: ${colors.text};
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: ${fontSize.xs};
    margin: ${spacing.sm} 0;
  }

  thead tr {
    background: ${colors.bgHover};
  }

  th, td {
    border: 1px solid ${colors.border};
    padding: ${spacing.xs} ${spacing.sm};
    text-align: left;
  }

  tbody tr:nth-child(even) {
    background: ${colors.bgSurface};
  }

  code {
    background: ${colors.bgHover};
    color: ${colors.primary};
    padding: 1px 5px;
    border-radius: ${radius.sm};
    font-size: ${fontSize.xs};
  }

  pre {
    background: ${colors.bgHover};
    border-radius: ${radius.sm};
    padding: ${spacing.sm};
    overflow-x: auto;
    margin: ${spacing.sm} 0;
  }

  pre code {
    background: none;
    padding: 0;
  }

  blockquote {
    border-left: 3px solid ${colors.border};
    margin: ${spacing.sm} 0;
    padding-left: ${spacing.sm};
    color: ${colors.textMuted};
  }
`

interface Props {
  children: string
}

export default function MarkdownContent({ children }: Props) {
  return (
    <Wrapper>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </Wrapper>
  )
}
