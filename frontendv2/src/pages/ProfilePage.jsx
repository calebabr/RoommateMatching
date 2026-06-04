import React, { useState, useRef, useEffect } from 'react';

function EyeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );
}
import { useNavigate } from 'react-router-dom';
import { Colors } from '../utils/theme';
import { CATEGORIES, LIFESTYLE_TAGS } from '../utils/categories';

const RELIGION_OPTIONS = [
  'Christian', 'Catholic', 'Muslim', 'Jewish', 'Hindu',
  'Buddhist', 'Agnostic', 'Atheist', 'Spiritual', 'Other', 'Prefer not to say',
];

const MAJOR_OPTIONS = [
  'Accounting', 'Aerospace Engineering', 'Architecture', 'Biology',
  'Business Administration', 'Chemical Engineering', 'Chemistry',
  'Civil Engineering', 'Communications', 'Computer Science',
  'Criminal Justice', 'Economics', 'Education', 'Electrical Engineering',
  'English', 'Finance', 'Graphic Design', 'History', 'Industrial Engineering',
  'Information Systems', 'Kinesiology', 'Marketing', 'Mathematics',
  'Mechanical Engineering', 'Nursing', 'Philosophy', 'Physics',
  'Political Science', 'Psychology', 'Public Health', 'Sociology',
  'Software Engineering', 'Statistics', 'Theater', 'Undecided', 'Other',
];

const GRADUATION_SEASONS = ['Spring', 'Summer', 'Fall'];
const GRADUATION_YEARS = [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035];
import { useAuth } from '../context/AuthContext';
import posthog from 'posthog-js';
import { updateUser, uploadPhoto, getPhotoUrl, getBlockedUsers, unblockUser, exportUserData, deleteAccount, pauseProfile, unpauseProfile, deactivateProfile, reactivateProfile } from '../services/api';
import SliderPicker from '../components/SliderPicker';
import Toggle from '../components/Toggle';
import NotificationBell from '../components/NotificationBell';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

export default function ProfilePage() {
  const { user, refreshUser, logout } = useAuth();
  const [editing, setEditing] = useState(false);
  const [saving,  setSaving]  = useState(false);
  const [modal,   setModal]   = useState(null);
  const [bio,     setBio]     = useState(user?.bio || '');
  const [username, setUsername] = useState(user?.username || '');
  const [photoFile,    setPhotoFile]    = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [selectedTags,     setSelectedTags]     = useState(user?.lifestyleTags || []);
  const [religionTag,      setReligionTag]      = useState(user?.religionTag || '');
  const [major,            setMajor]            = useState(() => {
    const m = user?.major || '';
    return m.startsWith('Other: ') ? 'Other' : m;
  });
  const [majorOther,       setMajorOther]       = useState(() => {
    const m = user?.major || '';
    return m.startsWith('Other: ') ? m.slice(7) : '';
  });
  const [graduationSeason, setGraduationSeason] = useState(user?.graduationSeason || '');
  const [graduationYear,   setGraduationYear]   = useState(user?.graduationYear ? String(user.graduationYear) : '');
  const fileInputRef   = useRef(null);
  const cameraInputRef = useRef(null);

  // Blocked users
  const [blockedUsers,     setBlockedUsers]     = useState([]);
  const [unblockingId,     setUnblockingId]     = useState(null);

  // Danger zone — delete with password
  const [showDeleteModal,  setShowDeleteModal]  = useState(false);
  const [deletePassword,   setDeletePassword]   = useState('');
  const [deleting,         setDeleting]         = useState(false);
  const [showDeletePassword, setShowDeletePassword] = useState(false);
  const [restoreToken,     setRestoreToken]      = useState(null);
  const [tokenCopied,      setTokenCopied]      = useState(false);

  // Danger zone — export
  const [exporting,        setExporting]        = useState(false);

  // Danger zone — pause
  const [pausing,          setPausing]          = useState(false);

  // Danger zone — deactivate
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  const [deactivatePassword,  setDeactivatePassword]  = useState('');
  const [deactivating,        setDeactivating]        = useState(false);
  const [showDeactivatePassword, setShowDeactivatePassword] = useState(false);

  // Reactivate (edge case: deactivated user still logged in)
  const [reactivating,     setReactivating]     = useState(false);

  const navigate = useNavigate();

  const [preferences, setPreferences] = useState(
    CATEGORIES.reduce((acc, cat) => {
      acc[cat.key] = {
        value: user?.[cat.key]?.value ?? Math.round((cat.max - cat.min) / 2),
        isDealBreaker: user?.[cat.key]?.isDealBreaker ?? false,
      };
      return acc;
    }, {})
  );

  const updatePref = (key, field, val) =>
    setPreferences(prev => ({ ...prev, [key]: { ...prev[key], [field]: val } }));

  const toggleTag = (tag) =>
    setSelectedTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) { setPhotoFile(file); setPhotoPreview(URL.createObjectURL(file)); }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const resolvedMajor = major === 'Other' ? (majorOther.trim() ? `Other: ${majorOther.trim()}` : '') : major;
      const payload = {
        username: username.trim() || user.username,
        gender: user.gender || 'male',
        bio: bio.trim(),
        lifestyleTags: selectedTags,
        religionTag: religionTag || undefined,
        major: resolvedMajor || undefined,
        graduationSeason: graduationSeason || undefined,
        graduationYear: graduationYear ? parseInt(graduationYear) : undefined,
        ...preferences,
      };
      await updateUser(user.id, payload);
      if (photoFile) {
        await uploadPhoto(user.id, photoFile);
        posthog.capture('photo_uploaded');
      }
      await refreshUser();
      setEditing(false); setPhotoFile(null); setPhotoPreview(null);
      posthog.capture('profile_completed');
      setModal({ title: 'Saved', message: 'Your profile has been updated.' });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map(d => `${d.field}: ${d.message}`).join('\n')
        : detail || err?.message || 'Could not update profile.';
      setModal({ title: 'Error', message });
    } finally { setSaving(false); }
  };

  const handleCancel = () => {
    setEditing(false); setPhotoFile(null); setPhotoPreview(null);
    setBio(user?.bio || '');
    setSelectedTags(user?.lifestyleTags || []);
    setReligionTag(user?.religionTag || '');
    const m = user?.major || '';
    setMajor(m.startsWith('Other: ') ? 'Other' : m);
    setMajorOther(m.startsWith('Other: ') ? m.slice(7) : '');
    setGraduationSeason(user?.graduationSeason || '');
    setGraduationYear(user?.graduationYear ? String(user.graduationYear) : '');
    setPreferences(CATEGORIES.reduce((acc, cat) => {
      acc[cat.key] = { value: user?.[cat.key]?.value ?? Math.round((cat.max - cat.min) / 2), isDealBreaker: user?.[cat.key]?.isDealBreaker ?? false };
      return acc;
    }, {}));
  };

  useEffect(() => {
    if (!user?.id) return;
    getBlockedUsers(user.id).then(setBlockedUsers).catch(() => {});
  }, [user?.id]);

  const handleUnblock = async (targetId) => {
    setUnblockingId(targetId);
    try {
      await unblockUser(targetId);
      setBlockedUsers(prev => prev.filter(u => u.id !== targetId));
    } catch {
      setModal({ title: 'Error', message: 'Could not unblock user.' });
    } finally {
      setUnblockingId(null);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const data = await exportUserData(user.id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = 'roommatch-data.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setModal({ title: 'Error', message: 'Could not export data.' });
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!deletePassword.trim()) return;
    setDeleting(true);
    try {
      const result = await deleteAccount(user.id, deletePassword);
      setShowDeleteModal(false);
      setDeletePassword('');
      setRestoreToken(result.restore_token || null);
      posthog.capture('account_deleted');
      await logout();
      if (!result.restore_token) navigate('/login');
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not delete account. Check your password.' });
    } finally {
      setDeleting(false);
    }
  };

  const handlePauseToggle = async () => {
    setPausing(true);
    try {
      if (user.is_paused) {
        await unpauseProfile(user.id);
      } else {
        await pauseProfile(user.id);
      }
      await refreshUser();
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not update pause status.' });
    } finally {
      setPausing(false);
    }
  };

  const handleDeactivateAccount = async () => {
    if (!deactivatePassword.trim()) return;
    setDeactivating(true);
    try {
      await deactivateProfile(user.id, deactivatePassword);
      setShowDeactivateModal(false);
      setDeactivatePassword('');
      posthog.capture('account_deactivated');
      await logout();
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not deactivate account. Check your password.' });
    } finally {
      setDeactivating(false);
    }
  };

  const handleReactivate = async () => {
    setReactivating(true);
    try {
      await reactivateProfile(user.id);
      await refreshUser();
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not reactivate account.' });
    } finally {
      setReactivating(false);
    }
  };

  if (!user) return null;

  const displayPhotoUrl = photoPreview || getPhotoUrl(user.photoUrl);
  const matchCount = user?.matchCount ?? (user?.matched ? 1 : 0);
  const genderLabel = user.gender === 'female' ? '♀ Female' : user.gender === 'male' ? '♂ Male' : '';

  return (
    <div className="full-height overflow-y bg-base">
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} onConfirm={modal.onConfirm} confirmText={modal.confirmText} danger={modal.danger} />}
      <input ref={fileInputRef}   type="file" accept="image/*"           onChange={handleFileChange} style={{ display: 'none' }} />
      <input ref={cameraInputRef} type="file" accept="image/*" capture="user" onChange={handleFileChange} style={{ display: 'none' }} />

      {/* Deactivated-while-logged-in banner */}
      {user.is_deactivated && (
        <div className="profile-deactivated-banner">
          <span className="profile-deactivated-banner-text">
            Your account is deactivated. Reactivate to make your profile visible again.
          </span>
          <button
            className="profile-reactivate-btn"
            onClick={handleReactivate}
            disabled={reactivating}
          >
            {reactivating ? '...' : 'Reactivate'}
          </button>
        </div>
      )}

      <div className="profile-page">
        {/* Top bar */}
        <div className="profile-topbar">
          <span className="profile-topbar-title">Profile</span>
          <NotificationBell />
        </div>

        <div className="two-col-layout">
          {/* ── Left column: avatar + info ── */}
          <div className="col-left-280">
            <div className="profile-avatar-card">
              {displayPhotoUrl ? (
                <img src={displayPhotoUrl} alt="avatar" className="profile-avatar-image" />
              ) : (
                <div className="profile-avatar-large">
                  <span style={{ fontSize: 36, fontWeight: 800 }} className="text-accent">
                    {(user.username || '?')[0].toUpperCase()}
                  </span>
                </div>
              )}

              {editing && (
                <div className="profile-photo-edit-row">
                  <button onClick={() => fileInputRef.current.click()} className="profile-photo-edit-btn">🖼️ Gallery</button>
                  <button onClick={() => cameraInputRef.current.click()} className="profile-photo-edit-btn">📷 Camera</button>
                  {(photoFile || user.photoUrl) && (
                    <button onClick={() => { setPhotoFile(null); setPhotoPreview(null); }} className="profile-photo-edit-btn profile-photo-edit-btn--danger">✕</button>
                  )}
                </div>
              )}

              <p className="profile-username">{user.username}</p>
              <p className="profile-user-id">ID: {user.id}</p>

              {genderLabel && (
                <span className="profile-gender-badge">{genderLabel}</span>
              )}

              {user.bio && <p className="profile-bio">{user.bio}</p>}

              {(user.lifestyleTags || []).length > 0 && (
                <div className="profile-tags">
                  {(user.lifestyleTags || []).map(tag => (
                    <span key={tag} className="tag-pill tag-pill-accent" style={{ fontSize: 11 }}>{tag}</span>
                  ))}
                  {user.religionTag && (
                    <span className="tag-pill" style={{ fontSize: 11, background: 'rgba(139,92,246,0.2)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.3)' }}>{user.religionTag}</span>
                  )}
                </div>
              )}
              {!(user.lifestyleTags || []).length && user.religionTag && (
                <div className="profile-tags">
                  <span className="tag-pill" style={{ fontSize: 11, background: 'rgba(139,92,246,0.2)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.3)' }}>{user.religionTag}</span>
                </div>
              )}

              {(user.major || (user.graduationSeason && user.graduationYear)) && (
                <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {user.major && (
                    <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #A0A0A0)', margin: 0 }}>
                      Major: {user.major}
                    </p>
                  )}
                  {user.graduationSeason && user.graduationYear && (
                    <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #A0A0A0)', margin: 0 }}>
                      Graduating {user.graduationSeason} {user.graduationYear}
                    </p>
                  )}
                </div>
              )}

              <span className={`profile-match-status ${matchCount > 0 ? 'profile-match-status--matched' : 'profile-match-status--searching'}`}>
                {matchCount > 0 ? `Matched with ${matchCount} roommate${matchCount > 1 ? 's' : ''}` : 'Searching for roommate'}
              </span>

              <div className="profile-logout-area">
                <button className="profile-logout-btn" onClick={logout}>Log Out</button>
              </div>
            </div>
          </div>

          {/* ── Right column: bio/tags edit + preferences ── */}
          <div className="col-right-flex">
            {editing && (
              <>
                <div className="profile-section">
                  <p className="profile-section-title">Profile Info</p>
                  <label className="profile-label">Name</label>
                  <input
                    className="profile-input"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    maxLength={30}
                    placeholder="Your name"
                  />
                  <label className="profile-label" style={{ marginTop: 12 }}>Bio</label>
                  <textarea
                    className="profile-input"
                    style={{ minHeight: 80, resize: 'vertical', paddingTop: 14 }}
                    value={bio}
                    onChange={e => setBio(e.target.value)}
                    maxLength={200}
                    placeholder="A short intro about yourself..."
                  />
                  <p className="profile-bio-count">{bio.length}/200</p>
                </div>

                <div className="profile-section">
                  <p className="profile-section-title">Lifestyle Tags</p>
                  <div className="profile-lifestyle-tags">
                    {LIFESTYLE_TAGS.map(tag => {
                      const sel = selectedTags.includes(tag);
                      return (
                        <button
                          key={tag}
                          onClick={() => toggleTag(tag)}
                          className={`profile-tag-btn ${sel ? 'profile-tag-btn--selected' : ''}`}
                        >
                          {tag}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="profile-section">
                  <p className="profile-section-title">Religion</p>
                  <p style={{ fontSize: 12, color: 'var(--color-text-secondary, #A0A0A0)', marginBottom: 10 }}>Optional — select one</p>
                  <div className="profile-lifestyle-tags">
                    {RELIGION_OPTIONS.map(opt => {
                      const sel = religionTag === opt;
                      return (
                        <button
                          key={opt}
                          onClick={() => setReligionTag(sel ? '' : opt)}
                          className={`profile-tag-btn ${sel ? 'profile-tag-btn--selected' : ''}`}
                        >
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="profile-section">
                  <p className="profile-section-title">Major</p>
                  <select
                    className="profile-input"
                    value={major}
                    onChange={e => { setMajor(e.target.value); if (e.target.value !== 'Other') setMajorOther(''); }}
                  >
                    <option value="">Select your major...</option>
                    {MAJOR_OPTIONS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                  {major === 'Other' && (
                    <input
                      className="profile-input"
                      style={{ marginTop: 8 }}
                      placeholder="Enter your major"
                      value={majorOther}
                      onChange={e => setMajorOther(e.target.value)}
                    />
                  )}
                </div>

                <div className="profile-section">
                  <p className="profile-section-title">Graduation</p>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <select
                      className="profile-input"
                      style={{ flex: 1 }}
                      value={graduationSeason}
                      onChange={e => setGraduationSeason(e.target.value)}
                    >
                      <option value="">Season</option>
                      {GRADUATION_SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <select
                      className="profile-input"
                      style={{ flex: 1 }}
                      value={graduationYear}
                      onChange={e => setGraduationYear(e.target.value)}
                    >
                      <option value="">Year</option>
                      {GRADUATION_YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                    </select>
                  </div>
                </div>
              </>
            )}

            <div className="profile-section">
              <div className="profile-prefs-header">
                <span className="profile-prefs-title">Your Preferences</span>
                {!editing && <button className="profile-edit-link" onClick={() => setEditing(true)}>Edit</button>}
              </div>

              <div className="pref-grid">
                {CATEGORIES.map(cat => {
                  const pref = editing ? preferences[cat.key] : user[cat.key];
                  if (!pref) return null;
                  return (
                    <div key={cat.key} className="pref-card">
                      <div className="profile-pref-header">
                        <span className="profile-pref-name">{cat.label}</span>
                        {pref.isDealBreaker && !editing && (
                          <span className="profile-dealbreaker-badge">Deal-breaker</span>
                        )}
                      </div>
                      {editing ? (
                        <>
                          <div className="profile-pref-editing-dealbreaker">
                            <span className="profile-pref-dealbreaker-label">Deal-breaker</span>
                            <Toggle value={preferences[cat.key].isDealBreaker} onChange={v => updatePref(cat.key, 'isDealBreaker', v)} />
                          </div>
                          <SliderPicker min={cat.min} max={cat.max} value={preferences[cat.key].value} onChange={v => updatePref(cat.key, 'value', v)} formatLabel={cat.formatValue} />
                        </>
                      ) : (
                        <>
                          <p className="profile-pref-value">{cat.formatValue(pref.value)}</p>
                          <div className="profile-pref-bar-track">
                            <div className="profile-pref-bar-fill" style={{ width: `${(pref.value / cat.max) * 100}%` }} />
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>

              {editing && (
                <div className="profile-save-cancel-row">
                  <button className="profile-save-btn" onClick={handleSave} disabled={saving}>
                    {saving ? <Spinner size={18} color={Colors.black} /> : 'Save Changes'}
                  </button>
                  <button className="profile-cancel-btn" onClick={handleCancel}>Cancel</button>
                </div>
              )}
            </div>

            {/* ── Blocked Users ── */}
            {blockedUsers.length > 0 && (
              <div className="profile-section" style={{ marginTop: 28 }}>
                <p className="profile-section-title">Blocked Users</p>
                <div className="flex-col" style={{ gap: 10 }}>
                  {blockedUsers.map(bu => (
                    <div key={bu.id} className="blocked-user-row">
                      <div className="blocked-user-avatar">
                        {bu.photoUrl
                          ? <img src={bu.photoUrl.startsWith('http') ? bu.photoUrl : getPhotoUrl(bu.photoUrl)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          : <span className="avatar-letter-muted">{(bu.username || '?')[0].toUpperCase()}</span>
                        }
                      </div>
                      <span className="blocked-user-name">{bu.username}</span>
                      <button
                        className={`blocked-unblock-btn ${unblockingId === bu.id ? 'blocked-unblock-btn--loading' : ''}`}
                        onClick={() => handleUnblock(bu.id)}
                        disabled={unblockingId === bu.id}
                      >
                        {unblockingId === bu.id ? '...' : 'Unblock'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Danger Zone ── */}
            <div className="danger-zone">
              <p className="danger-zone-title">Danger Zone</p>
              <div className="danger-zone-actions">
                <div className="danger-zone-row">
                  <div>
                    <p className="danger-action-label">Export My Data</p>
                    <p className="danger-action-desc">Download a JSON copy of all your account data.</p>
                  </div>
                  <button
                    className={`danger-action-btn danger-action-btn--neutral ${exporting ? 'danger-action-btn--exporting' : ''}`}
                    onClick={handleExport}
                    disabled={exporting}
                  >
                    {exporting ? '...' : 'Export Data'}
                  </button>
                </div>

                {/* Pause Profile */}
                <div className="danger-zone-row danger-zone-row--bordered">
                  <div>
                    <p className="danger-action-label">
                      {user.is_paused ? 'Profile Paused' : 'Pause Profile'}
                    </p>
                    <p className="danger-action-desc">
                      Pausing hides you from Discover and Liked You. Your existing matches and chats remain.
                    </p>
                    {user.is_paused && (
                      <p className="danger-paused-notice">
                        Your profile is paused — you're hidden from new users.
                      </p>
                    )}
                  </div>
                  <button
                    className={`danger-action-btn ${user.is_paused ? 'danger-action-btn--unpause' : 'danger-action-btn--pause'}`}
                    onClick={handlePauseToggle}
                    disabled={pausing}
                  >
                    {pausing ? '...' : user.is_paused ? 'Unpause' : 'Pause Profile'}
                  </button>
                </div>

                {/* Deactivate Account */}
                <div className="danger-zone-row danger-zone-row--bordered">
                  <div>
                    <p className="danger-action-label">Deactivate Account</p>
                    <p className="danger-action-desc">
                      Hides your profile from everyone. You can reactivate within 30 days.
                    </p>
                  </div>
                  <button
                    className="danger-action-btn danger-action-btn--warning"
                    onClick={() => setShowDeactivateModal(true)}
                  >
                    Deactivate
                  </button>
                </div>

                <div className="danger-zone-row danger-zone-row--bordered">
                  <div>
                    <p className="danger-action-label text-danger">Delete Account</p>
                    <p className="danger-action-desc">This will delete your account. You have 7 days to restore it.</p>
                  </div>
                  <button
                    className="danger-action-btn danger-action-btn--danger"
                    onClick={() => setShowDeleteModal(true)}
                  >
                    Delete Account
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Delete account confirmation modal */}
      {showDeleteModal && (
        <div className="overlay-bg" onClick={() => { setShowDeleteModal(false); setDeletePassword(''); }}>
          <div className="inline-modal delete-modal" onClick={e => e.stopPropagation()}>
            <p className="delete-modal-title">Delete Account</p>
            <p className="delete-modal-desc">
              This will delete your account. You have 7 days to restore it using the restore token provided after deletion.
            </p>
            <label className="delete-modal-label">Enter your password to confirm</label>
            <div className="profile-input-wrapper">
              <input
                type={showDeletePassword ? 'text' : 'password'}
                className="delete-modal-input"
                value={deletePassword}
                onChange={e => setDeletePassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleDeleteAccount()}
                placeholder="Password"
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowDeletePassword(p => !p)}
                className="password-toggle-btn"
                aria-label={showDeletePassword ? 'Hide password' : 'Show password'}
              >
                {showDeletePassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            <div className="delete-modal-actions">
              <button
                className={`delete-confirm-btn ${(!deletePassword.trim() || deleting) ? 'delete-confirm-btn--disabled' : ''}`}
                onClick={handleDeleteAccount}
                disabled={!deletePassword.trim() || deleting}
              >
                {deleting ? '...' : 'Delete Account'}
              </button>
              <button
                className="delete-cancel-btn"
                onClick={() => { setShowDeleteModal(false); setDeletePassword(''); }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deactivate account confirmation modal */}
      {showDeactivateModal && (
        <div className="overlay-bg" onClick={() => { setShowDeactivateModal(false); setDeactivatePassword(''); }}>
          <div className="inline-modal delete-modal" onClick={e => e.stopPropagation()}>
            <p className="delete-modal-title">Deactivate Account</p>
            <p className="delete-modal-desc">
              Deactivating hides your profile from everyone, including your matches. You can reactivate within 30 days. After 30 days your account is permanently deleted.
            </p>
            <label className="delete-modal-label">Enter your password to confirm</label>
            <div className="profile-input-wrapper">
              <input
                type={showDeactivatePassword ? 'text' : 'password'}
                className="delete-modal-input"
                value={deactivatePassword}
                onChange={e => setDeactivatePassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleDeactivateAccount()}
                placeholder="Password"
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowDeactivatePassword(p => !p)}
                className="password-toggle-btn"
                aria-label={showDeactivatePassword ? 'Hide password' : 'Show password'}
              >
                {showDeactivatePassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            <div className="delete-modal-actions">
              <button
                className={`deactivate-confirm-btn ${(!deactivatePassword.trim() || deactivating) ? 'delete-confirm-btn--disabled' : ''}`}
                onClick={handleDeactivateAccount}
                disabled={!deactivatePassword.trim() || deactivating}
              >
                {deactivating ? '...' : 'Deactivate Account'}
              </button>
              <button
                className="delete-cancel-btn"
                onClick={() => { setShowDeactivateModal(false); setDeactivatePassword(''); }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Restore token notice */}
      {restoreToken && (
        <div className="overlay-bg">
          <div className="inline-modal">
            <p className="delete-modal-title">Account Deleted</p>
            <p className="delete-modal-desc">
              Save this token to restore your account within 7 days:
            </p>
            <div className="restore-token-box">
              <code className="restore-token-code">{restoreToken}</code>
              <button
                className="restore-token-copy-btn"
                onClick={() => { navigator.clipboard.writeText(restoreToken); setTokenCopied(true); }}
              >
                {tokenCopied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <button
              className="restore-token-continue-btn"
              onClick={() => { setRestoreToken(null); navigate('/login'); }}
            >
              Continue to Login
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
