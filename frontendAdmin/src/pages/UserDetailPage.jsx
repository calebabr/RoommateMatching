import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { adminGetUser, adminBanUser, adminUnbanUser, adminGetUserActivity } from '../services/adminApi';
import ConfirmDialog from '../components/ConfirmDialog';

const PREFS = [
  ['sleepSchedule', 'Sleep Schedule'],
  ['cleanliness', 'Cleanliness'],
  ['noiseTolerance', 'Noise Tolerance'],
  ['guestFrequency', 'Guest Frequency'],
  ['studyHabits', 'Study Habits'],
  ['smokingTolerance', 'Smoking Tolerance'],
];

function Field({ label, value }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <span style={{ color: '#888', fontSize: 12, display: 'block', marginBottom: 2 }}>{label}</span>
      <span style={{ fontSize: 14, color: '#222' }}>{value ?? '—'}</span>
    </div>
  );
}

export default function UserDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialog, setDialog] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [activity, setActivity] = useState(null);
  const [activityLoading, setActivityLoading] = useState(true);
  const [activityError, setActivityError] = useState('');

  const fetchUser = useCallback(() => {
    setLoading(true);
    adminGetUser(id)
      .then(res => setUser(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load user.'))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    fetchUser();
    setActivityLoading(true);
    adminGetUserActivity(id)
      .then(res => setActivity(res.data))
      .catch(() => setActivityError('Could not load activity.'))
      .finally(() => setActivityLoading(false));
  }, [fetchUser, id]);

  async function handleBanAction() {
    setActionLoading(true);
    try {
      if (user.is_banned) {
        await adminUnbanUser(id);
      } else {
        await adminBanUser(id);
      }
      setDialog(false);
      fetchUser();
    } catch (err) {
      setError(err.response?.data?.detail || 'Action failed.');
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <div style={{ padding: 32, color: '#888' }}>Loading...</div>;
  if (error) return <div style={{ padding: 32, color: '#dd4444' }}>{error}</div>;
  if (!user) return null;

  return (
    <div style={{ padding: 32, maxWidth: 720 }}>
      <button
        onClick={() => navigate('/users')}
        style={{
          background: 'none', border: '1px solid #e0e0e0',
          borderRadius: 6, padding: '7px 16px', cursor: 'pointer',
          fontSize: 13, color: '#555', marginBottom: 24,
        }}
      >
        Back to Users
      </button>

      <div style={{
        background: '#ffffff', borderRadius: 8,
        border: '1px solid #e0e0e0', padding: 28, marginBottom: 20,
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 24 }}>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: '0 0 4px', fontSize: 22 }}>{user.username || 'Unknown'}</h2>
            <p style={{ margin: 0, color: '#888', fontSize: 14 }}>{user.email}</p>
          </div>
          {user.is_banned && (
            <span style={{
              background: '#ffeaea', color: '#dd4444',
              border: '1px solid #dd4444', borderRadius: 6,
              padding: '6px 16px', fontWeight: 700, fontSize: 14,
            }}>
              BANNED
            </span>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 32px' }}>
          <Field label="ID" value={user.id} />
          <Field label="Gender" value={user.gender} />
          <Field label="Matches" value={user.matchCount} />
          <Field label="Joined" value={user.createdAt ? new Date(user.createdAt.endsWith('Z') ? user.createdAt : user.createdAt + 'Z').toLocaleString() : null} />
          <Field label="Bio" value={user.bio} />
        </div>
      </div>

      {PREFS.some(([key]) => user[key] != null) && (
        <div style={{
          background: '#ffffff', borderRadius: 8,
          border: '1px solid #e0e0e0', padding: 28, marginBottom: 20,
        }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 16 }}>Preferences</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 32px' }}>
            {PREFS.map(([key, label]) => (
              user[key] != null && <Field key={key} label={label} value={user[key]} />
            ))}
          </div>
        </div>
      )}

      <div style={{
        background: '#ffffff', borderRadius: 8,
        border: '1px solid #e0e0e0', padding: 28, marginBottom: 20,
      }}>
        <h3 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600, color: '#333' }}>Activity</h3>
        {activityLoading && (
          <p style={{ color: '#aaa', fontSize: 13 }}>Loading activity...</p>
        )}
        {!activityLoading && activityError && (
          <p style={{ color: '#aaa', fontSize: 13 }}>{activityError}</p>
        )}
        {!activityLoading && !activityError && activity && (
          <>
            <div>
              <h4 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600, color: '#333' }}>Matches</h4>
              {activity.matches && activity.matches.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', color: '#888', fontWeight: 500, paddingBottom: 6, borderBottom: '1px solid #f0f0f0' }}>Name</th>
                      <th style={{ textAlign: 'left', color: '#888', fontWeight: 500, paddingBottom: 6, borderBottom: '1px solid #f0f0f0' }}>Matched Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activity.matches.map((m, i) => (
                      <tr key={i}>
                        <td style={{ padding: '6px 0', color: '#222' }}>{m.name}</td>
                        <td style={{ padding: '6px 0', color: '#555' }}>{m.matched_at ? new Date(m.matched_at).toLocaleDateString() : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{ color: '#aaa', fontStyle: 'italic', fontSize: 13, margin: 0 }}>No matches yet.</p>
              )}
            </div>

            <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16, marginTop: 16 }}>
              <h4 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600, color: '#333' }}>Likes Sent</h4>
              {activity.likes_sent && activity.likes_sent.length > 0 ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {activity.likes_sent.map((l, i) => (
                    <span key={i} style={{
                      background: '#f0f0f0', color: '#555',
                      borderRadius: 12, padding: '3px 10px', fontSize: 12,
                    }}>
                      {l.name}
                    </span>
                  ))}
                </div>
              ) : (
                <p style={{ color: '#aaa', fontSize: 13, margin: 0 }}>No likes sent.</p>
              )}
            </div>

            <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16, marginTop: 16 }}>
              <h4 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 600, color: '#333' }}>Chat Partners</h4>
              {activity.chat_partners && activity.chat_partners.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', color: '#888', fontWeight: 500, paddingBottom: 6, borderBottom: '1px solid #f0f0f0' }}>Name</th>
                      <th style={{ textAlign: 'left', color: '#888', fontWeight: 500, paddingBottom: 6, borderBottom: '1px solid #f0f0f0' }}>Messages</th>
                      <th style={{ textAlign: 'left', color: '#888', fontWeight: 500, paddingBottom: 6, borderBottom: '1px solid #f0f0f0' }}>Last Active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activity.chat_partners.map((c, i) => (
                      <tr key={i}>
                        <td style={{ padding: '6px 0', color: '#222' }}>{c.name}</td>
                        <td style={{ padding: '6px 0', color: '#555' }}>{c.messages}</td>
                        <td style={{ padding: '6px 0', color: '#555' }}>{c.last_activity ? new Date(c.last_activity).toLocaleString() : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{ color: '#aaa', fontSize: 13, margin: 0 }}>No chats yet.</p>
              )}
            </div>
          </>
        )}
      </div>

      <button
        onClick={() => setDialog(true)}
        disabled={actionLoading}
        style={{
          padding: '10px 24px', borderRadius: 6, border: 'none',
          background: user.is_banned ? '#22aa55' : '#dd4444',
          color: '#ffffff', fontSize: 14, fontWeight: 600,
          cursor: actionLoading ? 'not-allowed' : 'pointer',
        }}
      >
        {user.is_banned ? 'Unban User' : 'Ban User'}
      </button>

      <ConfirmDialog
        open={dialog}
        title={user.is_banned ? `Unban ${user.username}?` : `Ban ${user.username}?`}
        message={
          user.is_banned
            ? `This will restore ${user.username}'s access to RoomMatch.`
            : `Are you sure you want to ban ${user.username}? This will prevent them from logging in.`
        }
        onConfirm={handleBanAction}
        onCancel={() => setDialog(false)}
      />
    </div>
  );
}
