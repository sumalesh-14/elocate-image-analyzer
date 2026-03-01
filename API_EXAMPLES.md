# API Examples and Testing

This document provides example API calls for testing the Image Device Identification Service.

## Table of Contents

1. [Health Check](#health-check)
2. [Image Analysis](#image-analysis)
3. [Error Scenarios](#error-scenarios)
4. [Integration Examples](#integration-examples)

## Prerequisites

Set environment variables for easier testing:

```bash
export API_URL="http://localhost:8000"  # or your deployed URL
export API_KEY="your_api_key_here"
```

## Health Check

### Basic Health Check

```bash
curl $API_URL/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "gemini_api_available": true
}
```

### Health Check with Verbose Output

```bash
curl -v $API_URL/health
```

## Image Analysis

### Analyze Device Image (JPEG)

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.jpg"
```

### Analyze Device Image (PNG)

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.png"
```

### Analyze Device Image (WebP)

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.webp"
```

### Save Response to File

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.jpg" \
  -o response.json
```

### Pretty Print Response

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.jpg" | jq .
```

**Expected Success Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:45.123Z",
  "processingTimeMs": 3456,
  "data": {
    "category": "mobile",
    "brand": "Samsung",
    "model": "Galaxy S21",
    "deviceType": "smartphone",
    "confidenceScore": 0.87,
    "attributes": {
      "color": "phantom gray",
      "condition": "good",
      "visiblePorts": "USB-C",
      "screenSize": "approximately 6.2 inches"
    },
    "lowConfidence": false
  },
  "error": null
}
```

**Expected Low Confidence Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:31:22.456Z",
  "processingTimeMs": 4123,
  "data": {
    "category": "charger",
    "brand": null,
    "model": null,
    "deviceType": "USB wall charger",
    "confidenceScore": 0.42,
    "attributes": {
      "color": "white",
      "connectorType": "USB-A",
      "condition": "used"
    },
    "lowConfidence": true
  },
  "error": null
}
```

## Error Scenarios

### Missing API Key

```bash
curl -X POST $API_URL/api/v1/analyze \
  -F "file=@/path/to/device-image.jpg"
```

**Expected Response:**
```json
{
  "success": false,
  "timestamp": "2024-01-15T10:32:10.789Z",
  "processingTimeMs": 5,
  "data": null,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

### Invalid API Key

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: invalid_key" \
  -F "file=@/path/to/device-image.jpg"
```

### Missing File

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY"
```

**Expected Response:**
```json
{
  "success": false,
  "timestamp": "2024-01-15T10:33:15.123Z",
  "processingTimeMs": 10,
  "data": null,
  "error": {
    "code": "MISSING_FILE",
    "message": "No image file provided"
  }
}
```

### Invalid File Type

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/document.pdf"
```

**Expected Response:**
```json
{
  "success": false,
  "timestamp": "2024-01-15T10:34:20.456Z",
  "processingTimeMs": 15,
  "data": null,
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "Please upload a valid image file (JPEG, PNG, or WebP)"
  }
}
```

### File Too Large

```bash
# Create a large file for testing (>10MB)
dd if=/dev/zero of=large-file.jpg bs=1M count=11

curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@large-file.jpg"
```

**Expected Response:**
```json
{
  "success": false,
  "timestamp": "2024-01-15T10:35:30.789Z",
  "processingTimeMs": 20,
  "data": null,
  "error": {
    "code": "INVALID_FILE_SIZE",
    "message": "File size exceeds 10MB limit"
  }
}
```

### Rate Limit Exceeded

```bash
# Send multiple requests rapidly
for i in {1..15}; do
  curl -X POST $API_URL/api/v1/analyze \
    -H "X-API-Key: $API_KEY" \
    -F "file=@/path/to/device-image.jpg" &
done
wait
```

**Expected Response (after limit):**
```json
{
  "success": false,
  "timestamp": "2024-01-15T10:36:45.123Z",
  "processingTimeMs": 5,
  "data": null,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded, please try again later"
  }
}
```

### CORS Preflight Request

```bash
curl -X OPTIONS $API_URL/api/v1/analyze \
  -H "Origin: https://your-frontend.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: X-API-Key" \
  -v
```

**Check for CORS headers in response:**
- `Access-Control-Allow-Origin`
- `Access-Control-Allow-Methods`
- `Access-Control-Allow-Headers`

## Integration Examples

### JavaScript/TypeScript (Fetch API)

```javascript
async function analyzeDeviceImage(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('https://your-service.com/api/v1/analyze', {
      method: 'POST',
      headers: {
        'X-API-Key': 'your_api_key',
      },
      body: formData,
    });

    const result = await response.json();

    if (result.success) {
      console.log('Device identified:', result.data);
      return result.data;
    } else {
      console.error('Analysis failed:', result.error);
      throw new Error(result.error.message);
    }
  } catch (error) {
    console.error('Request failed:', error);
    throw error;
  }
}

// Usage
const fileInput = document.querySelector('input[type="file"]');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (file) {
    const deviceData = await analyzeDeviceImage(file);
    console.log(deviceData);
  }
});
```

### Python (requests library)

```python
import requests

def analyze_device_image(image_path, api_url, api_key):
    """Analyze a device image using the API."""
    with open(image_path, 'rb') as f:
        files = {'file': f}
        headers = {'X-API-Key': api_key}
        
        response = requests.post(
            f'{api_url}/api/v1/analyze',
            headers=headers,
            files=files
        )
        
        result = response.json()
        
        if result['success']:
            print('Device identified:', result['data'])
            return result['data']
        else:
            print('Analysis failed:', result['error'])
            raise Exception(result['error']['message'])

# Usage
device_data = analyze_device_image(
    image_path='/path/to/device.jpg',
    api_url='https://your-service.com',
    api_key='your_api_key'
)
```

### Java (Spring Boot)

```java
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

public class ImageAnalyzerClient {
    
    private final RestTemplate restTemplate;
    private final String apiUrl;
    private final String apiKey;
    
    public ImageAnalyzerClient(String apiUrl, String apiKey) {
        this.restTemplate = new RestTemplate();
        this.apiUrl = apiUrl;
        this.apiKey = apiKey;
    }
    
    public DeviceData analyzeImage(String imagePath) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        headers.set("X-API-Key", apiKey);
        
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new FileSystemResource(imagePath));
        
        HttpEntity<MultiValueMap<String, Object>> requestEntity = 
            new HttpEntity<>(body, headers);
        
        ResponseEntity<AnalysisResponse> response = restTemplate.exchange(
            apiUrl + "/api/v1/analyze",
            HttpMethod.POST,
            requestEntity,
            AnalysisResponse.class
        );
        
        AnalysisResponse result = response.getBody();
        
        if (result.isSuccess()) {
            return result.getData();
        } else {
            throw new RuntimeException(result.getError().getMessage());
        }
    }
}
```

### cURL with Authentication and Error Handling

```bash
#!/bin/bash

# Configuration
API_URL="https://your-service.com"
API_KEY="your_api_key"
IMAGE_PATH="/path/to/device-image.jpg"

# Function to analyze image
analyze_image() {
    local image_path=$1
    
    echo "Analyzing image: $image_path"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/analyze" \
        -H "X-API-Key: $API_KEY" \
        -F "file=@$image_path")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ]; then
        echo "Success!"
        echo "$body" | jq .
    else
        echo "Error: HTTP $http_code"
        echo "$body" | jq .
    fi
}

# Run analysis
analyze_image "$IMAGE_PATH"
```

## Performance Testing

### Measure Response Time

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.jpg" \
  -w "\nTime: %{time_total}s\n" \
  -o /dev/null -s
```

### Concurrent Requests Test

```bash
#!/bin/bash

# Test with 5 concurrent requests
for i in {1..5}; do
  (
    time curl -X POST $API_URL/api/v1/analyze \
      -H "X-API-Key: $API_KEY" \
      -F "file=@/path/to/device-image.jpg" \
      -o "response_$i.json" -s
  ) &
done
wait

echo "All requests completed"
```

### Load Testing with Apache Bench

```bash
# Install Apache Bench (if not installed)
# Ubuntu/Debian: apt-get install apache2-utils
# macOS: brew install httpd

# Note: ab doesn't support multipart/form-data well
# Use for health endpoint testing instead
ab -n 100 -c 10 $API_URL/health
```

## Debugging

### Verbose Output

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.jpg" \
  -v
```

### Show Response Headers Only

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.jpg" \
  -I
```

### Trace Request

```bash
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/device-image.jpg" \
  --trace-ascii trace.txt
```

### Test with Different Image Sizes

```bash
# Small image (~100KB)
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@small-device.jpg"

# Medium image (~2MB)
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@medium-device.jpg"

# Large image (~8MB)
curl -X POST $API_URL/api/v1/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "file=@large-device.jpg"
```

## Notes

- Replace `$API_URL` with your actual service URL
- Replace `$API_KEY` with your actual API key
- Replace file paths with actual image file paths
- Use `jq` for pretty-printing JSON responses (install with `apt-get install jq` or `brew install jq`)
- All timestamps are in ISO 8601 format (UTC)
- Processing times are in milliseconds
- Confidence scores range from 0.0 to 1.0
