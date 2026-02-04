from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

from core.database import db
from core.auth import get_current_user, require_admin
from services.notification_service import send_notification

router = APIRouter(prefix="/content", tags=["Content Management"])

# ===================== MODELS =====================

class ContentCreate(BaseModel):
    title: str
    slug: str
    content_type: str  # page, announcement, faq, guide, news
    body: str
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    is_published: bool = False
    publish_at: Optional[str] = None
    featured_image: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

class ContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None
    featured_image: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

class AnnouncementCreate(BaseModel):
    title: str
    message: str
    priority: str = "normal"  # low, normal, high, critical
    target_roles: List[str] = []  # Empty = all users
    expires_at: Optional[str] = None

class FAQCreate(BaseModel):
    question: str
    answer: str
    category: str
    order: int = 0

# ===================== CONTENT CRUD =====================

@router.post("/create")
async def create_content(
    content: ContentCreate,
    current_user: dict = Depends(require_admin)
):
    """Create new content (admin only)"""
    try:
        # Check slug uniqueness
        existing = await db.content.find_one({"slug": content.slug})
        if existing:
            raise HTTPException(status_code=400, detail="Slug already exists")

        content_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        content_data = {
            "id": content_id,
            "title": content.title,
            "slug": content.slug,
            "content_type": content.content_type,
            "body": content.body,
            "summary": content.summary,
            "category": content.category,
            "tags": content.tags,
            "is_published": content.is_published,
            "publish_at": content.publish_at,
            "featured_image": content.featured_image,
            "meta_title": content.meta_title or content.title,
            "meta_description": content.meta_description or content.summary,
            "author_id": current_user["id"],
            "version": 1,
            "view_count": 0,
            "created_at": now,
            "updated_at": now,
            "published_at": now if content.is_published else None
        }

        await db.content.insert_one(content_data)

        # Store initial version
        await db.content_versions.insert_one({
            "id": str(uuid.uuid4()),
            "content_id": content_id,
            "version": 1,
            "body": content.body,
            "edited_by": current_user["id"],
            "created_at": now
        })

        return {
            "message": "Content created",
            "content_id": content_id,
            "slug": content.slug
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/list")
async def list_content(
    content_type: Optional[str] = None,
    category: Optional[str] = None,
    is_published: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20
):
    """List content with filters"""
    try:
        query = {}
        if content_type:
            query["content_type"] = content_type
        if category:
            query["category"] = category
        if is_published is not None:
            query["is_published"] = is_published

        content_list = await db.content.find(
            query,
            {"_id": 0, "body": 0}  # Exclude body for listing
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

        # Enrich with author info
        for content in content_list:
            author = await db.users.find_one(
                {"id": content.get("author_id")},
                {"_id": 0, "username": 1}
            )
            if author:
                content["author_username"] = author.get("username")

        total = await db.content.count_documents(query)

        return {"content": content_list, "total": total}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/by-slug/{slug}")
async def get_content_by_slug(slug: str):
    """Get content by slug (public)"""
    try:
        content = await db.content.find_one(
            {"slug": slug, "is_published": True},
            {"_id": 0}
        )

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Increment view count
        await db.content.update_one(
            {"slug": slug},
            {"$inc": {"view_count": 1}}
        )

        # Get author info
        author = await db.users.find_one(
            {"id": content.get("author_id")},
            {"_id": 0, "username": 1, "avatar_url": 1}
        )
        if author:
            content["author_username"] = author.get("username")
            content["author_avatar"] = author.get("avatar_url")

        return content
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{content_id}")
async def get_content_by_id(
    content_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get content by ID (including unpublished for authors/admins)"""
    try:
        content = await db.content.find_one({"id": content_id}, {"_id": 0})

        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        # Check access for unpublished content
        if not content.get("is_published"):
            is_author = content.get("author_id") == current_user["id"]
            is_admin = current_user.get("role") in ["admin", "Admin"]
            if not (is_author or is_admin):
                raise HTTPException(status_code=403, detail="Access denied")

        # Get version history
        versions = await db.content_versions.find(
            {"content_id": content_id},
            {"_id": 0}
        ).sort("version", -1).to_list(10)

        return {
            "content": content,
            "versions": versions
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{content_id}")
async def update_content(
    content_id: str,
    update: ContentUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update content with version tracking"""
    try:
        content = await db.content.find_one({"id": content_id})
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        now = datetime.now(timezone.utc).isoformat()
        update_data = {k: v for k, v in update.dict().items() if v is not None}
        update_data["updated_at"] = now

        # If body changed, create new version
        if "body" in update_data:
            new_version = content.get("version", 1) + 1
            update_data["version"] = new_version

            await db.content_versions.insert_one({
                "id": str(uuid.uuid4()),
                "content_id": content_id,
                "version": new_version,
                "body": update_data["body"],
                "edited_by": current_user["id"],
                "created_at": now
            })

        # If publishing
        if update_data.get("is_published") and not content.get("is_published"):
            update_data["published_at"] = now

        await db.content.update_one(
            {"id": content_id},
            {"$set": update_data}
        )

        return {"message": "Content updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete content (soft delete)"""
    try:
        result = await db.content.update_one(
            {"id": content_id},
            {"$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": current_user["id"]
            }}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Content not found")

        return {"message": "Content deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{content_id}/restore")
async def restore_content(
    content_id: str,
    current_user: dict = Depends(require_admin)
):
    """Restore deleted content"""
    try:
        result = await db.content.update_one(
            {"id": content_id, "is_deleted": True},
            {"$set": {
                "is_deleted": False,
                "restored_at": datetime.now(timezone.utc).isoformat(),
                "restored_by": current_user["id"]
            }}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Deleted content not found")

        return {"message": "Content restored"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{content_id}/versions/{version}")
async def get_content_version(
    content_id: str,
    version: int,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific version of content"""
    try:
        content_version = await db.content_versions.find_one(
            {"content_id": content_id, "version": version},
            {"_id": 0}
        )

        if not content_version:
            raise HTTPException(status_code=404, detail="Version not found")

        return content_version
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{content_id}/revert/{version}")
async def revert_to_version(
    content_id: str,
    version: int,
    current_user: dict = Depends(require_admin)
):
    """Revert content to a previous version"""
    try:
        # Get target version
        target_version = await db.content_versions.find_one(
            {"content_id": content_id, "version": version}
        )

        if not target_version:
            raise HTTPException(status_code=404, detail="Version not found")

        content = await db.content.find_one({"id": content_id})
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")

        now = datetime.now(timezone.utc).isoformat()
        new_version = content.get("version", 1) + 1

        # Create new version with reverted body
        await db.content_versions.insert_one({
            "id": str(uuid.uuid4()),
            "content_id": content_id,
            "version": new_version,
            "body": target_version["body"],
            "edited_by": current_user["id"],
            "reverted_from": version,
            "created_at": now
        })

        # Update content
        await db.content.update_one(
            {"id": content_id},
            {"$set": {
                "body": target_version["body"],
                "version": new_version,
                "updated_at": now
            }}
        )

        return {
            "message": "Content reverted",
            "new_version": new_version,
            "reverted_from": version
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== ANNOUNCEMENTS =====================

@router.post("/announcements")
async def create_announcement(
    announcement: AnnouncementCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a system announcement"""
    try:
        announcement_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.announcements.insert_one({
            "id": announcement_id,
            "title": announcement.title,
            "message": announcement.message,
            "priority": announcement.priority,
            "target_roles": announcement.target_roles,
            "expires_at": announcement.expires_at,
            "is_active": True,
            "created_by": current_user["id"],
            "created_at": now
        })

        # Send notifications based on target roles
        if announcement.target_roles:
            users = await db.users.find(
                {"role": {"$in": announcement.target_roles}},
                {"_id": 0, "id": 1}
            ).to_list(None)
        else:
            users = await db.users.find({}, {"_id": 0, "id": 1}).to_list(None)

        for user in users:
            await send_notification(
                user_id=user["id"],
                title=announcement.title,
                message=announcement.message,
                notification_type="system",
                category="announcement"
            )

        return {
            "message": "Announcement created",
            "announcement_id": announcement_id,
            "notified_users": len(users)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/announcements")
async def get_announcements(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """Get announcements for current user"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        user_role = current_user.get("role", "citizen")

        query = {}
        if active_only:
            query["is_active"] = True
            query["$or"] = [
                {"expires_at": None},
                {"expires_at": {"$gt": now}}
            ]

        announcements = await db.announcements.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)

        # Filter by role
        filtered = [
            a for a in announcements
            if not a.get("target_roles") or user_role in a.get("target_roles", [])
        ]

        return {"announcements": filtered}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/announcements/{announcement_id}")
async def deactivate_announcement(
    announcement_id: str,
    current_user: dict = Depends(require_admin)
):
    """Deactivate an announcement"""
    try:
        result = await db.announcements.update_one(
            {"id": announcement_id},
            {"$set": {"is_active": False}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")

        return {"message": "Announcement deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== FAQ =====================

@router.post("/faq")
async def create_faq(
    faq: FAQCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a FAQ entry"""
    try:
        faq_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await db.faqs.insert_one({
            "id": faq_id,
            "question": faq.question,
            "answer": faq.answer,
            "category": faq.category,
            "order": faq.order,
            "is_published": True,
            "view_count": 0,
            "helpful_count": 0,
            "created_by": current_user["id"],
            "created_at": now
        })

        return {"message": "FAQ created", "faq_id": faq_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/faq")
async def get_faqs(category: Optional[str] = None):
    """Get all FAQs"""
    try:
        query = {"is_published": True}
        if category:
            query["category"] = category

        faqs = await db.faqs.find(
            query,
            {"_id": 0}
        ).sort("order", 1).to_list(100)

        # Group by category
        by_category = {}
        for faq in faqs:
            cat = faq.get("category", "general")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(faq)

        return {
            "faqs": faqs,
            "by_category": by_category
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/faq/{faq_id}/helpful")
async def mark_faq_helpful(faq_id: str):
    """Mark a FAQ as helpful"""
    try:
        result = await db.faqs.update_one(
            {"id": faq_id},
            {"$inc": {"helpful_count": 1}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="FAQ not found")

        return {"message": "Marked as helpful"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===================== STATS =====================

@router.get("/stats")
async def get_content_stats(current_user: dict = Depends(require_admin)):
    """Get content statistics (admin only)"""
    try:
        total_content = await db.content.count_documents({"is_deleted": {"$ne": True}})
        published = await db.content.count_documents({"is_published": True, "is_deleted": {"$ne": True}})
        drafts = await db.content.count_documents({"is_published": False, "is_deleted": {"$ne": True}})

        total_announcements = await db.announcements.count_documents({})
        active_announcements = await db.announcements.count_documents({"is_active": True})

        total_faqs = await db.faqs.count_documents({"is_published": True})

        # Content by type
        type_pipeline = [
            {"$match": {"is_deleted": {"$ne": True}}},
            {"$group": {"_id": "$content_type", "count": {"$sum": 1}}}
        ]
        type_result = await db.content.aggregate(type_pipeline).to_list(None)
        by_type = {item["_id"]: item["count"] for item in type_result if item["_id"]}

        # Most viewed content
        most_viewed = await db.content.find(
            {"is_published": True},
            {"_id": 0, "id": 1, "title": 1, "view_count": 1}
        ).sort("view_count", -1).limit(10).to_list(10)

        return {
            "stats": {
                "total_content": total_content,
                "published": published,
                "drafts": drafts,
                "total_announcements": total_announcements,
                "active_announcements": active_announcements,
                "total_faqs": total_faqs,
                "by_type": by_type
            },
            "most_viewed": most_viewed
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
