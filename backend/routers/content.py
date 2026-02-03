from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
import uuid
import re

from core.database import db
from core.auth import get_current_user

router = APIRouter(prefix="/content", tags=["Content Management"])

class ContentCreate(BaseModel):
    title: str
    content_type: str = "article"
    content_body: dict
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    category_id: Optional[str] = None
    tags: List[str] = []
    status: str = "draft"
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None

def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title"""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    return slug

@router.post("/")
async def create_content(
    content: ContentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create new content"""
    content_id = str(uuid.uuid4())
    slug = generate_slug(content.title)

    # Ensure unique slug
    existing = await db.content_items.find_one({"slug": slug})
    if existing:
        slug = f"{slug}-{str(uuid.uuid4())[:8]}"

    now = datetime.now(timezone.utc).isoformat()

    # Create content
    await db.content_items.insert_one({
        "id": content_id,
        "title": content.title,
        "slug": slug,
        "content_type": content.content_type,
        "content_body": content.content_body,
        "excerpt": content.excerpt,
        "featured_image": content.featured_image,
        "author_id": current_user["id"],
        "category_id": content.category_id,
        "status": content.status,
        "seo_title": content.seo_title or content.title,
        "seo_description": content.seo_description or content.excerpt,
        "published_at": now if content.status == "published" else None,
        "created_at": now,
        "updated_at": now
    })

    # Create initial version
    await db.content_versions.insert_one({
        "id": str(uuid.uuid4()),
        "content_id": content_id,
        "version_number": 1,
        "title": content.title,
        "content_body": content.content_body,
        "author_id": current_user["id"],
        "change_summary": "Initial version",
        "created_at": now
    })

    # Add tags
    for tag_name in content.tags:
        tag_slug = generate_slug(tag_name)
        tag = await db.content_tags.find_one({"slug": tag_slug})

        if not tag:
            tag_id = str(uuid.uuid4())
            await db.content_tags.insert_one({
                "id": tag_id,
                "name": tag_name,
                "slug": tag_slug,
                "usage_count": 1,
                "created_at": now
            })
        else:
            tag_id = tag["id"]
            await db.content_tags.update_one(
                {"id": tag_id},
                {"$inc": {"usage_count": 1}}
            )

        await db.content_tag_mappings.insert_one({
            "id": str(uuid.uuid4()),
            "content_id": content_id,
            "tag_id": tag_id,
            "created_at": now
        })

    return {"message": "Content created successfully", "content_id": content_id, "slug": slug}

@router.get("/")
async def list_content(
    status: Optional[str] = None,
    content_type: Optional[str] = None,
    category_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 20
):
    """List content items"""
    query = {}

    if status:
        query["status"] = status
    else:
        query["status"] = "published"

    if content_type:
        query["content_type"] = content_type

    if category_id:
        query["category_id"] = category_id

    items = await db.content_items.find(
        query, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    return {"content": items, "total": len(items)}

@router.get("/{slug}")
async def get_content_by_slug(slug: str):
    """Get content by slug"""
    content = await db.content_items.find_one({"slug": slug}, {"_id": 0})

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Get tags
    tag_mappings = await db.content_tag_mappings.find(
        {"content_id": content["id"]},
        {"_id": 0, "tag_id": 1}
    ).to_list(50)

    tag_ids = [m["tag_id"] for m in tag_mappings]
    tags = await db.content_tags.find(
        {"id": {"$in": tag_ids}},
        {"_id": 0}
    ).to_list(50)

    content["tags"] = tags

    return content

@router.get("/categories/")
async def list_categories():
    """List all active categories"""
    categories = await db.content_categories.find(
        {"is_active": True},
        {"_id": 0}
    ).sort("display_order", 1).to_list(50)

    return {"categories": categories}
