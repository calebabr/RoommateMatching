import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminGetUsers } from '../services/adminApi';

function StatusPill({ isBanned }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 10px',
      borderRadius: 12,
      fontSize: 12,
      fontWeight: 600,
      background: isBanned ? '#ffeaea' : '#eafff0',
      color: isBanned ? '#dd4444' : '#22aa55',
      border: `1px solid ${isBanned ? '#dd4444' : '#22aa55'}`,
    }}>
      {isBanned ? 'Banned' : 'Active'}
    </span>
  );
}

export default function UserListPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    adminGetUsers()
      .then(res => setUsers(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load users.'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = users.filter(u => {
    const q = search.toLowerCase();
    return (
      (u.username || '').toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q)
    );
  });

  return (
    <div style={{ padding: 32 }}>
      <h2 style={{ margin: '0 0 20px', fontSize: 24 }}>All Users</h2>

      <input
        type="text"
        placeholder="Search by name or email..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={{
          padding: '9px 14px', borderRadius: 6,
          border: '1px solid #e0e0e0', fontSize: 14,
          width: 280, marginBottom: 20,
        }}
      />

      {loading && <p style={{ color: '#888' }}>Loading users...</p>}
      {error && <p style={{ color: '#dd4444' }}>{error}</p>}

      {!loading && !error && (
        <div style={{
          background: '#ffffff', borderRadius: 8,
          border: '1px solid #e0e0e0', overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ background: '#f5f5f5' }}>
                {['ID', 'Name', 'Email', 'Gender', 'Matches', 'Joined', 'Status'].map(h => (
                  <th key={h} style={{
                    padding: '12px 16px', textAlign: 'left',
                    fontWeight: 600, color: '#555',
                    borderBottom: '1px solid #e0e0e0',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((user, i) => (
                <tr
                  key={user.id}
                  onClick={() => navigate(`/users/${user.id}`)}
                  style={{
                    cursor: 'pointer',
                    background: i % 2 === 0 ? '#ffffff' : '#fafafa',
                    borderBottom: '1px solid #f0f0f0',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#f0f6ff'}
                  onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? '#ffffff' : '#fafafa'}
                >
                  <td style={{ padding: '12px 16px', color: '#999', fontFamily: 'monospace', fontSize: 12 }}>
                    {user.id}
                  </td>
                  <td style={{ padding: '12px 16px', fontWeight: 500 }}>{user.username || '—'}</td>
                  <td style={{ padding: '12px 16px', color: '#555' }}>{user.email || '—'}</td>
                  <td style={{ padding: '12px 16px', color: '#555', textTransform: 'capitalize' }}>{user.gender || '—'}</td>
                  <td style={{ padding: '12px 16px', color: '#555' }}>{user.matchCount ?? 0}</td>
                  <td style={{ padding: '12px 16px', color: '#555' }}>
                    {user.createdAt ? new Date(user.createdAt.endsWith('Z') ? user.createdAt : user.createdAt + 'Z').toLocaleDateString() : '—'}
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <StatusPill isBanned={user.is_banned} />
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} style={{ padding: '24px 16px', textAlign: 'center', color: '#aaa' }}>
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
