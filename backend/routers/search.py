from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from core.auth import get_current_user
from core.database import supabase

router = APIRouter(prefix="/api/search", tags=["Search"])

class SearchQuery(BaseModel):
    query: str
    filters: Optional[dict] = {}
    sort_by: Optional[str] = "relevance"

@router.get("/global")
async def global_search(
    q: str = Query(..., min_length=2),
    type: Optional[str] = None,
    limit: int = Query(50, le=100),
    current_user: dict = Depends(get_current_user)
):
    try:
        results = {
            "query": q,
            "results": {
                "users": [],
                "courses": [],
                "projects": [],
                "proposals": [],
                "jobs": [],
                "bounties": []
            },
            "total_results": 0
        }

        if not type or type == "users":
            users_result = supabase.table("users").select("id, username, avatar, bio").ilike("username", f"%{q}%").limit(limit).execute()
            results["results"]["users"] = users_result.data or []

        if not type or type == "courses":
            courses_result = supabase.table("courses").select("*").or_(f"title.ilike.%{q}%,description.ilike.%{q}%").limit(limit).execute()
            results["results"]["courses"] = courses_result.data or []

        if not type or type == "projects":
            projects_result = supabase.table("projects").select("*").or_(f"title.ilike.%{q}%,description.ilike.%{q}%").limit(limit).execute()
            results["results"]["projects"] = projects_result.data or []

        if not type or type == "proposals":
            proposals_result = supabase.table("proposals").select("*").or_(f"title.ilike.%{q}%,description.ilike.%{q}%").limit(limit).execute()
            results["results"]["proposals"] = proposals_result.data or []

        if not type or type == "jobs":
            jobs_result = supabase.table("jobs").select("*").or_(f"title.ilike.%{q}%,description.ilike.%{q}%").limit(limit).execute()
            results["results"]["jobs"] = jobs_result.data or []

        if not type or type == "bounties":
            bounties_result = supabase.table("bounties").select("*").or_(f"title.ilike.%{q}%,description.ilike.%{q}%").limit(limit).execute()
            results["results"]["bounties"] = bounties_result.data or []

        total = sum(len(v) for v in results["results"].values())
        results["total_results"] = total

        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/courses")
async def search_courses(
    q: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    min_rating: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("courses").select("*")

        if q:
            query = query.or_(f"title.ilike.%{q}%,description.ilike.%{q}%")
        if category:
            query = query.eq("category", category)
        if difficulty:
            query = query.eq("difficulty", difficulty)
        if min_rating:
            query = query.gte("average_rating", min_rating)

        result = query.order("created_at", desc=True).execute()

        return {"courses": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/projects")
async def search_projects(
    q: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("projects").select("*")

        if q:
            query = query.or_(f"title.ilike.%{q}%,description.ilike.%{q}%")
        if category:
            query = query.eq("category", category)
        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).execute()

        return {"projects": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs")
async def search_jobs(
    q: Optional[str] = None,
    job_type: Optional[str] = None,
    min_budget: Optional[float] = None,
    skills: Optional[List[str]] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("jobs").select("*")

        if q:
            query = query.or_(f"title.ilike.%{q}%,description.ilike.%{q}%")
        if job_type:
            query = query.eq("job_type", job_type)
        if min_budget:
            query = query.gte("budget", min_budget)

        result = query.order("created_at", desc=True).execute()

        if skills and result.data:
            filtered_results = []
            for job in result.data:
                job_skills = job.get("required_skills", [])
                if any(skill in job_skills for skill in skills):
                    filtered_results.append(job)
            return {"jobs": filtered_results}

        return {"jobs": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users")
async def search_users(
    q: Optional[str] = None,
    role: Optional[str] = None,
    skills: Optional[List[str]] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        query = supabase.table("users").select("id, username, avatar, bio, role, skills, xp, level")

        if q:
            query = query.or_(f"username.ilike.%{q}%,bio.ilike.%{q}%")
        if role:
            query = query.eq("role", role)

        result = query.order("xp", desc=True).execute()

        if skills and result.data:
            filtered_results = []
            for user in result.data:
                user_skills = user.get("skills", [])
                if any(skill in user_skills for skill in skills):
                    filtered_results.append(user)
            return {"users": filtered_results}

        return {"users": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tags")
async def search_by_tags(
    tags: List[str] = Query(...),
    content_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        results = {
            "tags": tags,
            "results": []
        }

        if not content_type or content_type == "courses":
            courses_result = supabase.table("content_tags").select("*, courses(*)").in_("tag", tags).eq("content_type", "course").execute()
            results["results"].extend([{"type": "course", "data": t.get("courses")} for t in courses_result.data or [] if t.get("courses")])

        if not content_type or content_type == "projects":
            projects_result = supabase.table("content_tags").select("*, projects(*)").in_("tag", tags).eq("content_type", "project").execute()
            results["results"].extend([{"type": "project", "data": t.get("projects")} for t in projects_result.data or [] if t.get("projects")])

        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/trending")
async def get_trending_content(
    content_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    try:
        trending = {
            "courses": [],
            "projects": [],
            "proposals": []
        }

        if not content_type or content_type == "courses":
            courses_result = supabase.table("courses").select("*").order("views", desc=True).limit(10).execute()
            trending["courses"] = courses_result.data or []

        if not content_type or content_type == "projects":
            projects_result = supabase.table("projects").select("*").order("likes", desc=True).limit(10).execute()
            trending["projects"] = projects_result.data or []

        if not content_type or content_type == "proposals":
            proposals_result = supabase.table("proposals").select("*").order("votes_for", desc=True).limit(10).execute()
            trending["proposals"] = proposals_result.data or []

        return {"trending": trending}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/recommendations")
async def get_recommendations(current_user: dict = Depends(get_current_user)):
    try:
        user_result = supabase.table("users").select("skills, role").eq("id", current_user["id"]).execute()

        if not user_result.data:
            return {"recommendations": []}

        user_skills = user_result.data[0].get("skills", [])

        recommended_courses = []
        if user_skills:
            for skill in user_skills[:3]:
                courses_result = supabase.table("courses").select("*").contains("skills_taught", [skill]).limit(5).execute()
                if courses_result.data:
                    recommended_courses.extend(courses_result.data)

        recommended_jobs = []
        if user_skills:
            for skill in user_skills[:3]:
                jobs_result = supabase.table("jobs").select("*").contains("required_skills", [skill]).limit(5).execute()
                if jobs_result.data:
                    recommended_jobs.extend(jobs_result.data)

        return {
            "recommendations": {
                "courses": recommended_courses[:10],
                "jobs": recommended_jobs[:10]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/save-search")
async def save_search(
    search_query: SearchQuery,
    current_user: dict = Depends(get_current_user)
):
    try:
        data = {
            "user_id": current_user["id"],
            "query": search_query.query,
            "filters": search_query.filters,
            "sort_by": search_query.sort_by
        }

        result = supabase.table("saved_searches").insert(data).execute()

        return {"message": "Search saved", "saved_search": result.data[0]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/saved-searches")
async def get_saved_searches(current_user: dict = Depends(get_current_user)):
    try:
        result = supabase.table("saved_searches").select("*").eq("user_id", current_user["id"]).execute()
        return {"saved_searches": result.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2),
    type: Optional[str] = "all"
):
    try:
        suggestions = []

        if type in ["all", "users"]:
            users = supabase.table("users").select("username").ilike("username", f"{q}%").limit(5).execute()
            suggestions.extend([{"type": "user", "value": u["username"]} for u in users.data or []])

        if type in ["all", "courses"]:
            courses = supabase.table("courses").select("title").ilike("title", f"{q}%").limit(5).execute()
            suggestions.extend([{"type": "course", "value": c["title"]} for c in courses.data or []])

        return {"suggestions": suggestions[:10]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
