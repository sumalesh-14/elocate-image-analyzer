import os
from dotenv import load_dotenv
from google import genai

def test_keys():
    # Load environment variables
    load_dotenv()
    
    # Read the keys
    keys_str = os.getenv("GEMINI_API_KEYS")
    if not keys_str:
        print("❌ GEMINI_API_KEYS is not set in the .env file")
        return
        
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    print(f"Found {len(keys)} API keys in GEMINI_API_KEYS.")
    
    for i, key in enumerate(keys):
        masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
        
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents='Say "Hello"'
            )
            print(f"✅ Key #{i+1} ({masked_key}) is WORKING!")
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"❌ Key #{i+1} ({masked_key}) FAILED! Reason: Rate Limit (429)")
            elif "400" in error_str or "API_KEY_INVALID" in error_str:
                print(f"❌ Key #{i+1} ({masked_key}) FAILED! Reason: Invalid Key (400)")
            else:
                print(f"❌ Key #{i+1} ({masked_key}) FAILED! Reason: Other Error")

if __name__ == "__main__":
    test_keys()
