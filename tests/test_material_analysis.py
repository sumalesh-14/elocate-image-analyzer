"""
Simple test script for the material analysis endpoint.
Run this after starting the server to test the new endpoint.
"""

import requests
import json

# API endpoint
BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/api/v1/analyze-materials"

# Sample request data
sample_request = {
    "brand_id": "BR001",
    "brand_name": "Samsung",
    "category_id": "CAT001",
    "category_name": "Smartphone",
    "model_id": "MOD001",
    "model_name": "Galaxy S21",
    "country": "India",
    "description": "Material recovery estimation from the device based on internal components."
}

def test_material_analysis():
    """Test the material analysis endpoint."""
    print("Testing Material Analysis Endpoint")
    print("=" * 50)
    print(f"\nRequest URL: {ENDPOINT}")
    print(f"\nRequest Data:")
    print(json.dumps(sample_request, indent=2))
    
    try:
        # Make the request
        response = requests.post(
            ENDPOINT,
            json=sample_request,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": "XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk"
            }
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"\nResponse Data:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n✓ Test passed!")
        else:
            print("\n✗ Test failed!")
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to server. Make sure the server is running.")
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    test_material_analysis()
