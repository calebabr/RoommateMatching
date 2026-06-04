import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/LegalPage.css';

export default function TermsOfServicePage() {
  const navigate = useNavigate();

  return (
    <div className="legal-page">
      <div className="legal-container">
        <button className="legal-back-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>

        <p className="legal-app-name">RoomMatch</p>
        <h1 className="legal-title">Terms of Service</h1>
        <p className="legal-effective-date">Effective date: June 3, 2026</p>

        <div className="legal-section">
          <h2 className="legal-section-heading">1. Eligibility</h2>
          <p>
            You must be at least 18 years old to use RoomMatch. By creating an account,
            you confirm that you are 18 years of age or older. We reserve the right to
            terminate accounts if we discover a user does not meet this requirement.
          </p>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">2. Your Account</h2>
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
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">3. Acceptable Use</h2>
          <p>You agree not to use RoomMatch to:</p>
          <ul>
            <li>Harass, threaten, or intimidate other users</li>
            <li>Create fake, misleading, or deceptive profiles</li>
            <li>Scrape, copy, or collect other users' personal information</li>
            <li>Use the app for commercial solicitation or advertising</li>
            <li>Attempt to access accounts or data other than your own</li>
            <li>Violate any applicable laws or regulations</li>
          </ul>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">4. User Content</h2>
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
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">5. Matching</h2>
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
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">6. Account Suspension</h2>
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
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">7. Limitation of Liability</h2>
          <p>
            RoomMatch is provided "as is" without warranties of any kind, either express
            or implied. To the fullest extent permitted by law, we are not liable for any
            direct, indirect, incidental, or consequential damages arising from your use
            of the app, including any harm resulting from interactions with other users.
          </p>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">8. Governing Law</h2>
          <p>
            These Terms of Service are governed by and construed in accordance with the
            laws of the State of Alabama, without regard to its conflict of law provisions.
          </p>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">9. Changes to These Terms</h2>
          <p>
            We may update these Terms of Service from time to time. We will make
            reasonable efforts to notify you of material changes. Your continued use of
            RoomMatch after any changes constitutes your acceptance of the updated Terms.
          </p>
        </div>

        <div className="legal-section">
          <h2 className="legal-section-heading">10. Contact</h2>
          <p>
            If you have questions or concerns about these Terms of Service, please
            contact us at:{' '}
            <a href="mailto:cjabrantes06@gmail.com">cjabrantes06@gmail.com</a>
          </p>
        </div>
      </div>
    </div>
  );
}
