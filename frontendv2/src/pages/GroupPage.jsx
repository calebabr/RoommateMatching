import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getCompatibilityColor, getCompatibilityLabel } from '../utils/categories';
import {
  getMyGroup, createGroup, inviteToGroup, respondToGroupInvite,
  leaveGroup, disbandGroup, getGroupCompatibility,
  getMatches, getUser, getPhotoUrl,
} from '../services/api';
import NotificationBell from '../components/NotificationBell';
import Modal from '../components/Modal';
import Spinner from '../components/Spinner';

const DEFAULT_MAX_SIZE = 4;

/**
 * The compatibility endpoint returns `pairs: [{userA, userB, compatibilityScore}]`
 * plus a symmetric `matrix` ({"1": {"2": 0.9}, "2": {"1": 0.9}}). Prefer `pairs`,
 * fall back to the matrix, and tolerate the other field spellings either could use.
 */
function normalizePairs(data) {
  const list   = data?.pairs ?? data?.compatibility;
  const matrix = data?.matrix;

  const pairs = [];
  const seen  = new Set();
  const add = (a, b, score) => {
    if (a == null || b == null || score == null) return;
    const na = Number(a), nb = Number(b), ns = Number(score);
    if (!Number.isFinite(na) || !Number.isFinite(nb) || !Number.isFinite(ns) || na === nb) return;
    const key = na < nb ? `${na}-${nb}` : `${nb}-${na}`;
    if (seen.has(key)) return;  // matrix is symmetric — keep one entry per pair
    seen.add(key);
    pairs.push({ a: na, b: nb, score: ns });
  };

  if (Array.isArray(list)) {
    list.forEach(p => add(
      p?.userA ?? p?.user1_id ?? p?.userId1 ?? p?.a ?? p?.[0],
      p?.userB ?? p?.user2_id ?? p?.userId2 ?? p?.b ?? p?.[1],
      p?.compatibilityScore ?? p?.score ?? p?.[2],
    ));
  }

  if (pairs.length === 0 && matrix && typeof matrix === 'object') {
    Object.entries(matrix).forEach(([a, row]) => {
      if (!row || typeof row !== 'object') return;
      Object.entries(row).forEach(([b, score]) => add(a, b, score));
    });
  }

  return pairs;
}

export default function GroupPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [loading,   setLoading]   = useState(true);
  const [group,     setGroup]     = useState(null);
  const [members,   setMembers]   = useState([]);
  const [invites,   setInvites]   = useState([]);   // pending invites addressed to me
  const [pairs,     setPairs]     = useState([]);
  const [modal,     setModal]     = useState(null);
  const [busy,      setBusy]      = useState(false);

  // Invite picker
  const [showInvite,    setShowInvite]    = useState(false);
  const [eligible,      setEligible]      = useState([]);
  const [eligibleLoad,  setEligibleLoad]  = useState(false);
  const [invitingId,    setInvitingId]    = useState(null);
  const [inviteNotice,  setInviteNotice]  = useState('');

  const load = useCallback(async () => {
    if (!user?.id) return;
    let data = null;
    try {
      data = await getMyGroup();
    } catch {
      data = null; // 404 = no group yet
    }

    const g = data?.group ?? (data?.id != null ? data : null);
    const pendingInvites = data?.pendingInvites ?? data?.invites ?? [];
    setInvites(Array.isArray(pendingInvites) ? pendingInvites : []);

    if (!g) {
      setGroup(null); setMembers([]); setPairs([]);
      return;
    }
    setGroup(g);

    // Members — prefer an enriched list, otherwise resolve ids one by one
    const enriched = Array.isArray(g.members) && g.members.length && typeof g.members[0] === 'object'
      ? g.members
      : await Promise.all((g.memberIds || []).map(async (id) => {
          try { const p = await getUser(id); return { ...p, id }; }
          catch { return { id, username: `User #${id}` }; }
        }));
    setMembers(enriched);

    try {
      const comp = await getGroupCompatibility(g.id);
      setPairs(normalizePairs(comp));
    } catch {
      setPairs([]);
    }
  }, [user?.id]);

  useEffect(() => {
    let active = true;
    (async () => { setLoading(true); await load(); if (active) setLoading(false); })();
    return () => { active = false; };
  }, [load]);

  const memberIds = members.map(m => m.id);
  const isCreator = group && user && group.createdBy === user.id;
  const isFull    = group && memberIds.length >= (group.maxSize || DEFAULT_MAX_SIZE);

  const meanScore = pairs.length
    ? pairs.reduce((s, p) => s + p.score, 0) / pairs.length
    : null;
  const weakest = pairs.length
    ? pairs.reduce((lo, p) => (p.score < lo.score ? p : lo), pairs[0])
    : null;

  const nameFor = (id) => members.find(m => m.id === id)?.username || `User #${id}`;

  // ── Actions ──────────────────────────────────────────────────────────────
  const handleCreate = async () => {
    setBusy(true);
    try {
      await createGroup({ maxSize: DEFAULT_MAX_SIZE });
      await load();
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not create a group.' });
    } finally {
      setBusy(false);
    }
  };

  const openInvitePicker = async () => {
    setShowInvite(true);
    setInviteNotice('');
    setEligibleLoad(true);
    try {
      const raw = await getMatches(user.id);
      const partners = await Promise.all(
        (raw || []).map(async (m) => {
          const partnerId = m.user1_id === user.id ? m.user2_id : m.user1_id;
          try { const p = await getUser(partnerId); return { id: partnerId, username: p.username || `User #${partnerId}`, photoUrl: p.photoUrl }; }
          catch { return { id: partnerId, username: `User #${partnerId}`, photoUrl: null }; }
        })
      );
      setEligible(partners.filter(p => !memberIds.includes(p.id)));
    } catch {
      setEligible([]);
    } finally {
      setEligibleLoad(false);
    }
  };

  const handleInvite = async (targetId) => {
    if (!group) return;
    setInvitingId(targetId);
    setInviteNotice('');
    try {
      await inviteToGroup(group.id, targetId);
      setEligible(prev => prev.filter(p => p.id !== targetId));
      setInviteNotice('Invite sent.');
    } catch (err) {
      setInviteNotice(err?.response?.data?.detail || 'Could not send that invite.');
    } finally {
      setInvitingId(null);
    }
  };

  // Backend expects { action: "accept" | "decline" }
  const handleRespond = async (invite, action) => {
    setBusy(true);
    try {
      await respondToGroupInvite(invite.groupId ?? invite.group_id, invite.id ?? invite._id, action);
      await load();
    } catch (err) {
      setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not respond to that invite.' });
    } finally {
      setBusy(false);
    }
  };

  const confirmLeave = () => setModal({
    title: 'Leave group?',
    message: 'You will be removed from this group. Your individual matches and chats are not affected.',
    danger: true,
    confirmText: 'Leave',
    onConfirm: async () => {
      try { await leaveGroup(group.id); await load(); }
      catch (err) { setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not leave the group.' }); }
    },
  });

  const confirmDisband = () => setModal({
    title: 'Disband group?',
    message: 'This deletes the group for everyone and cancels any pending invites. This cannot be undone.',
    danger: true,
    confirmText: 'Disband',
    onConfirm: async () => {
      try { await disbandGroup(group.id); await load(); }
      catch (err) { setModal({ title: 'Error', message: err?.response?.data?.detail || 'Could not disband the group.' }); }
    },
  });

  if (loading) return (
    <div className="loading-page">
      <Spinner size={40} />
      <p className="text-secondary group-loading-text">Loading your group...</p>
    </div>
  );

  return (
    <div className="full-height overflow-y bg-base">
      {modal && (
        <Modal
          title={modal.title}
          message={modal.message}
          onClose={() => setModal(null)}
          onConfirm={modal.onConfirm}
          confirmText={modal.confirmText}
          danger={modal.danger}
        />
      )}

      <div className="page-container">
        <div className="page-header">
          <div>
            <p className="page-header-title">Group</p>
            <p className="page-header-sub">
              {group
                ? `${memberIds.length} of ${group.maxSize || DEFAULT_MAX_SIZE} members`
                : 'Live with more than one roommate'}
            </p>
          </div>
          <NotificationBell />
        </div>

        {/* ── Pending invites to me ── */}
        {invites.length > 0 && (
          <div className="group-invites">
            <p className="group-section-title">Group invites</p>
            {invites.map(inv => (
              <div key={inv.id ?? inv._id} className="group-invite-row">
                <span className="group-invite-text">
                  {inv.fromUsername || `User #${inv.fromUserId ?? inv.from_user_id}`} invited you to their group
                </span>
                <div className="group-invite-actions">
                  <button
                    className="group-btn group-btn--primary"
                    onClick={() => handleRespond(inv, 'accept')}
                    disabled={busy}
                  >
                    Accept
                  </button>
                  <button
                    className="group-btn group-btn--ghost"
                    onClick={() => handleRespond(inv, 'decline')}
                    disabled={busy}
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {!group ? (
          <div className="empty-state">
            <span className="group-empty-emoji">👥</span>
            <p className="empty-state-title">No Group Yet</p>
            <p className="empty-state-desc">
              Groups let you plan a 3- or 4-person apartment. Start one, then invite people
              you've already matched with.
            </p>
            <button className="group-btn group-btn--primary" onClick={handleCreate} disabled={busy}>
              {busy ? '...' : 'Create a group'}
            </button>
          </div>
        ) : (
          <>
            {/* ── Summary ── */}
            <div className="group-summary">
              <div className="group-summary-item">
                <span className="group-summary-label">Group average</span>
                <span
                  className="group-summary-value"
                  style={meanScore != null ? { color: getCompatibilityColor(meanScore) } : undefined}
                >
                  {meanScore != null ? `${Math.round(meanScore * 100)}%` : '—'}
                </span>
                {meanScore != null && (
                  <span className="group-summary-sub">{getCompatibilityLabel(meanScore)}</span>
                )}
              </div>
              <div className="group-summary-item">
                <span className="group-summary-label">Weakest pair</span>
                <span className="group-summary-value">
                  {weakest ? `${Math.round(weakest.score * 100)}%` : '—'}
                </span>
                {weakest && (
                  <span className="group-summary-sub">{nameFor(weakest.a)} &amp; {nameFor(weakest.b)}</span>
                )}
              </div>
              <div className="group-summary-item">
                <span className="group-summary-label">Status</span>
                <span className="group-summary-value group-summary-value--text">
                  {isFull ? 'Full' : (group.status || 'open')}
                </span>
              </div>
            </div>

            {/* ── Members ── */}
            <p className="group-section-title">Members</p>
            <div className="group-members-grid">
              {members.map(m => {
                const photoSrc = getPhotoUrl(m.photoUrl);
                const isMe = m.id === user?.id;
                return (
                  <div key={m.id} className="group-member-card">
                    <div
                      className="group-member-head"
                      onClick={() => !isMe && navigate(`/user/${m.id}`)}
                    >
                      {photoSrc ? (
                        <img src={photoSrc} alt="" className="group-member-avatar-img" />
                      ) : (
                        <div className="group-member-avatar">
                          {(m.username || '?')[0].toUpperCase()}
                        </div>
                      )}
                      <div className="group-member-identity">
                        <p className="group-member-name">
                          {m.username || `User #${m.id}`}{isMe ? ' (you)' : ''}
                        </p>
                        {group.createdBy === m.id && <p className="group-member-role">Creator</p>}
                      </div>
                    </div>

                    <div className="group-member-pairs">
                      {members.filter(o => o.id !== m.id).map(other => {
                        const pair = pairs.find(p =>
                          (p.a === m.id && p.b === other.id) || (p.a === other.id && p.b === m.id));
                        const score = pair?.score;
                        return (
                          <div key={other.id} className="group-pair-row">
                            <span className="group-pair-name">with {other.username || `User #${other.id}`}</span>
                            <span
                              className="group-pair-score"
                              style={score != null ? { color: getCompatibilityColor(score) } : undefined}
                            >
                              {score != null ? `${Math.round(score * 100)}%` : '—'}
                            </span>
                          </div>
                        );
                      })}
                      {members.length === 1 && (
                        <p className="group-pair-empty">Invite someone to see pairwise scores.</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* ── Actions ── */}
            <div className="group-actions">
              <button
                className="group-btn group-btn--primary"
                onClick={openInvitePicker}
                disabled={isFull}
                title={isFull ? 'This group is full' : undefined}
              >
                {isFull ? 'Group is full' : '➕ Invite a match'}
              </button>
              <button className="group-btn group-btn--ghost" onClick={confirmLeave}>Leave group</button>
              {isCreator && (
                <button className="group-btn group-btn--danger" onClick={confirmDisband}>Disband group</button>
              )}
            </div>
          </>
        )}
      </div>

      {/* ── Invite picker ── */}
      {showInvite && (
        <div className="overlay-bg overlay-bg--sheet" onClick={() => setShowInvite(false)}>
          <div className="inline-modal group-invite-modal" onClick={e => e.stopPropagation()}>
            <p className="group-invite-modal-title">Invite a match</p>
            <p className="group-invite-modal-desc">
              You can invite anyone you've already matched with. They'll get a notification and
              can accept or decline.
            </p>

            {eligibleLoad ? (
              <div className="group-invite-loading"><Spinner size={24} /></div>
            ) : eligible.length === 0 ? (
              <p className="group-invite-empty">No matches available to invite right now.</p>
            ) : (
              <div className="group-invite-list">
                {eligible.map(p => {
                  const photoSrc = getPhotoUrl(p.photoUrl);
                  return (
                    <div key={p.id} className="group-invite-candidate">
                      {photoSrc ? (
                        <img src={photoSrc} alt="" className="group-member-avatar-img" />
                      ) : (
                        <div className="group-member-avatar">{(p.username || '?')[0].toUpperCase()}</div>
                      )}
                      <span className="group-invite-candidate-name">{p.username}</span>
                      <button
                        className="group-btn group-btn--small"
                        onClick={() => handleInvite(p.id)}
                        disabled={invitingId === p.id}
                      >
                        {invitingId === p.id ? '...' : 'Invite'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {inviteNotice && <p className="group-invite-notice">{inviteNotice}</p>}

            <button className="group-btn group-btn--ghost group-btn--block" onClick={() => setShowInvite(false)}>
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
