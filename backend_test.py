#!/usr/bin/env python3
"""
REALUM Backend Security Testing Suite
Tests all P1 Critical Priority security modules
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Get backend URL from environment
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://realum-analytics.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class SecurityTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_data = {
            "email": "2fatest@realum.io",
            "username": "2fatest",
            "password": "Test123!@#",
            "role": "citizen"
        }
        self.results = {
            "password_complexity": {"passed": 0, "failed": 0, "errors": []},
            "2fa": {"passed": 0, "failed": 0, "errors": []},
            "gdpr": {"passed": 0, "failed": 0, "errors": []},
            "rate_limiting": {"passed": 0, "failed": 0, "errors": []},
            "security_status": {"passed": 0, "failed": 0, "errors": []},
            "account_lockout": {"passed": 0, "failed": 0, "errors": []},
            "monitoring": {"passed": 0, "failed": 0, "errors": []},
            "password_change": {"passed": 0, "failed": 0, "errors": []}
        }

    def log_result(self, category: str, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {category}: {test_name}")
        if details:
            print(f"    Details: {details}")
        
        if success:
            self.results[category]["passed"] += 1
        else:
            self.results[category]["failed"] += 1
            self.results[category]["errors"].append(f"{test_name}: {details}")

    def make_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{API_BASE}{endpoint}"
        
        # Add auth header if token exists
        if self.auth_token and headers is None:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
        elif self.auth_token and headers:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                return self.session.get(url, headers=headers, params=data)
            elif method.upper() == "POST":
                return self.session.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                return self.session.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                return self.session.delete(url, headers=headers)
        except Exception as e:
            print(f"Request error: {e}")
            raise

    def test_password_complexity(self):
        """Test password complexity requirements (M124-128)"""
        print("\n=== Testing Password Complexity ===")
        
        # Test 1: Get password requirements
        try:
            response = self.make_request("GET", "/auth/password-requirements")
            if response.status_code == 200:
                requirements = response.json()
                expected_keys = ["min_length", "requirements"]
                if all(key in requirements for key in expected_keys):
                    self.log_result("password_complexity", "Get password requirements", True, 
                                  f"Min length: {requirements['min_length']}")
                else:
                    self.log_result("password_complexity", "Get password requirements", False, 
                                  "Missing required fields in response")
            else:
                self.log_result("password_complexity", "Get password requirements", False, 
                              f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("password_complexity", "Get password requirements", False, str(e))

        # Test 2: Register with weak password - should fail
        weak_passwords = [
            "weak",  # Too short
            "weakpassword",  # No uppercase, digit, special
            "WeakPassword",  # No digit, special
            "WeakPassword123",  # No special character
        ]
        
        for i, weak_password in enumerate(weak_passwords):
            try:
                weak_user_data = {
                    "email": f"weaktest{i}@realum.io",
                    "username": f"weaktest{i}",
                    "password": weak_password,
                    "role": "citizen"
                }
                response = self.make_request("POST", "/auth/register", weak_user_data)
                if response.status_code == 400:
                    error_data = response.json()
                    if "Password requirements not met" in str(error_data):
                        self.log_result("password_complexity", f"Reject weak password '{weak_password}'", True)
                    else:
                        self.log_result("password_complexity", f"Reject weak password '{weak_password}'", False, 
                                      "Wrong error message")
                else:
                    self.log_result("password_complexity", f"Reject weak password '{weak_password}'", False, 
                                  f"Expected 400, got {response.status_code}")
            except Exception as e:
                self.log_result("password_complexity", f"Reject weak password '{weak_password}'", False, str(e))

        # Test 3: Register with strong password - should succeed
        try:
            response = self.make_request("POST", "/auth/register", self.test_user_data)
            if response.status_code == 200:
                result = response.json()
                if "access_token" in result and "user" in result:
                    self.auth_token = result["access_token"]
                    self.log_result("password_complexity", "Accept strong password", True, 
                                  "User registered successfully")
                else:
                    self.log_result("password_complexity", "Accept strong password", False, 
                                  "Missing token or user in response")
            else:
                self.log_result("password_complexity", "Accept strong password", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("password_complexity", "Accept strong password", False, str(e))

    def test_2fa_authentication(self):
        """Test Two-Factor Authentication (M124-128)"""
        print("\n=== Testing Two-Factor Authentication ===")
        
        if not self.auth_token:
            self.log_result("2fa", "All 2FA tests", False, "No auth token available")
            return

        # Test 1: Enable 2FA
        try:
            response = self.make_request("POST", "/security/2fa/enable")
            if response.status_code == 200:
                result = response.json()
                expected_keys = ["secret", "qr_code", "backup_codes", "message"]
                if all(key in result for key in expected_keys):
                    self.totp_secret = result["secret"]
                    self.backup_codes = result["backup_codes"]
                    self.log_result("2fa", "Enable 2FA", True, 
                                  f"Secret generated, {len(result['backup_codes'])} backup codes")
                else:
                    self.log_result("2fa", "Enable 2FA", False, "Missing required fields")
            else:
                self.log_result("2fa", "Enable 2FA", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("2fa", "Enable 2FA", False, str(e))

        # Test 2: Get 2FA status
        try:
            response = self.make_request("GET", "/security/2fa/status")
            if response.status_code == 200:
                result = response.json()
                expected_keys = ["enabled", "backup_codes_remaining"]
                if all(key in result for key in expected_keys):
                    self.log_result("2fa", "Get 2FA status", True, 
                                  f"Enabled: {result['enabled']}, Backup codes: {result['backup_codes_remaining']}")
                else:
                    self.log_result("2fa", "Get 2FA status", False, "Missing required fields")
            else:
                self.log_result("2fa", "Get 2FA status", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("2fa", "Get 2FA status", False, str(e))

        # Test 3: Verify 2FA with invalid token (should fail)
        try:
            response = self.make_request("POST", "/security/2fa/verify", {"token": "000000"})
            if response.status_code == 400:
                self.log_result("2fa", "Reject invalid 2FA token", True)
            else:
                self.log_result("2fa", "Reject invalid 2FA token", False, 
                              f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.log_result("2fa", "Reject invalid 2FA token", False, str(e))

    def test_gdpr_compliance(self):
        """Test GDPR Compliance (M129-133)"""
        print("\n=== Testing GDPR Compliance ===")
        
        if not self.auth_token:
            self.log_result("gdpr", "All GDPR tests", False, "No auth token available")
            return

        # Test 1: Get consent status
        try:
            response = self.make_request("GET", "/security/gdpr/consent")
            if response.status_code == 200:
                self.log_result("gdpr", "Get consent status", True, "Consent data retrieved")
            else:
                self.log_result("gdpr", "Get consent status", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("gdpr", "Get consent status", False, str(e))

        # Test 2: Update consent
        try:
            consent_data = {"consent_type": "marketing_emails", "value": True}
            response = self.make_request("POST", "/security/gdpr/consent", consent_data)
            if response.status_code == 200:
                self.log_result("gdpr", "Update consent", True, "Marketing emails consent updated")
            else:
                self.log_result("gdpr", "Update consent", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("gdpr", "Update consent", False, str(e))

        # Test 3: Get retention policy
        try:
            response = self.make_request("GET", "/security/gdpr/retention-policy")
            if response.status_code == 200:
                self.log_result("gdpr", "Get retention policy", True, "Retention policy retrieved")
            else:
                self.log_result("gdpr", "Get retention policy", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("gdpr", "Get retention policy", False, str(e))

        # Test 4: Export user data
        try:
            response = self.make_request("GET", "/security/gdpr/export", {"format": "json"})
            if response.status_code == 200:
                result = response.json()
                if "data" in result and "exported_at" in result:
                    self.log_result("gdpr", "Export user data", True, "Data export successful")
                else:
                    self.log_result("gdpr", "Export user data", False, "Missing required fields")
            else:
                self.log_result("gdpr", "Export user data", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("gdpr", "Export user data", False, str(e))

        # Test 5: Schedule deletion
        try:
            deletion_data = {"days_from_now": 30}
            response = self.make_request("POST", "/security/gdpr/schedule-deletion", deletion_data)
            if response.status_code == 200:
                result = response.json()
                if "scheduled_for" in result:
                    self.log_result("gdpr", "Schedule deletion", True, f"Scheduled for: {result['scheduled_for']}")
                else:
                    self.log_result("gdpr", "Schedule deletion", False, "Missing scheduled_for field")
            else:
                self.log_result("gdpr", "Schedule deletion", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("gdpr", "Schedule deletion", False, str(e))

    def test_rate_limiting(self):
        """Test Rate Limiting (M134-138)"""
        print("\n=== Testing Rate Limiting ===")
        
        # Test rapid requests to password requirements endpoint
        rate_limit_hit = False
        successful_requests = 0
        
        print("Making 25 rapid requests to test rate limiting...")
        for i in range(25):
            try:
                response = self.make_request("GET", "/auth/password-requirements")
                if response.status_code == 200:
                    successful_requests += 1
                elif response.status_code == 429:
                    rate_limit_hit = True
                    self.log_result("rate_limiting", "Rate limit enforcement", True, 
                                  f"Rate limit hit after {successful_requests} requests")
                    break
                time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                self.log_result("rate_limiting", "Rate limit test", False, str(e))
                break
        
        if not rate_limit_hit:
            self.log_result("rate_limiting", "Rate limit enforcement", False, 
                          f"No rate limit hit after {successful_requests} requests")

    def test_security_status(self):
        """Test Security Status endpoint"""
        print("\n=== Testing Security Status ===")
        
        if not self.auth_token:
            self.log_result("security_status", "Security status", False, "No auth token available")
            return

        try:
            response = self.make_request("GET", "/security/status")
            if response.status_code == 200:
                result = response.json()
                expected_keys = ["security_score", "max_score", "email_verified", "two_factor_enabled", "recommendations"]
                if all(key in result for key in expected_keys):
                    self.log_result("security_status", "Get security status", True, 
                                  f"Score: {result['security_score']}/{result['max_score']}")
                else:
                    self.log_result("security_status", "Get security status", False, "Missing required fields")
            else:
                self.log_result("security_status", "Get security status", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("security_status", "Get security status", False, str(e))

    def test_account_lockout(self):
        """Test Account Lockout after failed attempts"""
        print("\n=== Testing Account Lockout ===")
        
        # Create a test user for lockout testing
        lockout_user = {
            "email": "lockouttest@realum.io",
            "username": "lockouttest",
            "password": "Test123!@#",
            "role": "citizen"
        }
        
        try:
            # Register test user
            response = self.make_request("POST", "/auth/register", lockout_user)
            if response.status_code != 200:
                self.log_result("account_lockout", "Setup lockout test user", False, 
                              f"Registration failed: {response.status_code}")
                return
        except Exception as e:
            self.log_result("account_lockout", "Setup lockout test user", False, str(e))
            return

        # Try 6 failed login attempts
        lockout_triggered = False
        for attempt in range(6):
            try:
                wrong_credentials = {
                    "email": lockout_user["email"],
                    "password": "WrongPassword123!"
                }
                response = self.make_request("POST", "/auth/login", wrong_credentials)
                
                if response.status_code == 423:  # Account locked
                    lockout_triggered = True
                    self.log_result("account_lockout", "Account lockout after failed attempts", True, 
                                  f"Account locked after {attempt + 1} attempts")
                    break
                elif response.status_code == 400:
                    # Expected for wrong credentials
                    continue
                else:
                    self.log_result("account_lockout", f"Failed login attempt {attempt + 1}", False, 
                                  f"Unexpected status: {response.status_code}")
                    
            except Exception as e:
                self.log_result("account_lockout", f"Failed login attempt {attempt + 1}", False, str(e))
        
        if not lockout_triggered:
            self.log_result("account_lockout", "Account lockout after failed attempts", False, 
                          "Account was not locked after 6 failed attempts")

    def test_monitoring_endpoints(self):
        """Test Monitoring endpoints"""
        print("\n=== Testing Monitoring Endpoints ===")
        
        # Test health endpoint
        try:
            response = self.make_request("GET", "/monitoring/health")
            if response.status_code == 200:
                result = response.json()
                if "status" in result and result["status"] == "healthy":
                    self.log_result("monitoring", "Health check", True, "Service is healthy")
                else:
                    self.log_result("monitoring", "Health check", False, "Unhealthy status")
            else:
                self.log_result("monitoring", "Health check", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("monitoring", "Health check", False, str(e))

    def test_password_change(self):
        """Test Password Change functionality"""
        print("\n=== Testing Password Change ===")
        
        if not self.auth_token:
            self.log_result("password_change", "Password change", False, "No auth token available")
            return

        # Test password change with valid data
        try:
            password_data = {
                "current_password": self.test_user_data["password"],
                "new_password": "NewTest123!@#"
            }
            response = self.make_request("POST", "/auth/change-password", password_data)
            if response.status_code == 200:
                self.log_result("password_change", "Change password", True, "Password changed successfully")
            else:
                self.log_result("password_change", "Change password", False, 
                              f"Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            self.log_result("password_change", "Change password", False, str(e))

        # Test forgot password
        try:
            reset_data = {"email": self.test_user_data["email"]}
            response = self.make_request("POST", "/auth/forgot-password", reset_data)
            if response.status_code == 200:
                self.log_result("password_change", "Forgot password", True, "Reset token generated")
            else:
                self.log_result("password_change", "Forgot password", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_result("password_change", "Forgot password", False, str(e))

    def run_all_tests(self):
        """Run all security tests"""
        print(f"Starting REALUM Security Testing Suite")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        print("=" * 60)
        
        # Run all test suites
        self.test_password_complexity()
        self.test_2fa_authentication()
        self.test_gdpr_compliance()
        self.test_rate_limiting()
        self.test_security_status()
        self.test_account_lockout()
        self.test_monitoring_endpoints()
        self.test_password_change()
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            status = "✅ PASS" if failed == 0 else "❌ FAIL"
            print(f"{status} {category.replace('_', ' ').title()}: {passed} passed, {failed} failed")
            
            # Print errors if any
            if results["errors"]:
                for error in results["errors"]:
                    print(f"    ❌ {error}")
        
        print("-" * 60)
        print(f"OVERALL: {total_passed} passed, {total_failed} failed")
        
        if total_failed == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"⚠️  {total_failed} TESTS FAILED - Review errors above")
        
        return total_failed == 0

if __name__ == "__main__":
    tester = SecurityTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)