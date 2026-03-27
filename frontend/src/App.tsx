import { createBrowserRouter, Navigate, Outlet, RouterProvider } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Holdings from './pages/Holdings'
import Analysis from './pages/Analysis'
import AutoTrading from './pages/AutoTrading'
import Performance from './pages/Performance'
import Settings from './pages/Settings'
import LoginSetup from './pages/LoginSetup'

function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return null
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Outlet />
}

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginSetup />,
  },
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <Layout />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: 'dashboard', element: <Dashboard /> },
          { path: 'holdings', element: <Holdings /> },
          { path: 'analysis', element: <Analysis /> },
          { path: 'auto-trading', element: <AutoTrading /> },
          { path: 'performance', element: <Performance /> },
          { path: 'settings', element: <Settings /> },
        ],
      },
    ],
  },
])

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  )
}
