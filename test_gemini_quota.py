"""
Test script to check Gemini API key status and quota.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"{YELLOW}ℹ {text}{RESET}")


def check_api_key_exists():
    """Check if API key is set in environment."""
    api_key = os.getenv('GEMINI_API_KEY', '')
    
    if not api_key:
        print_error("GEMINI_API_KEY not found in .env file")
        return None
    
    print_success("GEMINI_API_KEY found in .env file")
    print_info(f"Key starts with: {api_key[:20]}...")
    print_info(f"Key length: {len(api_key)} characters")
    
    return api_key


def test_api_connectivity(api_key: str):
    """Test if API key works by making a simple request."""
    try:
        import google.generativeai as genai
        
        print_info("Configuring Gemini API...")
        genai.configure(api_key=api_key)
        
        print_info("Creating model instance...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print_info("Testing API with simple request...")
        response = model.generate_content("Say 'API is working' in exactly 3 words")
        
        print_success("API request successful!")
        print_info(f"Response: {response.text.strip()}")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        
        if "API key expired" in error_msg or "API_KEY_INVALID" in error_msg:
            print_error("API key has EXPIRED")
            print_warning("You need to create a new API key")
            print_info("Get new key at: https://aistudio.google.com/app/apikey")
            
        elif "quota" in error_msg.lower() or "exhausted" in error_msg.lower():
            print_error("API quota exceeded")
            print_warning("You've hit your rate limit or daily quota")
            print_info("Check quota at: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas")
            
        elif "429" in error_msg or "Too Many Requests" in error_msg:
            print_error("Rate limit exceeded")
            print_warning("Too many requests in short time")
            print_info("Wait a few minutes and try again")
            
        elif "API key not valid" in error_msg:
            print_error("API key is invalid")
            print_warning("The API key format is incorrect or doesn't exist")
            print_info("Verify your API key at: https://aistudio.google.com/app/apikey")
            
        else:
            print_error(f"API request failed: {error_msg}")
        
        return False


def check_quota_info():
    """Display information about quota limits."""
    print_header("Gemini API Free Tier Limits")
    
    print("Model: gemini-1.5-flash (used by this app)")
    print("")
    print("Free Tier Quotas:")
    print("  • Requests per minute (RPM): 15")
    print("  • Requests per day (RPD): 1,500")
    print("  • Tokens per minute (TPM): 1,000,000")
    print("")
    print("What this means for your app:")
    print("  • You can analyze ~15 images per minute")
    print("  • You can analyze ~1,500 images per day")
    print("  • Quota resets at midnight Pacific Time")
    print("")


def show_quota_check_urls():
    """Show URLs to check quota."""
    print_header("Where to Check Your Quota")
    
    print("1. API Keys & Status:")
    print("   https://aistudio.google.com/app/apikey")
    print("")
    print("2. Quota Limits:")
    print("   https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas")
    print("")
    print("3. Usage Metrics:")
    print("   https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/metrics")
    print("")
    print("4. Billing (for paid tier):")
    print("   https://console.cloud.google.com/billing")
    print("")


def show_next_steps(api_working: bool):
    """Show next steps based on test results."""
    print_header("Next Steps")
    
    if api_working:
        print_success("Your API key is working!")
        print("")
        print("You can now:")
        print("  1. Deploy your application")
        print("  2. Test image analysis locally")
        print("  3. Monitor usage in Google Cloud Console")
        print("")
        print("To test image analysis:")
        print("  • Visit: http://localhost:8000/test-ui")
        print("  • Or use: http://localhost:8000/docs")
        print("")
    else:
        print_error("Your API key is not working")
        print("")
        print("To fix this:")
        print("  1. Go to: https://aistudio.google.com/app/apikey")
        print("  2. Create a new API key (or check existing ones)")
        print("  3. Copy the new API key")
        print("  4. Update .env file:")
        print("     GEMINI_API_KEY=your-new-key-here")
        print("  5. Run this test again: python test_gemini_quota.py")
        print("")


def main():
    """Run all quota checks."""
    print(f"\n{BLUE}{'='*60}")
    print(f"  Gemini API Quota Checker")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{RESET}\n")
    
    # Check if API key exists
    print_header("Step 1: Check API Key")
    api_key = check_api_key_exists()
    
    if not api_key:
        print("")
        print_error("Cannot proceed without API key")
        print_info("Add GEMINI_API_KEY to your .env file")
        return 1
    
    print("")
    
    # Test API connectivity
    print_header("Step 2: Test API Connectivity")
    api_working = test_api_connectivity(api_key)
    
    print("")
    
    # Show quota information
    check_quota_info()
    
    # Show where to check quota
    show_quota_check_urls()
    
    # Show next steps
    show_next_steps(api_working)
    
    # Summary
    print_header("Summary")
    
    if api_working:
        print_success("API Status: WORKING ✓")
        print_info("Your Gemini API key is valid and working")
        print_info("You can proceed with deployment")
        return 0
    else:
        print_error("API Status: NOT WORKING ✗")
        print_warning("Fix the API key issue before deploying")
        print_info("Follow the steps above to get a new API key")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Test interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{RED}Unexpected error: {e}{RESET}")
        sys.exit(1)
