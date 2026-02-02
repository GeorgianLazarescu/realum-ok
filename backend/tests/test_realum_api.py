"""
REALUM Platform API Tests
Tests for: Auth, Jobs, Voting/DAO, Wallet, City Zones, Leaderboard, Badges
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_1 = {
    "email": f"test1_{uuid.uuid4().hex[:8]}@realum.io",
    "password": "Test123456!",
    "username": f"TestUser1_{uuid.uuid4().hex[:8]}"
}

TEST_USER_2 = {
    "email": f"test2_{uuid.uuid4().hex[:8]}@realum.io",
    "password": "Test123456!",
    "username": f"TestUser2_{uuid.uuid4().hex[:8]}"
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
def registered_user_1(api_client, seeded_db):
    """Register test user 1"""
    response = api_client.post(f"{BASE_URL}/api/auth/register", json=TEST_USER_1)
    if response.status_code == 400 and "already" in response.text.lower():
        # User exists, try login
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_1["email"],
            "password": TEST_USER_1["password"]
        })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user" in data
    return data


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
    data = response.json()
    assert "access_token" in data
    return data


@pytest.fixture(scope="module")
def auth_headers_1(registered_user_1):
    """Auth headers for user 1"""
    return {"Authorization": f"Bearer {registered_user_1['access_token']}"}


@pytest.fixture(scope="module")
def auth_headers_2(registered_user_2):
    """Auth headers for user 2"""
    return {"Authorization": f"Bearer {registered_user_2['access_token']}"}


class TestSeedEndpoint:
    """Test seed data endpoint"""
    
    def test_seed_creates_data(self, api_client):
        response = api_client.post(f"{BASE_URL}/api/seed")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "seeded"
        assert data["jobs"] == 30
        assert data["zones"] == 8
        assert data["proposals"] == 7


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_register_new_user(self, api_client, seeded_db):
        """Test user registration"""
        unique_user = {
            "email": f"newuser_{uuid.uuid4().hex[:8]}@realum.io",
            "password": "SecurePass123!",
            "username": f"NewUser_{uuid.uuid4().hex[:8]}"
        }
        response = api_client.post(f"{BASE_URL}/api/auth/register", json=unique_user)
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == unique_user["email"]
        assert data["user"]["username"] == unique_user["username"]
        assert data["user"]["role"] == "citizen"
        assert data["user"]["realum_balance"] == 1000.0
        assert data["user"]["xp"] == 0
        assert data["user"]["level"] == 1
        assert "newcomer" in data["user"]["badges"]
    
    def test_register_duplicate_email(self, api_client, registered_user_1):
        """Test duplicate email registration fails"""
        response = api_client.post(f"{BASE_URL}/api/auth/register", json=TEST_USER_1)
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()
    
    def test_login_success(self, api_client, registered_user_1):
        """Test successful login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_USER_1["email"],
            "password": TEST_USER_1["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_USER_1["email"]
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with wrong password"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    def test_get_current_user(self, api_client, auth_headers_1, registered_user_1):
        """Test get current user endpoint"""
        response = api_client.get(f"{BASE_URL}/api/auth/me", headers=auth_headers_1)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_USER_1["email"]
        assert data["username"] == TEST_USER_1["username"]
        assert "realum_balance" in data
        assert "xp" in data
        assert "level" in data
        assert "badges" in data
    
    def test_get_user_without_auth(self, api_client):
        """Test accessing protected endpoint without auth"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401


class TestCityZonesEndpoints:
    """City zones endpoint tests"""
    
    def test_get_all_zones(self, api_client, seeded_db):
        """Test getting all city zones"""
        response = api_client.get(f"{BASE_URL}/api/city/zones")
        assert response.status_code == 200
        zones = response.json()
        
        assert len(zones) >= 8  # May have more due to multiple seeds
        zone_ids = [z["id"] for z in zones]
        expected_zones = ["downtown", "tech-district", "industrial", "residential", 
                         "education", "marketplace", "cultural", "civic"]
        for expected in expected_zones:
            assert expected in zone_ids
        
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
            assert len(zone["buildings"]) > 0


class TestJobsEndpoints:
    """Jobs endpoint tests"""
    
    def test_get_available_jobs(self, api_client, auth_headers_1, seeded_db):
        """Test getting available jobs"""
        response = api_client.get(f"{BASE_URL}/api/jobs", headers=auth_headers_1)
        assert response.status_code == 200
        jobs = response.json()
        
        # Should have jobs available for level 1 user
        assert len(jobs) > 0
        
        # Validate job structure
        for job in jobs:
            assert "id" in job
            assert "title" in job
            assert "description" in job
            assert "company" in job
            assert "zone" in job
            assert "reward" in job
            assert "xp_reward" in job
            assert "duration_minutes" in job
            assert "required_level" in job
    
    def test_apply_for_job(self, api_client, auth_headers_1, seeded_db):
        """Test applying for a job"""
        # Get available jobs first
        jobs_response = api_client.get(f"{BASE_URL}/api/jobs", headers=auth_headers_1)
        jobs = jobs_response.json()
        
        # Find a level 1 job
        level_1_job = next((j for j in jobs if j["required_level"] == 1), None)
        assert level_1_job is not None
        
        response = api_client.post(f"{BASE_URL}/api/jobs/apply", 
                                   json={"job_id": level_1_job["id"]},
                                   headers=auth_headers_1)
        # Could be 200 (success) or 400 (already applied)
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "applied"
            assert "job" in data
    
    def test_get_active_jobs(self, api_client, auth_headers_1):
        """Test getting active jobs"""
        response = api_client.get(f"{BASE_URL}/api/jobs/active", headers=auth_headers_1)
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
    
    def test_complete_job(self, api_client, auth_headers_1, seeded_db):
        """Test completing a job"""
        # First apply for a job
        jobs_response = api_client.get(f"{BASE_URL}/api/jobs", headers=auth_headers_1)
        jobs = jobs_response.json()
        level_1_job = next((j for j in jobs if j["required_level"] == 1), None)
        
        if level_1_job:
            # Apply
            api_client.post(f"{BASE_URL}/api/jobs/apply", 
                           json={"job_id": level_1_job["id"]},
                           headers=auth_headers_1)
            
            # Complete
            response = api_client.post(f"{BASE_URL}/api/jobs/complete",
                                       json={"job_id": level_1_job["id"]},
                                       headers=auth_headers_1)
            # Could be 200 (success) or 400 (not working on this job)
            assert response.status_code in [200, 400]
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "completed"
                assert "reward" in data
                assert "xp_gained" in data
                assert "new_balance" in data
                assert "new_xp" in data
    
    def test_apply_job_not_found(self, api_client, auth_headers_1):
        """Test applying for non-existent job"""
        response = api_client.post(f"{BASE_URL}/api/jobs/apply",
                                   json={"job_id": "non-existent-job"},
                                   headers=auth_headers_1)
        assert response.status_code == 404


class TestProposalsEndpoints:
    """DAO/Voting endpoint tests"""
    
    def test_get_proposals(self, api_client, seeded_db):
        """Test getting all proposals"""
        response = api_client.get(f"{BASE_URL}/api/proposals")
        assert response.status_code == 200
        proposals = response.json()
        
        assert len(proposals) >= 7  # May have more due to multiple seeds
        
        # Validate proposal structure
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
    
    def test_vote_on_proposal(self, api_client, auth_headers_1, seeded_db):
        """Test voting on a proposal"""
        # Get proposals
        proposals_response = api_client.get(f"{BASE_URL}/api/proposals")
        proposals = proposals_response.json()
        
        active_proposal = next((p for p in proposals if p["status"] == "active"), None)
        assert active_proposal is not None
        
        response = api_client.post(f"{BASE_URL}/api/proposals/vote",
                                   json={"proposal_id": active_proposal["id"], "vote": True},
                                   headers=auth_headers_1)
        # Could be 200 (success) or 400 (already voted)
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "voted"
            assert data["vote"] == "for"
    
    def test_vote_against_proposal(self, api_client, auth_headers_2, seeded_db):
        """Test voting against a proposal"""
        proposals_response = api_client.get(f"{BASE_URL}/api/proposals")
        proposals = proposals_response.json()
        
        active_proposal = next((p for p in proposals if p["status"] == "active"), None)
        
        response = api_client.post(f"{BASE_URL}/api/proposals/vote",
                                   json={"proposal_id": active_proposal["id"], "vote": False},
                                   headers=auth_headers_2)
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert data["vote"] == "against"
    
    def test_vote_proposal_not_found(self, api_client, auth_headers_1):
        """Test voting on non-existent proposal"""
        response = api_client.post(f"{BASE_URL}/api/proposals/vote",
                                   json={"proposal_id": "non-existent", "vote": True},
                                   headers=auth_headers_1)
        assert response.status_code == 404
    
    def test_create_proposal_level_requirement(self, api_client, seeded_db):
        """Test creating proposal requires level 2"""
        # Register a fresh level 1 user
        new_user = {
            "email": f"level1_{uuid.uuid4().hex[:8]}@realum.io",
            "password": "Test123!",
            "username": f"Level1User_{uuid.uuid4().hex[:8]}"
        }
        reg_response = api_client.post(f"{BASE_URL}/api/auth/register", json=new_user)
        assert reg_response.status_code == 200
        token = reg_response.json()["access_token"]
        
        # Try to create proposal
        response = api_client.post(f"{BASE_URL}/api/proposals",
                                   json={"title": "Test", "description": "Test desc"},
                                   headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 400
        assert "level 2" in response.json()["detail"].lower()


class TestWalletEndpoints:
    """Wallet endpoint tests"""
    
    def test_get_balance(self, api_client, auth_headers_1):
        """Test getting wallet balance"""
        response = api_client.get(f"{BASE_URL}/api/wallet/balance", headers=auth_headers_1)
        assert response.status_code == 200
        data = response.json()
        assert "realum_balance" in data
        assert isinstance(data["realum_balance"], (int, float))
    
    def test_get_transactions(self, api_client, auth_headers_1):
        """Test getting transaction history"""
        response = api_client.get(f"{BASE_URL}/api/wallet/transactions", headers=auth_headers_1)
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert isinstance(data["transactions"], list)
    
    def test_transfer_coins(self, api_client, auth_headers_1, registered_user_2):
        """Test transferring coins between users"""
        recipient_id = registered_user_2["user"]["id"]
        
        response = api_client.post(f"{BASE_URL}/api/wallet/transfer",
                                   json={"to_user_id": recipient_id, "amount": 10},
                                   headers=auth_headers_1)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "transaction_id" in data
        assert "new_balance" in data
    
    def test_transfer_insufficient_balance(self, api_client, auth_headers_1, registered_user_2):
        """Test transfer with insufficient balance"""
        recipient_id = registered_user_2["user"]["id"]
        
        response = api_client.post(f"{BASE_URL}/api/wallet/transfer",
                                   json={"to_user_id": recipient_id, "amount": 999999999},
                                   headers=auth_headers_1)
        assert response.status_code == 400
        assert "insufficient" in response.json()["detail"].lower()
    
    def test_transfer_invalid_amount(self, api_client, auth_headers_1, registered_user_2):
        """Test transfer with invalid amount"""
        recipient_id = registered_user_2["user"]["id"]
        
        response = api_client.post(f"{BASE_URL}/api/wallet/transfer",
                                   json={"to_user_id": recipient_id, "amount": -10},
                                   headers=auth_headers_1)
        assert response.status_code == 400
    
    def test_transfer_to_nonexistent_user(self, api_client, auth_headers_1):
        """Test transfer to non-existent user"""
        response = api_client.post(f"{BASE_URL}/api/wallet/transfer",
                                   json={"to_user_id": "non-existent-user", "amount": 10},
                                   headers=auth_headers_1)
        assert response.status_code == 404
    
    def test_connect_wallet(self, api_client, auth_headers_1):
        """Test connecting MetaMask wallet"""
        wallet_address = "0x" + "a" * 40  # Valid format
        
        response = api_client.post(f"{BASE_URL}/api/wallet/connect",
                                   json={"wallet_address": wallet_address},
                                   headers=auth_headers_1)
        assert response.status_code in [200, 400]  # 400 if already connected
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "connected"
            assert data["wallet_address"] == wallet_address
    
    def test_connect_invalid_wallet(self, api_client, auth_headers_1):
        """Test connecting invalid wallet address"""
        response = api_client.post(f"{BASE_URL}/api/wallet/connect",
                                   json={"wallet_address": "invalid"},
                                   headers=auth_headers_1)
        assert response.status_code == 400


class TestLeaderboardEndpoints:
    """Leaderboard endpoint tests"""
    
    def test_get_leaderboard(self, api_client, seeded_db):
        """Test getting leaderboard"""
        response = api_client.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200
        leaderboard = response.json()
        
        assert isinstance(leaderboard, list)
        
        if len(leaderboard) > 0:
            entry = leaderboard[0]
            assert "rank" in entry
            assert "user_id" in entry
            assert "username" in entry
            assert "level" in entry
            assert "xp" in entry
            assert "realum_balance" in entry
            assert "badges_count" in entry
            
            # Verify ranking order
            for i, entry in enumerate(leaderboard):
                assert entry["rank"] == i + 1


class TestBadgesEndpoints:
    """Badges endpoint tests"""
    
    def test_get_all_badges(self, api_client):
        """Test getting all available badges"""
        response = api_client.get(f"{BASE_URL}/api/badges")
        assert response.status_code == 200
        data = response.json()
        
        assert "badges" in data
        badges = data["badges"]
        assert len(badges) > 20  # Should have many badges
        
        # Validate badge structure
        for badge in badges:
            assert "id" in badge
            assert "name" in badge
            assert "description" in badge
            assert "icon" in badge
            assert "rarity" in badge
            assert badge["rarity"] in ["common", "uncommon", "rare", "epic", "legendary"]


class TestPlatformStatsEndpoints:
    """Platform statistics endpoint tests"""
    
    def test_get_platform_stats(self, api_client, seeded_db):
        """Test getting platform statistics"""
        response = api_client.get(f"{BASE_URL}/api/stats/platform")
        assert response.status_code == 200
        data = response.json()
        
        assert "total_users" in data
        assert "total_transactions" in data
        assert "active_proposals" in data
        assert "jobs_completed" in data
        assert "total_realum_supply" in data
        
        assert isinstance(data["total_users"], int)
        assert isinstance(data["total_transactions"], int)
        assert data["total_realum_supply"] == 1000000000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
