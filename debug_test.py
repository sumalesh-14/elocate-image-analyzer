"""Quick debug test to check what's failing"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_gemini():
    """Test Gemini API connection"""
    try:
        print("Loading environment variables...")
        from app.config import settings
        print(f"API Key configured: {bool(settings.GEMINI_API_KEY)}")
        print(f"API Key (first 10 chars): {settings.GEMINI_API_KEY[:10] if settings.GEMINI_API_KEY else 'None'}...")
        
        print("\nInitializing Gemini service...")
        from app.services.gemini_service import gemini_service
        print("Gemini service initialized")
        
        print("\nTesting Gemini API connection with direct call...")
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Try a direct synchronous call
        print("Making test API call...")
        response = model.generate_content("Say hello")
        print(f"Response: {response.text}")
        print("\n✅ Direct API call successful!")
        
        print("\nTesting through service...")
        is_available = await gemini_service.check_availability()
        print(f"Gemini API available: {is_available}")
        return is_available
    except Exception as e:
        print(f"Error testing Gemini API: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_analyzer():
    """Test analyzer with a sample file"""
    try:
        from app.services.analyzer import analyzer_service
        print("\nTesting analyzer service...")
        
        # Create a mock UploadFile
        from fastapi import UploadFile
        from io import BytesIO
        
        # You'll need to provide an actual image file path
        test_image = Path(__file__).parent / "test_image.jpg"
        if not test_image.exists():
            print(f"Test image not found at {test_image}")
            print("Please provide a test image to continue")
            return False
        
        with open(test_image, "rb") as f:
            content = f.read()
        
        file = UploadFile(
            filename="test.jpg",
            file=BytesIO(content)
        )
        
        result = await analyzer_service.analyze_device(file)
        print(f"Analysis result: {result}")
        return True
        
    except Exception as e:
        print(f"Error testing analyzer: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=== Debug Test ===\n")
    
    # Test Gemini API
    gemini_ok = await test_gemini()
    
    if not gemini_ok:
        print("\n❌ Gemini API test failed")
        return
    
    print("\n✅ Gemini API test passed")
    
    # Test analyzer (optional, needs test image)
    # await test_analyzer()

if __name__ == "__main__":
    asyncio.run(main())
