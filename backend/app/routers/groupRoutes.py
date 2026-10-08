"""P3FT.13 — Roommate group endpoints.

Registered in main.py with the `/api` prefix, so every path below is served at
`/api/groups/...`.

Ownership is taken from the bearer token (`get_current_user`) rather than from a
`{user_id}` path parameter, so `get_current_user_or_403` is deliberately not
used here — note that `POST /groups/{group_id}/invite/{user_id}` names the
*invitee*, not the caller.

Service exceptions map to status codes as follows:
    LookupError     -> 404
    PermissionError -> 403
    ValueError      -> 400
"""
from contextlib import contextmanager
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import get_current_user
from app.limiter import limiter
from app.models import GROUP_MAX_SIZE, GroupCreate, GroupInviteRespondRequest
from app.services.groupService import GroupService

router = APIRouter(tags=["groups"])

groupService = GroupService()


@contextmanager
def _service_errors():
    try:
        yield
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups")
@limiter.limit("10/hour")
async def create_group(
    request: Request,
    body: Optional[GroupCreate] = None,
    current_user: dict = Depends(get_current_user),
):
    """Create a roommate group with the caller as its first member."""
    name = body.name if body else None
    max_size = body.maxSize if body else GROUP_MAX_SIZE
    with _service_errors():
        return await groupService.create_group(current_user["id"], name=name, max_size=max_size)


@router.get("/groups/mine")
@limiter.limit("60/minute")
async def get_my_group(request: Request, current_user: dict = Depends(get_current_user)):
    """The caller's active group (or null) plus any invites addressed to them."""
    with _service_errors():
        return await groupService.get_my_group(current_user["id"])


@router.post("/groups/{group_id}/invite/{user_id}")
@limiter.limit("10/hour")
async def invite_to_group(
    request: Request,
    group_id: int,
    user_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Invite `user_id` — who must be a match of some current member — to the group."""
    with _service_errors():
        return await groupService.invite(group_id, current_user["id"], user_id)


@router.post("/groups/{group_id}/invites/{invite_id}/respond")
@limiter.limit("30/minute")
async def respond_to_group_invite(
    request: Request,
    group_id: int,
    invite_id: int,
    body: GroupInviteRespondRequest,
    current_user: dict = Depends(get_current_user),
):
    """Accept or decline an invite addressed to the caller."""
    with _service_errors():
        return await groupService.respond_to_invite(
            group_id, invite_id, current_user["id"], body.action
        )


@router.post("/groups/{group_id}/leave")
@limiter.limit("10/hour")
async def leave_group(request: Request, group_id: int, current_user: dict = Depends(get_current_user)):
    """Leave a group. The group closes when its last member leaves."""
    with _service_errors():
        return await groupService.leave(group_id, current_user["id"])


@router.delete("/groups/{group_id}")
@limiter.limit("10/hour")
async def disband_group(request: Request, group_id: int, current_user: dict = Depends(get_current_user)):
    """Disband a group. Allowed for the creator, or for the last remaining member."""
    with _service_errors():
        return await groupService.disband(group_id, current_user["id"])


@router.get("/groups/{group_id}/compatibility")
@limiter.limit("60/minute")
async def group_compatibility(request: Request, group_id: int, current_user: dict = Depends(get_current_user)):
    """Pairwise compatibility matrix, mean score, and weakest pair for the group."""
    with _service_errors():
        return await groupService.compatibility(group_id, current_user["id"])
