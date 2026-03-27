import styled from '@emotion/styled'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { settingsApi } from '../api/endpoints'
import { useAuth } from '../contexts/AuthContext'
import { colors, spacing, fontSize } from '../theme'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/holdings', label: 'Holdings', icon: '💼' },
  { to: '/analysis', label: 'AI Analysis', icon: '🤖' },
  { to: '/auto-trading', label: 'Auto Trading', icon: '⚡' },
  { to: '/performance', label: 'Performance', icon: '📈' },
  { to: '/settings', label: 'Settings', icon: '⚙️' },
]

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { data: status } = useQuery({
    queryKey: ['settingsStatus'],
    queryFn: settingsApi.status,
    staleTime: 30_000,
  })

  const showBanner = status && !status.ok && location.pathname !== '/settings'

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <Shell>
      <Sidebar>
        <SidebarHeader>
          <Logo>Portfolio</Logo>
          <LogoSub>AI Manager</LogoSub>
        </SidebarHeader>
        <Nav>
          {navItems.map(item => (
            <NavItem key={item.to} to={item.to}>
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavItem>
          ))}
        </Nav>
        <SidebarFooter>
          <LogoutBtn onClick={handleLogout}>로그아웃</LogoutBtn>
        </SidebarFooter>
      </Sidebar>
      <MainArea>
        {showBanner && (
          <ConfigBanner>
            <span>{status.message}</span>
            <ConfigLink to="/settings">Settings에서 수정하기 →</ConfigLink>
          </ConfigBanner>
        )}
        <Main>
          <Outlet />
        </Main>
      </MainArea>
    </Shell>
  )
}

const Shell = styled.div`
  display: flex;
  min-height: 100vh;
  background: ${colors.bg};
  color: ${colors.text};
`

const Sidebar = styled.aside`
  width: 220px;
  min-width: 220px;
  background: ${colors.bgSurface};
  border-right: 1px solid ${colors.border};
  display: flex;
  flex-direction: column;
  padding: ${spacing.lg} 0;
`

const SidebarHeader = styled.div`
  padding: 0 ${spacing.lg} ${spacing.lg};
  border-bottom: 1px solid ${colors.border};
  margin-bottom: ${spacing.md};
`

const Logo = styled.div`
  font-size: ${fontSize.lg};
  font-weight: 700;
  color: ${colors.primary};
  letter-spacing: -0.5px;
`

const LogoSub = styled.div`
  font-size: ${fontSize.xs};
  color: ${colors.textMuted};
  margin-top: 2px;
`

const Nav = styled.nav`
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 ${spacing.sm};
  flex: 1;
`

const SidebarFooter = styled.div`
  padding: ${spacing.md} ${spacing.sm};
  border-top: 1px solid ${colors.border};
`

const LogoutBtn = styled.button`
  width: 100%;
  background: transparent;
  border: 1px solid ${colors.border};
  border-radius: 8px;
  padding: ${spacing.sm} ${spacing.md};
  font-size: ${fontSize.sm};
  color: ${colors.textMuted};
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  text-align: left;

  &:hover {
    background: ${colors.bgHover};
    color: ${colors.text};
  }
`

const NavItem = styled(NavLink)`
  display: flex;
  align-items: center;
  gap: ${spacing.sm};
  padding: ${spacing.sm} ${spacing.md};
  border-radius: 8px;
  font-size: ${fontSize.sm};
  color: ${colors.textMuted};
  text-decoration: none;
  transition: background 0.15s, color 0.15s;

  &:hover {
    background: ${colors.bgHover};
    color: ${colors.text};
  }

  &.active {
    background: ${colors.bgHover};
    color: ${colors.primary};
    font-weight: 600;
  }
`

const MainArea = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`

const ConfigBanner = styled.div`
  background: #7f1d1d;
  color: #fecaca;
  padding: ${spacing.sm} ${spacing.xl};
  font-size: ${fontSize.sm};
  display: flex;
  align-items: center;
  gap: ${spacing.lg};
  flex-shrink: 0;
`

const ConfigLink = styled(NavLink)`
  color: #fca5a5;
  font-weight: 600;
  text-decoration: underline;
  white-space: nowrap;

  &:hover {
    color: #ffffff;
  }
`

const Main = styled.main`
  flex: 1;
  overflow-y: auto;
  padding: ${spacing.xl};
`
