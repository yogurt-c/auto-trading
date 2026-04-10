import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import styled from '@emotion/styled'
import { colors, spacing, fontSize, radius } from '../theme'

// AI 응답 렌더러용 제한적 스키마 — style/script/이벤트 핸들러 명시적 차단
const sanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    // style 속성 제거 (XSS 벡터)
    '*': (defaultSchema.attributes?.['*'] ?? []).filter(
      (attr) => attr !== 'style' && attr !== 'className'
    ),
  },
  // 허용할 태그를 GFM + 마크다운 출력에 필요한 것만으로 제한
  tagNames: [
    'p', 'br', 'strong', 'em', 'del', 'code', 'pre',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'blockquote', 'hr',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'a',
  ],
}

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
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}
        components={{
          a: ({ href, children: linkChildren }) => {
            const safe = href?.startsWith('https://') || href?.startsWith('http://')
            return safe ? (
              <a href={href} target="_blank" rel="noopener noreferrer">{linkChildren}</a>
            ) : (
              <>{linkChildren}</>
            )
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </Wrapper>
  )
}
