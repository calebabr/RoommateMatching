"""P3FT.13 — Roommate group formation.

A group is 2-4 same-gender users who intend to live together.  Rules:

  * a user belongs to at most one active (open/full) group at a time
  * an invitee must already be a match of at least one current member
    (the check reuses `auth.dependencies.verify_match_exists`, so blocks apply)
  * all members must be gender-compatible (`matchScore.genderCompatible`)
  * group membership does NOT consume the `MAX_MATCHES = 5` cap

Error convention used throughout this module:
  LookupError     -> 404 (group / invite does not exist)
  PermissionError -> 403 (caller is not allowed to do this)
  ValueError      -> 400 (request is understood but not valid right now)
"""
from datetime import datetime, timezone

from fastapi import HTTPException
from pymongo import ReturnDocument

from app.auth.dependencies import verify_match_exists
from app.database import (
    groups_collection,
    group_invites_collection,
    users_collection,
    counters_collection,
)
from app.models import GROUP_MIN_SIZE, GROUP_MAX_SIZE, UserInDB
from app.services.matchScore import matchScore
from app.services.notificationService import NotificationService

# A user occupies one of these until the group is closed or disbanded.
ACTIVE_STATUSES = ("open", "full")


def _strip(doc: dict) -> dict:
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


class GroupService:
    def __init__(self):
        self.groups = groups_collection
        self.invites = group_invites_collection
        self.users = users_collection
        self.counters = counters_collection
        self.scorer = matchScore()
        self.notifications = NotificationService()

    # --- internals ---------------------------------------------------------

    async def _next_id(self, counter_name: str) -> int:
        """Atomic integer id, same counters pattern used for user ids."""
        result = await self.counters.find_one_and_update(
            {"_id": counter_name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return result["seq"]

    async def _is_match(self, user_a: int, user_b: int) -> bool:
        """Reuse verify_match_exists so block handling stays identical."""
        try:
            await verify_match_exists(user_a, user_b)
            return True
        except HTTPException:
            return False

    async def _get_group(self, group_id: int) -> dict:
        group = await self.groups.find_one({"id": group_id})
        if not group:
            raise LookupError("Group not found")
        return group

    async def _active_group_for(self, user_id: int) -> dict:
        return await self.groups.find_one({
            "memberIds": user_id,
            "status": {"$in": list(ACTIVE_STATUSES)},
        })

    async def _username(self, user_id: int) -> str:
        user = await self.users.find_one({"id": user_id})
        return user.get("username", f"User #{user_id}") if user else f"User #{user_id}"

    async def _assert_gender_compatible(self, member_ids: list, candidate: dict) -> None:
        for member_id in member_ids:
            member = await self.users.find_one({"id": member_id})
            if member and not self.scorer.genderCompatible(member, candidate):
                raise PermissionError("All group members must be the same gender")

    def _status_for(self, member_count: int, max_size: int) -> str:
        if member_count == 0:
            return "closed"
        return "full" if member_count >= max_size else "open"

    async def _cancel_invites(self, query: dict) -> int:
        """Mark matching pending invites as declined. Returns how many changed."""
        query = dict(query)
        query["status"] = "pending"
        result = await self.invites.update_many(query, {"$set": {"status": "declined"}})
        return result.modified_count

    async def _member_summaries(self, member_ids: list) -> list:
        members = []
        for member_id in member_ids:
            user = await self.users.find_one({"id": member_id})
            if not user:
                continue
            members.append({
                "id": user["id"],
                "username": user.get("username", f"User #{member_id}"),
                "photoUrl": user.get("photoUrl", ""),
                "gender": user.get("gender", ""),
            })
        return members

    async def _serialize_group(self, group: dict) -> dict:
        group = _strip(dict(group))
        group["members"] = await self._member_summaries(group.get("memberIds", []))
        pending = []
        async for invite in self.invites.find({"groupId": group["id"], "status": "pending"}):
            invite = _strip(invite)
            invite["toUsername"] = await self._username(invite["toUserId"])
            pending.append(invite)
        group["invites"] = pending
        return group

    async def _remove_member(self, group: dict, user_id: int, notify: bool) -> dict:
        """Take user_id out of `group`, fixing status/creator and pending invites."""
        remaining = [m for m in group.get("memberIds", []) if m != user_id]
        max_size = group.get("maxSize", GROUP_MAX_SIZE)
        new_status = self._status_for(len(remaining), max_size)

        update = {"memberIds": remaining, "status": new_status}
        # Hand the group over if the creator walked out but others remain.
        if remaining and group.get("createdBy") == user_id:
            update["createdBy"] = remaining[0]

        await self.groups.update_one({"id": group["id"]}, {"$set": update})

        # Invites this user sent on the group's behalf are no longer theirs to make.
        await self._cancel_invites({"groupId": group["id"], "fromUserId": user_id})
        if not remaining:
            await self._cancel_invites({"groupId": group["id"]})

        if notify and remaining:
            username = await self._username(user_id)
            for member_id in remaining:
                await self.notifications.create(
                    "group_member_left", user_id, member_id,
                    f"{username} left your roommate group.",
                )

        return await self._get_group(group["id"])

    # --- public API --------------------------------------------------------

    async def create_group(self, user_id: int, name=None, max_size: int = GROUP_MAX_SIZE) -> dict:
        if max_size < GROUP_MIN_SIZE or max_size > GROUP_MAX_SIZE:
            raise ValueError(f"maxSize must be between {GROUP_MIN_SIZE} and {GROUP_MAX_SIZE}")

        existing = await self._active_group_for(user_id)
        if existing:
            raise ValueError("You are already in a group")

        user = await self.users.find_one({"id": user_id})
        if not user:
            raise LookupError("User not found")

        group = {
            "id": await self._next_id("group_id"),
            "name": name,
            "memberIds": [user_id],
            "createdBy": user_id,
            "createdAt": datetime.now(timezone.utc),
            "maxSize": max_size,
            "status": "open",
        }
        await self.groups.insert_one(dict(group))
        return await self._serialize_group(group)

    async def get_my_group(self, user_id: int) -> dict:
        """The caller's active group (or None) plus invites addressed to them."""
        group = await self._active_group_for(user_id)
        serialized = await self._serialize_group(group) if group else None

        pending = []
        async for invite in self.invites.find({"toUserId": user_id, "status": "pending"}):
            invite = _strip(invite)
            invite_group = await self.groups.find_one({"id": invite["groupId"]})
            if not invite_group or invite_group.get("status") not in ACTIVE_STATUSES:
                continue
            invite["groupName"] = invite_group.get("name")
            invite["memberCount"] = len(invite_group.get("memberIds", []))
            invite["maxSize"] = invite_group.get("maxSize", GROUP_MAX_SIZE)
            invite["fromUsername"] = await self._username(invite["fromUserId"])
            pending.append(invite)

        return {"group": serialized, "pendingInvites": pending}

    async def invite(self, group_id: int, from_user_id: int, to_user_id: int) -> dict:
        group = await self._get_group(group_id)
        if group.get("status") not in ACTIVE_STATUSES:
            raise ValueError("Group is closed")
        if from_user_id not in group.get("memberIds", []):
            raise PermissionError("You are not a member of this group")
        if from_user_id == to_user_id:
            raise ValueError("Cannot invite yourself")

        member_ids = group.get("memberIds", [])
        if len(member_ids) >= group.get("maxSize", GROUP_MAX_SIZE):
            raise ValueError("Group is full")
        if to_user_id in member_ids:
            raise ValueError("That user is already a member of this group")

        invitee = await self.users.find_one({"id": to_user_id})
        if (
            not invitee
            or invitee.get("deletedAt")
            or invitee.get("is_deactivated")
            or invitee.get("is_banned")
        ):
            raise LookupError("User not found")

        if await self._active_group_for(to_user_id):
            raise ValueError("That user is already in a group")

        await self._assert_gender_compatible(member_ids, invitee)

        matched_with_a_member = False
        for member_id in member_ids:
            if await self._is_match(member_id, to_user_id):
                matched_with_a_member = True
                break
        if not matched_with_a_member:
            raise PermissionError("You can only invite one of your matches")

        duplicate = await self.invites.find_one({
            "groupId": group_id, "toUserId": to_user_id, "status": "pending",
        })
        if duplicate:
            raise ValueError("An invite is already pending for that user")

        invite = {
            "id": await self._next_id("group_invite_id"),
            "groupId": group_id,
            "fromUserId": from_user_id,
            "toUserId": to_user_id,
            "status": "pending",
            "createdAt": datetime.now(timezone.utc),
        }
        await self.invites.insert_one(dict(invite))

        inviter = await self._username(from_user_id)
        await self.notifications.create(
            "group_invite", from_user_id, to_user_id,
            f"{inviter} invited you to join their roommate group.",
        )
        return invite

    async def respond_to_invite(self, group_id: int, invite_id: int, user_id: int, action: str) -> dict:
        invite = await self.invites.find_one({"id": invite_id, "groupId": group_id})
        if not invite:
            raise LookupError("Invite not found")
        if invite["toUserId"] != user_id:
            raise PermissionError("This invite is not addressed to you")
        if invite.get("status") != "pending":
            raise ValueError("This invite has already been answered")

        if action == "decline":
            await self.invites.update_one({"id": invite_id}, {"$set": {"status": "declined"}})
            return {"status": "declined", "group": None}

        group = await self._get_group(group_id)
        if group.get("status") not in ACTIVE_STATUSES:
            raise ValueError("Group is closed")
        if await self._active_group_for(user_id):
            raise ValueError("You are already in a group")

        member_ids = group.get("memberIds", [])
        max_size = group.get("maxSize", GROUP_MAX_SIZE)
        if len(member_ids) >= max_size:
            raise ValueError("Group is full")

        user = await self.users.find_one({"id": user_id})
        if not user:
            raise LookupError("User not found")
        await self._assert_gender_compatible(member_ids, user)

        new_members = member_ids + [user_id]
        await self.groups.update_one(
            {"id": group_id},
            {"$set": {
                "memberIds": new_members,
                "status": self._status_for(len(new_members), max_size),
            }},
        )
        await self.invites.update_one({"id": invite_id}, {"$set": {"status": "accepted"}})
        # Any other group still waiting on this user is now moot.
        await self._cancel_invites({"toUserId": user_id})

        username = user.get("username", f"User #{user_id}")
        for member_id in member_ids:
            await self.notifications.create(
                "group_invite_accepted", user_id, member_id,
                f"{username} joined your roommate group.",
            )

        return {"status": "accepted", "group": await self._serialize_group(await self._get_group(group_id))}

    async def leave(self, group_id: int, user_id: int) -> dict:
        group = await self._get_group(group_id)
        if user_id not in group.get("memberIds", []):
            raise PermissionError("You are not a member of this group")
        updated = await self._remove_member(group, user_id, notify=True)
        return {"message": "Left group", "group": _strip(updated)}

    async def disband(self, group_id: int, user_id: int) -> dict:
        group = await self._get_group(group_id)
        member_ids = group.get("memberIds", [])
        if user_id not in member_ids:
            raise PermissionError("You are not a member of this group")
        if group.get("createdBy") != user_id and len(member_ids) > 1:
            raise PermissionError("Only the group creator can disband the group")

        for member_id in member_ids:
            if member_id != user_id:
                await self.notifications.create(
                    "group_disbanded", user_id, member_id,
                    "Your roommate group was disbanded.",
                )

        await self.invites.delete_many({"groupId": group_id})
        await self.groups.delete_one({"id": group_id})
        return {"message": "Group disbanded"}

    async def compatibility(self, group_id: int, user_id: int) -> dict:
        group = await self._get_group(group_id)
        member_ids = group.get("memberIds", [])
        if user_id not in member_ids:
            raise PermissionError("You are not a member of this group")

        match_dicts = {}
        for member_id in member_ids:
            user = await self.users.find_one({"id": member_id})
            if not user:
                continue
            try:
                match_dicts[member_id] = UserInDB(**user).toMatchDict()
            except Exception:
                continue  # legacy profile missing preferences — omit from the matrix

        matrix = {str(mid): {} for mid in match_dicts}
        pairs = []
        scorable = list(match_dicts.keys())
        for i in range(len(scorable)):
            for j in range(i + 1, len(scorable)):
                a, b = scorable[i], scorable[j]
                score = round(self.scorer.compatibilityScore(match_dicts[a], match_dicts[b]), 6)
                matrix[str(a)][str(b)] = score
                matrix[str(b)][str(a)] = score
                pairs.append({"userA": a, "userB": b, "compatibilityScore": score})

        mean = round(sum(p["compatibilityScore"] for p in pairs) / len(pairs), 6) if pairs else 0.0
        weakest = min(pairs, key=lambda p: p["compatibilityScore"]) if pairs else None

        return {
            "groupId": group_id,
            "memberIds": member_ids,
            "matrix": matrix,
            "pairs": pairs,
            "mean": mean,
            "weakestPair": weakest,
        }

    # --- cascades ----------------------------------------------------------

    async def remove_user_everywhere(self, user_id: int) -> None:
        """Deactivate / delete cascade: drop the user from any group, kill invites."""
        # Materialize before mutating — the loop body rewrites these documents.
        groups = await self.groups.find({"memberIds": user_id}).to_list(length=None)
        for group in groups:
            await self._remove_member(group, user_id, notify=True)
        await self._cancel_invites({"toUserId": user_id})
        await self._cancel_invites({"fromUserId": user_id})

    async def separate_pair(self, initiator_id: int, other_id: int) -> None:
        """Block / unmatch cascade.

        The user who acted keeps their group; the other party is removed from it
        when the two share one.  Pending invites between them are cancelled in
        both directions.
        """
        await self._cancel_invites({"fromUserId": initiator_id, "toUserId": other_id})
        await self._cancel_invites({"fromUserId": other_id, "toUserId": initiator_id})

        shared = await self.groups.find({
            "memberIds": {"$all": [initiator_id, other_id]},
            "status": {"$in": list(ACTIVE_STATUSES)},
        }).to_list(length=None)
        for group in shared:
            await self._remove_member(group, other_id, notify=True)
