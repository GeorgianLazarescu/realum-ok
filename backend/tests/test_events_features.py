"""
Test suite for REALUM Events Features - Day/Night Cycle, NPCs, Objectives, Calendar
Tests: World Time, NPCs, Objectives, Seasonal Events Calendar
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestWorldTime:
    """Day/Night cycle endpoint tests"""
    
    def test_world_time_returns_period(self):
        """GET /api/events/world/time should return period and is_day flag"""
        response = requests.get(f"{BASE_URL}/api/events/world/time")
        assert response.status_code == 200
        
        data = response.json()
        # Verify required fields
        assert "period" in data
        assert data["period"] in ["morning", "afternoon", "evening", "night"]
        assert "is_day" in data
        assert isinstance(data["is_day"], bool)
        assert "virtual_hour" in data
        assert "description" in data
        assert "sun_position" in data
        
    def test_world_time_period_matches_is_day(self):
        """Verify period and is_day flag are consistent"""
        response = requests.get(f"{BASE_URL}/api/events/world/time")
        data = response.json()
        
        # is_day should be True for morning/afternoon, False for evening/night
        if data["period"] in ["morning", "afternoon"]:
            assert data["is_day"] == True
        else:
            assert data["is_day"] == False


class TestNPCs:
    """NPC endpoints tests"""
    
    def test_get_npcs_list(self):
        """GET /api/events/npcs should return list of NPCs"""
        response = requests.get(f"{BASE_URL}/api/events/npcs")
        assert response.status_code == 200
        
        data = response.json()
        assert "npcs" in data
        assert isinstance(data["npcs"], list)
        assert len(data["npcs"]) >= 1
        
    def test_npc_has_required_fields(self):
        """Each NPC should have required fields"""
        response = requests.get(f"{BASE_URL}/api/events/npcs")
        data = response.json()
        
        for npc in data["npcs"]:
            assert "id" in npc
            assert "name" in npc
            assert "role" in npc
            assert "location" in npc
            assert "activity" in npc
            assert "available" in npc
            assert isinstance(npc["available"], bool)
            assert "avatar" in npc
            
    def test_npc_locations_are_valid_zones(self):
        """NPC locations should be valid REALUM zones"""
        valid_zones = ["Learning Zone", "Marketplace", "Social Plaza", "Wellness Center", "Treasury", "Jobs Hub", "DAO Hall"]
        
        response = requests.get(f"{BASE_URL}/api/events/npcs")
        data = response.json()
        
        for npc in data["npcs"]:
            assert npc["location"] in valid_zones, f"Invalid location: {npc['location']}"


class TestObjectives:
    """Objectives endpoint tests (requires authentication)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "lazarescugeorgian@yahoo.com",
            "password": "Lazarescu4."
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
        
    def test_get_objectives_requires_auth(self):
        """GET /api/events/objectives should require authentication"""
        response = requests.get(f"{BASE_URL}/api/events/objectives")
        assert response.status_code == 401
        
    def test_get_objectives_with_auth(self, auth_token):
        """GET /api/events/objectives should return objectives with auth"""
        response = requests.get(
            f"{BASE_URL}/api/events/objectives",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "objectives" in data
        assert isinstance(data["objectives"], list)
        
    def test_objectives_have_rlm_rewards(self, auth_token):
        """Each objective should have RLM reward"""
        response = requests.get(
            f"{BASE_URL}/api/events/objectives",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        for obj in data["objectives"]:
            assert "id" in obj
            assert "title" in obj
            assert "description" in obj
            assert "reward_rlm" in obj
            assert isinstance(obj["reward_rlm"], (int, float))
            assert obj["reward_rlm"] > 0
            assert "completed" in obj
            assert isinstance(obj["completed"], bool)


class TestSeasonalCalendar:
    """Seasonal Events Calendar tests"""
    
    def test_get_calendar(self):
        """GET /api/events/calendar should return calendar data"""
        response = requests.get(f"{BASE_URL}/api/events/calendar")
        assert response.status_code == 200
        
        data = response.json()
        assert "current_month" in data
        assert "month_events" in data
        assert "active_events" in data
        assert "upcoming_events" in data
        assert "total_events_this_year" in data
        
    def test_calendar_has_events(self):
        """Calendar should have events throughout the year"""
        response = requests.get(f"{BASE_URL}/api/events/calendar")
        data = response.json()
        
        assert data["total_events_this_year"] >= 20, "Should have at least 20 events per year"
        
    def test_get_active_events(self):
        """GET /api/events/calendar/active should return active events"""
        response = requests.get(f"{BASE_URL}/api/events/calendar/active")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_events" in data
        assert isinstance(data["active_events"], list)
        
    def test_upcoming_events_have_required_fields(self):
        """Upcoming events should have required fields"""
        response = requests.get(f"{BASE_URL}/api/events/calendar")
        data = response.json()
        
        for event in data["upcoming_events"]:
            assert "name" in event
            assert "type" in event
            assert "description" in event
            assert "start_date" in event
            assert "end_date" in event
            assert "bonus_rlm" in event or "bonus_xp" in event
            assert "days_until" in event


class TestMiniTasks:
    """Mini-Tasks endpoint tests (requires authentication)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "lazarescugeorgian@yahoo.com",
            "password": "Lazarescu4."
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
        
    def test_get_tasks_with_auth(self, auth_token):
        """GET /api/events/tasks should return tasks with auth"""
        response = requests.get(
            f"{BASE_URL}/api/events/tasks",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)
        
    def test_tasks_have_required_fields(self, auth_token):
        """Each task should have required fields"""
        response = requests.get(
            f"{BASE_URL}/api/events/tasks",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        data = response.json()
        
        for task in data["tasks"]:
            assert "id" in task
            assert "name" in task
            assert "description" in task
            assert "reward_rlm" in task
            assert "time_limit_mins" in task
            assert "status" in task


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
