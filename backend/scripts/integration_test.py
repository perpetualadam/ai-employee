#!/usr/bin/env python3
"""
Integration test suite - full booking flow end-to-end.
Tests the complete user journey from registration to booking confirmation.

Usage:
    python scripts/integration_test.py
    python scripts/integration_test.py --api-url https://api.yourdomain.com --skip-cleanup
"""

import argparse
import sys
import uuid
from datetime import datetime, timedelta
import requests


class IntegrationTest:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1"
        self.token = None
        self.business_id = None
        self.customer_id = None
        self.appointment_id = None
        self.test_email = f"integration-test-{uuid.uuid4()}@example.com"
        
    def log(self, message: str, status: str = "INFO"):
        """Log test progress."""
        icons = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
        print(f"{icons.get(status, '')} [{status}] {message}")

    def assert_status(self, response, expected: int, message: str):
        """Assert response status code."""
        if response.status_code == expected:
            self.log(f"{message} - Status {response.status_code}", "PASS")
            return True
        else:
            self.log(f"{message} - Expected {expected}, got {response.status_code}", "FAIL")
            self.log(f"Response: {response.text}", "FAIL")
            return False

    def test_1_register_user(self) -> bool:
        """Test 1: Register new user account."""
        self.log("Test 1: Registering new user...")
        
        response = requests.post(f"{self.api_url}/auth/register", json={
            "email": self.test_email,
            "password": "TestPassword123!",
            "full_name": "Integration Test User"
        }, timeout=10)
        
        if not self.assert_status(response, 201, "User registration"):
            return False
        
        data = response.json()
        self.token = data.get("access_token")
        if not self.token:
            self.log("No access token in response", "FAIL")
            return False
        
        self.log(f"Registered user: {self.test_email}", "PASS")
        return True

    def test_2_get_user_profile(self) -> bool:
        """Test 2: Get user profile."""
        self.log("Test 2: Getting user profile...")
        
        response = requests.get(f"{self.api_url}/auth/me",
                               headers={"Authorization": f"Bearer {self.token}"},
                               timeout=5)
        
        if not self.assert_status(response, 200, "Get user profile"):
            return False
        
        data = response.json()
        self.log(f"User profile: {data.get('email')}", "PASS")
        return True

    def test_3_get_business_profile(self) -> bool:
        """Test 3: Get business profile (created automatically on registration)."""
        self.log("Test 3: Getting business profile...")
        
        response = requests.get(f"{self.api_url}/business",
                               headers={"Authorization": f"Bearer {self.token}"},
                               timeout=5)
        
        if not self.assert_status(response, 200, "Get business profile"):
            return False
        
        data = response.json()
        self.business_id = data.get("id")
        self.log(f"Business: {data.get('name')} (ID: {self.business_id[:8]}...)", "PASS")
        return True

    def test_4_update_business(self) -> bool:
        """Test 4: Update business settings."""
        self.log("Test 4: Updating business settings...")
        
        response = requests.patch(f"{self.api_url}/business", json={
            "name": "Integration Test Plumbing",
            "industry": "plumbing",
            "timezone": "America/New_York",
            "working_hours": {
                "monday": {"open": "08:00", "close": "17:00"},
                "tuesday": {"open": "08:00", "close": "17:00"},
                "wednesday": {"open": "08:00", "close": "17:00"},
                "thursday": {"open": "08:00", "close": "17:00"},
                "friday": {"open": "08:00", "close": "17:00"}
            }
        }, headers={"Authorization": f"Bearer {self.token}"}, timeout=10)
        
        if not self.assert_status(response, 200, "Update business"):
            return False
        
        data = response.json()
        self.log(f"Business updated: {data.get('name')}", "PASS")
        return True

    def test_5_create_customer(self) -> bool:
        """Test 5: Create customer in CRM."""
        self.log("Test 5: Creating customer...")
        
        response = requests.post(f"{self.api_url}/customers", json={
            "name": "John Smith",
            "phone": "+15555551234",
            "email": "john.smith@example.com",
            "address": "123 Main St, New York, NY 10001"
        }, headers={"Authorization": f"Bearer {self.token}"}, timeout=10)
        
        if not self.assert_status(response, 201, "Create customer"):
            return False
        
        data = response.json()
        self.customer_id = data.get("id")
        self.log(f"Customer created: {data.get('name')} (ID: {self.customer_id[:8]}...)", "PASS")
        return True

    def test_6_check_availability(self) -> bool:
        """Test 6: Check calendar availability."""
        self.log("Test 6: Checking appointment availability...")
        
        # Check tomorrow's availability
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = requests.get(f"{self.api_url}/appointments/availability?date={tomorrow}",
                               headers={"Authorization": f"Bearer {self.token}"},
                               timeout=5)
        
        if not self.assert_status(response, 200, "Check availability"):
            return False
        
        data = response.json()
        slots = data.get("slots", [])
        self.log(f"Found {len(slots)} available slots for {tomorrow}", "PASS")
        return len(slots) > 0

    def test_7_book_appointment(self) -> bool:
        """Test 7: Book an appointment."""
        self.log("Test 7: Booking appointment...")
        
        if not self.customer_id:
            self.log("No customer_id available", "FAIL")
            return False
        
        # Book tomorrow at 9 AM
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        response = requests.post(f"{self.api_url}/appointments", json={
            "customer_id": self.customer_id,
            "service_type": "Drain cleaning",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "notes": "Integration test appointment"
        }, headers={"Authorization": f"Bearer {self.token}"}, timeout=10)
        
        if not self.assert_status(response, 201, "Book appointment"):
            return False
        
        data = response.json()
        self.appointment_id = data.get("id")
        self.log(f"Appointment booked: {data.get('service_type')} at {data.get('start_time')}", "PASS")
        return True

    def test_8_list_appointments(self) -> bool:
        """Test 8: List appointments."""
        self.log("Test 8: Listing appointments...")
        
        response = requests.get(f"{self.api_url}/appointments",
                               headers={"Authorization": f"Bearer {self.token}"},
                               timeout=5)
        
        if not self.assert_status(response, 200, "List appointments"):
            return False
        
        # Note: Endpoint might not be paginated yet, check both formats
        data = response.json()
        if isinstance(data, dict) and "items" in data:
            appointments = data.get("items", [])
        else:
            appointments = data
        
        self.log(f"Found {len(appointments)} appointment(s)", "PASS")
        return True

    def test_9_cleanup(self) -> bool:
        """Test 9: Cleanup - cancel test appointment."""
        self.log("Test 9: Cleaning up test data...")
        
        if not self.appointment_id:
            self.log("No appointment to cleanup", "WARN")
            return True
        
        response = requests.post(f"{self.api_url}/appointments/{self.appointment_id}/cancel",
                                headers={"Authorization": f"Bearer {self.token}"},
                                timeout=5)
        
        if response.status_code in [200, 404]:
            self.log("Test appointment cancelled", "PASS")
            return True
        else:
            self.log(f"Cleanup failed: Status {response.status_code}", "WARN")
            return True  # Don't fail the test suite on cleanup

    def run_all_tests(self, skip_cleanup: bool = False) -> bool:
        """Run all integration tests in sequence."""
        tests = [
            self.test_1_register_user,
            self.test_2_get_user_profile,
            self.test_3_get_business_profile,
            self.test_4_update_business,
            self.test_5_create_customer,
            self.test_6_check_availability,
            self.test_7_book_appointment,
            self.test_8_list_appointments,
        ]
        
        if not skip_cleanup:
            tests.append(self.test_9_cleanup)
        
        print(f"\n{'='*60}")
        print("🧪 Running Integration Tests")
        print(f"{'='*60}\n")
        
        for test in tests:
            if not test():
                self.log(f"Test suite failed at: {test.__name__}", "FAIL")
                return False
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Run integration tests")
    parser.add_argument("--api-url", default="http://localhost:8000",
                       help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--skip-cleanup", action="store_true",
                       help="Skip cleanup of test data")
    args = parser.parse_args()
    
    test_suite = IntegrationTest(args.api_url)
    success = test_suite.run_all_tests(args.skip_cleanup)
    
    print(f"\n{'='*60}")
    if success:
        print("✅ ALL INTEGRATION TESTS PASSED")
        print(f"{'='*60}\n")
        sys.exit(0)
    else:
        print("❌ INTEGRATION TESTS FAILED")
        print(f"{'='*60}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
