import React, { useState, useRef, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';

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
import { Colors } from '../utils/theme';
import { CATEGORIES, LIFESTYLE_TAGS } from '../utils/categories';
import posthog from 'posthog-js';
import { uploadPhoto, setApiBase } from '../services/api';

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
import SliderPicker from '../components/SliderPicker';
import Toggle from '../components/Toggle';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

export default function SignupPage() {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [step, setStep]   = useState(0);
  const [email,         setEmail]         = useState('');
  const [password,      setPassword]      = useState('');
  const [username,      setUsername]      = useState('');
  const [gender,        setGender]        = useState('');
  const [bio,           setBio]           = useState('');
  const [dateOfBirth,   setDateOfBirth]   = useState('');
  const [dobError,      setDobError]      = useState('');
  const [photoFile,    setPhotoFile]    = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [selectedTags,      setSelectedTags]      = useState([]);
  const [religionTag,       setReligionTag]       = useState('');
  const [major,             setMajor]             = useState('');
  const [majorOther,        setMajorOther]        = useState('');
  const [graduationSeason,  setGraduationSeason]  = useState('');
  const [graduationYear,    setGraduationYear]    = useState('');
  const [agreedToTerms,   setAgreedToTerms]   = useState(false);
  const [termsError,      setTermsError]      = useState('');
  const [loading, setLoading] = useState(false);
  const [modal,   setModal]   = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const signupStartedFired = useRef(false);

  const handleSignupStarted = useCallback(() => {
    if (!signupStartedFired.current) {
      signupStartedFired.current = true;
      posthog.capture('signup_started');
    }
  }, []);

  const [preferences, setPreferences] = useState(
    CATEGORIES.reduce((acc, cat) => {
      acc[cat.key] = { value: Math.round((cat.max - cat.min) / 2), isDealBreaker: false };
      return acc;
    }, {})
  );

  const calculateAge = (dobString) => {
    const dob = new Date(dobString);
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
    return age;
  };

  const updatePref = (key, field, val) =>
    setPreferences(prev => ({ ...prev, [key]: { ...prev[key], [field]: val } }));

  const toggleTag = (tag) =>
    setSelectedTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) { setPhotoFile(file); setPhotoPreview(URL.createObjectURL(file)); }
  };

  const handleCreate = async () => {
    if (!agreedToTerms) { setTermsError('You must agree to the Terms of Service and Privacy Policy to continue.'); return; }
    if (!email.trim())    { setModal({ title: 'Missing Email', message: 'Please enter your email address.' }); return; }
    if (!password)        { setModal({ title: 'Missing Password', message: 'Please enter a password.' }); return; }
    if (!username.trim()) { setModal({ title: 'Missing Name', message: 'Please enter a username.' }); return; }
    if (!gender)          { setModal({ title: 'Missing Gender', message: 'Please select your gender.' }); return; }
    if (!dateOfBirth)     { setModal({ title: 'Missing Date of Birth', message: 'Please enter your date of birth.' }); return; }
    if (calculateAge(dateOfBirth) < 18) {
      setModal({ title: 'Age Requirement', message: 'You must be at least 18 years old to sign up.' });
      return;
    }
    setLoading(true);
    try {
      const resolvedMajor = major === 'Other' ? (majorOther.trim() ? `Other: ${majorOther.trim()}` : '') : major;
      const profileData = {
        username: username.trim(),
        gender,
        bio: bio.trim(),
        lifestyleTags: selectedTags,
        religionTag: religionTag || undefined,
        major: resolvedMajor || undefined,
        graduationSeason: graduationSeason || undefined,
        graduationYear: graduationYear ? parseInt(graduationYear) : undefined,
        dateOfBirth,
        termsVersion: "2026-06-03",
        ...preferences,
      };
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
    <div className="signup-page">
      {modal && (
        <Modal
          title={modal.title} message={modal.message}
          onClose={() => setModal(null)}
          onConfirm={modal.onConfirm}
          confirmText="Continue"
        />
      )}

      {/* Header */}
      <div className="signup-header">
        <button className="signup-back-btn" onClick={() => step === 0 ? navigate('/login') : setStep(s => s - 1)}>
          ← Back
        </button>
        <div className="signup-step-row">
          {[0, 1, 2].map((i) => (
            <React.Fragment key={i}>
              {i > 0 && <div className={`signup-step-line ${step >= i ? 'signup-step-line--active' : ''}`} />}
              <div className={`signup-step-dot ${step >= i ? 'signup-step-dot--active' : ''}`} />
            </React.Fragment>
          ))}
        </div>
      </div>

      <div className="signup-scroll">
        {step === 0 && (
          <>
            <h2 className="signup-title">Create Your Profile</h2>
            <p className="signup-subtitle">Tell potential roommates about yourself</p>

            <div className="input-group">
              <label className="form-label">Email</label>
              <input className="form-input" placeholder="you@example.com" type="email" value={email} onChange={e => setEmail(e.target.value)} onFocus={handleSignupStarted} />
            </div>

            <div className="input-group">
              <label className="form-label">Password</label>
              <div className="signup-input-wrapper">
                <input className="form-input login-input-padded" placeholder="Choose a password" type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} />
                <button
                  type="button"
                  onClick={() => setShowPassword(p => !p)}
                  className="password-toggle-btn"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                </button>
              </div>
            </div>

            <div className="input-group">
              <label className="form-label">Username</label>
              <input className="form-input" placeholder="Enter a unique username" value={username} onChange={e => setUsername(e.target.value)} />
            </div>

            <div className="input-group">
              <label className="form-label">Date of Birth</label>
              <input
                className="form-input"
                type="date"
                value={dateOfBirth}
                onChange={e => { setDateOfBirth(e.target.value); setDobError(''); }}
                max={new Date(new Date().setFullYear(new Date().getFullYear() - 18)).toISOString().split('T')[0]}
              />
              {dobError && (
                <p style={{ color: 'var(--color-danger)', fontSize: 13, marginTop: 4 }}>{dobError}</p>
              )}
            </div>

            <div className="input-group">
              <label className="form-label">Gender</label>
              <p className="signup-gender-note">
                You'll only be matched with roommates of the same gender
              </p>
              <div className="signup-gender-row">
                {['male', 'female'].map(g => (
                  <button
                    key={g}
                    onClick={() => setGender(g)}
                    className={`signup-gender-btn ${gender === g ? 'signup-gender-btn--selected' : ''}`}
                  >
                    <span style={{ fontSize: 36 }}>{g === 'male' ? '👨' : '👩'}</span>
                    <span className={`signup-gender-label ${gender === g ? 'signup-gender-label--selected' : ''}`}>
                      {g === 'male' ? 'Male' : 'Female'}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="input-group">
              <label className="form-label">Bio</label>
              <textarea
                className="form-input"
                style={{ minHeight: 80, resize: 'vertical', paddingTop: 14 }}
                placeholder="A short intro — what are you like as a roommate?"
                value={bio} onChange={e => setBio(e.target.value)}
                maxLength={200}
              />
              <p className="signup-bio-count">{bio.length}/200</p>
            </div>

            <div className="input-group">
              <label className="form-label">Major (optional)</label>
              <select
                className="form-input"
                value={major}
                onChange={e => { setMajor(e.target.value); if (e.target.value !== 'Other') setMajorOther(''); }}
              >
                <option value="">Select your major...</option>
                {MAJOR_OPTIONS.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              {major === 'Other' && (
                <input
                  className="form-input"
                  style={{ marginTop: 8 }}
                  placeholder="Enter your major"
                  value={majorOther}
                  onChange={e => setMajorOther(e.target.value)}
                />
              )}
            </div>

            <div className="input-group">
              <label className="form-label">Graduation (optional)</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <select
                  className="form-input"
                  style={{ flex: 1 }}
                  value={graduationSeason}
                  onChange={e => setGraduationSeason(e.target.value)}
                >
                  <option value="">Season</option>
                  {GRADUATION_SEASONS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <select
                  className="form-input"
                  style={{ flex: 1 }}
                  value={graduationYear}
                  onChange={e => setGraduationYear(e.target.value)}
                >
                  <option value="">Year</option>
                  {GRADUATION_YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
              </div>
            </div>

            <div className="input-group">
              <label className="form-label">Profile Photo (optional)</label>
              <input ref={fileInputRef}    type="file" accept="image/*"          onChange={handleFileChange} style={{ display: 'none' }} />
              <input ref={cameraInputRef}  type="file" accept="image/*" capture="user" onChange={handleFileChange} style={{ display: 'none' }} />
              {photoPreview ? (
                <div className="signup-photo-preview">
                  <img src={photoPreview} alt="preview" className="signup-photo-preview-img" />
                  <button onClick={() => { setPhotoFile(null); setPhotoPreview(null); }} className="signup-remove-btn">
                    ✕ Remove
                  </button>
                </div>
              ) : (
                <div className="signup-photo-picker-row">
                  <button onClick={() => fileInputRef.current.click()} className="signup-photo-picker-btn">
                    <span style={{ fontSize: 28 }}>🖼️</span>
                    <span className="signup-photo-picker-label">Choose Photo</span>
                  </button>
                  <button onClick={() => cameraInputRef.current.click()} className="signup-photo-picker-btn">
                    <span style={{ fontSize: 28 }}>📷</span>
                    <span className="signup-photo-picker-label">Take Photo</span>
                  </button>
                </div>
              )}
            </div>

            <button
              className={`signup-next-btn ${!email.trim() || !password || !username.trim() || !gender || !dateOfBirth ? 'signup-next-btn--disabled' : ''}`}
              onClick={() => {
                if (!email.trim())    { setModal({ title: 'Missing Email', message: 'Please enter your email address.' }); return; }
                if (!password)        { setModal({ title: 'Missing Password', message: 'Please enter a password.' }); return; }
                if (password.length < 8) { setModal({ title: 'Password Too Weak', message: 'Password must be at least 8 characters long.' }); return; }
                if (username.trim().length === 0) { setModal({ title: 'Missing Name', message: 'Please enter a username.' }); return; }
                if (!dateOfBirth)     { setModal({ title: 'Missing Date of Birth', message: 'Please enter your date of birth.' }); return; }
                if (calculateAge(dateOfBirth) < 18) {
                  setDobError('You must be at least 18 years old to sign up.');
                  return;
                }
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
            <h2 className="signup-title">Your Preferences</h2>
            <p className="signup-subtitle">Rate each category and mark deal-breakers</p>
            {CATEGORIES.map(cat => (
              <div key={cat.key} className="signup-pref-card">
                <div className="signup-pref-header">
                  <span className="signup-pref-label">{cat.label}</span>
                  <div className="signup-pref-dealbreaker-row">
                    <span className="signup-pref-dealbreaker-text">Deal-breaker</span>
                    <Toggle value={preferences[cat.key].isDealBreaker} onChange={v => updatePref(cat.key, 'isDealBreaker', v)} />
                  </div>
                </div>
                <p className="signup-pref-desc">{cat.description}</p>
                <SliderPicker
                  min={cat.min} max={cat.max}
                  value={preferences[cat.key].value}
                  onChange={v => updatePref(cat.key, 'value', v)}
                  formatLabel={cat.formatValue}
                />
              </div>
            ))}
            <button className="signup-next-btn" onClick={() => setStep(2)}>Next — Lifestyle Tags</button>
          </>
        )}

        {step === 2 && (
          <>
            <h2 className="signup-title">Lifestyle Tags</h2>
            <p className="signup-subtitle">Pick tags that describe you — shared tags boost your match score!</p>
            <div className="signup-tag-row">
              {LIFESTYLE_TAGS.map(tag => {
                const sel = selectedTags.includes(tag);
                return (
                  <button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    className={`signup-tag-btn ${sel ? 'signup-tag-btn--selected' : ''}`}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
            <p className="signup-tag-count">{selectedTags.length} selected</p>

            <div style={{ marginTop: 28, marginBottom: 8 }}>
              <p className="signup-title" style={{ fontSize: 18, marginBottom: 4 }}>Religion</p>
              <p className="signup-subtitle" style={{ fontSize: 13, marginBottom: 12 }}>Optional — select one that applies to you</p>
              <div className="signup-tag-row">
                {RELIGION_OPTIONS.map(opt => {
                  const sel = religionTag === opt;
                  return (
                    <button
                      key={opt}
                      onClick={() => setReligionTag(sel ? '' : opt)}
                      className={`signup-tag-btn ${sel ? 'signup-tag-btn--selected' : ''}`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, margin: '20px 0 4px' }}>
              <input
                id="agree-to-terms"
                type="checkbox"
                checked={agreedToTerms}
                onChange={e => { setAgreedToTerms(e.target.checked); if (e.target.checked) setTermsError(''); }}
                style={{ marginTop: 3, accentColor: '#E8A838', width: 16, height: 16, flexShrink: 0, cursor: 'pointer' }}
              />
              <label htmlFor="agree-to-terms" style={{ fontSize: 14, lineHeight: 1.5, color: '#A0A0A0', cursor: 'pointer' }}>
                I agree to the{' '}
                <Link to="/terms" target="_blank" rel="noopener noreferrer" style={{ color: '#E8A838', textDecoration: 'underline' }}>
                  Terms of Service
                </Link>
                {' '}and{' '}
                <Link to="/privacy" target="_blank" rel="noopener noreferrer" style={{ color: '#E8A838', textDecoration: 'underline' }}>
                  Privacy Policy
                </Link>
              </label>
            </div>
            {termsError && (
              <p style={{ color: 'var(--color-danger)', fontSize: 13, margin: '4px 0 8px' }}>{termsError}</p>
            )}

            <button
              className={`signup-next-btn ${loading ? 'signup-next-btn--disabled' : ''}`}
              onClick={handleCreate}
              disabled={loading}
            >
              {loading ? <Spinner size={20} color={Colors.black} /> : 'Create Account'}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
