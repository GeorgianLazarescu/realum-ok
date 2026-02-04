#!/usr/bin/env python3
"""
Test Account Lockout After Fix
"""

import requests
import time
import os

BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://realum-analytics.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

def make_request(method: str, endpoint: str, data: dict = None):
    """Make HTTP request"""
    url = f"{API_BASE}{endpoint}"
    session = requests.Session()
    
    if method.upper() == "GET":
        return session.get(url, params=data)
    elif method.upper() == "POST":
        return session.post(url, json=data)

def test_account_lockout_fixed():
    """Test Account Lockout after the datetime fix"""
    print("=== Testing Account Lockout (After Fix) ===")
    
    # Create a unique test user
    timestamp = int(time.time())
    lockout_user = {
        "email": f"lockoutfix{timestamp}@realum.io",
        "username": f"lockoutfix{timestamp}",
        "password": "Test123!@#",
        "role": "citizen"
    }
    
    try:
        # Register test user
        print(f"Registering user: {lockout_user['email']}")
        response = make_request("POST", "/auth/register", lockout_user)
        if response.status_code != 200:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False
        print("✅ User registered successfully")
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return False

    # Try 6 failed login attempts
    print("Testing failed login attempts...")
    
    for attempt in range(6):
        try:
            wrong_credentials = {
                "email": lockout_user["email"],
                "password": "WrongPassword123!"
            }
            
            print(f"Attempt {attempt + 1}: Trying wrong password...")
            response = make_request("POST", "/auth/login", wrong_credentials)
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 423:  # Account locked
                print(f"✅ Account locked after {attempt + 1} attempts!")
                print(f"   Response: {response.json()}")
                return True
            elif response.status_code == 400:
                print(f"   Expected 400 for wrong credentials")
            elif response.status_code == 429:
                print(f"   Rate limited, waiting...")
                time.sleep(5)
                continue
            elif response.status_code == 500:
                print(f"   Server error: {response.text}")
            else:
                print(f"   Unexpected status: {response.status_code}")
                print(f"   Response: {response.text}")
            
            # Small delay between attempts
            time.sleep(1)
                
        except Exception as e:
            print(f"❌ Login attempt {attempt + 1} error: {e}")
    
    print("❌ Account was not locked after 6 failed attempts")
    return False

if __name__ == "__main__":
    success = test_account_lockout_fixed()
    if success:
        print("\n🎉 Account lockout is working correctly!")
    else:
        print("\n⚠️  Account lockout test failed")