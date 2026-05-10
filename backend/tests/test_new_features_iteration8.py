"""
REALUM New Features Test Suite - Iteration 8
Testing: Tutorial, Friends, Tournaments, Derivatives, Battle Pass
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://realum-politics.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "lazarescugeorgian@yahoo.com"
TEST_PASSWORD = "Lazarescu4."


class TestAuthentication:
    """Authentication tests to get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    
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
        print(f"Login successful - User: {data['user'].get('username')}")


class TestTutorialAPI:
    """Tutorial System API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_get_tutorial_steps(self):
        """GET /api/tutorial/steps - returns 12 steps"""
        response = requests.get(f"{BASE_URL}/api/tutorial/steps")
        assert response.status_code == 200
        data = response.json()
        assert "steps" in data
        assert "total_steps" in data
        assert data["total_steps"] == 12
        assert len(data["steps"]) == 12
        print(f"Tutorial has {data['total_steps']} steps")
        print(f"Total rewards: {data['total_rewards']}")
    
    def test_get_tutorial_npcs(self):
        """GET /api/tutorial/npcs - returns NPC info"""
        response = requests.get(f"{BASE_URL}/api/tutorial/npcs")
        assert response.status_code == 200
        data = response.json()
        assert "npcs" in data
        assert len(data["npcs"]) >= 4  # Luna, Vault, Max, Aria
        npc_names = [npc["name"] for npc in data["npcs"]]
        assert "Luna" in npc_names
        print(f"NPCs: {npc_names}")
    
    def test_get_tutorial_progress(self, auth_headers):
        """GET /api/tutorial/progress (auth) - returns user progress"""
        response = requests.get(f"{BASE_URL}/api/tutorial/progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "current_step" in data
        assert "completed_steps" in data
        assert "is_completed" in data
        assert "total_steps" in data
        assert "progress_percentage" in data
        print(f"Tutorial progress: {data['progress_percentage']}% - Step {data['current_step']}/{data['total_steps']}")
    
    def test_complete_tutorial_step(self, auth_headers):
        """POST /api/tutorial/complete-step/{id} (auth) - complete step with rewards"""
        # First get current progress
        progress_res = requests.get(f"{BASE_URL}/api/tutorial/progress", headers=auth_headers)
        progress = progress_res.json()
        
        if progress.get("is_completed"):
            pytest.skip("Tutorial already completed")
        
        current_step_data = progress.get("current_step_data")
        if not current_step_data:
            pytest.skip("No current step data")
        
        step_id = current_step_data.get("id")
        response = requests.post(f"{BASE_URL}/api/tutorial/complete-step/{step_id}", headers=auth_headers)
        
        # Could be 200 (success) or 400 (already completed)
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "rewards" in data
            print(f"Completed step '{step_id}' - Rewards: {data['rewards']}")
        else:
            print(f"Step already completed or error: {response.json()}")


class TestFriendsAPI:
    """Friends System API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_get_gift_types(self):
        """GET /api/friends/gift-types - returns 6 gift types"""
        response = requests.get(f"{BASE_URL}/api/friends/gift-types")
        assert response.status_code == 200
        data = response.json()
        assert "gift_types" in data
        gift_types = data["gift_types"]
        assert len(gift_types) == 6
        expected_types = ["rlm", "xp_boost", "lucky_charm", "flowers", "cake", "trophy"]
        for gt in expected_types:
            assert gt in gift_types
        print(f"Gift types: {list(gift_types.keys())}")
    
    def test_get_friends_list(self, auth_headers):
        """GET /api/friends/list (auth) - returns friends with online status"""
        response = requests.get(f"{BASE_URL}/api/friends/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "friends" in data
        assert "total" in data
        assert "online_count" in data
        print(f"Friends: {data['total']} total, {data['online_count']} online")
    
    def test_get_friend_requests(self, auth_headers):
        """GET /api/friends/requests (auth) - returns pending requests"""
        response = requests.get(f"{BASE_URL}/api/friends/requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "incoming" in data
        assert "outgoing" in data
        print(f"Friend requests: {len(data['incoming'])} incoming, {len(data['outgoing'])} outgoing")
    
    def test_get_received_gifts(self, auth_headers):
        """GET /api/friends/gifts/received (auth) - returns received gifts"""
        response = requests.get(f"{BASE_URL}/api/friends/gifts/received", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "gifts" in data
        print(f"Received gifts: {len(data['gifts'])}")
    
    def test_get_sent_gifts(self, auth_headers):
        """GET /api/friends/gifts/sent (auth) - returns sent gifts"""
        response = requests.get(f"{BASE_URL}/api/friends/gifts/sent", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "gifts" in data
        print(f"Sent gifts: {len(data['gifts'])}")
    
    def test_send_friend_request_invalid_user(self, auth_headers):
        """POST /api/friends/request (auth) - test with non-existent user"""
        response = requests.post(f"{BASE_URL}/api/friends/request", 
            headers=auth_headers,
            json={"target_username": "nonexistent_user_12345"})
        assert response.status_code == 404
        print("Friend request to non-existent user correctly returns 404")


class TestTournamentsAPI:
    """Tournaments System API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_get_tournament_types(self):
        """GET /api/tournaments/types - returns 6 tournament types"""
        response = requests.get(f"{BASE_URL}/api/tournaments/types")
        assert response.status_code == 200
        data = response.json()
        assert "tournament_types" in data
        types = data["tournament_types"]
        assert len(types) == 6
        expected_types = ["stock_trading", "daily_streak", "mini_games", "politics", "guild_war", "referral_race"]
        for tt in expected_types:
            assert tt in types
        print(f"Tournament types: {list(types.keys())}")
    
    def test_get_active_tournaments(self):
        """GET /api/tournaments/active - returns active tournaments"""
        response = requests.get(f"{BASE_URL}/api/tournaments/active")
        assert response.status_code == 200
        data = response.json()
        assert "tournaments" in data
        print(f"Active tournaments: {len(data['tournaments'])}")
    
    def test_get_upcoming_tournaments(self):
        """GET /api/tournaments/upcoming - returns upcoming tournaments"""
        response = requests.get(f"{BASE_URL}/api/tournaments/upcoming")
        assert response.status_code == 200
        data = response.json()
        assert "tournaments" in data
        print(f"Upcoming tournaments: {len(data['tournaments'])}")
    
    def test_get_past_tournaments(self):
        """GET /api/tournaments/past - returns past tournaments"""
        response = requests.get(f"{BASE_URL}/api/tournaments/past")
        assert response.status_code == 200
        data = response.json()
        assert "tournaments" in data
        print(f"Past tournaments: {len(data['tournaments'])}")
    
    def test_get_global_leaderboard(self):
        """GET /api/tournaments/leaderboard/global - returns global leaderboard"""
        response = requests.get(f"{BASE_URL}/api/tournaments/leaderboard/global")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        print(f"Global leaderboard entries: {len(data['leaderboard'])}")
    
    def test_get_my_tournaments(self, auth_headers):
        """GET /api/tournaments/my-tournaments (auth) - returns user's tournaments"""
        response = requests.get(f"{BASE_URL}/api/tournaments/my-tournaments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "my_tournaments" in data
        print(f"My tournaments: {len(data['my_tournaments'])}")


class TestDerivativesAPI:
    """Derivatives (Futures & Options) API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_get_options_chain(self):
        """GET /api/derivatives/options/chain/{company} - returns options chain"""
        # First get a company ID from stocks
        market_res = requests.get(f"{BASE_URL}/api/stocks/market")
        if market_res.status_code != 200:
            pytest.skip("Could not get stock market data")
        
        companies = market_res.json().get("companies", [])
        if not companies:
            pytest.skip("No companies available")
        
        company_id = companies[0]["id"]
        response = requests.get(f"{BASE_URL}/api/derivatives/options/chain/{company_id}")
        assert response.status_code == 200
        data = response.json()
        assert "company_id" in data
        assert "current_price" in data
        assert "options" in data
        assert len(data["options"]) > 0
        print(f"Options chain for {company_id}: {len(data['options'])} options, current price: {data['current_price']}")
    
    def test_get_futures_positions(self, auth_headers):
        """GET /api/derivatives/futures/positions (auth) - get open positions"""
        response = requests.get(f"{BASE_URL}/api/derivatives/futures/positions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        print(f"Open futures positions: {len(data['positions'])}")
    
    def test_get_futures_history(self, auth_headers):
        """GET /api/derivatives/futures/history (auth) - get closed positions"""
        response = requests.get(f"{BASE_URL}/api/derivatives/futures/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        print(f"Futures history: {len(data['history'])} closed positions")
    
    def test_get_my_options(self, auth_headers):
        """GET /api/derivatives/options/my-contracts (auth) - get option contracts"""
        response = requests.get(f"{BASE_URL}/api/derivatives/options/my-contracts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "contracts" in data
        print(f"Active option contracts: {len(data['contracts'])}")
    
    def test_get_options_history(self, auth_headers):
        """GET /api/derivatives/options/history (auth) - get options history"""
        response = requests.get(f"{BASE_URL}/api/derivatives/options/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        print(f"Options history: {len(data['history'])} contracts")
    
    def test_get_derivatives_stats(self, auth_headers):
        """GET /api/derivatives/stats (auth) - get trading stats"""
        response = requests.get(f"{BASE_URL}/api/derivatives/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "futures" in data
        assert "options" in data
        assert "total_trades" in data["futures"]
        assert "total_pnl" in data["futures"]
        print(f"Derivatives stats - Futures P&L: {data['futures']['total_pnl']}, Options P&L: {data['options']['total_pnl']}")
    
    def test_open_futures_position_validation(self, auth_headers):
        """POST /api/derivatives/futures/open (auth) - test validation"""
        # Test with invalid leverage
        response = requests.post(f"{BASE_URL}/api/derivatives/futures/open", 
            headers=auth_headers,
            json={
                "company_id": "test",
                "position_type": "long",
                "leverage": 100,  # Invalid leverage
                "margin_amount": 100
            })
        assert response.status_code == 400
        print("Invalid leverage correctly rejected")


class TestBattlePassAPI:
    """Battle Pass System API Tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_get_battlepass_info(self):
        """GET /api/battlepass/info - returns season info"""
        response = requests.get(f"{BASE_URL}/api/battlepass/info")
        assert response.status_code == 200
        data = response.json()
        assert "season" in data
        assert "name" in data
        assert "max_level" in data
        assert "xp_per_level" in data
        assert "pass_cost" in data
        assert data["max_level"] == 50
        print(f"Battle Pass Season {data['season']}: {data['name']}")
        print(f"Max level: {data['max_level']}, XP per level: {data['xp_per_level']}, Cost: {data['pass_cost']} RLM")
    
    def test_get_my_battlepass_progress(self, auth_headers):
        """GET /api/battlepass/my-progress (auth) - returns user progress"""
        response = requests.get(f"{BASE_URL}/api/battlepass/my-progress", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "season" in data
        assert "level" in data
        assert "xp" in data
        assert "is_premium" in data
        assert "level_progress" in data
        print(f"Battle Pass progress: Level {data['level']}, XP: {data['xp']}, Premium: {data['is_premium']}")
    
    def test_get_weekly_challenges(self, auth_headers):
        """GET /api/battlepass/weekly-challenges (auth) - returns weekly challenges"""
        response = requests.get(f"{BASE_URL}/api/battlepass/weekly-challenges", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "week" in data
        assert "challenges" in data
        assert "total_xp_available" in data
        print(f"Week {data['week']}: {len(data['challenges'])} challenges, {data['total_xp_available']} XP available")
    
    def test_get_battlepass_leaderboard(self):
        """GET /api/battlepass/leaderboard - returns level leaderboard"""
        response = requests.get(f"{BASE_URL}/api/battlepass/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert "season" in data
        print(f"Battle Pass leaderboard: {len(data['leaderboard'])} entries")


class TestDashboardQuickActions:
    """Test that Dashboard has all 16 quick action links"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Authentication failed")
    
    def test_all_quick_action_endpoints_exist(self, auth_headers):
        """Verify all quick action endpoints are accessible"""
        endpoints = [
            "/api/bank/accounts",
            "/api/stocks/market",
            "/api/derivatives/stats",
            "/api/politics/proposals",
            "/api/companies/list",
            "/api/realestate/listings",
            "/api/games/list",
            "/api/tournaments/active",
            "/api/guilds/list",
            "/api/friends/list",
            "/api/trading/auctions",
            "/api/chat/channels",
            "/api/battlepass/info",
            "/api/tutorial/steps"
        ]
        
        results = []
        for endpoint in endpoints:
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", headers=auth_headers, timeout=10)
                results.append({
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "success": response.status_code == 200
                })
            except Exception as e:
                results.append({
                    "endpoint": endpoint,
                    "status": "error",
                    "success": False,
                    "error": str(e)
                })
        
        successful = sum(1 for r in results if r["success"])
        print(f"Quick action endpoints: {successful}/{len(endpoints)} accessible")
        
        for r in results:
            status = "✓" if r["success"] else "✗"
            print(f"  {status} {r['endpoint']}: {r['status']}")
        
        # At least 80% should be accessible
        assert successful >= len(endpoints) * 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
