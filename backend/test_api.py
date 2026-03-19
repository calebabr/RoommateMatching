"""
RoomMatch API Test Script
=========================
Tests the full backend flow against a running server.

Prerequisites:
  1. MongoDB running on localhost:27017
  2. Backend running: cd backend && uvicorn app.main:app --reload
  3. pip install requests

Usage:
  python test_api.py                         # default: http://localhost:8000/api
  python test_api.py http://192.168.1.5:8000/api  # custom URL

What it tests:
  - Health check
  - User creation (all 9 categories + bio/photo/tags)
  - User retrieval
  - Recommendation computation
  - Top matches retrieval
  - Match score calculation
  - Like system (send like, mutual like > match)
  - Unmatch flow
  - Profile update
  - User deletion + cleanup
"""

import sys
import json
import requests
import time

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/api"
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

# ─── Health ──────────────────────────────────────────────

def test_health():
    r = requests.get(BASE.replace("/api", "/health"))
    assert r.status_code == 200, f"status {r.status_code}"
    assert r.json().get("status") == "ok", f"body: {r.text}"

# ─── User Creation ───────────────────────────────────────

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

def test_create_user_full():
    u = make_user(f"test_full_{int(time.time())}", {
        "bio": "Hello from test",
        "photoUrl": "https://example.com/pic.jpg",
        "lifestyleTags": ["Fitness", "Night Owl", "Gaming"],
    })
    assert "id" in u, "no id returned"
    assert u["username"].startswith("test_full_"), f"username: {u['username']}"
    assert u["matched"] == False, "should not be matched"

def test_create_user_new_fields_present():
    u = make_user(f"test_fields_{int(time.time())}")
    assert "personalityScore" in u, "personalityScore missing from response"
    assert "smokingScore" in u, "smokingScore missing from response"
    assert "sharedSpaceScore" in u, "sharedSpaceScore missing from response"
    assert "communicationScore" in u, "communicationScore missing from response"

def test_create_duplicate_fails():
    name = f"test_dup_{int(time.time())}"
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

# ─── User Retrieval ──────────────────────────────────────

def test_get_user():
    u = make_user(f"test_get_{int(time.time())}")
    r = requests.get(f"{BASE}/users/{u['id']}")
    assert r.status_code == 200, f"status {r.status_code}"
    data = r.json()
    assert data["id"] == u["id"]
    assert data["username"] == u["username"]

def test_get_user_404():
    r = requests.get(f"{BASE}/users/999999")
    assert r.status_code == 404, f"expected 404, got {r.status_code}"

def test_get_all_users():
    r = requests.get(f"{BASE}/users/all")
    assert r.status_code == 200, f"status {r.status_code}"
    assert isinstance(r.json(), list), "expected list"

# ─── Recommendations ─────────────────────────────────────

def test_top_matches():
    # Create two similar users > they should appear in each other's recommendations
    ts = int(time.time())
    u1 = make_user(f"test_rec_a_{ts}", {"lifestyleTags": ["Fitness", "Studying"]})
    u2 = make_user(f"test_rec_b_{ts}", {"lifestyleTags": ["Fitness", "Studying"]})

    # Trigger recompute
    requests.post(f"{BASE}/admin/recompute")

    r = requests.get(f"{BASE}/users/{u1['id']}/top-matches")
    assert r.status_code == 200, f"status {r.status_code}: {r.text}"
    matches = r.json().get("matches", [])
    match_ids = [m["user_id"] for m in matches]
    assert u2["id"] in match_ids, f"user {u2['id']} not in recommendations for {u1['id']}: {match_ids}"

# ─── Match Score ─────────────────────────────────────────

def test_match_score():
    ts = int(time.time())
    u1 = make_user(f"test_score_a_{ts}")
    u2 = make_user(f"test_score_b_{ts}")
    r = requests.post(f"{BASE}/matchScore", json={
        "user1_id": u1["id"],
        "user2_id": u2["id"],
    })
    assert r.status_code == 200, f"status {r.status_code}: {r.text}"
    data = r.json()
    assert "compatibilityScore" in data, f"missing score: {data}"
    assert 0.0 <= data["compatibilityScore"] <= 1.0, f"score out of range: {data['compatibilityScore']}"

def test_match_score_dealbreaker():
    """Two users with conflicting dealbreakers should score 0."""
    ts = int(time.time())
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

# ─── Like + Match Flow ───────────────────────────────────

def test_like_flow():
    ts = int(time.time())
    u1 = make_user(f"test_like_a_{ts}")
    u2 = make_user(f"test_like_b_{ts}")

    # u1 likes u2 > status should be "liked"
    r = requests.post(f"{BASE}/users/{u1['id']}/like", json={"toUser": u2["id"]})
    assert r.status_code == 200, f"like failed: {r.text}"
    assert r.json()["status"] == "liked", f"expected 'liked': {r.json()}"

    # u2 should see u1 in likes-received
    r = requests.get(f"{BASE}/users/{u2['id']}/likes-received")
    assert r.status_code == 200
    from_ids = [l["fromUser"] for l in r.json()]
    assert u1["id"] in from_ids, f"u1 not in u2's likes: {from_ids}"

    # u2 likes u1 back > should match
    r = requests.post(f"{BASE}/users/{u2['id']}/like", json={"toUser": u1["id"]})
    assert r.status_code == 200
    assert r.json()["status"] == "matched", f"expected 'matched': {r.json()}"

    # Both should show as matched
    r1 = requests.get(f"{BASE}/users/{u1['id']}")
    r2 = requests.get(f"{BASE}/users/{u2['id']}")
    assert r1.json()["matched"] == True, "u1 not marked matched"
    assert r2.json()["matched"] == True, "u2 not marked matched"
    assert r1.json()["matchedWith"] == u2["id"]
    assert r2.json()["matchedWith"] == u1["id"]

    # Matches endpoint should list the match
    r = requests.get(f"{BASE}/users/{u1['id']}/matches")
    assert r.status_code == 200
    assert len(r.json()) >= 1, "no matches found"

def test_like_self_fails():
    ts = int(time.time())
    u = make_user(f"test_self_{ts}")
    r = requests.post(f"{BASE}/users/{u['id']}/like", json={"toUser": u["id"]})
    assert r.status_code == 400, f"expected 400: {r.text}"

# ─── Unmatch ─────────────────────────────────────────────

def test_unmatch_flow():
    ts = int(time.time())
    u1 = make_user(f"test_um_a_{ts}")
    u2 = make_user(f"test_um_b_{ts}")

    # Create a match
    requests.post(f"{BASE}/users/{u1['id']}/like", json={"toUser": u2["id"]})
    requests.post(f"{BASE}/users/{u2['id']}/like", json={"toUser": u1["id"]})

    # Unmatch
    r = requests.post(f"{BASE}/users/{u1['id']}/unmatch")
    assert r.status_code == 200, f"unmatch failed: {r.text}"

    # Both should be unmatched now
    r1 = requests.get(f"{BASE}/users/{u1['id']}")
    r2 = requests.get(f"{BASE}/users/{u2['id']}")
    assert r1.json()["matched"] == False, "u1 still matched"
    assert r2.json()["matched"] == False, "u2 still matched"

# ─── Profile Update ──────────────────────────────────────

def test_update_profile():
    ts = int(time.time())
    u = make_user(f"test_upd_{ts}")

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
        "photoUrl": "https://example.com/new.jpg",
        "lifestyleTags": ["Reading", "Homebody"],
    }
    r = requests.put(f"{BASE}/users/{u['id']}", json=payload)
    assert r.status_code == 200, f"update failed: {r.text}"
    data = r.json()
    assert data["cleanlinessScore"]["value"] == 10, f"cleanliness not updated: {data}"

# ─── Delete ──────────────────────────────────────────────

def test_delete_user():
    ts = int(time.time())
    u = make_user(f"test_del_{ts}")
    uid = u["id"]

    r = requests.delete(f"{BASE}/users/{uid}")
    assert r.status_code == 200, f"delete failed: {r.text}"

    r = requests.get(f"{BASE}/users/{uid}")
    assert r.status_code == 404, f"user still exists after delete"

    # Remove from cleanup list since already deleted
    if uid in CREATED_IDS:
        CREATED_IDS.remove(uid)

# ─── Recompute Admin ─────────────────────────────────────

def test_admin_recompute():
    r = requests.post(f"{BASE}/admin/recompute")
    # Should succeed if there are 2+ users, or 400 if not
    assert r.status_code in [200, 400], f"unexpected status: {r.status_code}"

# ─── Upload Users (JSON file) ────────────────────────────

def test_upload_users():
    test_data = {
        "users": [
            {
                "id": 9001,
                "username": f"upload_test_{int(time.time())}",
                "sleepScoreWD": {"value": 22, "isDealBreaker": False},
                "sleepScoreWE": {"value": 23, "isDealBreaker": False},
                "cleanlinessScore": {"value": 7, "isDealBreaker": False},
                "noiseToleranceScore": {"value": 5, "isDealBreaker": False},
                "guestsScore": {"value": 3, "isDealBreaker": False},
                "personalityScore": {"value": 5, "isDealBreaker": False},
                "smokingScore": {"value": 0, "isDealBreaker": False},
                "sharedSpaceScore": {"value": 5, "isDealBreaker": False},
                "communicationScore": {"value": 5, "isDealBreaker": False},
            }
        ]
    }
    json_bytes = json.dumps(test_data).encode()
    r = requests.post(
        f"{BASE}/uploadUsers",
        files={"file": ("test.json", json_bytes, "application/json")},
    )
    assert r.status_code == 200, f"upload failed: {r.text}"
    assert "Created" in r.json().get("message", ""), f"unexpected response: {r.json()}"
    # Clean up
    try:
        # Find the user by username to get actual assigned ID
        all_users = requests.get(f"{BASE}/users/all").json()
        for u in all_users:
            if u.get("username", "").startswith("upload_test_"):
                CREATED_IDS.append(u["id"])
    except:
        pass

# ─── Run All ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nRoomMatch API Tests")
    print(f"Target: {BASE}")
    print(f"{'=' * 50}\n")

    # Connectivity
    print("[Health]")
    test("health check", test_health)

    # CRUD
    print("\n[User CRUD]")
    test("create user (full fields)", test_create_user_full)
    test("new preference fields in response", test_create_user_new_fields_present)
    test("duplicate username rejected", test_create_duplicate_fails)
    test("get user by ID", test_get_user)
    test("get nonexistent user > 404", test_get_user_404)
    test("get all users", test_get_all_users)
    test("update profile", test_update_profile)
    test("delete user", test_delete_user)

    # Scoring
    print("\n[Matching Algorithm]")
    test("match score between two users", test_match_score)
    test("dealbreaker > score 0.0", test_match_score_dealbreaker)

    # Recommendations
    print("\n[Recommendations]")
    test("admin recompute", test_admin_recompute)
    test("top matches after recompute", test_top_matches)

    # Likes + Matching
    print("\n[Likes & Matching]")
    test("like > mutual like > match", test_like_flow)
    test("like self > rejected", test_like_self_fails)
    test("unmatch flow", test_unmatch_flow)

    # Upload
    print("\n[Bulk Upload]")
    test("upload users JSON", test_upload_users)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
    if FAIL == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"FAILURES DETECTED")
    print()

    # Cleanup
    print("Cleaning up test users...")
    cleanup()
    print("Done.\n")

    sys.exit(0 if FAIL == 0 else 1)