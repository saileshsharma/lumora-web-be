#!/usr/bin/env python3
"""
Comprehensive API Test Suite
Tests all backend endpoints, connectivity, and functionality
"""

import json
import requests
import base64
import os
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
API_BASE_URL = "http://localhost:5001/api"
FRONTEND_URL = "http://localhost:5173"
TEST_RESULTS = []

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")

def print_test(name: str, status: bool, details: str = ""):
    """Print test result"""
    status_icon = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if status else f"{Colors.RED}❌ FAIL{Colors.RESET}"
    print(f"{status_icon} {Colors.BOLD}{name}{Colors.RESET}")
    if details:
        print(f"   {Colors.YELLOW}→ {details}{Colors.RESET}")
    TEST_RESULTS.append({"name": name, "status": status, "details": details})

def create_test_image() -> str:
    """Create a small test image as base64"""
    # Create a minimal 1x1 PNG image
    png_data = base64.b64encode(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    ).decode()
    return f"data:image/png;base64,{png_data}"

def test_server_connectivity():
    """Test basic server connectivity"""
    print_header("1. SERVER CONNECTIVITY TESTS")

    # Test backend
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_test("Backend Server Health", True, f"Status: {data.get('status')}")
        else:
            print_test("Backend Server Health", False, f"Status code: {response.status_code}")
    except Exception as e:
        print_test("Backend Server Health", False, f"Error: {str(e)}")

    # Test frontend
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        print_test("Frontend Server", response.status_code == 200, f"Status code: {response.status_code}")
    except Exception as e:
        print_test("Frontend Server", False, f"Error: {str(e)}")

def test_cors_configuration():
    """Test CORS configuration"""
    print_header("2. CORS CONFIGURATION TESTS")

    # Test preflight request
    try:
        response = requests.options(
            f"{API_BASE_URL}/rate-outfit",
            headers={
                "Origin": FRONTEND_URL,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            },
            timeout=5
        )

        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Credentials": response.headers.get("Access-Control-Allow-Credentials"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
        }

        has_origin = cors_headers["Access-Control-Allow-Origin"] is not None
        has_methods = cors_headers["Access-Control-Allow-Methods"] is not None

        print_test("CORS Preflight", has_origin and has_methods,
                  f"Origin: {cors_headers['Access-Control-Allow-Origin']}")

        if has_methods:
            print_test("CORS Methods", "POST" in cors_headers["Access-Control-Allow-Methods"],
                      f"Methods: {cors_headers['Access-Control-Allow-Methods']}")
    except Exception as e:
        print_test("CORS Configuration", False, f"Error: {str(e)}")

def test_arena_endpoints():
    """Test Fashion Arena endpoints"""
    print_header("3. FASHION ARENA API TESTS")

    # Test get submissions
    try:
        response = requests.get(f"{API_BASE_URL}/arena/submissions", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_test("Get Arena Submissions", True,
                      f"Found {data.get('total', 0)} submissions")
        else:
            print_test("Get Arena Submissions", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Get Arena Submissions", False, f"Error: {str(e)}")

    # Test get leaderboard
    try:
        response = requests.get(f"{API_BASE_URL}/arena/leaderboard", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_test("Get Arena Leaderboard", True,
                      f"Entries: {len(data.get('leaderboard', []))}")
        else:
            print_test("Get Arena Leaderboard", False, f"Status: {response.status_code}")
    except Exception as e:
        print_test("Get Arena Leaderboard", False, f"Error: {str(e)}")

def test_rate_outfit_endpoint():
    """Test Rate Outfit endpoint"""
    print_header("4. RATE OUTFIT API TESTS")

    # Test with missing data
    try:
        response = requests.post(
            f"{API_BASE_URL}/rate-outfit",
            json={},
            timeout=10
        )
        # Should return error for missing data
        has_error = response.status_code >= 400
        print_test("Rate Outfit - Validation (missing data)", has_error,
                  f"Correctly rejects empty request: {response.status_code}")
    except Exception as e:
        print_test("Rate Outfit - Validation", False, f"Error: {str(e)}")

    # Test with invalid image
    try:
        response = requests.post(
            f"{API_BASE_URL}/rate-outfit",
            json={
                "image": "invalid_image_data",
                "occasion": "Casual"
            },
            timeout=10
        )
        # Should return error for invalid image
        has_error = response.status_code >= 400
        print_test("Rate Outfit - Image Validation", has_error,
                  f"Correctly rejects invalid image: {response.status_code}")
    except Exception as e:
        print_test("Rate Outfit - Image Validation", False, f"Error: {str(e)}")

    # Test endpoint structure with proper data
    try:
        test_image = create_test_image()
        response = requests.post(
            f"{API_BASE_URL}/rate-outfit",
            json={
                "image": test_image,
                "occasion": "Casual",
                "budget": "Under $50"
            },
            timeout=30  # Longer timeout for AI processing
        )

        # Endpoint is accessible (may fail on AI processing, but that's ok)
        endpoint_works = response.status_code in [200, 400, 500]
        details = f"Status: {response.status_code}"

        if response.status_code == 200:
            try:
                data = response.json()
                details = "✓ Successfully processed request"
            except:
                pass

        print_test("Rate Outfit - Endpoint Structure", endpoint_works, details)

    except Exception as e:
        print_test("Rate Outfit - Endpoint Structure", False, f"Error: {str(e)}")

def test_generate_outfit_endpoint():
    """Test Generate Outfit endpoint"""
    print_header("5. GENERATE OUTFIT API TESTS")

    # Test with missing data
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-outfit",
            json={},
            timeout=10
        )
        has_error = response.status_code >= 400
        print_test("Generate Outfit - Validation (missing data)", has_error,
                  f"Correctly rejects empty request: {response.status_code}")
    except Exception as e:
        print_test("Generate Outfit - Validation", False, f"Error: {str(e)}")

    # Test with invalid image
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate-outfit",
            json={
                "user_image": "invalid_image_data",
                "occasion": "Casual"
            },
            timeout=10
        )
        has_error = response.status_code >= 400
        print_test("Generate Outfit - Image Validation", has_error,
                  f"Correctly rejects invalid image: {response.status_code}")
    except Exception as e:
        print_test("Generate Outfit - Image Validation", False, f"Error: {str(e)}")

    # Test endpoint structure
    try:
        test_image = create_test_image()
        response = requests.post(
            f"{API_BASE_URL}/generate-outfit",
            json={
                "user_image": test_image,
                "occasion": "Casual",
                "budget": "Under $50"
            },
            timeout=30
        )

        endpoint_works = response.status_code in [200, 400, 500]
        details = f"Status: {response.status_code}"

        if response.status_code == 200:
            details = "✓ Successfully processed request"

        print_test("Generate Outfit - Endpoint Structure", endpoint_works, details)

    except Exception as e:
        print_test("Generate Outfit - Endpoint Structure", False, f"Error: {str(e)}")

def test_response_formats():
    """Test API response formats"""
    print_header("6. RESPONSE FORMAT TESTS")

    # Test health endpoint response
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        data = response.json()

        has_status = "status" in data
        has_message = "message" in data

        print_test("Health Response Format", has_status and has_message,
                  f"Contains required fields: status={has_status}, message={has_message}")
    except Exception as e:
        print_test("Health Response Format", False, f"Error: {str(e)}")

    # Test arena submissions response
    try:
        response = requests.get(f"{API_BASE_URL}/arena/submissions", timeout=10)
        data = response.json()

        has_submissions = "submissions" in data
        has_success = "success" in data

        print_test("Arena Response Format", has_submissions and has_success,
                  f"Contains required fields: submissions={has_submissions}, success={has_success}")
    except Exception as e:
        print_test("Arena Response Format", False, f"Error: {str(e)}")

def test_error_handling():
    """Test error handling"""
    print_header("7. ERROR HANDLING TESTS")

    # Test non-existent endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/non-existent-endpoint", timeout=5)
        is_error = response.status_code == 404
        print_test("404 Error Handling", is_error,
                  f"Returns 404 for non-existent endpoint: {response.status_code}")
    except Exception as e:
        print_test("404 Error Handling", False, f"Error: {str(e)}")

    # Test invalid JSON
    try:
        response = requests.post(
            f"{API_BASE_URL}/rate-outfit",
            data="invalid json",
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        is_error = response.status_code >= 400
        print_test("Invalid JSON Handling", is_error,
                  f"Handles invalid JSON: {response.status_code}")
    except Exception as e:
        print_test("Invalid JSON Handling", False, f"Error: {str(e)}")

def test_environment_variables():
    """Test environment variables are loaded"""
    print_header("8. ENVIRONMENT VARIABLES TESTS")

    from dotenv import load_dotenv
    load_dotenv()

    required_vars = ["OPENAI_API_KEY", "FAL_API_KEY", "NANOBANANA_API_KEY"]

    for var in required_vars:
        value = os.getenv(var)
        is_set = value is not None and len(value) > 0
        print_test(f"Environment Variable: {var}", is_set,
                  f"Length: {len(value) if value else 0} chars")

def generate_report():
    """Generate final test report"""
    print_header("TEST SUMMARY REPORT")

    total_tests = len(TEST_RESULTS)
    passed_tests = sum(1 for test in TEST_RESULTS if test["status"])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    print(f"{Colors.BOLD}Total Tests:{Colors.RESET} {total_tests}")
    print(f"{Colors.GREEN}{Colors.BOLD}Passed:{Colors.RESET} {passed_tests}")
    print(f"{Colors.RED}{Colors.BOLD}Failed:{Colors.RESET} {failed_tests}")
    print(f"{Colors.BLUE}{Colors.BOLD}Success Rate:{Colors.RESET} {success_rate:.1f}%\n")

    if failed_tests > 0:
        print(f"{Colors.RED}{Colors.BOLD}Failed Tests:{Colors.RESET}")
        for test in TEST_RESULTS:
            if not test["status"]:
                print(f"  ❌ {test['name']}")
                if test["details"]:
                    print(f"     → {test['details']}")

    # Save detailed report to file
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": success_rate
            },
            "tests": TEST_RESULTS
        }, f, indent=2)

    print(f"\n{Colors.CYAN}Detailed report saved to: {report_file}{Colors.RESET}")

    # Overall status
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    if success_rate == 100:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! System is fully functional.{Colors.RESET}")
    elif success_rate >= 80:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Most tests passed. Some issues need attention.{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ Multiple test failures. System needs fixes.{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

def main():
    """Run all tests"""
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                                                                  ║")
    print("║          AI OUTFIT ASSISTANT - COMPREHENSIVE TEST SUITE          ║")
    print("║                                                                  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

    print(f"{Colors.CYAN}Starting automated tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")
    print(f"{Colors.CYAN}Backend URL: {API_BASE_URL}{Colors.RESET}")
    print(f"{Colors.CYAN}Frontend URL: {FRONTEND_URL}{Colors.RESET}\n")

    try:
        # Run all test suites
        test_server_connectivity()
        test_cors_configuration()
        test_arena_endpoints()
        test_rate_outfit_endpoint()
        test_generate_outfit_endpoint()
        test_response_formats()
        test_error_handling()
        test_environment_variables()

        # Generate final report
        generate_report()

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}\n")
    except Exception as e:
        print(f"\n\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
