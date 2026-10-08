"""P3FT.14 — curated profile prompts and `promptAnswers`.

Two layers:

  * `GET /api/profile-prompts` — the catalogue endpoint.  It is deliberately
    PUBLIC: the signup form fetches it before a token exists, so an auth
    requirement here would silently break the register step rather than fail
    loudly.  Tests pin that.
  * `promptAnswers` validation and persistence on register / `POST /users` /
    `PUT /users/{id}`.

The most consequential behaviour covered here is the omitted-vs-empty
distinction on update: omitting `promptAnswers` PRESERVES stored answers, while
an explicit `[]` CLEARS them.  Conflating the two would erase user-authored
content on every unrelated profile save, so both paths are tested separately.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    MAX_PROMPT_ANSWERS,
    PROFILE_PROMPTS,
    PROFILE_PROMPT_IDS,
    PROMPT_ANSWER_MAX_LENGTH,
)
from tests.helpers import auth_header, declared_rate_limits, make_user, prefs

client = TestClient(app)
BASE = "/api"

# Three known-good prompt ids, taken from the catalogue rather than hardcoded so
# a future rename of the list cannot leave these tests asserting dead ids.
P1, P2, P3 = [p["id"] for p in PROFILE_PROMPTS[:3]]
P4 = PROFILE_PROMPTS[3]["id"]


def _register_body(tag: str, **extra) -> dict:
    body = {
        "email": f"prompt_{tag}@auburn.edu",
        "password": "TestPass123!",
        "username": f"prompt{tag}",
        "gender": "male",
    }
    body.update(prefs())
    body.update(extra)
    return body


def _user_create_body(tag: str, **extra) -> dict:
    body = {"username": f"pc{tag}", "gender": "female"}
    body.update(prefs())
    body.update(extra)
    return body


def _answer(prompt_id: str, text: str = "Something reasonable.") -> dict:
    return {"promptId": prompt_id, "answer": text}


# ---------------------------------------------------------------------------
# GET /api/profile-prompts
# ---------------------------------------------------------------------------

class TestProfilePromptsEndpoint:

    def test_returns_200_without_any_auth_header(self):
        """Signup fetches this before a token exists — auth here breaks signup."""
        r = client.get(f"{BASE}/profile-prompts")
        assert r.status_code == 200, r.text

    def test_returns_200_with_a_garbage_auth_header(self):
        r = client.get(
            f"{BASE}/profile-prompts",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert r.status_code == 200, r.text

    def test_returns_twenty_prompts(self):
        body = client.get(f"{BASE}/profile-prompts").json()
        assert isinstance(body, list)
        assert len(body) == 20

    def test_every_entry_is_id_and_text_strings(self):
        for item in client.get(f"{BASE}/profile-prompts").json():
            assert set(item.keys()) == {"id", "text"}
            assert isinstance(item["id"], str) and item["id"]
            assert isinstance(item["text"], str) and item["text"]

    def test_order_is_stable_across_calls(self):
        first = [p["id"] for p in client.get(f"{BASE}/profile-prompts").json()]
        second = [p["id"] for p in client.get(f"{BASE}/profile-prompts").json()]
        assert first == second

    def test_ids_match_the_server_side_catalogue(self):
        served = [p["id"] for p in client.get(f"{BASE}/profile-prompts").json()]
        assert served == [p["id"] for p in PROFILE_PROMPTS]

    def test_ids_are_unique(self):
        served = [p["id"] for p in client.get(f"{BASE}/profile-prompts").json()]
        assert len(set(served)) == len(served)

    def test_rate_limit_is_60_per_minute(self):
        assert declared_rate_limits(
            "app.routers.userRoutes.get_profile_prompts"
        ) == ["60 per 1 minute"]


# ---------------------------------------------------------------------------
# promptAnswers validation — register
# ---------------------------------------------------------------------------

class TestPromptAnswerValidationOnRegister:

    def test_register_without_prompt_answers_succeeds(self):
        r = client.post(f"{BASE}/auth/register", json=_register_body("none"))
        assert r.status_code == 201, r.text

    def test_register_with_zero_answers_succeeds(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("empty", promptAnswers=[]))
        assert r.status_code == 201, r.text

    @pytest.mark.parametrize("count", [1, 2, 3])
    def test_register_accepts_up_to_three_answers(self, count):
        answers = [_answer(p) for p in (P1, P2, P3)][:count]
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body(f"n{count}", promptAnswers=answers))
        assert r.status_code == 201, r.text

    def test_register_rejects_four_answers(self):
        answers = [_answer(p) for p in (P1, P2, P3, P4)]
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("four", promptAnswers=answers))
        assert r.status_code == 422

    def test_register_rejects_unknown_prompt_id(self):
        r = client.post(
            f"{BASE}/auth/register",
            json=_register_body("unknown",
                                promptAnswers=[_answer("not_a_real_prompt")]),
        )
        assert r.status_code == 422

    def test_register_rejects_duplicate_prompt_ids(self):
        r = client.post(
            f"{BASE}/auth/register",
            json=_register_body("dup",
                                promptAnswers=[_answer(P1, "a"), _answer(P1, "b")]),
        )
        assert r.status_code == 422

    def test_register_rejects_empty_answer(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("blank", promptAnswers=[_answer(P1, "")]))
        assert r.status_code == 422

    def test_register_rejects_whitespace_only_answer(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("ws", promptAnswers=[_answer(P1, "   ")]))
        assert r.status_code == 422

    def test_register_accepts_answer_at_max_length(self):
        text = "x" * PROMPT_ANSWER_MAX_LENGTH
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("max", promptAnswers=[_answer(P1, text)]))
        assert r.status_code == 201, r.text

    def test_register_rejects_answer_over_max_length(self):
        text = "x" * (PROMPT_ANSWER_MAX_LENGTH + 1)
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("over", promptAnswers=[_answer(P1, text)]))
        assert r.status_code == 422

    def test_answer_length_is_measured_after_html_stripping(self):
        """`<b>` wrappers must not let a 150-char answer sneak past the cap, and
        must not cause a short answer wrapped in long markup to be rejected."""
        inner = "y" * PROMPT_ANSWER_MAX_LENGTH
        r = client.post(
            f"{BASE}/auth/register",
            json=_register_body("html", promptAnswers=[_answer(P1, f"<b>{inner}</b>")]),
        )
        assert r.status_code == 201, r.text

    def test_register_strips_html_from_stored_answer(self, test_db):
        r = client.post(
            f"{BASE}/auth/register",
            json=_register_body(
                "xss",
                promptAnswers=[_answer(P1, "<script>alert(1)</script>clean text")],
            ),
        )
        assert r.status_code == 201, r.text
        uid = r.json()["user"]["id"]
        stored = test_db["users"].find_one({"id": uid})["promptAnswers"]
        assert "<script>" not in stored[0]["answer"]
        assert "clean text" in stored[0]["answer"]

    def test_register_rejects_non_string_prompt_id(self):
        r = client.post(
            f"{BASE}/auth/register",
            json=_register_body("int", promptAnswers=[{"promptId": 7, "answer": "hi"}]),
        )
        assert r.status_code == 422

    def test_register_rejects_missing_answer_key(self):
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("noans", promptAnswers=[{"promptId": P1}]))
        assert r.status_code == 422

    def test_register_stores_answers_verbatim(self, test_db):
        answers = [_answer(P1, "First"), _answer(P2, "Second")]
        r = client.post(f"{BASE}/auth/register",
                        json=_register_body("store", promptAnswers=answers))
        assert r.status_code == 201, r.text
        uid = r.json()["user"]["id"]
        stored = test_db["users"].find_one({"id": uid})["promptAnswers"]
        assert stored == answers

    def test_register_without_answers_stores_empty_list_not_null(self, test_db):
        r = client.post(f"{BASE}/auth/register", json=_register_body("nullcheck"))
        assert r.status_code == 201, r.text
        uid = r.json()["user"]["id"]
        assert test_db["users"].find_one({"id": uid})["promptAnswers"] == []


# ---------------------------------------------------------------------------
# promptAnswers on POST /users
# ---------------------------------------------------------------------------

class TestPromptAnswersOnCreateUser:

    def test_post_users_accepts_prompt_answers(self, test_db):
        test_db["users"].insert_one(make_user(9100))
        r = client.post(
            f"{BASE}/users",
            json=_user_create_body("ok", promptAnswers=[_answer(P1, "Hello")]),
            headers=auth_header(9100),
        )
        assert r.status_code == 200, r.text

    def test_post_users_without_prompt_answers_stores_empty_list(self, test_db):
        test_db["users"].insert_one(make_user(9101))
        r = client.post(f"{BASE}/users", json=_user_create_body("empty"),
                        headers=auth_header(9101))
        assert r.status_code == 200, r.text
        created = test_db["users"].find_one({"username": "pcempty"})
        assert created["promptAnswers"] == []

    def test_post_users_rejects_four_answers(self, test_db):
        test_db["users"].insert_one(make_user(9102))
        r = client.post(
            f"{BASE}/users",
            json=_user_create_body("four",
                                   promptAnswers=[_answer(p) for p in (P1, P2, P3, P4)]),
            headers=auth_header(9102),
        )
        assert r.status_code == 422

    def test_post_users_rejects_unknown_prompt_id(self, test_db):
        test_db["users"].insert_one(make_user(9103))
        r = client.post(
            f"{BASE}/users",
            json=_user_create_body("bad", promptAnswers=[_answer("nope_not_here")]),
            headers=auth_header(9103),
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# PUT /users/{id} — the omit-preserves / empty-clears semantic
# ---------------------------------------------------------------------------

class TestPromptAnswersOnUpdate:

    def _seed(self, test_db, user_id: int, answers):
        test_db["users"].insert_one(make_user(user_id, promptAnswers=answers))

    def test_omitting_prompt_answers_preserves_stored_answers(self, test_db):
        """The single most damaging failure mode: an unrelated profile save must
        not wipe prompt answers."""
        stored = [_answer(P1, "Keep me"), _answer(P2, "Me too")]
        self._seed(test_db, 9200, stored)

        body = {"username": "user9200", "gender": "male"}
        body.update(prefs(6.0))
        r = client.put(f"{BASE}/users/9200", json=body, headers=auth_header(9200))
        assert r.status_code == 200, r.text

        assert test_db["users"].find_one({"id": 9200})["promptAnswers"] == stored

    def test_explicit_empty_list_clears_stored_answers(self, test_db):
        self._seed(test_db, 9201, [_answer(P1, "Delete me")])

        body = {"username": "user9201", "gender": "male", "promptAnswers": []}
        body.update(prefs())
        r = client.put(f"{BASE}/users/9201", json=body, headers=auth_header(9201))
        assert r.status_code == 200, r.text

        assert test_db["users"].find_one({"id": 9201})["promptAnswers"] == []

    def test_explicit_null_is_treated_as_omitted(self, test_db):
        """`null` is indistinguishable from "not supplied" and must preserve."""
        stored = [_answer(P1, "Survives null")]
        self._seed(test_db, 9202, stored)

        body = {"username": "user9202", "gender": "male", "promptAnswers": None}
        body.update(prefs())
        r = client.put(f"{BASE}/users/9202", json=body, headers=auth_header(9202))
        assert r.status_code == 200, r.text

        assert test_db["users"].find_one({"id": 9202})["promptAnswers"] == stored

    def test_new_answers_replace_old_ones_wholesale(self, test_db):
        self._seed(test_db, 9203, [_answer(P1, "Old")])

        replacement = [_answer(P2, "New")]
        body = {"username": "user9203", "gender": "male", "promptAnswers": replacement}
        body.update(prefs())
        r = client.put(f"{BASE}/users/9203", json=body, headers=auth_header(9203))
        assert r.status_code == 200, r.text

        assert test_db["users"].find_one({"id": 9203})["promptAnswers"] == replacement

    def test_update_rejects_four_answers(self, test_db):
        self._seed(test_db, 9204, [])
        body = {
            "username": "user9204", "gender": "male",
            "promptAnswers": [_answer(p) for p in (P1, P2, P3, P4)],
        }
        body.update(prefs())
        r = client.put(f"{BASE}/users/9204", json=body, headers=auth_header(9204))
        assert r.status_code == 422

    def test_update_rejects_duplicate_prompt_ids(self, test_db):
        self._seed(test_db, 9205, [])
        body = {
            "username": "user9205", "gender": "male",
            "promptAnswers": [_answer(P1, "a"), _answer(P1, "b")],
        }
        body.update(prefs())
        r = client.put(f"{BASE}/users/9205", json=body, headers=auth_header(9205))
        assert r.status_code == 422

    def test_update_rejects_unknown_prompt_id(self, test_db):
        self._seed(test_db, 9206, [])
        body = {
            "username": "user9206", "gender": "male",
            "promptAnswers": [_answer("ghost_prompt", "hi")],
        }
        body.update(prefs())
        r = client.put(f"{BASE}/users/9206", json=body, headers=auth_header(9206))
        assert r.status_code == 422

    def test_update_rejects_over_length_answer(self, test_db):
        self._seed(test_db, 9207, [])
        body = {
            "username": "user9207", "gender": "male",
            "promptAnswers": [_answer(P1, "z" * (PROMPT_ANSWER_MAX_LENGTH + 1))],
        }
        body.update(prefs())
        r = client.put(f"{BASE}/users/9207", json=body, headers=auth_header(9207))
        assert r.status_code == 422

    def test_a_rejected_update_leaves_stored_answers_untouched(self, test_db):
        stored = [_answer(P1, "Still here")]
        self._seed(test_db, 9208, stored)
        body = {
            "username": "user9208", "gender": "male",
            "promptAnswers": [_answer("bogus", "x")],
        }
        body.update(prefs())
        assert client.put(f"{BASE}/users/9208", json=body,
                          headers=auth_header(9208)).status_code == 422
        assert test_db["users"].find_one({"id": 9208})["promptAnswers"] == stored


# ---------------------------------------------------------------------------
# Model-level invariants
# ---------------------------------------------------------------------------

class TestPromptCatalogueInvariants:

    def test_max_prompt_answers_is_three(self):
        assert MAX_PROMPT_ANSWERS == 3

    def test_answer_max_length_is_150(self):
        assert PROMPT_ANSWER_MAX_LENGTH == 150

    def test_prompt_ids_frozenset_matches_the_list(self):
        assert PROFILE_PROMPT_IDS == frozenset(p["id"] for p in PROFILE_PROMPTS)

    def test_prompt_ids_are_snake_case_and_stable_looking(self):
        import re
        for pid in PROFILE_PROMPT_IDS:
            assert re.fullmatch(r"[a-z0-9_]+", pid), pid
