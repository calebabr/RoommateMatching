"""
RoomMatch API Test Script v2
=============================
Tests the full backend including chat and photo upload features.

Prerequisites:
  1. MongoDB running on localhost:27017
  2. Backend running: cd backend && uvicorn app.main:app --host 0.0.0.0 --reload
  3. pip install requests

Usage:
  python test_api_v2.py                              # default: http://localhost:8000/api
  python test_api_v2.py http://192.168.1.5:8000/api  # custom URL

What it tests:
  - Health check
  - User CRUD (all 9 categories + bio/photo/tags)
  - Match score calculation + dealbreaker logic
  - Recommendations (recompute + top-matches)
  - Like > mutual like > match flow
  - Unmatch flow
  - Photo upload + delete
  - Chat: send messages, retrieve messages, conversations list
  - Chat access control (unmatched users cannot chat)
  - Chat persistence (messages survive across fetches)
  - Bulk user upload
  - Cleanup of all test data
"""

import sys
import os
import json
import requests
import time
import tempfile

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api"
# Derive the root URL (without /api) for photo/static file checks
ROOT = BASE.replace("/api", "")
PASS = 0
FAIL = 0
CREATED_IDS = []

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  PASS  {name}")
    except AssertionError as e:
        FAIL += 1
        print(f"  FAIL  {name} - {e}")
    except Exception as e:
        FAIL += 1
        print(f"  ERR   {name} - {type(e).__name__}: {e}")

def cleanup():
    """Delete all test users we created."""
    for uid in CREATED_IDS:
        try:
            requests.delete(f"{BASE}/users/{uid}")
        except:
            pass

def make_user(username, overrides=None):
    """Create a user with all 9 preference fields + profile fields."""
    payload = {
        "username": username,
        "sleepScoreWD": {"value": 22, "isDealBreaker": False},
        "sleepScoreWE": {"value": 23, "isDealBreaker": False},
        "cleanlinessScore": {"value": 7, "isDealBreaker": False},
        "noiseToleranceScore": {"value": 4, "isDealBreaker": False},
        "guestsScore": {"value": 3, "isDealBreaker": False},
        "personalityScore": {"value": 5, "isDealBreaker": False},
        "smokingScore": {"value": 0, "isDealBreaker": True},
        "sharedSpaceScore": {"value": 5, "isDealBreaker": False},
        "communicationScore": {"value": 6, "isDealBreaker": False},
        "bio": f"Test bio for {username}",
        "photoUrl": "",
        "lifestyleTags": ["Fitness", "Studying"],
    }
    if overrides:
        payload.update(overrides)
    r = requests.post(f"{BASE}/users", json=payload)
    assert r.status_code == 200, f"status {r.status_code}: {r.text}"
    data = r.json()
    CREATED_IDS.append(data["id"])
    return data

def make_matched_pair():
    """Create two users and match them via mutual likes. Returns (u1, u2)."""
    ts = int(time.time() * 1000)
    u1 = make_user(f"test_pair_a_{ts}")
    u2 = make_user(f"test_pair_b_{ts}")
    requests.post(f"{BASE}/users/{u1['id']}/like", json={"toUser": u2["id"]})
    requests.post(f"{BASE}/users/{u2['id']}/like", json={"toUser": u1["id"]})
    return u1, u2


# === Health ===

def test_health():
    r = requests.get(ROOT + "/health")
    assert r.status_code == 200, f"status {r.status_code}"
    assert r.json().get("status") == "ok", f"body: {r.text}"

def test_root_version():
    r = requests.get(ROOT + "/")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data, f"no version in root: {data}"


# === User CRUD ===

def test_create_user_full():
    u = make_user(f"test_full_{int(time.time() * 1000)}", {
        "bio": "Hello from test",
        "lifestyleTags": ["Fitness", "Night Owl", "Gaming"],
    })
    assert "id" in u, "no id returned"
    assert u["matched"] == False, "should not be matched"

def test_all_nine_categories_present():
    u = make_user(f"test_9cat_{int(time.time() * 1000)}")
    for field in ["sleepScoreWD", "sleepScoreWE", "cleanlinessScore", "noiseToleranceScore",
                   "guestsScore", "personalityScore", "smokingScore", "sharedSpaceScore",
                   "communicationScore"]:
        assert field in u, f"{field} missing from response"
        assert "value" in u[field], f"{field} has no value"
        assert "isDealBreaker" in u[field], f"{field} has no isDealBreaker"

def test_create_duplicate_fails():
    name = f"test_dup_{int(time.time() * 1000)}"
    make_user(name)
    r = requests.post(f"{BASE}/users", json={
        "username": name,
        "sleepScoreWD": {"value": 1, "isDealBreaker": False},
        "sleepScoreWE": {"value": 1, "isDealBreaker": False},
        "cleanlinessScore": {"value": 5, "isDealBreaker": False},
        "noiseToleranceScore": {"value": 5, "isDealBreaker": False},
        "guestsScore": {"value": 5, "isDealBreaker": False},
        "personalityScore": {"value": 5, "isDealBreaker": False},
        "smokingScore": {"value": 5, "isDealBreaker": False},
        "sharedSpaceScore": {"value": 5, "isDealBreaker": False},
        "communicationScore": {"value": 5, "isDealBreaker": False},
    })
    assert r.status_code == 400, f"expected 400, got {r.status_code}"

def test_get_user():
    u = make_user(f"test_get_{int(time.time() * 1000)}")
    r = requests.get(f"{BASE}/users/{u['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == u["id"]
    assert r.json()["username"] == u["username"]

def test_get_user_404():
    r = requests.get(f"{BASE}/users/999999")
    assert r.status_code == 404, f"expected 404, got {r.status_code}"

def test_get_all_users():
    r = requests.get(f"{BASE}/users/all")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_update_profile():
    u = make_user(f"test_upd_{int(time.time() * 1000)}")
    payload = {
        "username": u["username"],
        "sleepScoreWD": {"value": 20, "isDealBreaker": True},
        "sleepScoreWE": {"value": 21, "isDealBreaker": False},
        "cleanlinessScore": {"value": 10, "isDealBreaker": True},
        "noiseToleranceScore": {"value": 1, "isDealBreaker": True},
        "guestsScore": {"value": 0, "isDealBreaker": False},
        "personalityScore": {"value": 2, "isDealBreaker": False},
        "smokingScore": {"value": 0, "isDealBreaker": True},
        "sharedSpaceScore": {"value": 2, "isDealBreaker": False},
        "communicationScore": {"value": 9, "isDealBreaker": False},
        "bio": "Updated bio!",
        "photoUrl": "",
        "lifestyleTags": ["Reading", "Homebody"],
    }
    r = requests.put(f"{BASE}/users/{u['id']}", json=payload)
    assert r.status_code == 200, f"update failed: {r.text}"
    assert r.json()["cleanlinessScore"]["value"] == 10

def test_delete_user():
    u = make_user(f"test_del_{int(time.time() * 1000)}")
    uid = u["id"]
    r = requests.delete(f"{BASE}/users/{uid}")
    assert r.status_code == 200
    r = requests.get(f"{BASE}/users/{uid}")
    assert r.status_code == 404, "user still exists after delete"
    if uid in CREATED_IDS:
        CREATED_IDS.remove(uid)


# === Match Scoring ===

def test_match_score():
    ts = int(time.time() * 1000)
    u1 = make_user(f"test_score_a_{ts}")
    u2 = make_user(f"test_score_b_{ts}")
    r = requests.post(f"{BASE}/matchScore", json={
        "user1_id": u1["id"],
        "user2_id": u2["id"],
    })
    assert r.status_code == 200
    score = r.json()["compatibilityScore"]
    assert 0.0 <= score <= 1.0, f"score out of range: {score}"

def test_match_score_dealbreaker():
    ts = int(time.time() * 1000)
    u1 = make_user(f"test_db_a_{ts}", {
        "smokingScore": {"value": 0, "isDealBreaker": True},
    })
    u2 = make_user(f"test_db_b_{ts}", {
        "smokingScore": {"value": 8, "isDealBreaker": False},
    })
    r = requests.post(f"{BASE}/matchScore", json={
        "user1_id": u1["id"],
        "user2_id": u2["id"],
    })
    assert r.status_code == 200
    score = r.json()["compatibilityScore"]
    assert score == 0.0, f"expected 0.0 for dealbreaker conflict, got {score}"

def test_identical_users_high_score():
    ts = int(time.time() * 1000)
    prefs = {
        "sleepScoreWD": {"value": 12, "isDealBreaker": False},
        "sleepScoreWE": {"value": 12, "isDealBreaker": False},
        "cleanlinessScore": {"value": 5, "isDealBreaker": False},
        "noiseToleranceScore": {"value": 5, "isDealBreaker": False},
        "guestsScore": {"value": 5, "isDealBreaker": False},
        "personalityScore": {"value": 5, "isDealBreaker": False},
        "smokingScore": {"value": 5, "isDealBreaker": False},
        "sharedSpaceScore": {"value": 5, "isDealBreaker": False},
        "communicationScore": {"value": 5, "isDealBreaker": False},
    }
    u1 = make_user(f"test_ident_a_{ts}", prefs)
    u2 = make_user(f"test_ident_b_{ts}", prefs)
    r = requests.post(f"{BASE}/matchScore", json={
        "user1_id": u1["id"],
        "user2_id": u2["id"],
    })
    assert r.status_code == 200
    score = r.json()["compatibilityScore"]
    assert score >= 0.95, f"identical users should score near 1.0, got {score}"


# === Recommendations ===

def test_admin_recompute():
    r = requests.post(f"{BASE}/admin/recompute")
    assert r.status_code in [200, 400], f"unexpected status: {r.status_code}"

def test_top_matches():
    ts = int(time.time() * 1000)
    u1 = make_user(f"test_rec_a_{ts}", {"lifestyleTags": ["Fitness", "Studying"]})
    u2 = make_user(f"test_rec_b_{ts}", {"lifestyleTags": ["Fitness", "Studying"]})
    requests.post(f"{BASE}/admin/recompute")
    r = requests.get(f"{BASE}/users/{u1['id']}/top-matches")
    assert r.status_code == 200, f"status {r.status_code}: {r.text}"
    matches = r.json().get("matches", [])
    match_ids = [m["user_id"] for m in matches]
    assert u2["id"] in match_ids, f"user {u2['id']} not in recs for {u1['id']}: {match_ids}"


# === Like + Match Flow ===

def test_like_flow():
    ts = int(time.time() * 1000)
    u1 = make_user(f"test_like_a_{ts}")
    u2 = make_user(f"test_like_b_{ts}")

    # u1 likes u2
    r = requests.post(f"{BASE}/users/{u1['id']}/like", json={"toUser": u2["id"]})
    assert r.status_code == 200
    assert r.json()["status"] == "liked"

    # u2 should see u1 in likes-received
    r = requests.get(f"{BASE}/users/{u2['id']}/likes-received")
    assert r.status_code == 200
    from_ids = [l["fromUser"] for l in r.json()]
    assert u1["id"] in from_ids

    # u2 likes u1 back > match
    r = requests.post(f"{BASE}/users/{u2['id']}/like", json={"toUser": u1["id"]})
    assert r.status_code == 200
    assert r.json()["status"] == "matched"

    # Both matched
    r1 = requests.get(f"{BASE}/users/{u1['id']}")
    r2 = requests.get(f"{BASE}/users/{u2['id']}")
    assert r1.json()["matched"] == True
    assert r2.json()["matched"] == True
    assert r1.json()["matchedWith"] == u2["id"]
    assert r2.json()["matchedWith"] == u1["id"]

def test_like_self_fails():
    u = make_user(f"test_self_{int(time.time() * 1000)}")
    r = requests.post(f"{BASE}/users/{u['id']}/like", json={"toUser": u["id"]})
    assert r.status_code == 400

def test_like_already_matched_fails():
    u1, u2 = make_matched_pair()
    u3 = make_user(f"test_extra_{int(time.time() * 1000)}")
    r = requests.post(f"{BASE}/users/{u1['id']}/like", json={"toUser": u3["id"]})
    assert r.status_code == 400, f"matched user should not be able to like others"


# === Unmatch ===

def test_unmatch_flow():
    u1, u2 = make_matched_pair()
    r = requests.post(f"{BASE}/users/{u1['id']}/unmatch")
    assert r.status_code == 200
    r1 = requests.get(f"{BASE}/users/{u1['id']}")
    r2 = requests.get(f"{BASE}/users/{u2['id']}")
    assert r1.json()["matched"] == False
    assert r2.json()["matched"] == False

def test_unmatch_when_not_matched_fails():
    u = make_user(f"test_um_solo_{int(time.time() * 1000)}")
    r = requests.post(f"{BASE}/users/{u['id']}/unmatch")
    assert r.status_code == 400, f"expected 400, got {r.status_code}"


# === Photo Upload ===

def test_photo_upload():
    u = make_user(f"test_photo_{int(time.time() * 1000)}")
    # Create a tiny valid JPEG (smallest possible)
    # JFIF header for a 1x1 white pixel JPEG
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
        0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
        0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
        0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
        0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
        0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
        0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
        0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
        0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
        0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
        0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
        0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
        0x00, 0x00, 0x3F, 0x00, 0x7B, 0x94, 0x11, 0x00, 0x00, 0x00, 0x00, 0x00,
        0xFF, 0xD9
    ])

    r = requests.post(
        f"{BASE}/users/{u['id']}/photo",
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert r.status_code == 200, f"upload failed: {r.text}"
    photo_url = r.json().get("photoUrl", "")
    assert photo_url.startswith("/uploads/photos/"), f"bad photoUrl: {photo_url}"

    # Verify user record was updated
    r = requests.get(f"{BASE}/users/{u['id']}")
    assert r.json()["photoUrl"] == photo_url

    # Verify the file is accessible via static serving
    r = requests.get(f"{ROOT}{photo_url}")
    assert r.status_code == 200, f"photo not accessible at {ROOT}{photo_url}"

def test_photo_delete():
    u = make_user(f"test_photodel_{int(time.time() * 1000)}")
    # Upload first
    jpeg_bytes = bytes([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 50 + [0xFF, 0xD9])
    requests.post(
        f"{BASE}/users/{u['id']}/photo",
        files={"file": ("test.jpg", jpeg_bytes, "image/jpeg")},
    )
    # Delete
    r = requests.delete(f"{BASE}/users/{u['id']}/photo")
    assert r.status_code == 200
    # Verify cleared
    r = requests.get(f"{BASE}/users/{u['id']}")
    assert r.json().get("photoUrl", "") == "", "photoUrl not cleared after delete"

def test_photo_reject_large_file():
    u = make_user(f"test_bigphoto_{int(time.time() * 1000)}")
    # 6MB of zeros with JPEG header
    big = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + (b'\x00' * 6_000_000) + bytes([0xFF, 0xD9])
    r = requests.post(
        f"{BASE}/users/{u['id']}/photo",
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert r.status_code == 400, f"expected 400 for oversized file, got {r.status_code}"


# === Chat ===

def test_chat_send_and_retrieve():
    u1, u2 = make_matched_pair()

    # u1 sends a message
    r = requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u2["id"],
        "text": "Hey, want to be roommates?",
    })
    assert r.status_code == 200, f"send failed: {r.text}"
    msg = r.json()
    assert msg["senderId"] == u1["id"]
    assert msg["text"] == "Hey, want to be roommates?"
    assert "sentAt" in msg

    # u2 retrieves messages
    r = requests.get(f"{BASE}/chat/{u2['id']}/messages/{u1['id']}")
    assert r.status_code == 200
    messages = r.json().get("messages", [])
    assert len(messages) >= 1, "no messages returned"
    assert messages[0]["text"] == "Hey, want to be roommates?"

def test_chat_bidirectional():
    u1, u2 = make_matched_pair()

    # Both send messages
    requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u2["id"], "text": "Hello from u1",
    })
    requests.post(f"{BASE}/chat/{u2['id']}/send", json={
        "receiverId": u1["id"], "text": "Hello from u2",
    })
    requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u2["id"], "text": "Second message from u1",
    })

    # Both should see all 3 messages in order
    r = requests.get(f"{BASE}/chat/{u1['id']}/messages/{u2['id']}")
    msgs = r.json()["messages"]
    assert len(msgs) == 3, f"expected 3 messages, got {len(msgs)}"
    assert msgs[0]["text"] == "Hello from u1"
    assert msgs[1]["text"] == "Hello from u2"
    assert msgs[2]["text"] == "Second message from u1"

def test_chat_polling_with_after():
    u1, u2 = make_matched_pair()

    # Send first message
    requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u2["id"], "text": "First",
    })

    # Fetch all messages, get timestamp
    r = requests.get(f"{BASE}/chat/{u1['id']}/messages/{u2['id']}")
    msgs = r.json()["messages"]
    assert len(msgs) == 1
    last_ts = msgs[0]["sentAt"]

    # Send second message
    time.sleep(0.1)  # ensure different timestamp
    requests.post(f"{BASE}/chat/{u2['id']}/send", json={
        "receiverId": u1["id"], "text": "Second",
    })

    # Poll with after= should only return the new message
    r = requests.get(f"{BASE}/chat/{u1['id']}/messages/{u2['id']}", params={"after": last_ts})
    msgs = r.json()["messages"]
    assert len(msgs) == 1, f"expected 1 new message, got {len(msgs)}"
    assert msgs[0]["text"] == "Second"

def test_chat_conversations_list():
    u1, u2 = make_matched_pair()

    # Send a message so the conversation has content
    requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u2["id"], "text": "Hey!",
    })

    # Get conversations for u1
    r = requests.get(f"{BASE}/chat/{u1['id']}/conversations")
    assert r.status_code == 200
    convos = r.json().get("conversations", [])
    partner_ids = [c["partnerId"] for c in convos]
    assert u2["id"] in partner_ids, f"u2 not in conversations: {partner_ids}"

    # The conversation should have the last message
    convo = [c for c in convos if c["partnerId"] == u2["id"]][0]
    assert convo["lastMessage"] == "Hey!"

def test_chat_unmatched_users_blocked():
    ts = int(time.time() * 1000)
    u1 = make_user(f"test_nochat_a_{ts}")
    u2 = make_user(f"test_nochat_b_{ts}")

    # They are NOT matched - chat should fail
    r = requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u2["id"], "text": "Should fail",
    })
    assert r.status_code == 400, f"expected 400 for unmatched chat, got {r.status_code}"

def test_chat_empty_message_rejected():
    u1, u2 = make_matched_pair()
    r = requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u2["id"], "text": "   ",
    })
    assert r.status_code == 400, f"expected 400 for empty message, got {r.status_code}"

def test_chat_message_self_rejected():
    u1, u2 = make_matched_pair()
    r = requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u1["id"], "text": "Talking to myself",
    })
    assert r.status_code == 400, f"expected 400 for self-message, got {r.status_code}"

def test_chat_persistence():
    """Messages persist across multiple fetches."""
    u1, u2 = make_matched_pair()
    requests.post(f"{BASE}/chat/{u1['id']}/send", json={
        "receiverId": u2["id"], "text": "Persistent message",
    })

    # Fetch twice - should get same result
    r1 = requests.get(f"{BASE}/chat/{u1['id']}/messages/{u2['id']}")
    r2 = requests.get(f"{BASE}/chat/{u1['id']}/messages/{u2['id']}")
    assert r1.json()["messages"] == r2.json()["messages"], "messages changed between fetches"


# === Bulk Upload ===

def test_upload_users():
    test_data = {
        "users": [{
            "id": 9001,
            "username": f"upload_test_{int(time.time() * 1000)}",
            "sleepScoreWD": {"value": 22, "isDealBreaker": False},
            "sleepScoreWE": {"value": 23, "isDealBreaker": False},
            "cleanlinessScore": {"value": 7, "isDealBreaker": False},
            "noiseToleranceScore": {"value": 5, "isDealBreaker": False},
            "guestsScore": {"value": 3, "isDealBreaker": False},
            "personalityScore": {"value": 5, "isDealBreaker": False},
            "smokingScore": {"value": 0, "isDealBreaker": False},
            "sharedSpaceScore": {"value": 5, "isDealBreaker": False},
            "communicationScore": {"value": 5, "isDealBreaker": False},
        }]
    }
    json_bytes = json.dumps(test_data).encode()
    r = requests.post(
        f"{BASE}/uploadUsers",
        files={"file": ("test.json", json_bytes, "application/json")},
    )
    assert r.status_code == 200, f"upload failed: {r.text}"
    assert "Created" in r.json().get("message", "")
    # Clean up
    try:
        all_users = requests.get(f"{BASE}/users/all").json()
        for u in all_users:
            if u.get("username", "").startswith("upload_test_"):
                CREATED_IDS.append(u["id"])
    except:
        pass


# === Run All ===

if __name__ == "__main__":
    print(f"\nRoomMatch API Tests v2")
    print(f"Target: {BASE}")
    print(f"{'=' * 56}\n")

    print("[Health]")
    test("health check", test_health)
    test("root version", test_root_version)

    print("\n[User CRUD]")
    test("create user (full fields)", test_create_user_full)
    test("all 9 preference categories present", test_all_nine_categories_present)
    test("duplicate username rejected", test_create_duplicate_fails)
    test("get user by ID", test_get_user)
    test("get nonexistent user > 404", test_get_user_404)
    test("get all users", test_get_all_users)
    test("update profile", test_update_profile)
    test("delete user", test_delete_user)

    print("\n[Matching Algorithm]")
    test("match score between two users", test_match_score)
    test("dealbreaker > score 0.0", test_match_score_dealbreaker)
    test("identical users > high score", test_identical_users_high_score)

    print("\n[Recommendations]")
    test("admin recompute", test_admin_recompute)
    test("top matches after recompute", test_top_matches)

    print("\n[Likes & Matching]")
    test("like > mutual like > match", test_like_flow)
    test("like self > rejected", test_like_self_fails)
    test("like while matched > rejected", test_like_already_matched_fails)
    test("unmatch flow", test_unmatch_flow)
    test("unmatch when not matched > rejected", test_unmatch_when_not_matched_fails)

    print("\n[Photo Upload]")
    test("upload photo + verify accessible", test_photo_upload)
    test("delete photo", test_photo_delete)
    test("reject oversized photo", test_photo_reject_large_file)

    print("\n[Chat]")
    test("send message + retrieve", test_chat_send_and_retrieve)
    test("bidirectional conversation", test_chat_bidirectional)
    test("polling with after timestamp", test_chat_polling_with_after)
    test("conversations list", test_chat_conversations_list)
    test("unmatched users cannot chat", test_chat_unmatched_users_blocked)
    test("empty message rejected", test_chat_empty_message_rejected)
    test("self-message rejected", test_chat_message_self_rejected)
    test("message persistence", test_chat_persistence)

    print("\n[Bulk Upload]")
    test("upload users JSON", test_upload_users)

    # Summary
    total = PASS + FAIL
    print(f"\n{'=' * 56}")
    print(f"Results: {PASS} passed, {FAIL} failed out of {total} tests")
    if FAIL == 0:
        print("ALL TESTS PASSED")
    else:
        print("FAILURES DETECTED")
    print()

    # Cleanup
    print("Cleaning up test users...")
    cleanup()
    print("Done.\n")

    sys.exit(0 if FAIL == 0 else 1)