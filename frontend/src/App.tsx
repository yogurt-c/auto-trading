import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Holdings from './pages/Holdings'
import Analysis from './pages/Analysis'
import AutoTrading from './pages/AutoTrading'
import Settings from './pages/Settings'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'holdings', element: <Holdings /> },
      { path: 'analysis', element: <Analysis /> },
      { path: 'auto-trading', element: <AutoTrading /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
