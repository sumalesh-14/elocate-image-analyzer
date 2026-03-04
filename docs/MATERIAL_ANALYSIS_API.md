# Material Analysis API Documentation

## Overview

The Material Analysis endpoint analyzes electronic devices to estimate the quantity and market value of recyclable and precious materials they contain. The endpoint uses an LLM to identify materials based on device specifications and provides current market rates for the specified country.

## Endpoint

```
POST /api/v1/analyze-materials
```

## Authentication

Include your API key in the request header:
```
X-API-Key: your-api-key-here
```

## Request Format

### Request Body (JSON)

```json
{
  "brand_id": "string",
  "brand_name": "string",
  "category_id": "string",
  "category_name": "string",
  "model_id": "string",
  "model_name": "string",
  "country": "string",
  "description": "string (optional)"
}
```

### Field Descriptions

- `brand_id`: Unique identifier for the brand
- `brand_name`: Name of the device brand (e.g., "Samsung", "Apple")
- `category_id`: Unique identifier for the device category
- `category_name`: Device category (e.g., "Smartphone", "Laptop", "Tablet")
- `model_id`: Unique identifier for the device model
- `model_name`: Specific model name (e.g., "Galaxy S21", "iPhone 13")
- `country`: Country name or code for market rate lookup (e.g., "India", "USA")
- `description`: Optional additional context about the device

## Response Format

### Success Response (200 OK)

```json
{
  "success": true,
  "timestamp": "2026-03-04T18:20:00Z",
  "processingTimeMs": 1234,
  "data": {
    "brand": {
      "id": "BR001",
      "name": "Samsung"
    },
    "category": {
      "id": "CAT001",
      "name": "Smartphone"
    },
    "model": {
      "id": "MOD001",
      "name": "Galaxy S21"
    },
    "country": "India",
    "analysisDescription": "Material recovery estimation from the device based on internal components.",
    "materials": [
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.034,
        "marketRatePerGram": 6500,
        "currency": "INR",
        "foundIn": "Circuit board and connectors"
      },
      {
        "materialName": "Silver",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.25,
        "marketRatePerGram": 75,
        "currency": "INR",
        "foundIn": "Circuit board"
      },
      {
        "materialName": "Copper",
        "isPrecious": false,
        "estimatedQuantityGrams": 15,
        "marketRatePerGram": 0.85,
        "currency": "INR",
        "foundIn": "Wiring and circuit board"
      },
      {
        "materialName": "Aluminium",
        "isPrecious": false,
        "estimatedQuantityGrams": 8,
        "marketRatePerGram": 0.25,
        "currency": "INR",
        "foundIn": "Frame and casing"
      },
      {
        "materialName": "Lithium",
        "isPrecious": false,
        "estimatedQuantityGrams": 2,
        "marketRatePerGram": 3.2,
        "currency": "INR",
        "foundIn": "Lithium-ion battery"
      }
    ],
    "metadata": {
      "llmModel": "gemini-1.5-flash",
      "analysisTimestamp": "2026-03-04T18:20:00Z"
    }
  },
  "error": null
}
```

### Error Response

```json
{
  "success": false,
  "timestamp": "2026-03-04T18:20:00Z",
  "processingTimeMs": 500,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

## Material Data Fields

Each material in the `materials` array contains:

- `materialName`: Name of the material (e.g., "Gold", "Copper", "Lithium")
- `isPrecious`: Boolean indicating if this is a precious metal
- `estimatedQuantityGrams`: Estimated quantity in grams
- `marketRatePerGram`: Current market rate per gram in local currency
- `currency`: Currency code (e.g., "INR", "USD", "EUR")
- `foundIn`: Component/part where this material is typically found (e.g., "Circuit board", "Battery", "Display panel")

## Materials Typically Identified

The LLM analyzes devices and may identify:

### Precious Metals
- Gold
- Silver
- Platinum
- Palladium

### Base Metals
- Copper
- Aluminum
- Steel
- Tin

### Battery Materials
- Lithium
- Cobalt
- Nickel
- Manganese

### Rare Earth Elements
- Neodymium
- Dysprosium
- Tantalum
- Yttrium

## Error Codes

- `LLM_NO_RESPONSE`: LLM did not return a valid response
- `INVALID_LLM_RESPONSE`: LLM response format is invalid
- `NO_MATERIALS_FOUND`: No materials identified in the device
- `NO_VALID_MATERIALS`: No valid materials could be parsed
- `ANALYSIS_FAILED`: General analysis failure
- `VALIDATION_ERROR`: Request validation failed
- `INTERNAL_ERROR`: Unexpected server error

## Rate Limiting

The endpoint is rate-limited to 10 requests per minute per IP address.

## Example Usage

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-materials" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "brand_id": "BR001",
    "brand_name": "Samsung",
    "category_id": "CAT001",
    "category_name": "Smartphone",
    "model_id": "MOD001",
    "model_name": "Galaxy S21",
    "country": "India",
    "description": "Standard consumer smartphone"
  }'
```

### Python

```python
import requests

url = "http://localhost:8000/api/v1/analyze-materials"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key-here"
}
data = {
    "brand_id": "BR001",
    "brand_name": "Samsung",
    "category_id": "CAT001",
    "category_name": "Smartphone",
    "model_id": "MOD001",
    "model_name": "Galaxy S21",
    "country": "India"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

### JavaScript (fetch)

```javascript
const url = "http://localhost:8000/api/v1/analyze-materials";
const data = {
  brand_id: "BR001",
  brand_name: "Samsung",
  category_id: "CAT001",
  category_name: "Smartphone",
  model_id: "MOD001",
  model_name: "Galaxy S21",
  country: "India"
};

fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": "your-api-key-here"
  },
  body: JSON.stringify(data)
})
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error("Error:", error));
```

## Important Notes

1. **Market Rates**: The LLM provides estimated current market rates. For production use, consider integrating with real-time commodity price APIs for accurate rates.

2. **Quantity Estimates**: Material quantities are estimates based on typical device composition. Actual quantities may vary.

3. **No Calculations**: The API returns per-gram rates and quantities separately. Calculate total values on the client side as needed.

4. **Country-Specific Rates**: Market rates are provided in the local currency of the specified country.

5. **LLM Dependency**: This endpoint requires an active LLM API connection (Gemini, OpenAI, or Groq).

## Testing

Use the provided test script:

```bash
python test_material_analysis.py
```

Or access the interactive API documentation at:
```
http://localhost:8000/docs
```
