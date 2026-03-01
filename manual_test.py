"""
Manual integration testing script for the Image Device Identification Service.
This script tests various scenarios including:
- Valid device images (simulated)
- Non-device images
- Various file formats (JPEG, PNG, WebP)
- Oversized files
- Malformed files
"""

import io
import requests
from PIL import Image, ImageDraw, ImageFont
import os

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk"

def create_test_image(format_type="JPEG", size=(800, 600), text="Test Device", color="white"):
    """Create a test image with text"""
    img = Image.new('RGB', size, color=color)
    draw = ImageDraw.Draw(img)
    
    # Add text to simulate device label
    try:
        # Try to use a default font
        draw.text((size[0]//4, size[1]//2), text, fill="black")
    except:
        # If font fails, just create colored image
        pass
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format_type)
    img_bytes.seek(0)
    return img_bytes

def create_oversized_image():
    """Create an image larger than 10MB"""
    # Create a very large image
    img = Image.new('RGB', (5000, 5000), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

def create_malformed_file():
    """Create a malformed file (text file with .jpg extension)"""
    return io.BytesIO(b"This is not an image file")

def test_api_endpoint(file_data, filename, description):
    """Test the API with a given file"""
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"File: {filename}")
    print(f"{'='*60}")
    
    try:
        files = {'file': (filename, file_data, 'image/jpeg')}
        headers = {'X-API-Key': API_KEY}
        
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze",
            files=files,
            headers=headers,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        
        try:
            json_response = response.json()
            import json
            print(json.dumps(json_response, indent=2))
            
            # Validate response structure
            if response.status_code == 200:
                assert 'success' in json_response, "Missing 'success' field"
                assert 'timestamp' in json_response, "Missing 'timestamp' field"
                assert 'processingTimeMs' in json_response, "Missing 'processingTimeMs' field"
                
                if json_response['success']:
                    assert 'data' in json_response, "Missing 'data' field"
                    data = json_response['data']
                    assert 'category' in data, "Missing 'category' field"
                    assert 'confidenceScore' in data, "Missing 'confidenceScore' field"
                    assert 0.0 <= data['confidenceScore'] <= 1.0, "Invalid confidence score"
                    print("✓ Response structure is valid")
                else:
                    assert 'error' in json_response, "Missing 'error' field"
                    print("✓ Error response structure is valid")
        except ValueError:
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except AssertionError as e:
        print(f"✗ Validation failed: {e}")

def main():
    """Run all manual integration tests"""
    print("="*60)
    print("Image Device Identification Service - Manual Integration Tests")
    print("="*60)
    
    # Test 1: Valid JPEG image (simulated mobile device)
    test_api_endpoint(
        create_test_image("JPEG", text="Samsung Galaxy S21"),
        "mobile_device.jpg",
        "Valid JPEG - Simulated Mobile Device"
    )
    
    # Test 2: Valid PNG image (simulated laptop)
    test_api_endpoint(
        create_test_image("PNG", text="MacBook Pro", color="silver"),
        "laptop_device.png",
        "Valid PNG - Simulated Laptop"
    )
    
    # Test 3: Valid WebP image (simulated charger)
    test_api_endpoint(
        create_test_image("WEBP", text="USB Charger", color="white"),
        "charger_device.webp",
        "Valid WebP - Simulated Charger"
    )
    
    # Test 4: Non-device image (random colored image)
    test_api_endpoint(
        create_test_image("JPEG", text="Random Image", color="green"),
        "non_device.jpg",
        "Non-Device Image"
    )
    
    # Test 5: Oversized file (>10MB)
    print("\n" + "="*60)
    print("Test: Oversized File (>10MB)")
    print("="*60)
    oversized = create_oversized_image()
    size_mb = len(oversized.getvalue()) / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")
    if size_mb > 10:
        test_api_endpoint(
            oversized,
            "oversized.png",
            "Oversized File (>10MB)"
        )
    else:
        print("Note: Generated file is not large enough, skipping test")
    
    # Test 6: Malformed file
    test_api_endpoint(
        create_malformed_file(),
        "malformed.jpg",
        "Malformed File (text file with .jpg extension)"
    )
    
    # Test 7: Missing file
    print("\n" + "="*60)
    print("Test: Missing File Parameter")
    print("="*60)
    try:
        headers = {'X-API-Key': API_KEY}
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze",
            headers=headers,
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        import json
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 8: Invalid API key
    print("\n" + "="*60)
    print("Test: Invalid API Key")
    print("="*60)
    try:
        files = {'file': ('test.jpg', create_test_image("JPEG"), 'image/jpeg')}
        headers = {'X-API-Key': 'invalid_key'}
        response = requests.post(
            f"{BASE_URL}/api/v1/analyze",
            files=files,
            headers=headers,
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        import json
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n" + "="*60)
    print("Manual Integration Tests Complete")
    print("="*60)

if __name__ == "__main__":
    main()
