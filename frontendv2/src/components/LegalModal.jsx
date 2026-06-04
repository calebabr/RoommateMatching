import React from 'react';

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.7)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 10100,
  padding: '16px',
};

const boxStyle = {
  background: 'var(--color-surface, #1e1e1e)',
  border: '1px solid var(--color-border, rgba(255,255,255,0.12))',
  borderRadius: 12,
  width: '90%',
  maxWidth: 680,
  maxHeight: '85vh',
  display: 'flex',
  flexDirection: 'column',
  position: 'relative',
  overflow: 'hidden',
};

const headerStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '16px 20px',
  borderBottom: '1px solid var(--color-border, rgba(255,255,255,0.12))',
  flexShrink: 0,
};

const closeBtnStyle = {
  background: 'none',
  border: 'none',
  cursor: 'pointer',
  color: 'var(--color-text-secondary, #A0A0A0)',
  fontSize: 20,
  lineHeight: 1,
  padding: '4px 8px',
  borderRadius: 6,
};

const scrollBodyStyle = {
  overflowY: 'auto',
  padding: '20px 24px',
  flex: 1,
  color: 'var(--color-text, #fff)',
  fontSize: 14,
  lineHeight: 1.7,
};

const sectionHeadingStyle = {
  fontSize: 15,
  fontWeight: 700,
  color: 'var(--color-text, #fff)',
  marginTop: 24,
  marginBottom: 6,
};

const footerStyle = {
  padding: '14px 20px',
  borderTop: '1px solid var(--color-border, rgba(255,255,255,0.12))',
  display: 'flex',
  justifyContent: 'flex-end',
  flexShrink: 0,
};

const closeActionBtnStyle = {
  background: 'var(--color-accent, #E8A838)',
  color: '#1a1a1a',
  border: 'none',
  borderRadius: 8,
  padding: '8px 24px',
  fontWeight: 700,
  fontSize: 14,
  cursor: 'pointer',
};

function TermsContent() {
  return (
    <>
      <p style={{ color: 'var(--color-text-secondary, #A0A0A0)', fontSize: 13, marginTop: 0 }}>Effective date: June 3, 2026</p>

      <h3 style={sectionHeadingStyle}>1. Eligibility</h3>
      <p>
        You must be at least 18 years old to use RoomMatch. By creating an account,
        you confirm that you are 18 years of age or older. We reserve the right to
        terminate accounts if we discover a user does not meet this requirement.
      </p>

      <h3 style={sectionHeadingStyle}>2. Your Account</h3>
      <p>
        You are responsible for maintaining the confidentiality of your account
        credentials and for all activity that occurs under your account. You agree to:
      </p>
      <ul>
        <li>Provide accurate and truthful information when creating your profile</li>
        <li>Keep your login credentials secure and not share them with others</li>
        <li>Not create accounts on behalf of other people</li>
        <li>Notify us immediately if you suspect unauthorized use of your account</li>
      </ul>
      <p>
        Users may optionally provide their academic major and graduation year for display
        on their profile to help potential roommates learn more about them.
      </p>

      <h3 style={sectionHeadingStyle}>3. Acceptable Use</h3>
      <p>You agree not to use RoomMatch to:</p>
      <ul>
        <li>Harass, threaten, or intimidate other users</li>
        <li>Create fake, misleading, or deceptive profiles</li>
        <li>Scrape, copy, or collect other users' personal information</li>
        <li>Use the app for commercial solicitation or advertising</li>
        <li>Attempt to access accounts or data other than your own</li>
        <li>Violate any applicable laws or regulations</li>
      </ul>

      <h3 style={sectionHeadingStyle}>4. User Content</h3>
      <p>
        You retain ownership of the content you post on RoomMatch, including your
        profile photo, bio, and messages. By posting content, you grant RoomMatch a
        limited, non-exclusive license to display your content to other users for the
        purpose of facilitating roommate matching.
      </p>
      <p>
        We reserve the right to remove any content that violates these Terms or that
        we determine, in our sole discretion, is harmful to the community.
      </p>

      <h3 style={sectionHeadingStyle}>5. Matching</h3>
      <p>
        RoomMatch does not guarantee successful roommate matches. Our matching
        algorithm is designed to surface compatible users, but we are not responsible
        for the accuracy, completeness, or truthfulness of information provided by
        other users.
      </p>
      <p>
        Exercise your own judgment and take appropriate precautions when communicating
        with or meeting other users in person. RoomMatch is not responsible for any
        harm resulting from in-person interactions.
      </p>

      <h3 style={sectionHeadingStyle}>6. Account Suspension</h3>
      <p>
        We may suspend or terminate your account at any time and for any reason,
        including but not limited to:
      </p>
      <ul>
        <li>Violations of these Terms of Service</li>
        <li>Confirmed or suspected underage use</li>
        <li>Reports of abuse or harassment from other users</li>
        <li>Fraudulent or deceptive activity</li>
      </ul>

      <h3 style={sectionHeadingStyle}>7. Limitation of Liability</h3>
      <p>
        RoomMatch is provided "as is" without warranties of any kind, either express
        or implied. To the fullest extent permitted by law, we are not liable for any
        direct, indirect, incidental, or consequential damages arising from your use
        of the app, including any harm resulting from interactions with other users.
      </p>

      <h3 style={sectionHeadingStyle}>8. Governing Law</h3>
      <p>
        These Terms of Service are governed by and construed in accordance with the
        laws of the State of Alabama, without regard to its conflict of law provisions.
      </p>

      <h3 style={sectionHeadingStyle}>9. Changes to These Terms</h3>
      <p>
        We may update these Terms of Service from time to time. We will make
        reasonable efforts to notify you of material changes. Your continued use of
        RoomMatch after any changes constitutes your acceptance of the updated Terms.
      </p>

      <h3 style={sectionHeadingStyle}>10. Contact</h3>
      <p>
        If you have questions or concerns about these Terms of Service, please
        contact us at:{' '}
        <a href="mailto:cjabrantes06@gmail.com" style={{ color: 'var(--color-accent, #E8A838)' }}>cjabrantes06@gmail.com</a>
      </p>
    </>
  );
}

function PrivacyContent() {
  return (
    <>
      <p style={{ color: 'var(--color-text-secondary, #A0A0A0)', fontSize: 13, marginTop: 0 }}>Effective date: June 3, 2026</p>

      <h3 style={sectionHeadingStyle}>1. What We Collect</h3>
      <p>When you use RoomMatch, we collect the following information:</p>
      <ul>
        <li>Name and email address</li>
        <li>Date of birth and gender</li>
        <li>Profile photo</li>
        <li>Lifestyle preferences (sleep schedule, cleanliness, noise tolerance, and more)</li>
        <li>Academic major, expected graduation season and year</li>
        <li>Chat messages sent between matched users</li>
        <li>Usage and analytics data (pages visited, features used, session activity)</li>
      </ul>

      <h3 style={sectionHeadingStyle}>2. How We Use Your Data</h3>
      <p>We use the information we collect to:</p>
      <ul>
        <li>Match you with compatible roommates based on your preferences</li>
        <li>Enable chat between users who have matched with each other</li>
        <li>Send account-related emails (password resets, notifications)</li>
        <li>Monitor app performance and diagnose errors</li>
        <li>Understand how the product is used and improve it over time</li>
      </ul>

      <h3 style={sectionHeadingStyle}>3. Third-Party Services</h3>
      <p>
        RoomMatch uses third-party services to operate. Each service may receive
        relevant portions of your data and is governed by its own privacy policy:
      </p>
      <ul>
        <li><strong>Cloudinary</strong> — profile photo storage</li>
        <li><strong>SendGrid</strong> — email delivery</li>
        <li><strong>Sentry</strong> — error monitoring and crash reporting</li>
        <li><strong>PostHog</strong> — product analytics and session replay</li>
        <li><strong>MongoDB Atlas</strong> — database hosting</li>
        <li><strong>Render</strong> — backend server hosting</li>
        <li><strong>Vercel</strong> — frontend hosting</li>
      </ul>

      <h3 style={sectionHeadingStyle}>4. Data Retention</h3>
      <p>
        Your data is kept for as long as your account is active. When you delete your
        account, your profile and data are scheduled for permanent removal after a
        7-day restore window.
      </p>
      <p>
        Chat messages are retained until both parties involved in a conversation have
        deleted their accounts.
      </p>

      <h3 style={sectionHeadingStyle}>5. Your Rights</h3>
      <p>You have the following rights regarding your personal data:</p>
      <ul>
        <li>
          <strong>Export</strong> — you can download a copy of your data at any time
          from your Profile page.
        </li>
        <li>
          <strong>Deletion</strong> — you can delete your account at any time. Deleted
          accounts are permanently purged after a 7-day restore window.
        </li>
        <li>
          <strong>Correction</strong> — if any information we hold about you is
          inaccurate, contact us and we will correct it.
        </li>
      </ul>

      <h3 style={sectionHeadingStyle}>6. Age Requirement</h3>
      <p>
        RoomMatch is only available to users who are 18 years of age or older. We do
        not knowingly collect personal information from anyone under 18. If we become
        aware that a user is under 18, their account will be removed.
      </p>

      <h3 style={sectionHeadingStyle}>7. Contact</h3>
      <p>
        For privacy questions, data requests, or concerns about how we handle your
        information, please contact us at:{' '}
        <a href="mailto:cjabrantes06@gmail.com" style={{ color: 'var(--color-accent, #E8A838)' }}>cjabrantes06@gmail.com</a>
      </p>

      <h3 style={sectionHeadingStyle}>8. Changes to This Policy</h3>
      <p>
        We may update this Privacy Policy from time to time. Material changes will be
        communicated via an in-app notice or by email before they take effect.
        Continued use of RoomMatch after any changes constitutes your acceptance of
        the updated policy.
      </p>
    </>
  );
}

export default function LegalModal({ type, onClose }) {
  const isTerms = type === 'terms';
  const title = isTerms ? 'Terms of Service' : 'Privacy Policy';

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={boxStyle} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={headerStyle}>
          <span style={{ fontWeight: 700, fontSize: 16, color: 'var(--color-text, #fff)' }}>{title}</span>
          <button style={closeBtnStyle} onClick={onClose} aria-label="Close">&#10005;</button>
        </div>

        {/* Scrollable body */}
        <div style={scrollBodyStyle}>
          {isTerms ? <TermsContent /> : <PrivacyContent />}
        </div>

        {/* Footer */}
        <div style={footerStyle}>
          <button style={closeActionBtnStyle} onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
