"""
REALUM Platform Comprehensive API Tests
Tests for: Auth, Jobs, Voting/DAO, Wallet, City Zones, Leaderboard, Badges,
           Courses, Marketplace, Projects, Simulation, Token Economy
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = {
    "email": f"test_{uuid.uuid4().hex[:8]}@realum.io",
    "password": "Test123456!",
    "username": f"TestUser_{uuid.uuid4().hex[:8]}"
}

TEST_USER_2 = {
    "email": f"test2_{uuid.uuid4().hex[:8]}@realum.io",
    "password": "Test123456!",
    "username": f"TestUser2_{uuid.uuid4().hex[:8]}"
}

CREATOR_USER = {
    "email": f"creator_{uuid.uuid4().hex[:8]}@realum.io",
    "password": "Creator123!",
    "username": f"Creator_{uuid.uuid4().hex[:8]}",
    "role": "creator"
}


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def seeded_db(api_client):
    """Ensure database is seeded"""
    response = api_client.post(f"{BASE_URL}/api/seed")
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="module")
def registered_user(api_client, seeded_db):
    """Register test user"""
    response = api_client.post(f"{BASE_URL}/api/auth/register", json=TEST_USER)
    if response.status_code == 400 and "already" in response.text.lower():
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        })
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="module")
def registered_user_2(api_client, seeded_db):
    """Register test user 2"""
    response = api_client.post(f"{BASE_URL}/api/auth/register", json=TEST_USER_2)
    if response.status_code == 400 and "already" in response.text.lower():
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_2["email"],
            "password": TEST_USER_2["password"]
        })
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="module")
def creator_user(api_client, seeded_db):
    """Register creator user"""
    response = api_client.post(f"{BASE_URL}/api/auth/register", json=CREATOR_USER)
    if response.status_code == 400 and "already" in response.text.lower():
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": CREATOR_USER["email"],
            "password": CREATOR_USER["password"]
        })
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="module")
def auth_headers(registered_user):
    """Auth headers for user"""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest.fixture(scope="module")
def auth_headers_2(registered_user_2):
    """Auth headers for user 2"""
    return {"Authorization": f"Bearer {registered_user_2['access_token']}"}


@pytest.fixture(scope="module")
def creator_headers(creator_user):
    """Auth headers for creator"""
    return {"Authorization": f"Bearer {creator_user['access_token']}"}


# ==================== SEED TESTS ====================
class TestSeedEndpoint:
    """Test seed data endpoint"""
    
    def test_seed_creates_data(self, api_client):
        response = api_client.post(f"{BASE_URL}/api/seed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "seeded"
        assert data["jobs"] >= 20  # At least 20 jobs
        assert data["zones"] >= 8  # At least 8 zones
        assert data["proposals"] >= 5  # At least 5 proposals
        assert data["courses"] >= 5  # At least 5 courses
        assert data["marketplace_items"] >= 4  # At least 4 items


# ==================== AUTH TESTS ====================
class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_register_new_user(self, api_client, seeded_db):
        """Test user registration with role selection"""
        unique_user = {
            "email": f"newuser_{uuid.uuid4().hex[:8]}@realum.io",
            "password": "SecurePass123!",
            "username": f"NewUser_{uuid.uuid4().hex[:8]}",
            "role": "contributor"
        }
        response = api_client.post(f"{BASE_URL}/api/auth/register", json=unique_user)
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == unique_user["email"]
        assert data["user"]["username"] == unique_user["username"]
        assert data["user"]["role"] == "contributor"
        assert data["user"]["realum_balance"] == 1000.0
        assert data["user"]["xp"] == 0
        assert data["user"]["level"] == 1
        assert "newcomer" in data["user"]["badges"]
    
    def test_register_all_roles(self, api_client, seeded_db):
        """Test registration with all role types"""
        roles = ["citizen", "creator", "contributor", "evaluator", "partner"]
        for role in roles:
            user = {
                "email": f"{role}_{uuid.uuid4().hex[:8]}@realum.io",
                "password": "Test123!",
                "username": f"{role.capitalize()}_{uuid.uuid4().hex[:8]}",
                "role": role
            }
            response = api_client.post(f"{BASE_URL}/api/auth/register", json=user)
            assert response.status_code == 200
            assert response.json()["user"]["role"] == role
    
    def test_login_success(self, api_client, registered_user):
        """Test successful login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with wrong password"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
    
    def test_get_current_user(self, api_client, auth_headers, registered_user):
        """Test get current user endpoint"""
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "realum_balance" in data
        assert "xp" in data
        assert "level" in data
        assert "badges" in data
        assert "skills" in data
        assert "courses_completed" in data


# ==================== CITY ZONES TESTS ====================
class TestCityZonesEndpoints:
    """City zones endpoint tests"""
    
    def test_get_all_zones(self, api_client, seeded_db):
        """Test getting all city zones"""
        response = api_client.get(f"{BASE_URL}/api/city/zones")
        assert response.status_code == 200
        zones = response.json()
        
        assert len(zones) >= 8
        
        # Validate zone structure
        for zone in zones:
            assert "id" in zone
            assert "name" in zone
            assert "description" in zone
            assert "type" in zone
            assert "jobs_count" in zone
            assert "buildings" in zone
            assert "color" in zone
            assert "features" in zone
            assert isinstance(zone["buildings"], list)


# ==================== JOBS TESTS ====================
class TestJobsEndpoints:
    """Jobs endpoint tests"""
    
    def test_get_available_jobs(self, api_client, auth_headers, seeded_db):
        """Test getting available jobs"""
        response = api_client.get(f"{BASE_URL}/api/jobs", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json()
        
        assert len(jobs) > 0
        
        for job in jobs:
            assert "id" in job
            assert "title" in job
            assert "description" in job
            assert "company" in job
            assert "zone" in job
            assert "reward" in job
            assert "xp_reward" in job
            assert "duration_minutes" in job
    
    def test_filter_jobs_by_zone(self, api_client, auth_headers, seeded_db):
        """Test filtering jobs by zone"""
        response = api_client.get(f"{BASE_URL}/api/jobs?zone=tech-district", headers=auth_headers)
        assert response.status_code == 200
        jobs = response.json()
        for job in jobs:
            assert job["zone"] == "tech-district"
    
    def test_apply_for_job(self, api_client, auth_headers, seeded_db):
        """Test applying for a job"""
        jobs_response = api_client.get(f"{BASE_URL}/api/jobs", headers=auth_headers)
        jobs = jobs_response.json()
        
        level_1_job = next((j for j in jobs if j.get("required_level", 1) == 1), None)
        if level_1_job:
            response = api_client.post(f"{BASE_URL}/api/jobs/{level_1_job['id']}/apply", 
                                       headers=auth_headers)
            assert response.status_code in [200, 400]  # 400 if already applied
    
    def test_get_active_jobs(self, api_client, auth_headers):
        """Test getting active jobs"""
        response = api_client.get(f"{BASE_URL}/api/jobs/active", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "active_jobs" in data


# ==================== COURSES TESTS ====================
class TestCoursesEndpoints:
    """Learning Zone / Courses endpoint tests"""
    
    def test_get_all_courses(self, api_client, seeded_db):
        """Test getting all courses"""
        response = api_client.get(f"{BASE_URL}/api/courses")
        assert response.status_code == 200
        data = response.json()
        
        assert "courses" in data
        courses = data["courses"]
        assert len(courses) >= 5
        
        for course in courses:
            assert "id" in course
            assert "title" in course
            assert "description" in course
            assert "category" in course
            assert "difficulty" in course
            assert "duration_hours" in course
            assert "xp_reward" in course
            assert "rlm_reward" in course
            assert "skills_gained" in course
            assert "lessons" in course
    
    def test_filter_courses_by_category(self, api_client, seeded_db):
        """Test filtering courses by category"""
        response = api_client.get(f"{BASE_URL}/api/courses?category=tech")
        assert response.status_code == 200
        data = response.json()
        for course in data["courses"]:
            assert course["category"] == "tech"
    
    def test_enroll_in_course(self, api_client, auth_headers, seeded_db):
        """Test enrolling in a course"""
        courses_response = api_client.get(f"{BASE_URL}/api/courses")
        courses = courses_response.json()["courses"]
        
        if courses:
            course_id = courses[0]["id"]
            response = api_client.post(f"{BASE_URL}/api/courses/{course_id}/enroll",
                                       headers=auth_headers)
            assert response.status_code in [200, 400]  # 400 if already enrolled
    
    def test_get_course_details(self, api_client, auth_headers, seeded_db):
        """Test getting course details"""
        courses_response = api_client.get(f"{BASE_URL}/api/courses")
        courses = courses_response.json()["courses"]
        
        if courses:
            course_id = courses[0]["id"]
            response = api_client.get(f"{BASE_URL}/api/courses/{course_id}",
                                      headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "course" in data


# ==================== MARKETPLACE TESTS ====================
class TestMarketplaceEndpoints:
    """Marketplace endpoint tests"""
    
    def test_get_marketplace_items(self, api_client, seeded_db):
        """Test getting marketplace items"""
        response = api_client.get(f"{BASE_URL}/api/marketplace")
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        items = data["items"]
        assert len(items) >= 4
        
        for item in items:
            assert "id" in item
            assert "title" in item
            assert "description" in item
            assert "category" in item
            assert "price_rlm" in item
            assert "seller_id" in item
            assert "seller_name" in item
            assert "downloads" in item
            assert "rating" in item
    
    def test_filter_marketplace_by_category(self, api_client, seeded_db):
        """Test filtering marketplace by category"""
        response = api_client.get(f"{BASE_URL}/api/marketplace?category=design")
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["category"] == "design"
    
    def test_purchase_item(self, api_client, auth_headers, seeded_db):
        """Test purchasing marketplace item with 2% token burn"""
        items_response = api_client.get(f"{BASE_URL}/api/marketplace")
        items = items_response.json()["items"]
        
        # Find an item not owned by test user
        purchasable = next((i for i in items if i["seller_id"] != "test"), None)
        if purchasable:
            response = api_client.post(f"{BASE_URL}/api/marketplace/{purchasable['id']}/purchase",
                                       headers=auth_headers)
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "purchased"
                assert "amount_paid" in data
                assert "amount_burned" in data
                # Verify 2% burn
                expected_burn = purchasable["price_rlm"] * 0.02
                assert abs(data["amount_burned"] - expected_burn) < 0.01
    
    def test_creator_can_list_item(self, api_client, creator_headers, seeded_db):
        """Test that creators can list items"""
        new_item = {
            "title": f"Test Item {uuid.uuid4().hex[:8]}",
            "description": "A test marketplace item",
            "category": "design",
            "price_rlm": 50.0
        }
        response = api_client.post(f"{BASE_URL}/api/marketplace",
                                   json=new_item,
                                   headers=creator_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert "item" in data


# ==================== PROJECTS TESTS ====================
class TestProjectsEndpoints:
    """Projects endpoint tests"""
    
    def test_get_projects(self, api_client, seeded_db):
        """Test getting all projects"""
        response = api_client.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        data = response.json()
        
        assert "projects" in data
        projects = data["projects"]
        assert len(projects) >= 3
        
        for project in projects:
            assert "id" in project
            assert "title" in project
            assert "description" in project
            assert "creator_id" in project
            assert "category" in project
            assert "status" in project
            assert "budget_rlm" in project
            assert "participants" in project
            assert "tasks" in project
            assert "progress" in project
    
    def test_get_project_details(self, api_client, seeded_db):
        """Test getting project details"""
        projects_response = api_client.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()["projects"]
        
        if projects:
            project_id = projects[0]["id"]
            response = api_client.get(f"{BASE_URL}/api/projects/{project_id}")
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "title" in data
    
    def test_join_project(self, api_client, auth_headers, seeded_db):
        """Test joining a project"""
        projects_response = api_client.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json()["projects"]
        
        if projects:
            project_id = projects[0]["id"]
            response = api_client.post(f"{BASE_URL}/api/projects/{project_id}/join",
                                       headers=auth_headers)
            assert response.status_code in [200, 400]  # 400 if already joined


# ==================== DAO/VOTING TESTS ====================
class TestProposalsEndpoints:
    """DAO/Voting endpoint tests"""
    
    def test_get_proposals(self, api_client, seeded_db):
        """Test getting all proposals"""
        response = api_client.get(f"{BASE_URL}/api/proposals")
        assert response.status_code == 200
        proposals = response.json()
        
        assert len(proposals) >= 5
        
        for proposal in proposals:
            assert "id" in proposal
            assert "title" in proposal
            assert "description" in proposal
            assert "proposer_id" in proposal
            assert "proposer_name" in proposal
            assert "votes_for" in proposal
            assert "votes_against" in proposal
            assert "status" in proposal
            assert "created_at" in proposal
            assert "ends_at" in proposal
    
    def test_vote_on_proposal(self, api_client, auth_headers, seeded_db):
        """Test voting on a proposal"""
        proposals_response = api_client.get(f"{BASE_URL}/api/proposals")
        proposals = proposals_response.json()
        
        active_proposal = next((p for p in proposals if p["status"] == "active"), None)
        if active_proposal:
            response = api_client.post(f"{BASE_URL}/api/proposals/{active_proposal['id']}/vote",
                                       json={"vote_type": "for"},
                                       headers=auth_headers)
            assert response.status_code in [200, 400]  # 400 if already voted


# ==================== WALLET TESTS ====================
class TestWalletEndpoints:
    """Wallet endpoint tests"""
    
    def test_get_wallet(self, api_client, auth_headers):
        """Test getting wallet"""
        response = api_client.get(f"{BASE_URL}/api/wallet", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "balance" in data
        assert "transactions" in data
    
    def test_get_transactions(self, api_client, auth_headers):
        """Test getting transaction history"""
        response = api_client.get(f"{BASE_URL}/api/wallet/transactions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
    
    def test_transfer_tokens_with_burn(self, api_client, auth_headers, registered_user_2):
        """Test transferring tokens with 2% burn"""
        recipient_id = registered_user_2["user"]["id"]
        amount = 100
        
        response = api_client.post(f"{BASE_URL}/api/wallet/transfer",
                                   json={"to_user_id": recipient_id, "amount": amount},
                                   headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "amount_sent" in data
            assert "amount_received" in data
            assert "amount_burned" in data
            # Verify 2% burn
            expected_burn = amount * 0.02
            assert abs(data["amount_burned"] - expected_burn) < 0.01
    
    def test_connect_wallet(self, api_client, auth_headers):
        """Test connecting Web3 wallet"""
        wallet_address = "0x" + "a" * 40
        response = api_client.post(f"{BASE_URL}/api/wallet/connect",
                                   json={"wallet_address": wallet_address},
                                   headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"


# ==================== TOKEN ECONOMY TESTS ====================
class TestTokenEconomyEndpoints:
    """Token economy endpoint tests"""
    
    def test_get_token_stats(self, api_client, seeded_db):
        """Test getting token statistics"""
        response = api_client.get(f"{BASE_URL}/api/token/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_supply" in data
        assert "total_burned" in data
        assert "burn_rate" in data
        assert data["burn_rate"] == 2.0  # 2% burn rate
    
    def test_get_burn_history(self, api_client, seeded_db):
        """Test getting token burn history"""
        response = api_client.get(f"{BASE_URL}/api/token/burns")
        assert response.status_code == 200
        data = response.json()
        assert "burns" in data


# ==================== LEADERBOARD TESTS ====================
class TestLeaderboardEndpoints:
    """Leaderboard endpoint tests"""
    
    def test_get_leaderboard(self, api_client, seeded_db):
        """Test getting leaderboard"""
        response = api_client.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "leaderboard" in data
        leaderboard = data["leaderboard"]
        
        if len(leaderboard) > 0:
            entry = leaderboard[0]
            assert "rank" in entry
            assert "id" in entry
            assert "username" in entry
            assert "level" in entry
            assert "xp" in entry
            assert "realum_balance" in entry
            assert "badges_count" in entry


# ==================== BADGES TESTS ====================
class TestBadgesEndpoints:
    """Badges endpoint tests"""
    
    def test_get_all_badges(self, api_client):
        """Test getting all available badges"""
        response = api_client.get(f"{BASE_URL}/api/badges")
        assert response.status_code == 200
        data = response.json()
        
        assert "badges" in data
        badges = data["badges"]
        assert len(badges) >= 20
        
        for badge in badges:
            assert "id" in badge
            assert "name" in badge
            assert "description" in badge
            assert "icon" in badge
            assert "rarity" in badge


# ==================== SIMULATION TESTS ====================
class TestSimulationEndpoints:
    """Simulation endpoint tests (Andreea, Vlad, Sorin)"""
    
    def test_setup_simulation(self, api_client):
        """Test setting up simulation users"""
        response = api_client.post(f"{BASE_URL}/api/simulation/setup")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "simulation_ready"
        assert "users" in data
        users = data["users"]
        
        usernames = [u["username"] for u in users]
        assert "Andreea" in usernames
        assert "Vlad" in usernames
        assert "Sorin" in usernames
        
        # Verify roles
        andreea = next(u for u in users if u["username"] == "Andreea")
        vlad = next(u for u in users if u["username"] == "Vlad")
        sorin = next(u for u in users if u["username"] == "Sorin")
        
        assert andreea["role"] == "Creator"
        assert vlad["role"] == "Contributor"
        assert sorin["role"] == "Evaluator"
    
    def test_simulation_step1_purchase(self, api_client):
        """Test simulation step 1: Vlad purchases Andreea's design"""
        # Login as Vlad
        login_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "vlad@realum.io",
            "password": "Vlad123!"
        })
        if login_response.status_code != 200:
            pytest.skip("Vlad user not found - run simulation setup first")
        
        vlad_token = login_response.json()["access_token"]
        vlad_headers = {"Authorization": f"Bearer {vlad_token}"}
        
        # Find Andreea's item
        items_response = api_client.get(f"{BASE_URL}/api/marketplace")
        items = items_response.json()["items"]
        andreea_item = next((i for i in items if i["seller_name"] == "Andreea"), None)
        
        if andreea_item:
            response = api_client.post(f"{BASE_URL}/api/marketplace/{andreea_item['id']}/purchase",
                                       headers=vlad_headers)
            # Could be 200 (success) or 400 (insufficient balance or already purchased)
            assert response.status_code in [200, 400]


# ==================== PLATFORM STATS TESTS ====================
class TestPlatformStatsEndpoints:
    """Platform statistics endpoint tests"""
    
    def test_get_platform_stats(self, api_client, seeded_db):
        """Test getting platform statistics"""
        response = api_client.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_users" in data
        assert "active_proposals" in data
        assert "jobs_completed" in data
        assert "courses_available" in data
        assert "active_projects" in data
        assert "marketplace_items" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
