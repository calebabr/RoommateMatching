import React, { useState, useRef } from 'react';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, LIFESTYLE_TAGS } from '../utils/categories';
import { useAuth } from '../context/AuthContext';
import { updateUser, deleteUser, uploadPhoto, getPhotoUrl } from '../services/api';
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
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

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
      if (photoFile) { try { await uploadPhoto(user.id, photoFile); } catch {} }
      await refreshUser();
      setEditing(false);
      setPhotoFile(null);
      setPhotoPreview(null);
      setModal({ title: 'Saved', message: 'Your profile has been updated.' });
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not update profile.' });
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditing(false);
    setPhotoFile(null);
    setPhotoPreview(null);
    setBio(user?.bio || '');
    setSelectedTags(user?.lifestyleTags || []);
    setPreferences(CATEGORIES.reduce((acc, cat) => {
      acc[cat.key] = { value: user?.[cat.key]?.value ?? Math.round((cat.max - cat.min) / 2), isDealBreaker: user?.[cat.key]?.isDealBreaker ?? false };
      return acc;
    }, {}));
  };

  const handleDelete = () => {
    setModal({
      title: 'Delete Account',
      message: 'This will permanently delete your account, matches, and all data. This cannot be undone.',
      danger: true,
      confirmText: 'Delete',
      onConfirm: async () => {
        try { await deleteUser(user.id); await logout(); }
        catch { setModal({ title: 'Error', message: 'Could not delete account.' }); }
      },
    });
  };

  if (!user) return null;

  const displayPhotoUrl = photoPreview || getPhotoUrl(user.photoUrl);
  const matchCount = user?.matchCount ?? (user?.matched ? 1 : 0);
  const genderLabel = user.gender === 'female' ? '♀ Female' : user.gender === 'male' ? '♂ Male' : '';

  return (
    <div style={{ backgroundColor: Colors.bg, minHeight: '100%' }}>
      {modal && <Modal title={modal.title} message={modal.message} onClose={() => setModal(null)} onConfirm={modal.onConfirm} confirmText={modal.confirmText} danger={modal.danger} />}
      <input ref={fileInputRef}   type="file" accept="image/*"           onChange={handleFileChange} style={{ display: 'none' }} />
      <input ref={cameraInputRef} type="file" accept="image/*" capture="user" onChange={handleFileChange} style={{ display: 'none' }} />

      <div style={S.scroll}>
        {/* Top bar */}
        <div style={S.topBar}>
          <span style={{ fontSize: 28, fontWeight: 800, color: Colors.textPrimary }}>Profile</span>
          <NotificationBell />
        </div>

        {/* Avatar */}
        <div style={S.profileHeader}>
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
            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <button onClick={() => fileInputRef.current.click()} style={S.photoEditBtn}>🖼️ Gallery</button>
              <button onClick={() => cameraInputRef.current.click()} style={S.photoEditBtn}>📷 Camera</button>
              {(photoFile || user.photoUrl) && (
                <button onClick={() => { setPhotoFile(null); setPhotoPreview(null); }} style={{ ...S.photoEditBtn, borderColor: Colors.danger, color: Colors.danger }}>✕</button>
              )}
            </div>
          )}

          <p style={{ fontSize: 26, fontWeight: 800, color: Colors.textPrimary, margin: '0 0 4px' }}>{user.username}</p>
          <p style={{ fontSize: 14, color: Colors.textMuted, margin: 0 }}>ID: {user.id}</p>

          {genderLabel && (
            <span style={{ marginTop: 8, backgroundColor: Colors.infoDim, padding: '5px 14px', borderRadius: Radius.full, border: `1px solid ${Colors.info}`, fontSize: 13, fontWeight: 600, color: Colors.info }}>
              {genderLabel}
            </span>
          )}

          {user.bio && <p style={{ fontSize: 14, color: Colors.textSecondary, textAlign: 'center', marginTop: 10, lineHeight: '20px', paddingLeft: 12, paddingRight: 12 }}>{user.bio}</p>}

          {(user.lifestyleTags || []).length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6, marginTop: 12 }}>
              {(user.lifestyleTags || []).map(tag => (
                <span key={tag} style={{ backgroundColor: Colors.accentGlow, padding: '4px 10px', borderRadius: Radius.full, border: `1px solid ${Colors.accent}`, fontSize: 12, fontWeight: 600, color: Colors.accent }}>
                  {tag}
                </span>
              ))}
            </div>
          )}

          <span style={{ marginTop: 14, padding: '6px 16px', borderRadius: Radius.full, border: `1px solid ${matchCount > 0 ? Colors.success : Colors.accent}`, backgroundColor: matchCount > 0 ? Colors.successDim : Colors.accentGlow, fontSize: 13, fontWeight: 600, color: matchCount > 0 ? Colors.success : Colors.accent }}>
            {matchCount > 0 ? `Matched with ${matchCount} roommate${matchCount > 1 ? 's' : ''}` : 'Searching for roommate'}
          </span>
        </div>

        {/* Bio edit */}
        {editing && (
          <div style={S.section}>
            <p style={S.sectionTitle}>Profile Info</p>
            <div style={S.inputGroup}>
              <label style={S.label}>Bio</label>
              <textarea style={{ ...S.input, minHeight: 80, resize: 'vertical', paddingTop: 14 }} value={bio} onChange={e => setBio(e.target.value)} maxLength={200} placeholder="A short intro about yourself..." />
              <p style={{ textAlign: 'right', fontSize: 11, color: Colors.textMuted, margin: '4px 0 0' }}>{bio.length}/200</p>
            </div>
          </div>
        )}

        {/* Tag edit */}
        {editing && (
          <div style={S.section}>
            <p style={S.sectionTitle}>Lifestyle Tags</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {LIFESTYLE_TAGS.map(tag => {
                const sel = selectedTags.includes(tag);
                return (
                  <button key={tag} onClick={() => toggleTag(tag)} style={{ padding: '8px 14px', borderRadius: Radius.full, border: `1.5px solid ${sel ? Colors.accent : Colors.border}`, backgroundColor: sel ? Colors.accentGlow : Colors.bgCard, fontSize: 13, fontWeight: 600, color: sel ? Colors.accent : Colors.textSecondary, cursor: 'pointer' }}>
                    {tag}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Preferences */}
        <div style={S.section}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: Colors.textPrimary }}>Your Preferences</span>
            {!editing && <button style={{ background: 'none', border: 'none', fontSize: 15, fontWeight: 600, color: Colors.accent, cursor: 'pointer' }} onClick={() => setEditing(true)}>Edit</button>}
          </div>

          {CATEGORIES.map(cat => {
            const pref = editing ? preferences[cat.key] : user[cat.key];
            if (!pref) return null;
            return (
              <div key={cat.key} style={S.prefCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <span style={{ fontSize: 15, fontWeight: 600, color: Colors.textPrimary }}>{cat.label}</span>
                  {pref.isDealBreaker && !editing && (
                    <span style={{ backgroundColor: Colors.dangerDim, padding: '2px 8px', borderRadius: Radius.full, fontSize: 10, fontWeight: 700, color: Colors.danger, textTransform: 'uppercase' }}>Deal-breaker</span>
                  )}
                </div>
                {editing ? (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <span style={{ fontSize: 13, color: Colors.danger }}>Mark as deal-breaker</span>
                      <Toggle value={preferences[cat.key].isDealBreaker} onChange={v => updatePref(cat.key, 'isDealBreaker', v)} />
                    </div>
                    <SliderPicker min={cat.min} max={cat.max} value={preferences[cat.key].value} onChange={v => updatePref(cat.key, 'value', v)} formatLabel={cat.formatValue} />
                  </>
                ) : (
                  <>
                    <p style={{ fontSize: 15, fontWeight: 700, color: Colors.accent, margin: '0 0 8px' }}>{cat.formatValue(pref.value)}</p>
                    <div style={{ height: 6, backgroundColor: Colors.border, borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${(pref.value / cat.max) * 100}%`, backgroundColor: Colors.accent, borderRadius: 3 }} />
                    </div>
                  </>
                )}
              </div>
            );
          })}

          {editing && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <button style={S.saveBtn} onClick={handleSave} disabled={saving}>
                {saving ? <Spinner size={20} color={Colors.black} /> : 'Save Changes'}
              </button>
              <button style={S.cancelBtn} onClick={handleCancel}>Cancel</button>
            </div>
          )}
        </div>

        {/* Account */}
        <div style={S.section}>
          <p style={S.sectionTitle}>Account</p>
          <button style={S.logoutBtn}  onClick={logout}>Log Out</button>
          <button style={S.deleteBtn}  onClick={handleDelete}>Delete Account</button>
        </div>
      </div>
    </div>
  );
}

const S = {
  scroll: { padding: '24px 24px 60px', maxWidth: 600, margin: '0 auto' },
  topBar: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  profileHeader: { display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 32 },
  avatarLarge: { width: 88, height: 88, borderRadius: '50%', backgroundColor: Colors.accentGlow, display: 'flex', alignItems: 'center', justifyContent: 'center', border: `3px solid ${Colors.accent}`, marginBottom: 16 },
  avatarImage: { width: 88, height: 88, borderRadius: '50%', objectFit: 'cover', border: `3px solid ${Colors.accent}`, marginBottom: 16 },
  photoEditBtn: { padding: '8px 14px', borderRadius: Radius.full, border: `1px solid ${Colors.accent}`, backgroundColor: Colors.accentGlow, fontSize: 13, fontWeight: 600, color: Colors.accent, cursor: 'pointer' },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 18, fontWeight: 700, color: Colors.textPrimary, margin: '0 0 14px' },
  inputGroup: { marginBottom: 16 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, color: Colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.8 },
  input: { width: '100%', backgroundColor: Colors.bgInput, borderRadius: Radius.md, padding: '14px 16px', fontSize: 16, color: Colors.textPrimary, border: `1px solid ${Colors.border}`, outline: 'none' },
  prefCard: { backgroundColor: Colors.bgCard, borderRadius: Radius.md, padding: 16, marginBottom: 10, border: `1px solid ${Colors.border}` },
  saveBtn: { width: '100%', backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '14px 0', fontSize: 15, fontWeight: 700, color: Colors.black, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  cancelBtn: { width: '100%', backgroundColor: 'transparent', border: `1.5px solid ${Colors.border}`, borderRadius: Radius.md, padding: '14px 0', fontSize: 15, fontWeight: 600, color: Colors.textSecondary, cursor: 'pointer' },
  logoutBtn: { width: '100%', backgroundColor: Colors.bgCard, border: `1px solid ${Colors.border}`, borderRadius: Radius.md, padding: '14px 0', fontSize: 15, fontWeight: 600, color: Colors.textPrimary, cursor: 'pointer', marginBottom: 10 },
  deleteBtn: { width: '100%', backgroundColor: 'transparent', border: `1.5px solid ${Colors.danger}`, borderRadius: Radius.md, padding: '14px 0', fontSize: 15, fontWeight: 600, color: Colors.danger, cursor: 'pointer' },
};
