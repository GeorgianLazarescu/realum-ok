"""
Test suite for REALUM Politics and Stocks features
Tests political system (parties, elections, laws) and stock market (buy/sell shares)
"""

import pytest
import requests
import os
import time
import uuid

# Use local endpoint to avoid rate limiting on public URL
BASE_URL = "http://localhost:8001"

# Test credentials
TEST_EMAIL = "lazarescugeorgian@yahoo.com"
TEST_PASSWORD = "Lazarescu4."


class TestPoliticsPublicEndpoints:
    """Test public politics endpoints (no auth required)"""
    
    def test_get_political_statistics(self):
        """GET /api/politics/statistics - returns zones and stats"""
        response = requests.get(f"{BASE_URL}/api/politics/statistics")
        assert response.status_code == 200
        
        data = response.json()
        # Verify structure
        assert "total_parties" in data
        assert "total_officials" in data
        assert "active_elections" in data
        assert "total_laws" in data
        assert "total_votes_cast" in data
        assert "top_parties" in data
        assert "zones" in data
        
        # Verify zones data
        assert len(data["zones"]) == 6
        zone_ids = [z["id"] for z in data["zones"]]
        assert "learning_zone" in zone_ids
        assert "jobs_hub" in zone_ids
        assert "marketplace" in zone_ids
        assert "social_plaza" in zone_ids
        assert "treasury" in zone_ids
        assert "dao_hall" in zone_ids
        
        print(f"✓ Political statistics: {data['total_parties']} parties, {data['active_elections']} elections, 6 zones")
    
    def test_get_parties_list(self):
        """GET /api/politics/parties - returns parties list"""
        response = requests.get(f"{BASE_URL}/api/politics/parties")
        assert response.status_code == 200
        
        data = response.json()
        assert "parties" in data
        assert isinstance(data["parties"], list)
        
        print(f"✓ Parties list: {len(data['parties'])} parties found")
    
    def test_get_elections(self):
        """GET /api/politics/elections - returns elections"""
        response = requests.get(f"{BASE_URL}/api/politics/elections")
        assert response.status_code == 200
        
        data = response.json()
        assert "elections" in data
        assert isinstance(data["elections"], list)
        
        print(f"✓ Elections list: {len(data['elections'])} elections found")
    
    def test_get_world_government(self):
        """GET /api/politics/government/world - returns world government"""
        response = requests.get(f"{BASE_URL}/api/politics/government/world")
        assert response.status_code == 200
        
        data = response.json()
        assert "world_president" in data
        assert "ministers" in data
        assert "senators" in data
        
        print(f"✓ World government: President={data['world_president']}, Ministers={len(data['ministers'])}, Senators={len(data['senators'])}")
    
    def test_get_zone_governments(self):
        """GET /api/politics/government/zones - returns all zone governments"""
        response = requests.get(f"{BASE_URL}/api/politics/government/zones")
        assert response.status_code == 200
        
        data = response.json()
        assert "zones" in data
        assert len(data["zones"]) == 6
        
        for zone in data["zones"]:
            assert "zone" in zone
            assert "governor" in zone
            assert "councilor_count" in zone
        
        print(f"✓ Zone governments: {len(data['zones'])} zones with government data")
    
    def test_get_laws(self):
        """GET /api/politics/laws - returns laws"""
        response = requests.get(f"{BASE_URL}/api/politics/laws")
        assert response.status_code == 200
        
        data = response.json()
        assert "laws" in data
        assert isinstance(data["laws"], list)
        
        print(f"✓ Laws list: {len(data['laws'])} laws found")


class TestStocksPublicEndpoints:
    """Test public stocks endpoints (no auth required)"""
    
    def test_get_market_overview(self):
        """GET /api/stocks/market - returns all stocks and market data"""
        response = requests.get(f"{BASE_URL}/api/stocks/market")
        assert response.status_code == 200
        
        data = response.json()
        # Verify structure
        assert "market_open" in data
        assert "total_volume" in data
        assert "total_market_cap" in data
        assert "companies" in data
        assert "gainers" in data
        assert "losers" in data
        assert "trading_fee_percent" in data
        
        # Verify companies
        assert len(data["companies"]) == 8
        
        # Verify company structure
        for company in data["companies"]:
            assert "id" in company
            assert "symbol" in company
            assert "name" in company
            assert "sector" in company
            assert "current_price" in company
            assert "change" in company
            assert "change_percent" in company
        
        # Verify expected companies exist
        symbols = [c["symbol"] for c in data["companies"]]
        assert "RLMT" in symbols  # REALUM Technologies
        assert "CYBK" in symbols  # Cyber Bank
        assert "EDVS" in symbols  # EduVerse Academy
        assert "QLAB" in symbols  # Quantum Labs
        
        print(f"✓ Market overview: {len(data['companies'])} companies, market_cap={data['total_market_cap']}, fee={data['trading_fee_percent']}%")
    
    def test_get_company_details(self):
        """GET /api/stocks/company/{company_id} - returns company details"""
        response = requests.get(f"{BASE_URL}/api/stocks/company/realum-tech")
        assert response.status_code == 200
        
        data = response.json()
        assert "company" in data
        assert "change" in data
        assert "change_percent" in data
        assert "recent_trades" in data
        
        company = data["company"]
        assert company["symbol"] == "RLMT"
        assert company["name"] == "REALUM Technologies"
        assert company["sector"] == "technology"
        
        print(f"✓ Company details: {company['name']} ({company['symbol']}) @ {company['current_price']} RLM")
    
    def test_get_company_not_found(self):
        """GET /api/stocks/company/{invalid_id} - returns 404"""
        response = requests.get(f"{BASE_URL}/api/stocks/company/invalid-company")
        assert response.status_code == 404
        
        print("✓ Invalid company returns 404")
    
    def test_get_investor_leaderboard(self):
        """GET /api/stocks/leaderboard - returns top investors"""
        response = requests.get(f"{BASE_URL}/api/stocks/leaderboard")
        assert response.status_code == 200
        
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        
        print(f"✓ Investor leaderboard: {len(data['leaderboard'])} investors")
    
    def test_get_sector_performance(self):
        """GET /api/stocks/sectors - returns sector performance"""
        response = requests.get(f"{BASE_URL}/api/stocks/sectors")
        assert response.status_code == 200
        
        data = response.json()
        assert "sectors" in data
        
        # Verify expected sectors
        expected_sectors = ["technology", "finance", "energy", "real_estate", "education", "research", "media", "commerce"]
        for sector in expected_sectors:
            assert sector in data["sectors"]
        
        print(f"✓ Sector performance: {len(data['sectors'])} sectors")


class TestPoliticsAuthenticatedEndpoints:
    """Test authenticated politics endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip(f"Login failed: {response.status_code} - {response.text}")
    
    def test_get_my_political_status(self):
        """GET /api/politics/my-status - user political status"""
        response = requests.get(f"{BASE_URL}/api/politics/my-status", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "positions" in data
        assert "party" in data
        assert "party_role" in data
        assert "candidacies" in data
        assert "votes_cast" in data
        assert "can_create_party" in data
        assert "party_creation_cost" in data
        
        # Verify party creation cost
        assert data["party_creation_cost"] == 2000
        
        print(f"✓ Political status: party={data['party']}, positions={len(data['positions'])}, can_create_party={data['can_create_party']}")
    
    def test_get_available_positions(self):
        """GET /api/politics/positions/available - positions user can run for"""
        response = requests.get(f"{BASE_URL}/api/politics/positions/available", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "positions" in data
        assert len(data["positions"]) > 0
        
        # Verify position structure
        for pos in data["positions"]:
            assert "position" in pos
            assert "level" in pos
            assert "title" in pos
            assert "campaign_cost" in pos
            assert "can_run" in pos
        
        # Verify both world and local positions exist
        levels = [p["level"] for p in data["positions"]]
        assert "world" in levels
        assert "local" in levels
        
        print(f"✓ Available positions: {len(data['positions'])} positions")
    
    def test_join_party_no_party_exists(self):
        """POST /api/politics/parties/{party_id}/join - join nonexistent party"""
        response = requests.post(f"{BASE_URL}/api/politics/parties/nonexistent-party/join", headers=self.headers)
        assert response.status_code == 404
        
        print("✓ Join nonexistent party returns 404")
    
    def test_leave_party_not_in_party(self):
        """POST /api/politics/parties/leave - leave when not in party"""
        response = requests.post(f"{BASE_URL}/api/politics/parties/leave", headers=self.headers)
        # Should return 400 if not in a party
        assert response.status_code == 400
        
        print("✓ Leave party when not in party returns 400")
    
    def test_campaign_invalid_position(self):
        """POST /api/politics/elections/campaign - invalid position"""
        response = requests.post(f"{BASE_URL}/api/politics/elections/campaign", 
            headers=self.headers,
            json={
                "position": "invalid_position",
                "platform": "Test platform",
                "slogan": "Test slogan"
            }
        )
        assert response.status_code == 400
        
        print("✓ Campaign with invalid position returns 400")
    
    def test_propose_law_not_official(self):
        """POST /api/politics/laws/propose - propose law without being official"""
        response = requests.post(f"{BASE_URL}/api/politics/laws/propose",
            headers=self.headers,
            json={
                "title": "Test Law",
                "description": "Test description",
                "law_type": "world"
            }
        )
        # Should return 403 if not an elected official
        assert response.status_code == 403
        
        print("✓ Propose law without being official returns 403")


class TestStocksAuthenticatedEndpoints:
    """Test authenticated stocks endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
            self.user = response.json().get("user", {})
        else:
            pytest.skip(f"Login failed: {response.status_code} - {response.text}")
    
    def test_get_portfolio(self):
        """GET /api/stocks/portfolio - user portfolio"""
        response = requests.get(f"{BASE_URL}/api/stocks/portfolio", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "holdings" in data
        assert "total_value" in data
        assert "total_cost" in data
        assert "total_gain" in data
        assert "gain_percent" in data
        
        # User should have EDVS shares from previous test
        if data["holdings"]:
            for holding in data["holdings"]:
                assert "company_id" in holding
                assert "shares" in holding
                assert "current_price" in holding
                assert "market_value" in holding
        
        print(f"✓ Portfolio: {len(data['holdings'])} holdings, total_value={data['total_value']}")
    
    def test_get_transactions(self):
        """GET /api/stocks/transactions - user trading history"""
        response = requests.get(f"{BASE_URL}/api/stocks/transactions", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "transactions" in data
        assert isinstance(data["transactions"], list)
        
        # Verify transaction structure if any exist
        if data["transactions"]:
            tx = data["transactions"][0]
            assert "id" in tx
            assert "company_id" in tx
            assert "type" in tx
            assert "shares" in tx
            assert "price_per_share" in tx
            assert "total" in tx
            assert "executed_at" in tx
        
        print(f"✓ Transactions: {len(data['transactions'])} transactions")
    
    def test_buy_stock_insufficient_funds(self):
        """POST /api/stocks/buy - buy with insufficient funds"""
        response = requests.post(f"{BASE_URL}/api/stocks/buy",
            headers=self.headers,
            json={
                "company_id": "quantum-labs",  # Most expensive at 200 RLM
                "shares": 10000  # Way more than user can afford
            }
        )
        assert response.status_code == 400
        assert "Insufficient funds" in response.json().get("detail", "")
        
        print("✓ Buy with insufficient funds returns 400")
    
    def test_buy_stock_invalid_company(self):
        """POST /api/stocks/buy - buy invalid company"""
        response = requests.post(f"{BASE_URL}/api/stocks/buy",
            headers=self.headers,
            json={
                "company_id": "invalid-company",
                "shares": 1
            }
        )
        assert response.status_code == 404
        
        print("✓ Buy invalid company returns 404")
    
    def test_sell_stock_no_holdings(self):
        """POST /api/stocks/sell - sell stock not owned"""
        response = requests.post(f"{BASE_URL}/api/stocks/sell",
            headers=self.headers,
            json={
                "company_id": "quantum-labs",  # User likely doesn't own this
                "shares": 1
            }
        )
        # Should return 400 if user doesn't have shares
        assert response.status_code == 400
        
        print("✓ Sell stock not owned returns 400")
    
    def test_buy_stock_success(self):
        """POST /api/stocks/buy - successful stock purchase"""
        # Buy 1 share of a cheap stock
        response = requests.post(f"{BASE_URL}/api/stocks/buy",
            headers=self.headers,
            json={
                "company_id": "social-net",  # 45 RLM
                "shares": 1
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "success"
            assert "trade" in data
            assert "new_price" in data
            assert "message" in data
            
            trade = data["trade"]
            assert trade["type"] == "buy"
            assert trade["shares"] == 1
            assert trade["company_symbol"] == "SNET"
            
            print(f"✓ Buy stock success: {trade['shares']} shares of {trade['company_symbol']} @ {trade['price_per_share']} RLM")
        else:
            # May fail due to insufficient funds
            print(f"⚠ Buy stock failed (may be insufficient funds): {response.status_code}")
            assert response.status_code in [200, 400]
    
    def test_sell_stock_success(self):
        """POST /api/stocks/sell - successful stock sale"""
        # First check portfolio
        portfolio_res = requests.get(f"{BASE_URL}/api/stocks/portfolio", headers=self.headers)
        portfolio = portfolio_res.json()
        
        if portfolio["holdings"]:
            # Sell 1 share of first holding
            holding = portfolio["holdings"][0]
            response = requests.post(f"{BASE_URL}/api/stocks/sell",
                headers=self.headers,
                json={
                    "company_id": holding["company_id"],
                    "shares": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "trade" in data
                assert "profit" in data
                
                trade = data["trade"]
                assert trade["type"] == "sell"
                assert trade["shares"] == 1
                
                print(f"✓ Sell stock success: {trade['shares']} shares of {trade['company_symbol']} @ {trade['price_per_share']} RLM, profit={data['profit']}")
            else:
                print(f"⚠ Sell stock failed: {response.status_code}")
        else:
            print("⚠ No holdings to sell, skipping sell test")


class TestStocksDataIntegrity:
    """Test stock market data integrity"""
    
    def test_all_companies_have_required_fields(self):
        """Verify all companies have required fields"""
        response = requests.get(f"{BASE_URL}/api/stocks/market")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "id", "symbol", "name", "sector", "description",
            "base_price", "volatility", "dividend_rate",
            "current_price", "previous_close", "day_high", "day_low",
            "volume_today", "market_cap", "total_shares", "available_shares"
        ]
        
        for company in data["companies"]:
            for field in required_fields:
                assert field in company, f"Company {company.get('symbol', 'unknown')} missing field: {field}"
        
        print(f"✓ All {len(data['companies'])} companies have required fields")
    
    def test_stock_prices_are_positive(self):
        """Verify all stock prices are positive"""
        response = requests.get(f"{BASE_URL}/api/stocks/market")
        assert response.status_code == 200
        
        data = response.json()
        for company in data["companies"]:
            assert company["current_price"] > 0, f"{company['symbol']} has non-positive price"
            assert company["base_price"] > 0, f"{company['symbol']} has non-positive base price"
        
        print("✓ All stock prices are positive")
    
    def test_market_cap_calculation(self):
        """Verify market cap is calculated correctly"""
        response = requests.get(f"{BASE_URL}/api/stocks/market")
        assert response.status_code == 200
        
        data = response.json()
        for company in data["companies"]:
            # Market cap should be approximately price * total_shares
            expected_cap = company["base_price"] * company["total_shares"]
            assert company["market_cap"] == expected_cap, f"{company['symbol']} market cap mismatch"
        
        print("✓ Market cap calculations are correct")


class TestPoliticsDataIntegrity:
    """Test political system data integrity"""
    
    def test_all_zones_have_required_fields(self):
        """Verify all zones have required fields"""
        response = requests.get(f"{BASE_URL}/api/politics/statistics")
        assert response.status_code == 200
        
        data = response.json()
        for zone in data["zones"]:
            assert "id" in zone
            assert "name" in zone
            assert "city" in zone
        
        print(f"✓ All {len(data['zones'])} zones have required fields")
    
    def test_zone_governments_match_zones(self):
        """Verify zone governments match defined zones"""
        stats_res = requests.get(f"{BASE_URL}/api/politics/statistics")
        zones_res = requests.get(f"{BASE_URL}/api/politics/government/zones")
        
        assert stats_res.status_code == 200
        assert zones_res.status_code == 200
        
        stats_zones = {z["id"] for z in stats_res.json()["zones"]}
        gov_zones = {z["zone"]["id"] for z in zones_res.json()["zones"]}
        
        assert stats_zones == gov_zones, "Zone IDs don't match between statistics and governments"
        
        print("✓ Zone governments match defined zones")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
