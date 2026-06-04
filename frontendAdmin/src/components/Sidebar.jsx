import { NavLink } from 'react-router-dom';
import { useAdmin } from '../context/AuthContext';

const styles = {
  sidebar: {
    width: 220,
    minHeight: '100vh',
    background: '#1a1a2e',
    color: '#ffffff',
    display: 'flex',
    flexDirection: 'column',
    padding: '24px 0',
    flexShrink: 0,
  },
  brand: {
    padding: '0 24px 24px',
    fontSize: 18,
    fontWeight: 700,
    borderBottom: '1px solid rgba(255,255,255,0.1)',
    marginBottom: 16,
  },
  nav: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
  },
  link: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '12px 24px',
    color: '#ffffff',
    textDecoration: 'none',
    fontSize: 14,
    transition: 'background 0.15s',
  },
  logoutBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '12px 24px',
    color: '#ffffff',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: 14,
    width: '100%',
    textAlign: 'left',
    marginTop: 'auto',
    borderTop: '1px solid rgba(255,255,255,0.1)',
  },
};

function NavItem({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      style={({ isActive }) => ({
        ...styles.link,
        background: isActive ? '#0f3460' : 'transparent',
      })}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </NavLink>
  );
}

export default function Sidebar() {
  const { logout } = useAdmin();
  return (
    <div style={styles.sidebar}>
      <div style={styles.brand}>RoomMatch Admin</div>
      <nav style={styles.nav}>
        <NavItem to="/users" icon="👥" label="Users" />
        <NavItem to="/errors" icon="🐛" label="Error Logs" />
        <NavItem to="/feedback" icon="💬" label="User Feedback" />
        <NavItem to="/reports" icon="🚨" label="Reports" />
      </nav>
      <button style={styles.logoutBtn} onClick={logout}>
        <span>🚪</span>
        <span>Logout</span>
      </button>
    </div>
  );
}
