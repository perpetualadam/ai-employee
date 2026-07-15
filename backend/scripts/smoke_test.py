#!/usr/bin/env python3
"""
Smoke test suite - quick health checks for critical functionality.
Run before deployment to verify core features work.

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --api-url https://api.yourdomain.com
"""

import argparse
import sys
import requests
from typing import Any


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'


def print_test(name: str, passed: bool, message: str = ""):
    """Print test result with color coding."""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"  {status} {name}")
    if message:
        print(f"        {message}")


def test_health_endpoints(base_url: str) -> bool:
    """Test health check endpoints."""
    print("\n🏥 Health Check Tests")
    all_passed = True

    # Test /health/live
    try:
        response = requests.get(f"{base_url}/health/live", timeout=5)
        passed = response.status_code == 200 and response.json().get("status") == "ok"
        print_test("Health live endpoint", passed)
        all_passed &= passed
    except Exception as e:
        print_test("Health live endpoint", False, str(e))
        all_passed = False

    # Test /health/ready
    try:
        response = requests.get(f"{base_url}/health/ready", timeout=5)
        passed = response.status_code == 200
        data = response.json()
        db_ok = data.get("database", {}).get("ok", False)
        print_test("Health ready endpoint", passed and db_ok, 
                   f"DB status: {data.get('database', {}).get('status')}")
        all_passed &= passed and db_ok
    except Exception as e:
        print_test("Health ready endpoint", False, str(e))
        all_passed = False

    # Test /health (full status)
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        passed = response.status_code == 200
        data = response.json()
        print_test("Health status endpoint", passed,
                   f"AI: {data.get('providers', {}).get('ai')}, "
                   f"Voice: {data.get('providers', {}).get('voice')}")
        all_passed &= passed
    except Exception as e:
        print_test("Health status endpoint", False, str(e))
        all_passed = False

    return all_passed


def test_authentication(base_url: str) -> tuple[bool, str | None]:
    """Test authentication endpoints."""
    print("\n🔐 Authentication Tests")
    all_passed = True
    token = None

    # Test registration
    try:
        import uuid
        email = f"test-{uuid.uuid4()}@example.com"
        response = requests.post(f"{base_url}/api/v1/auth/register", json={
            "email": email,
            "password": "TestPassword123!",
            "full_name": "Test User"
        }, timeout=10)
        passed = response.status_code == 201
        if passed:
            token = response.json().get("access_token")
        print_test("User registration", passed)
        all_passed &= passed
    except Exception as e:
        print_test("User registration", False, str(e))
        all_passed = False

    # Test /me endpoint
    if token:
        try:
            response = requests.get(f"{base_url}/api/v1/auth/me",
                                   headers={"Authorization": f"Bearer {token}"},
                                   timeout=5)
            passed = response.status_code == 200
            data = response.json()
            print_test("Get current user", passed, f"User: {data.get('email')}")
            all_passed &= passed
        except Exception as e:
            print_test("Get current user", False, str(e))
            all_passed = False

    return all_passed, token


def test_rate_limiting(base_url: str) -> bool:
    """Test rate limiting on login endpoint."""
    print("\n🚦 Rate Limiting Tests")
    
    # Attempt to trigger rate limit on login
    try:
        rate_limited = False
        for i in range(10):
            response = requests.post(f"{base_url}/api/v1/auth/login", json={
                "email": "nonexistent@example.com",
                "password": "wrong"
            }, timeout=5)
            if response.status_code == 429:
                rate_limited = True
                break
        
        print_test("Login rate limiting", rate_limited,
                   "Rate limit triggered after multiple attempts" if rate_limited else "WARNING: No rate limit detected")
        return rate_limited
    except Exception as e:
        print_test("Login rate limiting", False, str(e))
        return False


def test_database(base_url: str, token: str) -> bool:
    """Test database operations."""
    print("\n💾 Database Tests")
    all_passed = True

    # Test customer creation
    try:
        response = requests.post(f"{base_url}/api/v1/customers", json={
            "name": "Smoke Test Customer",
            "phone": "+15555551234",
            "email": "smoke@test.com"
        }, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        passed = response.status_code == 201
        customer_id = response.json().get("id") if passed else None
        print_test("Create customer", passed)
        all_passed &= passed
    except Exception as e:
        print_test("Create customer", False, str(e))
        all_passed = False
        customer_id = None

    # Test customer list
    try:
        response = requests.get(f"{base_url}/api/v1/customers?page=1&page_size=10",
                               headers={"Authorization": f"Bearer {token}"},
                               timeout=5)
        passed = response.status_code == 200
        data = response.json()
        has_pagination = "items" in data and "total" in data
        print_test("List customers (paginated)", passed and has_pagination,
                   f"Found {data.get('total', 0)} customers")
        all_passed &= passed and has_pagination
    except Exception as e:
        print_test("List customers", False, str(e))
        all_passed = False

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Run smoke tests")
    parser.add_argument("--api-url", default="http://localhost:8000",
                       help="API base URL (default: http://localhost:8000)")
    args = parser.parse_args()

    base_url = args.api_url.rstrip('/')
    
    print(f"\n{'='*60}")
    print(f"🔬 AI Employee Smoke Tests")
    print(f"{'='*60}")
    print(f"Testing: {base_url}")

    all_tests_passed = True

    # Run test suites
    all_tests_passed &= test_health_endpoints(base_url)
    auth_passed, token = test_authentication(base_url)
    all_tests_passed &= auth_passed
    
    if token:
        all_tests_passed &= test_database(base_url, token)
    else:
        print(f"\n{Colors.YELLOW}⚠ Skipping database tests (no auth token){Colors.RESET}")

    # Rate limiting is optional
    test_rate_limiting(base_url)

    # Final summary
    print(f"\n{'='*60}")
    if all_tests_passed:
        print(f"{Colors.GREEN}✅ ALL CRITICAL TESTS PASSED{Colors.RESET}")
        sys.exit(0)
    else:
        print(f"{Colors.RED}❌ SOME TESTS FAILED{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
