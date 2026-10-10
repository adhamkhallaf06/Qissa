import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'

export function Brand() {
  return (
    <Link to="/" className="brand">
      Qissa<span lang="ar" dir="rtl">قصة</span>
    </Link>
  )
}

/** Top bar shared by every page; the page itself renders in <Outlet />. */
export function Layout() {
  const { user, loading, logout } = useAuth()

  return (
    <>
      <nav className="topbar">
        <div className="topbar-inner">
          <Brand />
          {!loading && (
            <div className="row">
              {user ? (
                <>
                  <span className="hint user-name" title={user.email}>{user.name}</span>
                  <button type="button" className="btn ghost small" onClick={logout}>Log out</button>
                </>
              ) : (
                <>
                  <Link to="/login" className="btn ghost small">Log in</Link>
                  <Link to="/signup" className="btn primary small">Sign up</Link>
                </>
              )}
            </div>
          )}
        </div>
      </nav>
      <Outlet />
    </>
  )
}
