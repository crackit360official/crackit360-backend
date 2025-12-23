from fastapi import APIRouter, Depends
from schemas.models import DiscussionCreate, ReplyCreate, VoteCreate
from services.discussion_service import (
    create_discussion,
    get_all_discussions,
    add_reply,
    vote_discussion,
    get_replies
)
from security import get_current_user

router = APIRouter(
    prefix="/api/discussions",
    tags=["Discussions"]
)


@router.get("/")
async def get_all():
    return await get_all_discussions()


@router.post("/")
async def create(
    data: DiscussionCreate,
    current_user: dict = Depends(get_current_user)
):
    return await create_discussion(data, current_user)




@router.post("/reply")
def reply(
    data: ReplyCreate,
    current_user: dict = Depends(get_current_user)
):
    add_reply(data, current_user)
    return {"message": "Reply added"}


@router.get("/{discussion_id}/replies")
async def fetch_replies(discussion_id: str):
    return await get_replies(discussion_id)


@router.post("/{discussion_id}/vote")
async def vote(
    discussion_id: str,
    data: VoteCreate,
    current_user: dict = Depends(get_current_user)
):
    await vote_discussion(discussion_id, current_user, data.type)
    return {"message": "Vote updated"}
