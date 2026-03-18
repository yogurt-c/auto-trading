import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Global, css } from '@emotion/react'
import App from './App'
import { colors, fontSize } from './theme'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

const globalStyles = css`
  *, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  html, body {
    height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
    font-size: ${fontSize.md};
    background: ${colors.bg};
    color: ${colors.text};
    -webkit-font-smoothing: antialiased;
  }

  #root {
    height: 100%;
  }

  ::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  ::-webkit-scrollbar-track {
    background: transparent;
  }

  ::-webkit-scrollbar-thumb {
    background: ${colors.border};
    border-radius: 3px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: ${colors.borderLight};
  }
`

const root = document.getElementById('root')!
createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Global styles={globalStyles} />
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
