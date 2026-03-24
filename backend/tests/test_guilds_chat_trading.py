"""
Test Suite for REALUM Guilds, Chat, and Trading Systems
Tests the 4 new high-impact features: Guilds/Alliances, Global Chat, P2P Trading, Auctions
"""

import pytest
import requests
import os
from datetime import datetime

# Use the public URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://realum-politics.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "lazarescugeorgian@yahoo.com"
TEST_PASSWORD = "Lazarescu4."


class TestGuildsPublicAPI:
    """Test public guild endpoints (no auth required)"""
    
    def test_list_guilds(self):
        """GET /api/guilds/list - List public guilds"""
        response = requests.get(f"{BASE_URL}/api/guilds/list")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "guilds" in data, "Response should contain 'guilds' key"
        assert isinstance(data["guilds"], list), "guilds should be a list"
        print(f"✓ List guilds: {len(data['guilds'])} public guilds found")
    
    def test_list_guilds_with_search(self):
        """GET /api/guilds/list?search=test - Search guilds"""
        response = requests.get(f"{BASE_URL}/api/guilds/list?search=test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "guilds" in data
        print(f"✓ Search guilds: {len(data['guilds'])} results for 'test'")
    
    def test_guild_leaderboard(self):
        """GET /api/guilds/leaderboard - Get top guilds"""
        response = requests.get(f"{BASE_URL}/api/guilds/leaderboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "leaderboard" in data, "Response should contain 'leaderboard' key"
        assert isinstance(data["leaderboard"], list), "leaderboard should be a list"
        
        # Verify structure if guilds exist
        if data["leaderboard"]:
            guild = data["leaderboard"][0]
            assert "rank" in guild, "Guild should have rank"
            assert "name" in guild, "Guild should have name"
            assert "level" in guild, "Guild should have level"
        print(f"✓ Guild leaderboard: {len(data['leaderboard'])} guilds ranked")
    
    def test_list_alliances(self):
        """GET /api/guilds/alliances - List all alliances"""
        response = requests.get(f"{BASE_URL}/api/guilds/alliances")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "alliances" in data
        print(f"✓ List alliances: {len(data['alliances'])} alliances found")


class TestChatPublicAPI:
    """Test public chat endpoints (no auth required)"""
    
    def test_get_channels(self):
        """GET /api/chat/channels - Get available chat channels"""
        response = requests.get(f"{BASE_URL}/api/chat/channels")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "channels" in data, "Response should contain 'channels' key"
        
        # Verify expected channels exist
        channels = data["channels"]
        expected_channels = ["global", "trade", "politics", "help"]
        for ch in expected_channels:
            assert ch in channels, f"Channel '{ch}' should exist"
        print(f"✓ Chat channels: {list(channels.keys())}")
    
    def test_get_global_messages(self):
        """GET /api/chat/messages/global - Get global channel messages"""
        response = requests.get(f"{BASE_URL}/api/chat/messages/global")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "messages" in data, "Response should contain 'messages' key"
        assert isinstance(data["messages"], list), "messages should be a list"
        print(f"✓ Global messages: {len(data['messages'])} messages")
    
    def test_get_trade_messages(self):
        """GET /api/chat/messages/trade - Get trade channel messages"""
        response = requests.get(f"{BASE_URL}/api/chat/messages/trade")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "messages" in data
        print(f"✓ Trade messages: {len(data['messages'])} messages")
    
    def test_get_politics_messages(self):
        """GET /api/chat/messages/politics - Get politics channel messages"""
        response = requests.get(f"{BASE_URL}/api/chat/messages/politics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "messages" in data
        print(f"✓ Politics messages: {len(data['messages'])} messages")
    
    def test_get_help_messages(self):
        """GET /api/chat/messages/help - Get help channel messages"""
        response = requests.get(f"{BASE_URL}/api/chat/messages/help")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "messages" in data
        print(f"✓ Help messages: {len(data['messages'])} messages")
    
    def test_invalid_channel_returns_404(self):
        """GET /api/chat/messages/invalid - Invalid channel should return 404"""
        response = requests.get(f"{BASE_URL}/api/chat/messages/invalid_channel_xyz")
        assert response.status_code == 404, f"Expected 404 for invalid channel, got {response.status_code}"
        print("✓ Invalid channel returns 404")
    
    def test_online_count(self):
        """GET /api/chat/online-count/global - Get online user count"""
        response = requests.get(f"{BASE_URL}/api/chat/online-count/global")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "channel" in data
        assert "online_count" in data
        print(f"✓ Online count for global: {data['online_count']}")


class TestTradingPublicAPI:
    """Test public trading/auction endpoints (no auth required)"""
    
    def test_list_auctions(self):
        """GET /api/trading/auctions - List active auctions"""
        response = requests.get(f"{BASE_URL}/api/trading/auctions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "auctions" in data, "Response should contain 'auctions' key"
        assert "categories" in data, "Response should contain 'categories' key"
        assert isinstance(data["auctions"], list), "auctions should be a list"
        
        # Verify categories
        expected_categories = ["collectibles", "equipment", "resources", "cosmetics", 
                              "property_deeds", "company_shares", "other"]
        for cat in expected_categories:
            assert cat in data["categories"], f"Category '{cat}' should exist"
        print(f"✓ Auctions: {len(data['auctions'])} active, {len(data['categories'])} categories")
    
    def test_list_auctions_with_category_filter(self):
        """GET /api/trading/auctions?category=collectibles - Filter by category"""
        response = requests.get(f"{BASE_URL}/api/trading/auctions?category=collectibles")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "auctions" in data
        print(f"✓ Collectibles auctions: {len(data['auctions'])}")
    
    def test_list_auctions_sorted_by_price_low(self):
        """GET /api/trading/auctions?sort_by=price_low - Sort by price ascending"""
        response = requests.get(f"{BASE_URL}/api/trading/auctions?sort_by=price_low")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "auctions" in data
        print(f"✓ Auctions sorted by price (low): {len(data['auctions'])}")
    
    def test_list_auctions_sorted_by_price_high(self):
        """GET /api/trading/auctions?sort_by=price_high - Sort by price descending"""
        response = requests.get(f"{BASE_URL}/api/trading/auctions?sort_by=price_high")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "auctions" in data
        print(f"✓ Auctions sorted by price (high): {len(data['auctions'])}")
    
    def test_list_auctions_sorted_by_newest(self):
        """GET /api/trading/auctions?sort_by=newest - Sort by newest"""
        response = requests.get(f"{BASE_URL}/api/trading/auctions?sort_by=newest")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "auctions" in data
        print(f"✓ Auctions sorted by newest: {len(data['auctions'])}")
    
    def test_list_auctions_with_search(self):
        """GET /api/trading/auctions?search=test - Search auctions"""
        response = requests.get(f"{BASE_URL}/api/trading/auctions?search=test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "auctions" in data
        print(f"✓ Search auctions: {len(data['auctions'])} results for 'test'")


class TestAuthenticatedGuildsAPI:
    """Test authenticated guild endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping authenticated tests")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.user = data.get("user", {})
        else:
            pytest.skip(f"Login failed: {response.status_code}")
    
    def test_my_guild_status(self):
        """GET /api/guilds/my-guild - Get user's guild status"""
        response = requests.get(f"{BASE_URL}/api/guilds/my-guild", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # User either has a guild or doesn't
        if data.get("has_guild"):
            assert "guild" in data, "Should have guild info"
            assert "membership" in data, "Should have membership info"
            print(f"✓ User is in guild: {data['guild']['name']}")
        else:
            assert "can_create" in data, "Should indicate if user can create guild"
            assert "creation_cost" in data, "Should show creation cost"
            print(f"✓ User has no guild. Can create: {data['can_create']}, Cost: {data['creation_cost']} RLM")


class TestAuthenticatedChatAPI:
    """Test authenticated chat endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping authenticated tests")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.user = data.get("user", {})
        else:
            pytest.skip(f"Login failed: {response.status_code}")
    
    def test_send_message_to_global(self):
        """POST /api/chat/send - Send message to global channel"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        response = requests.post(f"{BASE_URL}/api/chat/send", 
            headers=self.headers,
            json={
                "content": f"Test message from automated testing at {timestamp}",
                "channel": "global"
            }
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limited on chat")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert data["message"]["channel"] == "global"
        print(f"✓ Sent message to global channel")
    
    def test_get_private_conversations(self):
        """GET /api/chat/private - Get private conversations"""
        response = requests.get(f"{BASE_URL}/api/chat/private", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "conversations" in data, "Response should contain 'conversations' key"
        print(f"✓ Private conversations: {len(data['conversations'])}")


class TestAuthenticatedTradingAPI:
    """Test authenticated trading endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 429:
            pytest.skip("Rate limited - skipping authenticated tests")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.user = data.get("user", {})
        else:
            pytest.skip(f"Login failed: {response.status_code}")
    
    def test_get_incoming_offers(self):
        """GET /api/trading/offers/incoming - Get incoming P2P offers"""
        response = requests.get(f"{BASE_URL}/api/trading/offers/incoming", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "offers" in data, "Response should contain 'offers' key"
        assert isinstance(data["offers"], list), "offers should be a list"
        print(f"✓ Incoming offers: {len(data['offers'])}")
    
    def test_get_outgoing_offers(self):
        """GET /api/trading/offers/outgoing - Get outgoing P2P offers"""
        response = requests.get(f"{BASE_URL}/api/trading/offers/outgoing", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "offers" in data, "Response should contain 'offers' key"
        assert isinstance(data["offers"], list), "offers should be a list"
        print(f"✓ Outgoing offers: {len(data['offers'])}")
    
    def test_get_my_auctions(self):
        """GET /api/trading/my-auctions - Get user's auctions"""
        response = requests.get(f"{BASE_URL}/api/trading/my-auctions", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "selling" in data, "Response should contain 'selling' key"
        assert "bidding" in data, "Response should contain 'bidding' key"
        print(f"✓ My auctions - Selling: {len(data['selling'])}, Bidding: {len(data['bidding'])}")


class TestAPIErrorHandling:
    """Test error handling for various edge cases"""
    
    def test_unauthenticated_my_guild_returns_401(self):
        """GET /api/guilds/my-guild without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/guilds/my-guild")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated my-guild returns 401")
    
    def test_unauthenticated_send_message_returns_401(self):
        """POST /api/chat/send without auth should return 401"""
        response = requests.post(f"{BASE_URL}/api/chat/send", json={
            "content": "test",
            "channel": "global"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated send message returns 401")
    
    def test_unauthenticated_private_chat_returns_401(self):
        """GET /api/chat/private without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/chat/private")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated private chat returns 401")
    
    def test_unauthenticated_incoming_offers_returns_401(self):
        """GET /api/trading/offers/incoming without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/trading/offers/incoming")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated incoming offers returns 401")
    
    def test_unauthenticated_outgoing_offers_returns_401(self):
        """GET /api/trading/offers/outgoing without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/trading/offers/outgoing")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated outgoing offers returns 401")
    
    def test_unauthenticated_my_auctions_returns_401(self):
        """GET /api/trading/my-auctions without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/trading/my-auctions")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated my-auctions returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
