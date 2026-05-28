import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Colors, Radius } from '../utils/theme';
import { CATEGORIES, LIFESTYLE_TAGS } from '../utils/categories';
import { uploadPhoto, setApiBase } from '../services/api';
import { useAuth } from '../context/AuthContext';
import SliderPicker from '../components/SliderPicker';
import Toggle from '../components/Toggle';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

export default function SignupPage() {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [step, setStep]   = useState(0);
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [gender,   setGender]   = useState('');
  const [bio,      setBio]      = useState('');
  const [photoFile,    setPhotoFile]    = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [selectedTags, setSelectedTags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modal,   setModal]   = useState(null);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const [preferences, setPreferences] = useState(
    CATEGORIES.reduce((acc, cat) => {
      acc[cat.key] = { value: Math.round((cat.max - cat.min) / 2), isDealBreaker: false };
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

  const handleCreate = async () => {
    if (!email.trim())    { setModal({ title: 'Missing Email', message: 'Please enter your email address.' }); return; }
    if (!password)        { setModal({ title: 'Missing Password', message: 'Please enter a password.' }); return; }
    if (!username.trim()) { setModal({ title: 'Missing Name', message: 'Please enter a username.' }); return; }
    if (!gender)          { setModal({ title: 'Missing Gender', message: 'Please select your gender.' }); return; }
    setLoading(true);
    try {
      const profileData = { username: username.trim(), gender, bio: bio.trim(), lifestyleTags: selectedTags, ...preferences };
      const created = await signup(email.trim(), password, profileData);
      if (photoFile) {
        try { const r = await uploadPhoto(created.id, photoFile); created.photoUrl = r.photoUrl; }
        catch {}
      }
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not create account.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={S.page}>
      {modal && (
        <Modal
          title={modal.title} message={modal.message}
          onClose={() => setModal(null)}
          onConfirm={modal.onConfirm}
          confirmText="Continue"
        />
      )}

      {/* Header */}
      <div style={S.header}>
        <button style={S.backBtn} onClick={() => step === 0 ? navigate('/login') : setStep(s => s - 1)}>
          ← Back
        </button>
        <div style={S.stepRow}>
          {[0, 1, 2].map((i) => (
            <React.Fragment key={i}>
              {i > 0 && <div style={{ ...S.dotLine, ...(step >= i ? S.dotLineActive : {}) }} />}
              <div style={{ ...S.dot, ...(step >= i ? S.dotActive : {}) }} />
            </React.Fragment>
          ))}
        </div>
      </div>

      <div style={S.scroll}>
        {step === 0 && (
          <>
            <h2 style={S.title}>Create Your Profile</h2>
            <p style={S.subtitle}>Tell potential roommates about yourself</p>

            <div style={S.inputGroup}>
              <label style={S.label}>Email</label>
              <input style={S.input} placeholder="you@example.com" type="email" value={email} onChange={e => setEmail(e.target.value)} />
            </div>

            <div style={S.inputGroup}>
              <label style={S.label}>Password</label>
              <input style={S.input} placeholder="Choose a password" type="password" value={password} onChange={e => setPassword(e.target.value)} />
            </div>

            <div style={S.inputGroup}>
              <label style={S.label}>Username</label>
              <input style={S.input} placeholder="Enter a unique username" value={username} onChange={e => setUsername(e.target.value)} />
            </div>

            <div style={S.inputGroup}>
              <label style={S.label}>Gender</label>
              <p style={{ fontSize: 12, color: Colors.textMuted, fontStyle: 'italic', margin: '0 0 12px' }}>
                You'll only be matched with roommates of the same gender
              </p>
              <div style={{ display: 'flex', gap: 12 }}>
                {['male', 'female'].map(g => (
                  <button key={g} onClick={() => setGender(g)} style={{
                    flex: 1, padding: '20px 0',
                    borderRadius: Radius.lg, cursor: 'pointer',
                    border: `2px solid ${gender === g ? Colors.accent : Colors.border}`,
                    backgroundColor: gender === g ? Colors.accentGlow : Colors.bgCard,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                  }}>
                    <span style={{ fontSize: 36 }}>{g === 'male' ? '👨' : '👩'}</span>
                    <span style={{ fontSize: 16, fontWeight: 700, color: gender === g ? Colors.accent : Colors.textSecondary }}>
                      {g === 'male' ? 'Male' : 'Female'}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div style={S.inputGroup}>
              <label style={S.label}>Bio</label>
              <textarea
                style={{ ...S.input, minHeight: 80, resize: 'vertical', paddingTop: 14 }}
                placeholder="A short intro — what are you like as a roommate?"
                value={bio} onChange={e => setBio(e.target.value)}
                maxLength={200}
              />
              <p style={{ textAlign: 'right', fontSize: 11, color: Colors.textMuted, margin: '4px 0 0' }}>{bio.length}/200</p>
            </div>

            <div style={S.inputGroup}>
              <label style={S.label}>Profile Photo (optional)</label>
              <input ref={fileInputRef}    type="file" accept="image/*"          onChange={handleFileChange} style={{ display: 'none' }} />
              <input ref={cameraInputRef}  type="file" accept="image/*" capture="user" onChange={handleFileChange} style={{ display: 'none' }} />
              {photoPreview ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, marginTop: 12 }}>
                  <img src={photoPreview} alt="preview" style={{ width: 100, height: 100, borderRadius: '50%', objectFit: 'cover', border: `3px solid ${Colors.accent}` }} />
                  <button onClick={() => { setPhotoFile(null); setPhotoPreview(null); }} style={{ ...S.smallBtn, borderColor: Colors.danger, color: Colors.danger }}>
                    ✕ Remove
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                  <button onClick={() => fileInputRef.current.click()} style={S.photoPickerBtn}>
                    <span style={{ fontSize: 28 }}>🖼️</span>
                    <span style={{ fontSize: 13, fontWeight: 600, color: Colors.textSecondary }}>Choose Photo</span>
                  </button>
                  <button onClick={() => cameraInputRef.current.click()} style={S.photoPickerBtn}>
                    <span style={{ fontSize: 28 }}>📷</span>
                    <span style={{ fontSize: 13, fontWeight: 600, color: Colors.textSecondary }}>Take Photo</span>
                  </button>
                </div>
              )}
            </div>

            <button
              style={{ ...S.button, ...(!email.trim() || !password || !username.trim() || !gender ? S.buttonDisabled : {}) }}
              onClick={() => {
                if (!email.trim())    { setModal({ title: 'Missing Email', message: 'Please enter your email address.' }); return; }
                if (!password)        { setModal({ title: 'Missing Password', message: 'Please enter a password.' }); return; }
                if (!username.trim()) { setModal({ title: 'Missing Name', message: 'Please enter a username.' }); return; }
                if (!gender)          { setModal({ title: 'Missing Gender', message: 'Please select your gender.' }); return; }
                setStep(1);
              }}
            >
              Next — Set Preferences
            </button>
          </>
        )}

        {step === 1 && (
          <>
            <h2 style={S.title}>Your Preferences</h2>
            <p style={S.subtitle}>Rate each category and mark deal-breakers</p>
            {CATEGORIES.map(cat => (
              <div key={cat.key} style={S.prefCard}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 16, fontWeight: 700, color: Colors.textPrimary }}>{cat.label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 11, color: Colors.danger, fontWeight: 600, textTransform: 'uppercase' }}>Deal-breaker</span>
                    <Toggle value={preferences[cat.key].isDealBreaker} onChange={v => updatePref(cat.key, 'isDealBreaker', v)} />
                  </div>
                </div>
                <p style={{ fontSize: 13, color: Colors.textSecondary, margin: '4px 0 16px' }}>{cat.description}</p>
                <SliderPicker
                  min={cat.min} max={cat.max}
                  value={preferences[cat.key].value}
                  onChange={v => updatePref(cat.key, 'value', v)}
                  formatLabel={cat.formatValue}
                />
              </div>
            ))}
            <button style={S.button} onClick={() => setStep(2)}>Next — Lifestyle Tags</button>
          </>
        )}

        {step === 2 && (
          <>
            <h2 style={S.title}>Lifestyle Tags</h2>
            <p style={S.subtitle}>Pick tags that describe you — shared tags boost your match score!</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 16 }}>
              {LIFESTYLE_TAGS.map(tag => {
                const sel = selectedTags.includes(tag);
                return (
                  <button key={tag} onClick={() => toggleTag(tag)} style={{
                    padding: '10px 16px', borderRadius: Radius.full,
                    border: `1.5px solid ${sel ? Colors.accent : Colors.border}`,
                    backgroundColor: sel ? Colors.accentGlow : Colors.bgCard,
                    fontSize: 14, fontWeight: 600,
                    color: sel ? Colors.accent : Colors.textSecondary,
                    cursor: 'pointer',
                  }}>
                    {tag}
                  </button>
                );
              })}
            </div>
            <p style={{ textAlign: 'center', fontSize: 13, color: Colors.textMuted, marginBottom: 8 }}>{selectedTags.length} selected</p>
            <button style={{ ...S.button, ...(loading ? S.buttonDisabled : {}) }} onClick={handleCreate} disabled={loading}>
              {loading ? <Spinner size={20} color={Colors.black} /> : 'Create Account'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

const S = {
  page:   { height: '100dvh', backgroundColor: Colors.bg, display: 'flex', flexDirection: 'column', maxWidth: 480, margin: '0 auto' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 20px 12px', flexShrink: 0 },
  backBtn:{ background: 'none', border: 'none', fontSize: 16, color: Colors.accent, fontWeight: 600, cursor: 'pointer' },
  stepRow:{ display: 'flex', alignItems: 'center' },
  dot:    { width: 10, height: 10, borderRadius: '50%', backgroundColor: Colors.border },
  dotActive: { backgroundColor: Colors.accent },
  dotLine: { width: 24, height: 2, backgroundColor: Colors.border, margin: '0 4px' },
  dotLineActive: { backgroundColor: Colors.accent },
  scroll: { flex: 1, overflowY: 'auto', padding: '0 24px 60px' },
  title:  { fontSize: 28, fontWeight: 800, color: Colors.textPrimary, margin: '8px 0 4px' },
  subtitle: { fontSize: 15, color: Colors.textSecondary, margin: '0 0 28px' },
  inputGroup: { marginBottom: 20 },
  label:  { display: 'block', fontSize: 13, fontWeight: 600, color: Colors.textSecondary, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.8 },
  input:  { width: '100%', backgroundColor: Colors.bgInput, borderRadius: Radius.md, padding: '14px 16px', fontSize: 16, color: Colors.textPrimary, border: `1px solid ${Colors.border}`, outline: 'none' },
  button: { width: '100%', backgroundColor: Colors.accent, borderRadius: Radius.md, padding: '16px 0', fontSize: 16, fontWeight: 700, color: Colors.black, border: 'none', marginTop: 8, marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' },
  buttonDisabled: { opacity: 0.5 },
  prefCard: { backgroundColor: Colors.bgCard, borderRadius: Radius.lg, padding: 20, marginBottom: 16, border: `1px solid ${Colors.border}` },
  photoPickerBtn: { flex: 1, backgroundColor: Colors.bgCard, borderRadius: Radius.md, padding: '18px 0', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, border: `1.5px dashed ${Colors.border}`, cursor: 'pointer' },
  smallBtn: { background: 'transparent', padding: '6px 16px', borderRadius: Radius.full, border: `1px solid ${Colors.border}`, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
};
