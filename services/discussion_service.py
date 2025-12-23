from datetime import datetime
from db import discussion_col, reply_col, vote_col
from bson import ObjectId
from uuid import uuid4


async def create_discussion(data, user):
    doc = {
        "questionId": f"QST-{uuid4().hex[:8].upper()}",
        "title": data.title,
        "content": data.content,
        "category": data.category,
        "author": {
            "id": user["id"],
            "name": user["name"]
        },
        "stats": {
            "upvotes": 0,
            "downvotes": 0,
            "replies": 0
        },
        "status": "OPEN",
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }

    result = await discussion_col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

def add_reply(data, user):
    reply_col.insert_one({
        "discussionId": ObjectId(data.discussionId),
        "author": {
            "id": user["id"],
            "name": user["name"]
        },
        "content": data.content,
        "createdAt": datetime.utcnow()
    })

    discussion_col.update_one(
        {"_id": ObjectId(data.discussionId)},
        {
            "$inc": {"stats.replies": 1},
            "$set": {"updatedAt": datetime.utcnow()}
        }
    )


async def vote_discussion(discussion_id, user, vote_type):
    discussion_id = ObjectId(discussion_id)

    existing_vote = await vote_col.find_one({
        "discussionId": discussion_id,
        "userId": user["id"]
    })

    if existing_vote:
        if existing_vote["type"] == vote_type:
            await vote_col.delete_one({"_id": existing_vote["_id"]})
            field = "stats.upvotes" if vote_type == "UPVOTE" else "stats.downvotes"
            await discussion_col.update_one(
                {"_id": discussion_id},
                {"$inc": {field: -1}}
            )
            return

        old_field = "stats.upvotes" if existing_vote["type"] == "UPVOTE" else "stats.downvotes"
        new_field = "stats.upvotes" if vote_type == "UPVOTE" else "stats.downvotes"

        await vote_col.update_one(
            {"_id": existing_vote["_id"]},
            {"$set": {"type": vote_type}}
        )

        await discussion_col.update_one(
            {"_id": discussion_id},
            {"$inc": {old_field: -1, new_field: 1}}
        )
        return

    await vote_col.insert_one({
        "discussionId": discussion_id,
        "userId": user["id"],
        "type": vote_type,
        "createdAt": datetime.utcnow()
    })

    field = "stats.upvotes" if vote_type == "UPVOTE" else "stats.downvotes"
    await discussion_col.update_one(
        {"_id": discussion_id},
        {"$inc": {field: 1}}
    )


async def get_all_discussions():
    discussions = []
    cursor = discussion_col.find().sort("createdAt", -1)

    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        discussions.append(doc)

    return discussions


# ✅ NEW: get replies for a discussion
async def get_replies(discussion_id: str):
    pipeline = [
        {"$match": {"discussionId": ObjectId(discussion_id)}},
        {"$sort": {"createdAt": 1}},
        {
            "$project": {
                "_id": {"$toString": "$_id"},
                "content": 1,
                "author": 1,
                "createdAt": 1
            }
        }
    ]

    return await reply_col.aggregate(pipeline).to_list(length=100)
