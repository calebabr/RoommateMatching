import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/LegalPage.css';

export default function PrivacyPolicyPage() {
  const navigate = useNavigate();

  return (
    <div className="legal-page">
      <div className="legal-container">
        <button className="legal-back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>

        <p className="legal-app-name">RoomMatch</p>
        <h1 className="legal-title">Privacy Policy</h1>
        <p className="legal-effective-date">Effective date: June 3, 2026</p>

        <div className="legal-section">
          <h2 className="legal-section-heading">1. What We Collect</h2>
          <p>
            When you use RoomMatch, we collect the following information:
          </p>
          <ul>
            <li>Name and email address</li>
            <li>Date of birth and gender</li>
            <li>Profile photo</li>
            <li>Lifestyle preferences (sleep schedule, cleanliness, noise tolerance, and more)</li>
            <li>Chat messages sent between matched users</li>
            <li>Usage and analytics data (pages visited, features used, session activity)</li>
          </ul>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">2. How We Use Your Data</h2>
          <p>We use the information we collect to:</p>
          <ul>
            <li>Match you with compatible roommates based on your preferences</li>
            <li>Enable chat between users who have matched with each other</li>
            <li>Send account-related emails (password resets, notifications)</li>
            <li>Monitor app performance and diagnose errors</li>
            <li>Understand how the product is used and improve it over time</li>
          </ul>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">3. Third-Party Services</h2>
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
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">4. Data Retention</h2>
          <p>
            Your data is kept for as long as your account is active. When you delete your
            account, your profile and data are scheduled for permanent removal after a
            7-day restore window.
          </p>
          <p>
            Chat messages are retained until both parties involved in a conversation have
            deleted their accounts.
          </p>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">5. Your Rights</h2>
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
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">6. Age Requirement</h2>
          <p>
            RoomMatch is only available to users who are 18 years of age or older. We do
            not knowingly collect personal information from anyone under 18. If we become
            aware that a user is under 18, their account will be removed.
          </p>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">7. Contact</h2>
          <p>
            For privacy questions, data requests, or concerns about how we handle your
            information, please contact us at:{' '}
            <a href="mailto:cjabrantes06@gmail.com">cjabrantes06@gmail.com</a>
          </p>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">8. Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy from time to time. Material changes will be
            communicated via an in-app notice or by email before they take effect.
            Continued use of RoomMatch after any changes constitutes your acceptance of
            the updated policy.
          </p>
        </div>
      </div>
    </div>
  );
}
