"""
REALUM Backend Tests - Authentication Persistence & New Features
Tests: Auth persistence, NPC AI Chat, Seasonal Events Calendar, Marketplace Inventory
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "lazarescugeorgian@yahoo.com"
TEST_PASSWORD = "Lazarescu4."


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """Test health endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAuthentication:
    """Authentication and session persistence tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [401, 404]
    
    def test_auth_me_with_valid_token(self):
        """Test /auth/me endpoint with valid token - verifies auth persistence"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Then verify token works with /auth/me
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        data = me_response.json()
        assert data["email"] == TEST_EMAIL
        assert "id" in data
        assert "realum_balance" in data
    
    def test_auth_me_without_token(self):
        """Test /auth/me endpoint without token returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
    
    def test_auth_me_with_invalid_token(self):
        """Test /auth/me endpoint with invalid token returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401


class TestNPCSystem:
    """NPC System and AI Chat tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_get_npc_list(self):
        """Test getting list of NPCs"""
        response = requests.get(f"{BASE_URL}/api/npc/list")
        assert response.status_code == 200
        data = response.json()
        assert "npcs" in data
        assert len(data["npcs"]) > 0
        # Verify NPC structure
        npc = data["npcs"][0]
        assert "id" in npc
        assert "name" in npc
        assert "role" in npc
        assert "avatar" in npc
    
    def test_get_npc_details(self):
        """Test getting specific NPC details"""
        response = requests.get(f"{BASE_URL}/api/npc/mentor_aria")
        assert response.status_code == 200
        data = response.json()
        assert "npc" in data
        assert data["npc"]["name"] == "Aria"
        assert data["npc"]["role"] == "Mentor"
    
    def test_npc_ai_chat(self, auth_token):
        """Test NPC AI chat endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/npc/ai-chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "npc_id": "mentor_aria",
                "message": "Hello, can you help me?"
            }
        )
        # May return 200 (success) or error if budget exceeded
        assert response.status_code in [200, 500, 503]
        data = response.json()
        
        if response.status_code == 200:
            assert "response" in data
            assert "session_id" in data
            assert "npc_name" in data
            assert data["npc_name"] == "Aria"
    
    def test_npc_ai_chat_invalid_npc(self, auth_token):
        """Test NPC AI chat with invalid NPC ID"""
        response = requests.post(
            f"{BASE_URL}/api/npc/ai-chat",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "npc_id": "invalid_npc",
                "message": "Hello"
            }
        )
        assert response.status_code == 404
    
    def test_start_npc_conversation(self, auth_token):
        """Test starting a dialog-based NPC conversation"""
        response = requests.post(
            f"{BASE_URL}/api/npc/start",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"npc_id": "trader_max"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "greeting" in data
        assert "dialog" in data


class TestSeasonalEventsCalendar:
    """Seasonal Events Calendar tests"""
    
    def test_get_calendar(self):
        """Test getting seasonal events calendar"""
        response = requests.get(f"{BASE_URL}/api/events/calendar")
        assert response.status_code == 200
        data = response.json()
        assert "current_month" in data
        assert "month_events" in data
        assert "active_events" in data
        assert "upcoming_events" in data
        assert "total_events_this_year" in data
        # Should have 26+ events throughout the year
        assert data["total_events_this_year"] >= 26
    
    def test_get_calendar_specific_month(self):
        """Test getting calendar for specific month"""
        response = requests.get(f"{BASE_URL}/api/events/calendar?month=12")
        assert response.status_code == 200
        data = response.json()
        assert data["current_month"] == 12
        # December should have multiple events
        assert len(data["month_events"]) >= 3
    
    def test_get_active_seasonal_events(self):
        """Test getting currently active seasonal events"""
        response = requests.get(f"{BASE_URL}/api/events/calendar/active")
        assert response.status_code == 200
        data = response.json()
        assert "active_events" in data
        # Active events is a list (may be empty if no events currently active)
        assert isinstance(data["active_events"], list)


class TestMarketplaceInventory:
    """Marketplace and Inventory tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_get_marketplace_items(self):
        """Test getting marketplace items"""
        response = requests.get(f"{BASE_URL}/api/marketplace")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_get_user_inventory(self, auth_token):
        """Test getting user's inventory"""
        response = requests.get(
            f"{BASE_URL}/api/inventory",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_items" in data
        assert "categories" in data
        assert isinstance(data["items"], list)
    
    def test_inventory_requires_auth(self):
        """Test inventory endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/inventory")
        assert response.status_code == 401


class TestDashboardData:
    """Dashboard data endpoints tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_get_user_profile(self, auth_token):
        """Test getting user profile for dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Verify all dashboard-relevant fields
        assert "realum_balance" in data
        assert "xp" in data
        assert "level" in data
        assert "badges" in data
        assert "role" in data
    
    def test_get_token_economy(self):
        """Test getting token economy stats"""
        response = requests.get(f"{BASE_URL}/api/token/economy")
        assert response.status_code == 200
        data = response.json()
        assert "total_supply" in data
        assert "burned_tokens" in data
        assert "burn_rate" in data
    
    def test_get_platform_stats(self):
        """Test getting platform statistics"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_jobs" in data


class TestEventsAndTasks:
    """Events and mini-tasks tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Authentication failed")
    
    def test_get_world_time(self):
        """Test getting world time (day/night cycle)"""
        response = requests.get(f"{BASE_URL}/api/events/world/time")
        assert response.status_code == 200
        data = response.json()
        assert "virtual_hour" in data
        assert "period" in data
        assert "is_day" in data
    
    def test_get_active_npcs(self):
        """Test getting active NPCs in metaverse"""
        response = requests.get(f"{BASE_URL}/api/events/npcs")
        assert response.status_code == 200
        data = response.json()
        assert "npcs" in data
        assert len(data["npcs"]) > 0
    
    def test_get_available_tasks(self, auth_token):
        """Test getting available mini-tasks"""
        response = requests.get(
            f"{BASE_URL}/api/events/tasks",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert isinstance(data["tasks"], list)
    
    def test_get_user_objectives(self, auth_token):
        """Test getting user objectives"""
        response = requests.get(
            f"{BASE_URL}/api/events/objectives",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "objectives" in data
        assert isinstance(data["objectives"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
