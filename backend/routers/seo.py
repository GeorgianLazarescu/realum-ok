from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
from pydantic import BaseModel
import uuid

from core.database import db
from core.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/seo", tags=["SEO & Marketing"])

# ===================== MODELS =====================

class MetaTagsUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = []
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    twitter_card: Optional[str] = "summary_large_image"
    canonical_url: Optional[str] = None

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    campaign_type: str = "referral"  # referral, promotion, event, partnership
    start_date: str
    end_date: str
    reward_type: str = "tokens"  # tokens, badge, xp
    reward_amount: float = 0
    target_actions: List[str] = []  # signup, purchase, share, complete_course
    max_participants: Optional[int] = None
    budget: float = 0

class LandingPageCreate(BaseModel):
    slug: str
    title: str
    subtitle: Optional[str] = None
    hero_image: Optional[str] = None
    cta_text: str = "Get Started"
    cta_url: str = "/register"
    sections: List[Dict] = []
    is_published: bool = False

class EmailCampaignCreate(BaseModel):
    name: str
    subject: str
    content: str
    target_segment: str = "all"  # all, active, inactive, new, premium
    scheduled_at: Optional[str] = None

# ===================== SEO ENDPOINTS =====================

@router.get("/meta/{page_type}")
async def get_page_meta(page_type: str):
    """Get SEO meta tags for a page type"""
    try:
        meta = await db.seo_meta.find_one(
            {"page_type": page_type},
            {"_id": 0}
        )
        
        if not meta:
            # Return defaults
            defaults = {
                "home": {
                    "title": "REALUM - Educational & Economic Metaverse",
                    "description": "Learn, collaborate, and earn in the REALUM metaverse. Join our community of creators, contributors, and learners.",
                    "keywords": ["metaverse", "education", "cryptocurrency", "blockchain", "learning", "DAO"]
                },
                "courses": {
                    "title": "Courses - REALUM Academy",
                    "description": "Learn new skills and earn RLM tokens. Explore our courses on blockchain, DeFi, Web3, and more.",
                    "keywords": ["courses", "blockchain education", "web3 learning", "crypto courses"]
                },
                "jobs": {
                    "title": "Jobs & Bounties - REALUM",
                    "description": "Find jobs and bounties in the REALUM ecosystem. Contribute and earn rewards.",
                    "keywords": ["crypto jobs", "blockchain jobs", "bounties", "freelance"]
                },
                "dao": {
                    "title": "DAO Governance - REALUM",
                    "description": "Participate in REALUM governance. Vote on proposals and shape the future of the platform.",
                    "keywords": ["DAO", "governance", "voting", "proposals"]
                }
            }
            meta = defaults.get(page_type, {
                "title": f"REALUM - {page_type.title()}",
                "description": "Explore the REALUM metaverse",
                "keywords": ["REALUM", "metaverse"]
            })
            meta["page_type"] = page_type
        
        return {"meta": meta}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/meta/{page_type}")
async def update_page_meta(
    page_type: str,
    update: MetaTagsUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update SEO meta tags for a page (admin only)"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        update_data = {k: v for k, v in update.dict().items() if v is not None}
        update_data["page_type"] = page_type
        update_data["updated_at"] = now
        update_data["updated_by"] = current_user["id"]
        
        await db.seo_meta.update_one(
            {"page_type": page_type},
            {"$set": update_data},
            upsert=True
        )
        
        return {"message": "Meta tags updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sitemap")
async def generate_sitemap():
    """Generate sitemap data for the platform"""
    try:
        base_url = "https://realum.io"
        now = datetime.now(timezone.utc).isoformat()
        
        # Static pages
        urls = [
            {"loc": f"{base_url}/", "priority": "1.0", "changefreq": "daily"},
            {"loc": f"{base_url}/courses", "priority": "0.9", "changefreq": "daily"},
            {"loc": f"{base_url}/jobs", "priority": "0.8", "changefreq": "daily"},
            {"loc": f"{base_url}/marketplace", "priority": "0.8", "changefreq": "daily"},
            {"loc": f"{base_url}/voting", "priority": "0.7", "changefreq": "weekly"},
            {"loc": f"{base_url}/leaderboard", "priority": "0.6", "changefreq": "daily"},
        ]
        
        # Dynamic content - Courses
        courses = await db.courses.find(
            {"is_published": True},
            {"_id": 0, "id": 1, "updated_at": 1}
        ).to_list(100)
        
        for course in courses:
            urls.append({
                "loc": f"{base_url}/courses/{course['id']}",
                "lastmod": course.get("updated_at", now),
                "priority": "0.7",
                "changefreq": "weekly"
            })
        
        # Dynamic content - Published content
        content = await db.content.find(
            {"status": "published"},
            {"_id": 0, "slug": 1, "updated_at": 1}
        ).to_list(100)
        
        for item in content:
            urls.append({
                "loc": f"{base_url}/content/{item['slug']}",
                "lastmod": item.get("updated_at", now),
                "priority": "0.6",
                "changefreq": "weekly"
            })
        
        return {
            "urls": urls,
            "count": len(urls),
            "generated_at": now
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/robots")
async def get_robots_txt():
    """Get robots.txt configuration"""
    return {
        "content": """User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /profile/
Disallow: /wallet/
Disallow: /settings/

Sitemap: https://realum.io/sitemap.xml
"""
    }


# ===================== MARKETING CAMPAIGNS =====================

@router.post("/campaigns")
async def create_campaign(
    campaign: CampaignCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a marketing campaign (admin only)"""
    try:
        campaign_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        campaign_data = {
            "id": campaign_id,
            **campaign.dict(),
            "status": "draft",
            "participants_count": 0,
            "conversions": 0,
            "total_rewards_distributed": 0,
            "created_by": current_user["id"],
            "created_at": now
        }
        
        await db.marketing_campaigns.insert_one(campaign_data)
        campaign_data.pop("_id", None)
        
        return {"message": "Campaign created", "campaign": campaign_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns")
async def get_campaigns(
    status: Optional[str] = None,
    campaign_type: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Get all marketing campaigns (admin only)"""
    try:
        query = {}
        if status:
            query["status"] = status
        if campaign_type:
            query["campaign_type"] = campaign_type
        
        campaigns = await db.marketing_campaigns.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        return {"campaigns": campaigns}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/campaigns/active")
async def get_active_campaigns():
    """Get active campaigns for users"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        campaigns = await db.marketing_campaigns.find(
            {
                "status": "active",
                "start_date": {"$lte": now},
                "end_date": {"$gte": now}
            },
            {"_id": 0, "id": 1, "name": 1, "description": 1, "campaign_type": 1,
             "reward_type": 1, "reward_amount": 1, "end_date": 1}
        ).to_list(20)
        
        return {"campaigns": campaigns}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/campaigns/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    status: str,
    current_user: dict = Depends(require_admin)
):
    """Update campaign status (admin only)"""
    try:
        if status not in ["draft", "active", "paused", "completed", "cancelled"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        result = await db.marketing_campaigns.update_one(
            {"id": campaign_id},
            {"$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return {"message": f"Campaign status updated to {status}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/campaigns/{campaign_id}/participate")
async def participate_in_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Participate in a marketing campaign"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        # Check campaign exists and is active
        campaign = await db.marketing_campaigns.find_one({"id": campaign_id})
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        if campaign["status"] != "active":
            raise HTTPException(status_code=400, detail="Campaign is not active")
        
        if campaign["end_date"] < now:
            raise HTTPException(status_code=400, detail="Campaign has ended")
        
        # Check if already participating
        existing = await db.campaign_participants.find_one({
            "campaign_id": campaign_id,
            "user_id": current_user["id"]
        })
        
        if existing:
            return {"message": "Already participating", "participant": existing}
        
        # Check max participants
        if campaign.get("max_participants"):
            count = await db.campaign_participants.count_documents({"campaign_id": campaign_id})
            if count >= campaign["max_participants"]:
                raise HTTPException(status_code=400, detail="Campaign is full")
        
        participant_id = str(uuid.uuid4())
        
        await db.campaign_participants.insert_one({
            "id": participant_id,
            "campaign_id": campaign_id,
            "user_id": current_user["id"],
            "username": current_user.get("username"),
            "completed_actions": [],
            "rewards_earned": 0,
            "joined_at": now
        })
        
        await db.marketing_campaigns.update_one(
            {"id": campaign_id},
            {"$inc": {"participants_count": 1}}
        )
        
        return {"message": "Joined campaign", "participant_id": participant_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===================== LANDING PAGES =====================

@router.post("/landing-pages")
async def create_landing_page(
    page: LandingPageCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a marketing landing page (admin only)"""
    try:
        # Check slug uniqueness
        existing = await db.landing_pages.find_one({"slug": page.slug})
        if existing:
            raise HTTPException(status_code=400, detail="Slug already exists")
        
        page_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        page_data = {
            "id": page_id,
            **page.dict(),
            "views": 0,
            "conversions": 0,
            "created_by": current_user["id"],
            "created_at": now
        }
        
        await db.landing_pages.insert_one(page_data)
        page_data.pop("_id", None)
        
        return {"message": "Landing page created", "page": page_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/landing-pages/{slug}")
async def get_landing_page(slug: str):
    """Get a landing page by slug"""
    try:
        page = await db.landing_pages.find_one(
            {"slug": slug, "is_published": True},
            {"_id": 0}
        )
        
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")
        
        # Track view
        await db.landing_pages.update_one(
            {"slug": slug},
            {"$inc": {"views": 1}}
        )
        
        return {"page": page}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/landing-pages")
async def list_landing_pages(current_user: dict = Depends(require_admin)):
    """List all landing pages (admin only)"""
    try:
        pages = await db.landing_pages.find(
            {},
            {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        
        return {"pages": pages}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===================== ANALYTICS =====================

@router.get("/analytics/overview")
async def get_marketing_analytics(
    period: str = "week",
    current_user: dict = Depends(require_admin)
):
    """Get marketing analytics overview (admin only)"""
    try:
        now = datetime.now(timezone.utc)
        
        if period == "day":
            start = (now - timedelta(days=1)).isoformat()
        elif period == "week":
            start = (now - timedelta(days=7)).isoformat()
        elif period == "month":
            start = (now - timedelta(days=30)).isoformat()
        else:
            start = (now - timedelta(days=7)).isoformat()
        
        # New signups
        new_users = await db.users.count_documents({
            "created_at": {"$gte": start}
        })
        
        # Active campaigns
        active_campaigns = await db.marketing_campaigns.count_documents({
            "status": "active"
        })
        
        # Total campaign participants
        total_participants = await db.campaign_participants.count_documents({
            "joined_at": {"$gte": start}
        })
        
        # Landing page views
        pipeline = [
            {"$match": {"is_published": True}},
            {"$group": {"_id": None, "total_views": {"$sum": "$views"}}}
        ]
        views_result = await db.landing_pages.aggregate(pipeline).to_list(1)
        total_views = views_result[0]["total_views"] if views_result else 0
        
        # Referral signups
        referral_signups = await db.users.count_documents({
            "referred_by": {"$exists": True, "$ne": None},
            "created_at": {"$gte": start}
        })
        
        return {
            "analytics": {
                "period": period,
                "new_signups": new_users,
                "active_campaigns": active_campaigns,
                "campaign_participants": total_participants,
                "landing_page_views": total_views,
                "referral_signups": referral_signups
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics/campaigns/{campaign_id}")
async def get_campaign_analytics(
    campaign_id: str,
    current_user: dict = Depends(require_admin)
):
    """Get detailed analytics for a campaign (admin only)"""
    try:
        campaign = await db.marketing_campaigns.find_one(
            {"id": campaign_id},
            {"_id": 0}
        )
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Get participant stats
        participants = await db.campaign_participants.find(
            {"campaign_id": campaign_id},
            {"_id": 0}
        ).to_list(None)
        
        total_rewards = sum(p.get("rewards_earned", 0) for p in participants)
        completed_all = sum(1 for p in participants 
                          if len(p.get("completed_actions", [])) == len(campaign.get("target_actions", [])))
        
        return {
            "campaign": campaign,
            "analytics": {
                "total_participants": len(participants),
                "total_rewards_distributed": total_rewards,
                "completion_rate": completed_all / len(participants) * 100 if participants else 0,
                "budget_used_percent": total_rewards / campaign["budget"] * 100 if campaign.get("budget") else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===================== UTM TRACKING =====================

@router.post("/track")
async def track_utm_visit(
    request: Request,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    utm_campaign: Optional[str] = None,
    utm_content: Optional[str] = None,
    utm_term: Optional[str] = None
):
    """Track UTM parameters for marketing attribution"""
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        tracking_data = {
            "id": str(uuid.uuid4()),
            "utm_source": utm_source,
            "utm_medium": utm_medium,
            "utm_campaign": utm_campaign,
            "utm_content": utm_content,
            "utm_term": utm_term,
            "ip_address": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "referer": request.headers.get("referer"),
            "timestamp": now
        }
        
        await db.utm_tracking.insert_one(tracking_data)
        tracking_data.pop("_id", None)
        
        return {"message": "Visit tracked", "tracking_id": tracking_data["id"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/track/stats")
async def get_utm_stats(
    period: str = "week",
    current_user: dict = Depends(require_admin)
):
    """Get UTM tracking statistics (admin only)"""
    try:
        now = datetime.now(timezone.utc)
        
        if period == "day":
            start = (now - timedelta(days=1)).isoformat()
        elif period == "week":
            start = (now - timedelta(days=7)).isoformat()
        else:
            start = (now - timedelta(days=30)).isoformat()
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": start}}},
            {"$group": {
                "_id": {
                    "source": "$utm_source",
                    "medium": "$utm_medium",
                    "campaign": "$utm_campaign"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 20}
        ]
        
        results = await db.utm_tracking.aggregate(pipeline).to_list(20)
        
        stats = [
            {
                "source": r["_id"].get("source"),
                "medium": r["_id"].get("medium"),
                "campaign": r["_id"].get("campaign"),
                "visits": r["count"]
            }
            for r in results
        ]
        
        return {"stats": stats, "period": period}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
