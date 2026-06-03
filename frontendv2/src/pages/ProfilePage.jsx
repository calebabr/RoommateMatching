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
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, LIFESTYLE_TAGS } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { updateUser, uploadPhoto, getPhotoUrl, getBlockedUsers, unblockUser, exportUserData, deleteAccount } from '../services/api';
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
  const [photoFile,    setPhotoFile]    = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [selectedTags, setSelectedTags] = useState(user?.lifestyleTags || []);
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
      const payload = { username: user.username, gender: user.gender || 'male', bio: bio.trim(), lifestyleTags: selectedTags, ...preferences };
      await updateUser(user.id, payload);
      if (photoFile) { await uploadPhoto(user.id, photoFile); }
      await refreshUser();
      setEditing(false); setPhotoFile(null); setPhotoPreview(null);
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
    setPreferences(CATEGORIES.reduce((acc, cat) => {
      acc[cat.key] = { value: user?.[cat.key]?.value ?? Math.round((cat.max - cat.min) / 2), isDealBreaker: user?.[cat.key]?.isDealBreaker ?? false };
      return acc;
    }, {}));
  };

  // Load blocked users on mount
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
      await logout();
      if (!result.restore_token) navigate('/login');
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not delete account. Check your password.' });
    } finally {
      setDeleting(false);
    }
  };

  if (!user) return null;

  const displayPhotoUrl = photoPreview || getPhotoUrl(user.photoUrl);
  const matchCount = user?.matchCount ?? (user?.matched ? 1 : 0);
  const genderLabel = user.gender === 'female' ? '♀ Female' : user.gender === 'male' ? '♂ Male' : '';

  return (
    <div style={{ height: '100%', overflowY: 'auto', backgroundColor: Colors.bg }}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} onConfirm={modal.onConfirm} confirmText={modal.confirmText} danger={modal.danger} />}
      <input ref={fileInputRef}   type="file" accept="image/*"           onChange={handleFileChange} style={{ display: 'none' }} />
      <input ref={cameraInputRef} type="file" accept="image/*" capture="user" onChange={handleFileChange} style={{ display: 'none' }} />

      <div style={S.page}>
        {/* Top bar */}
        <div style={S.topBar}>
          <span style={{ fontSize: 24, fontWeight: 800, color: Colors.textPrimary }}>Profile</span>
          <NotificationBell />
        </div>

        <div style={S.cols}>
          {/* ── Left column: avatar + info ── */}
          <div style={S.leftCol}>
            <div style={S.avatarCard}>
              {displayPhotoUrl ? (
                <img src={displayPhotoUrl} alt="avatar" style={S.avatarImage} />
              ) : (
                <div style={S.avatarLarge}>
                  <span style={{ fontSize: 36, fontWeight: 800, color: Colors.accent }}>
                    {(user.username || '?')[0].toUpperCase()}
                  </span>
                </div>
              )}

              {editing && (
                <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
                  <button onClick={() => fileInputRef.current.click()} style={S.photoEditBtn}>🖼️ Gallery</button>
                  <button onClick={() => cameraInputRef.current.click()} style={S.photoEditBtn}>📷 Camera</button>
                  {(photoFile || user.photoUrl) && (
                    <button onClick={() => { setPhotoFile(null); setPhotoPreview(null); }} style={{ ...S.photoEditBtn, borderColor: Colors.danger, color: Colors.danger }}>✕</button>
                  )}
                </div>
              )}

              <p style={{ fontSize: 22, fontWeight: 800, color: Colors.textPrimary, margin: '0 0 4px', textAlign: 'center' }}>{user.username}</p>
              <p style={{ fontSize: 13, color: Colors.textMuted, margin: 0 }}>ID: {user.id}</p>

              {genderLabel && (
                <span style={{ marginTop: 8, backgroundColor: Colors.infoDim, padding: '4px 12px', borderRadius: Radius.full, border: `1px solid ${Colors.info}`, fontSize: 12, fontWeight: 600, color: Colors.info }}>
                  {genderLabel}
                </span>
              )}

              {user.bio && <p style={{ fontSize: 14, color: Colors.textSecondary, textAlign: 'center', marginTop: 10, lineHeight: '20px' }}>{user.bio}</p>}

              {(user.lifestyleTags || []).length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6, marginTop: 10 }}>
                  {(user.lifestyleTags || []).map(tag => (
                    <span key={tag} style={{ backgroundColor: Colors.accentGlow, padding: '3px 10px', borderRadius: Radius.full, border: `1px solid ${Colors.accent}`, fontSize: 11, fontWeight: 600, color: Colors.accent }}>{tag}</span>
                  ))}
                </div>
              )}

              <span style={{ marginTop: 12, padding: '5px 14px', borderRadius: Radius.full, border: `1px solid ${matchCount > 0 ? Colors.success : Colors.accent}`, backgroundColor: matchCount > 0 ? Colors.successDim : Colors.accentGlow, fontSize: 12, fontWeight: 600, color: matchCount > 0 ? Colors.success : Colors.accent, textAlign: 'center' }}>
                {matchCount > 0 ? `Matched with ${matchCount} roommate${matchCount > 1 ? 's' : ''}` : 'Searching for roommate'}
              </span>

              <div style={{ width: '100%', marginTop: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button style={S.logoutBtn} onClick={logout}>Log Out</button>
              </div>
            </div>
          </div>

          {/* ── Right column: bio/tags edit + preferences ── */}
          <div style={S.rightCol}>
            {editing && (
              <>
                <div style={S.section}>
                  <p style={S.sectionTitle}>Profile Info</p>
                  <label style={S.label}>Bio</label>
                  <textarea style={{ ...S.input, minHeight: 80, resize: 'vertical', paddingTop: 14 }} value={bio} onChange={e => setBio(e.target.value)} maxLength={200} placeholder="A short intro about yourself..." />
                  <p style={{ textAlign: 'right', fontSize: 11, color: Colors.textMuted, margin: '4px 0 0' }}>{bio.length}/200</p>
                </div>

                <div style={S.section}>
                  <p style={S.sectionTitle}>Lifestyle Tags</p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {LIFESTYLE_TAGS.map(tag => {
                      const sel = selectedTags.includes(tag);
                      return (
                        <button key={tag} onClick={() => toggleTag(tag)} style={{ padding: '7px 13px', borderRadius: Radius.full, border: `1.5px solid ${sel ? Colors.accent : Colors.border}`, backgroundColor: sel ? Colors.accentGlow : Colors.bgCard, fontSize: 13, fontWeight: 600, color: sel ? Colors.accent : Colors.textSecondary, cursor: 'pointer' }}>
                          {tag}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </>
            )}

            <div style={S.section}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <span style={{ fontSize: 18, fontWeight: 700, color: Colors.textPrimary }}>Your Preferences</span>
                {!editing && <button style={{ background: 'none', border: 'none', fontSize: 15, fontWeight: 600, color: Colors.accent, cursor: 'pointer' }} onClick={() => setEditing(true)}>Edit</button>}
              </div>

              <div style={S.prefGrid}>
                {CATEGORIES.map(cat => {
                  const pref = editing ? preferences[cat.key] : user[cat.key];
                  if (!pref) return null;
                  return (
                    <div key={cat.key} style={S.prefCard}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: Colors.textPrimary }}>{cat.label}</span>
                        {pref.isDealBreaker && !editing && (
                          <span style={{ backgroundColor: Colors.dangerDim, padding: '2px 8px', borderRadius: Radius.full, fontSize: 10, fontWeight: 700, color: Colors.danger, textTransform: 'uppercase' }}>Deal-breaker</span>
                        )}
                      </div>
                      {editing ? (
                        <>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                            <span style={{ fontSize: 12, color: Colors.danger }}>Deal-breaker</span>
                            <Toggle value={preferences[cat.key].isDealBreaker} onChange={v => updatePref(cat.key, 'isDealBreaker', v)} />
                          </div>
                          <SliderPicker min={cat.min} max={cat.max} value={preferences[cat.key].value} onChange={v => updatePref(cat.key, 'value', v)} formatLabel={cat.formatValue} />
                        </>
                      ) : (
                        <>
                          <p style={{ fontSize: 14, fontWeight: 700, color: Colors.accent, margin: '0 0 8px' }}>{cat.formatValue(pref.value)}</p>
                          <div style={{ height: 5, backgroundColor: Colors.border, borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${(pref.value / cat.max) * 100}%`, backgroundColor: Colors.accent, borderRadius: 3 }} />
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>

              {editing && (
                <div style={{ marginTop: 16, display: 'flex', gap: 10 }}>
                  <button style={S.saveBtn} onClick={handleSave} disabled={saving}>
                    {saving ? <Spinner size={18} color={Colors.black} /> : 'Save Changes'}
                  </button>
                  <button style={S.cancelBtn} onClick={handleCancel}>Cancel</button>
                </div>
              )}
            </div>

            {/* ── Blocked Users ── */}
            {blockedUsers.length > 0 && (
              <div style={{ ...S.section, marginTop: 28 }}>
                <p style={S.sectionTitle}>Blocked Users</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {blockedUsers.map(bu => (
                    <div key={bu.id} style={{ display: 'flex', alignItems: 'center', gap: 12, backgroundColor: Colors.bgCard, borderRadius: Radius.md, padding: '12px 16px', border: `1px solid ${Colors.border}` }}>
                      <div style={{ width: 36, height: 36, borderRadius: '50%', backgroundColor: Colors.bgCardLight, border: `2px solid ${Colors.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, overflow: 'hidden' }}>
                        {bu.photoUrl
                          ? <img src={bu.photoUrl.startsWith('http') ? bu.photoUrl : getPhotoUrl(bu.photoUrl)} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          : <span style={{ fontSize: 16, fontWeight: 700, color: Colors.textMuted }}>{(bu.username || '?')[0].toUpperCase()}</span>
                        }
                      </div>
                      <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: Colors.textPrimary }}>{bu.username}</span>
                      <button
                        style={{ padding: '7px 14px', borderRadius: Radius.md, border: `1px solid ${Colors.border}`, backgroundColor: 'transparent', fontSize: 13, fontWeight: 600, color: Colors.textSecondary, cursor: 'pointer', opacity: unblockingId === bu.id ? 0.5 : 1 }}
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
            <div style={S.dangerZone}>
              <p style={{ fontSize: 16, fontWeight: 700, color: Colors.danger, margin: '0 0 14px' }}>Danger Zone</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600, color: Colors.textPrimary, margin: '0 0 2px' }}>Export My Data</p>
                    <p style={{ fontSize: 12, color: Colors.textMuted, margin: 0 }}>Download a JSON copy of all your account data.</p>
                  </div>
                  <button
                    style={{ ...S.dangerActionBtn, borderColor: Colors.textMuted, color: Colors.textSecondary, opacity: exporting ? 0.6 : 1 }}
                    onClick={handleExport}
                    disabled={exporting}
                  >
                    {exporting ? '...' : 'Export Data'}
                  </button>
                </div>
                <div style={{ borderTop: `1px solid ${Colors.border}`, paddingTop: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600, color: Colors.danger, margin: '0 0 2px' }}>Delete Account</p>
                    <p style={{ fontSize: 12, color: Colors.textMuted, margin: 0 }}>This will delete your account. You have 7 days to restore it.</p>
                  </div>
                  <button
                    style={{ ...S.dangerActionBtn, borderColor: Colors.danger, color: Colors.danger }}
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
        <div style={S.overlayBg} onClick={() => { setShowDeleteModal(false); setDeletePassword(''); }}>
          <div style={S.inlineModal} onClick={e => e.stopPropagation()}>
            <p style={{ fontSize: 17, fontWeight: 700, color: Colors.textPrimary, margin: '0 0 8px' }}>Delete Account</p>
            <p style={{ fontSize: 14, color: Colors.textSecondary, margin: '0 0 16px', lineHeight: '20px' }}>
              This will delete your account. You have 7 days to restore it using the restore token provided after deletion.
            </p>
            <label style={S.modalLabel}>Enter your password to confirm</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showDeletePassword ? 'text' : 'password'}
                style={{ ...S.modalInput, paddingRight: 40 }}
                value={deletePassword}
                onChange={e => setDeletePassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleDeleteAccount()}
                placeholder="Password"
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowDeletePassword(p => !p)}
                style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: '#888', display: 'flex', alignItems: 'center' }}
                aria-label={showDeletePassword ? 'Hide password' : 'Show password'}
              >
                {showDeletePassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
              <button
                style={{ ...S.modalActionBtn, backgroundColor: Colors.danger, color: Colors.white, opacity: (!deletePassword.trim() || deleting) ? 0.5 : 1 }}
                onClick={handleDeleteAccount}
                disabled={!deletePassword.trim() || deleting}
              >
                {deleting ? '...' : 'Delete Account'}
              </button>
              <button
                style={{ ...S.modalActionBtn, backgroundColor: 'transparent', border: `1.5px solid ${Colors.border}`, color: Colors.textSecondary }}
                onClick={() => { setShowDeleteModal(false); setDeletePassword(''); }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Restore token notice (shown after deletion, before redirect) */}
      {restoreToken && (
        <div style={S.overlayBg}>
          <div style={S.inlineModal}>
            <p style={{ fontSize: 17, fontWeight: 700, color: Colors.textPrimary, margin: '0 0 8px' }}>Account Deleted</p>
            <p style={{ fontSize: 14, color: Colors.textSecondary, margin: '0 0 12px', lineHeight: '20px' }}>
              Save this token to restore your account within 7 days:
            </p>
            <div style={{ backgroundColor: Colors.bgInput, borderRadius: Radius.md, padding: '11px 14px', border: `1px solid ${Colors.border}`, display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <code style={{ flex: 1, fontSize: 12, color: Colors.accent, wordBreak: 'break-all' }}>{restoreToken}</code>
              <button
                style={{ flexShrink: 0, padding: '6px 12px', borderRadius: Radius.md, border: `1px solid ${Colors.accent}`, backgroundColor: Colors.accentGlow, fontSize: 12, fontWeight: 600, color: Colors.accent, cursor: 'pointer' }}
                onClick={() => { navigator.clipboard.writeText(restoreToken); setTokenCopied(true); }}
              >
                {tokenCopied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <button
              style={{ width: '100%', backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '12px 0', fontSize: 14, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer' }}
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

const S = {
  page:       { padding: '28px 32px 60px', maxWidth: 1400 },
  topBar:     { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 },
  cols:       { display: 'flex', gap: 28, alignItems: 'flex-start' },
  leftCol:    { width: 280, flexShrink: 0 },
  rightCol:   { flex: 1, minWidth: 0 },
  avatarCard: { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 24, border: `1px solid ${Colors.border}`, display: 'flex', flexDirection: 'column', alignItems: 'center' },
  avatarLarge:{ width: 88, height: 88, borderRadius: '50%', backgroundColor: Colors.accentGlow, display: 'flex', alignItems: 'center', justifyContent: 'center', border: `3px solid ${Colors.accent}`, marginBottom: 16 },
  avatarImage:{ width: 88, height: 88, borderRadius: '50%', objectFit: 'cover', border: `3px solid ${Colors.accent}`, marginBottom: 16 },
  photoEditBtn:{ padding: '6px 12px', borderRadius: Radius.full, border: `1px solid ${Colors.accent}`, backgroundColor: Colors.accentGlow, fontSize: 12, fontWeight: 600, color: Colors.accent, cursor: 'pointer' },
  section:    { marginBottom: 28 },
  sectionTitle:{ fontSize: 18, fontWeight: 700, color: Colors.textPrimary, margin: '0 0 14px' },
  label:      { display: 'block', fontSize: 12, fontWeight: 600, color: Colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.8 },
  input:      { width: '100%', backgroundColor: Colors.bgInput, borderRadius: Radius.md, padding: '13px 16px', fontSize: 15, color: Colors.textPrimary, border: `1px solid ${Colors.border}`, outline: 'none' },
  prefGrid:   { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 },
  prefCard:   { backgroundColor: Colors.bgCard, borderRadius: Radius.md, padding: 16, border: `1px solid ${Colors.border}` },
  saveBtn:    { flex: 1, backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '13px 0', fontSize: 14, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  cancelBtn:  { flex: 1, backgroundColor: 'transparent', border: `1.5px solid ${Colors.border}`, borderRadius: Radius.md, padding: '13px 0', fontSize: 14, fontWeight: 600, color: Colors.textSecondary, cursor: 'pointer' },
  logoutBtn:  { width: '100%', backgroundColor: Colors.bgCardLight, border: `1px solid ${Colors.border}`, borderRadius: Radius.md, padding: '12px 0', fontSize: 14, fontWeight: 600, color: Colors.textPrimary, cursor: 'pointer' },
  dangerZone:   { marginTop: 28, padding: 20, borderRadius: Radius.lg, border: `1.5px solid ${Colors.danger}`, backgroundColor: Colors.dangerDim },
  dangerActionBtn: { flexShrink: 0, padding: '9px 16px', borderRadius: Radius.md, border: '1.5px solid', backgroundColor: 'transparent', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  overlayBg:   { position: 'fixed', inset: 0, zIndex: 9999, backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 },
  inlineModal: { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 24, width: '100%', maxWidth: 420, border: `1px solid ${Colors.border}` },
  modalLabel:  { display: 'block', fontSize: 12, fontWeight: 600, color: Colors.textSecondary, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.8 },
  modalInput:  { width: '100%', backgroundColor: Colors.bgInput, borderRadius: Radius.md, padding: '12px 14px', fontSize: 14, color: Colors.textPrimary, border: `1px solid ${Colors.border}`, outline: 'none', boxSizing: 'border-box' },
  modalActionBtn: { flex: 1, borderRadius: Radius.md, padding: '12px 0', fontSize: 14, fontWeight: 600, border: 'none', cursor: 'pointer' },
};
