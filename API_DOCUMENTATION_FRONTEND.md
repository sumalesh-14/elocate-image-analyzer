# Material Analysis API - Complete Frontend Documentation

## API Endpoint

```
POST /api/v1/analyze-materials
Content-Type: application/json
```

## Base URL
- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

## Request Structure

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `brand_id` | string | Brand identifier | `"mock"` or actual ID |
| `brand_name` | string | Brand name | `"Apple"` |
| `category_id` | string | Category identifier | `"mock"` or actual ID |
| `category_name` | string | Category name | `"Laptop"` |
| `model_id` | string | Model identifier | `"754d5a16-6d13-4478-97aa-9072cf6d2c9b"` |
| `model_name` | string | Model name | `"MacBook Pro 16 (M4)"` |
| `country` | string | Country code | `"IN"` for India, `"US"` for USA |

### Optional Fields

| Field | Type | Description | Allowed Values |
|-------|------|-------------|----------------|
| `deviceCondition` | string | Device condition code | `"EXCELLENT"`, `"GOOD"`, `"FAIR"`, `"POOR"` |
| `conditionNotes` | string | Detailed condition description | Any text |
| `description` | string | Additional device context | Any text |

### Device Condition Codes

| Code | Label | Description |
|------|-------|-------------|
| `EXCELLENT` | Pristine / Working | Fully functional, no damage |
| `GOOD` | Fair / Minor Issues | Working with cosmetic wear |
| `FAIR` | Broken / Damaged | Powers on but partial functionality |
| `POOR` | Scrap / Parts | Does not power on, non-functional |


## Complete Request Examples

### Example 1: Minimum Required Fields
```json
{
  "brand_id": "mock",
  "brand_name": "Apple",
  "category_id": "mock",
  "category_name": "Laptop",
  "model_id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
  "model_name": "MacBook Pro 16 (M4)",
  "country": "IN"
}
```

### Example 2: With Device Condition
```json
{
  "brand_id": "mock",
  "brand_name": "Apple",
  "category_id": "mock",
  "category_name": "Laptop",
  "model_id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
  "model_name": "MacBook Pro 16 (M4)",
  "country": "IN",
  "deviceCondition": "GOOD",
  "conditionNotes": "Minor scratches on bottom case, screen perfect, battery 85%, all functions working"
}
```

### Example 3: Complete Request
```json
{
  "brand_id": "apple-001",
  "brand_name": "Apple",
  "category_id": "laptop-001",
  "category_name": "Laptop",
  "model_id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
  "model_name": "MacBook Pro 16 (M4)",
  "country": "IN",
  "deviceCondition": "EXCELLENT",
  "conditionNotes": "Pristine condition, no visible wear, battery health 98%, all features working perfectly",
  "description": "Latest M4 chip model with 36GB RAM"
}
```


## Response Structure

### Success Response (HTTP 200)

```json
{
  "success": true,
  "timestamp": "2026-03-07T12:00:00.000000",
  "processingTimeMs": 2000,
  "data": {
    "brand": { ... },
    "category": { ... },
    "model": { ... },
    "country": "IN",
    "analysisDescription": "...",
    "materials": [ ... ],
    "devicePricing": { ... },
    "recyclingEstimate": { ... },
    "metadata": { ... }
  },
  "error": null
}
```

### Response Fields Breakdown

#### Root Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if successful, `false` if error |
| `timestamp` | string (ISO 8601) | Response timestamp |
| `processingTimeMs` | integer | Processing time in milliseconds |
| `data` | object | Analysis data (null if error) |
| `error` | object | Error details (null if success) |


#### Data Object Fields

##### 1. Brand Object
```json
{
  "id": "mock",
  "name": "Apple"
}
```

##### 2. Category Object
```json
{
  "id": "mock",
  "name": "Laptop"
}
```

##### 3. Model Object
```json
{
  "id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
  "name": "MacBook Pro 16 (M4)"
}
```

##### 4. Country
```json
"country": "IN"
```

##### 5. Analysis Description
```json
"analysisDescription": "The analysis methodology includes estimating the quantities of various materials present in a MacBook Pro 16 based on typical device composition and e-waste recycling market data. Recovery efficiency considerations are also taken into account, assuming an average recovery efficiency of 70%. Market rates are based on realistic e-waste scrap rates for India, adjusted for recovery costs and efficiency."
```


##### 6. Materials Array

Each material object contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `materialName` | string | Material name | `"Gold"` |
| `isPrecious` | boolean | Is precious metal | `true` |
| `estimatedQuantityGrams` | number | Quantity in grams | `0.034` |
| `marketRatePerGram` | number | Rate per gram | `4500.0` |
| `currency` | string | Currency code | `"INR"` |
| `foundIn` | string | Component location | `"Circuit board and connectors"` |

**Example Materials Array:**
```json
"materials": [
  {
    "materialName": "Gold",
    "isPrecious": true,
    "estimatedQuantityGrams": 0.034,
    "marketRatePerGram": 4500.0,
    "currency": "INR",
    "foundIn": "Circuit board and connectors"
  },
  {
    "materialName": "Silver",
    "isPrecious": true,
    "estimatedQuantityGrams": 1.2,
    "marketRatePerGram": 55.0,
    "currency": "INR",
    "foundIn": "Circuit board, keyboard, and display connectors"
  },
  {
    "materialName": "Copper",
    "isPrecious": false,
    "estimatedQuantityGrams": 450.0,
    "marketRatePerGram": 0.45,
    "currency": "INR",
    "foundIn": "Circuit board, wiring, and heat sinks"
  },
  {
    "materialName": "Aluminum",
    "isPrecious": false,
    "estimatedQuantityGrams": 1200.0,
    "marketRatePerGram": 0.165,
    "currency": "INR",
    "foundIn": "Body, frame, and heat sinks"
  }
]
```


##### 7. Device Pricing Object

**Structure:**
```json
"devicePricing": {
  "currentMarketPrice": null,
  "currency": null,
  "platformLinks": [
    {
      "platformName": "Flipkart",
      "link": "https://www.flipkart.com/search?q=Apple+MacBook+Pro+16+(M4)",
      "icon": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png",
      "displayOrder": 1
    },
    {
      "platformName": "Amazon",
      "link": "https://www.amazon.in/s?k=Apple+MacBook+Pro+16+(M4)",
      "icon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
      "displayOrder": 2
    }
  ]
}
```

**Platform Links Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `platformName` | string | Platform display name |
| `link` | string | Product/search URL |
| `icon` | string | Platform logo URL |
| `displayOrder` | integer | Display priority (lower = higher priority) |

**Platforms Included (India):**
1. Flipkart
2. Amazon
3. Snapdeal
4. Croma
5. Reliance Digital
6. Vijay Sales
7. Tata CLiQ
8. Paytm Mall
9. Brand Official Website (e.g., "Apple Official")


##### 8. Recycling Estimate Object

**Structure:**
```json
"recyclingEstimate": {
  "totalMaterialValue": 19797.00,
  "suggestedRecyclingPrice": 10888.35,
  "suggestedBuybackPrice": 137494.50,
  "conditionImpact": "Device condition 'GOOD' (Fair/Minor Issues - Working with cosmetic wear) results in 55% of material value. Minor cosmetic wear does not significantly impact material extraction efficiency.",
  "currency": "INR",
  "priceBreakdown": "Material value: 19797.00 | Recycling price: 10888.35 (...) | Buyback price: 137494.50 (...) | Recommendation: Buyback is 12.6x better than recycling. Device is suitable for resale/reuse."
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `totalMaterialValue` | number | Sum of all material values |
| `suggestedRecyclingPrice` | number | Recommended recycling price (condition-adjusted) |
| `suggestedBuybackPrice` | number | Recommended buyback price (null if not applicable) |
| `conditionImpact` | string | Explanation of condition impact on pricing |
| `currency` | string | Currency code |
| `priceBreakdown` | string | Detailed pricing explanation with recommendation |

**Pricing Logic:**
- `EXCELLENT`: 65% of material value (recycling), 70% of market price (buyback)
- `GOOD`: 55% of material value (recycling), 55% of market price (buyback)
- `FAIR`: 45% of material value (recycling), 35% of market price (buyback)
- `POOR`: 30% of material value (recycling), no buyback offered


##### 9. Metadata Object

```json
"metadata": {
  "llmModel": "llama-3.3-70b-versatile",
  "analysisTimestamp": "2026-03-07T12:00:00.000000"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `llmModel` | string | AI model used for analysis |
| `analysisTimestamp` | string (ISO 8601) | When analysis was performed |


## Complete Response Example

### Request:
```json
{
  "brand_id": "mock",
  "brand_name": "Apple",
  "category_id": "mock",
  "category_name": "Laptop",
  "model_id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
  "model_name": "MacBook Pro 16 (M4)",
  "country": "IN",
  "deviceCondition": "GOOD",
  "conditionNotes": "Minor scratches on bottom case, screen perfect, battery 85%"
}
```

### Response:
```json
{
  "success": true,
  "timestamp": "2026-03-07T12:00:00.000000",
  "processingTimeMs": 1954,
  "data": {
    "brand": {
      "id": "mock",
      "name": "Apple"
    },
    "category": {
      "id": "mock",
      "name": "Laptop"
    },
    "model": {
      "id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
      "name": "MacBook Pro 16 (M4)"
    },
    "country": "IN",
    "analysisDescription": "The analysis methodology includes estimating the quantities of various materials present in a MacBook Pro 16 based on typical device composition and e-waste recycling market data. Recovery efficiency considerations are also taken into account, assuming an average recovery efficiency of 70%. Market rates are based on realistic e-waste scrap rates for India, adjusted for recovery costs and efficiency.",
    "materials": [
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.034,
        "marketRatePerGram": 4500.0,
        "currency": "INR",
        "foundIn": "Circuit board and connectors"
      },
      {
        "materialName": "Silver",
        "isPrecious": true,
        "estimatedQuantityGrams": 1.2,
        "marketRatePerGram": 55.0,
        "currency": "INR",
        "foundIn": "Circuit board, keyboard, and display connectors"
      },
      {
        "materialName": "Copper",
        "isPrecious": false,
        "estimatedQuantityGrams": 450.0,
        "marketRatePerGram": 0.45,
        "currency": "INR",
        "foundIn": "Circuit board, wiring, and heat sinks"
      },
      {
        "materialName": "Aluminum",
        "isPrecious": false,
        "estimatedQuantityGrams": 1200.0,
        "marketRatePerGram": 0.165,
        "currency": "INR",
        "foundIn": "Body, frame, and heat sinks"
      },
      {
        "materialName": "Lithium",
        "isPrecious": false,
        "estimatedQuantityGrams": 60.0,
        "marketRatePerGram": 100.0,
        "currency": "INR",
        "foundIn": "Lithium-ion battery"
      },
      {
        "materialName": "Cobalt",
        "isPrecious": false,
        "estimatedQuantityGrams": 30.0,
        "marketRatePerGram": 350.0,
        "currency": "INR",
        "foundIn": "Lithium-ion battery"
      }
    ],
    "devicePricing": {
      "currentMarketPrice": null,
      "currency": null,
      "platformLinks": [
        {
          "platformName": "Flipkart",
          "link": "https://www.flipkart.com/search?q=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png",
          "displayOrder": 1
        },
        {
          "platformName": "Amazon",
          "link": "https://www.amazon.in/s?k=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
          "displayOrder": 2
        },
        {
          "platformName": "Snapdeal",
          "link": "https://www.snapdeal.com/search?keyword=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.snapdeal.com/favicon.ico",
          "displayOrder": 3
        },
        {
          "platformName": "Croma",
          "link": "https://www.croma.com/search?q=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.croma.com/favicon.ico",
          "displayOrder": 4
        },
        {
          "platformName": "Reliance Digital",
          "link": "https://www.reliancedigital.in/search?q=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.reliancedigital.in/favicon.ico",
          "displayOrder": 5
        },
        {
          "platformName": "Vijay Sales",
          "link": "https://www.vijaysales.com/search/Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.vijaysales.com/favicon.ico",
          "displayOrder": 6
        },
        {
          "platformName": "Tata CLiQ",
          "link": "https://www.tatacliq.com/search/?searchCategory=all&text=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.tatacliq.com/favicon.ico",
          "displayOrder": 7
        },
        {
          "platformName": "Paytm Mall",
          "link": "https://paytmmall.com/shop/search?q=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://paytmmall.com/favicon.ico",
          "displayOrder": 8
        },
        {
          "platformName": "Apple Official",
          "link": "https://www.apple.com/in/",
          "icon": "https://www.apple.com/favicon.ico",
          "displayOrder": 999
        }
      ]
    },
    "recyclingEstimate": {
      "totalMaterialValue": 19797.00,
      "suggestedRecyclingPrice": 10888.35,
      "suggestedBuybackPrice": 137494.50,
      "conditionImpact": "Device condition 'GOOD' (Fair/Minor Issues - Working with cosmetic wear) results in 55% of material value. Minor cosmetic wear does not significantly impact material extraction efficiency.",
      "currency": "INR",
      "priceBreakdown": "Material value: 19797.00 | Recycling price: 10888.35 (Device condition 'GOOD' (Fair/Minor Issues - Working with cosmetic wear) results in 55% of material value. Minor cosmetic wear does not significantly impact material extraction efficiency.) | Buyback price: 137494.50 (Buyback price is 55% of market price for 'GOOD' condition (Fair/Minor Issues - Working with cosmetic wear).) | Recommendation: Buyback is 12.6x better than recycling. Device is suitable for resale/reuse."
    },
    "metadata": {
      "llmModel": "llama-3.3-70b-versatile",
      "analysisTimestamp": "2026-03-07T12:00:00.000000"
    }
  },
  "error": null
}
```


## Error Responses

### Validation Error (HTTP 422)
```json
{
  "success": false,
  "timestamp": "2026-03-07T12:00:00.000000",
  "processingTimeMs": 10,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "deviceCondition must be one of: EXCELLENT, GOOD, FAIR, POOR",
    "details": {
      "field": "deviceCondition",
      "value": "invalid_value"
    }
  }
}
```

### Analysis Error (HTTP 200 with error)
```json
{
  "success": false,
  "timestamp": "2026-03-07T12:00:00.000000",
  "processingTimeMs": 1500,
  "data": null,
  "error": {
    "code": "ALL_WORKERS_FAILED",
    "message": "All LLM providers failed for material analysis"
  }
}
```

### Rate Limit Error (HTTP 429)
```json
{
  "success": false,
  "timestamp": "2026-03-07T12:00:00.000000",
  "processingTimeMs": 5,
  "data": null,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "retryAfter": 60
  }
}
```


## Frontend Implementation Examples

### JavaScript/Fetch
```javascript
async function analyzeMaterials(deviceData) {
  try {
    const response = await fetch('http://localhost:8000/api/v1/analyze-materials', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        brand_id: deviceData.brandId,
        brand_name: deviceData.brandName,
        category_id: deviceData.categoryId,
        category_name: deviceData.categoryName,
        model_id: deviceData.modelId,
        model_name: deviceData.modelName,
        country: 'IN',
        deviceCondition: deviceData.condition, // 'EXCELLENT', 'GOOD', 'FAIR', 'POOR'
        conditionNotes: deviceData.notes
      })
    });

    const result = await response.json();

    if (result.success) {
      return {
        materials: result.data.materials,
        pricing: result.data.devicePricing,
        recyclingEstimate: result.data.recyclingEstimate,
        processingTime: result.processingTimeMs
      };
    } else {
      throw new Error(result.error.message);
    }
  } catch (error) {
    console.error('Material analysis failed:', error);
    throw error;
  }
}

// Usage
const deviceData = {
  brandId: 'mock',
  brandName: 'Apple',
  categoryId: 'mock',
  categoryName: 'Laptop',
  modelId: '754d5a16-6d13-4478-97aa-9072cf6d2c9b',
  modelName: 'MacBook Pro 16 (M4)',
  condition: 'GOOD',
  notes: 'Minor scratches, fully functional'
};

analyzeMaterials(deviceData)
  .then(data => console.log('Analysis result:', data))
  .catch(error => console.error('Error:', error));
```


### React/Next.js Hook
```javascript
import { useState } from 'react';

export function useMaterialAnalysis() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const analyze = async (deviceData) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/analyze-materials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand_id: deviceData.brandId,
          brand_name: deviceData.brandName,
          category_id: deviceData.categoryId,
          category_name: deviceData.categoryName,
          model_id: deviceData.modelId,
          model_name: deviceData.modelName,
          country: deviceData.country || 'IN',
          deviceCondition: deviceData.condition,
          conditionNotes: deviceData.notes
        })
      });

      const result = await response.json();

      if (result.success) {
        setData(result.data);
        return result.data;
      } else {
        throw new Error(result.error.message);
      }
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { analyze, loading, error, data };
}

// Component usage
function MaterialAnalysisComponent() {
  const { analyze, loading, error, data } = useMaterialAnalysis();

  const handleAnalyze = async () => {
    try {
      await analyze({
        brandId: 'mock',
        brandName: 'Apple',
        categoryId: 'mock',
        categoryName: 'Laptop',
        modelId: '754d5a16-6d13-4478-97aa-9072cf6d2c9b',
        modelName: 'MacBook Pro 16 (M4)',
        condition: 'GOOD',
        notes: 'Minor scratches'
      });
    } catch (err) {
      console.error('Analysis failed:', err);
    }
  };

  if (loading) return <div>Analyzing materials...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <button onClick={handleAnalyze}>Analyze Device</button>
      {data && (
        <div>
          <h3>Materials Found: {data.materials.length}</h3>
          <p>Total Value: {data.recyclingEstimate.currency} {data.recyclingEstimate.totalMaterialValue}</p>
          <p>Recycling Price: {data.recyclingEstimate.currency} {data.recyclingEstimate.suggestedRecyclingPrice}</p>
          {data.recyclingEstimate.suggestedBuybackPrice && (
            <p>Buyback Price: {data.recyclingEstimate.currency} {data.recyclingEstimate.suggestedBuybackPrice}</p>
          )}
        </div>
      )}
    </div>
  );
}
```


### Axios Example
```javascript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const materialAnalysisAPI = {
  analyze: async (deviceData) => {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/analyze-materials`,
        {
          brand_id: deviceData.brandId,
          brand_name: deviceData.brandName,
          category_id: deviceData.categoryId,
          category_name: deviceData.categoryName,
          model_id: deviceData.modelId,
          model_name: deviceData.modelName,
          country: deviceData.country || 'IN',
          deviceCondition: deviceData.condition,
          conditionNotes: deviceData.notes
        },
        {
          headers: {
            'Content-Type': 'application/json'
          },
          timeout: 30000 // 30 seconds
        }
      );

      return response.data;
    } catch (error) {
      if (error.response) {
        // Server responded with error
        throw new Error(error.response.data.error?.message || 'Analysis failed');
      } else if (error.request) {
        // No response received
        throw new Error('No response from server');
      } else {
        // Request setup error
        throw new Error(error.message);
      }
    }
  }
};

// Usage
materialAnalysisAPI.analyze({
  brandId: 'mock',
  brandName: 'Apple',
  categoryId: 'mock',
  categoryName: 'Laptop',
  modelId: '754d5a16-6d13-4478-97aa-9072cf6d2c9b',
  modelName: 'MacBook Pro 16 (M4)',
  condition: 'GOOD',
  notes: 'Minor scratches'
})
  .then(result => {
    if (result.success) {
      console.log('Materials:', result.data.materials);
      console.log('Pricing:', result.data.recyclingEstimate);
    }
  })
  .catch(error => console.error('Error:', error));
```


## TypeScript Interfaces

```typescript
// Request interface
interface MaterialAnalysisRequest {
  brand_id: string;
  brand_name: string;
  category_id: string;
  category_name: string;
  model_id: string;
  model_name: string;
  country: string;
  deviceCondition?: 'EXCELLENT' | 'GOOD' | 'FAIR' | 'POOR';
  conditionNotes?: string;
  description?: string;
}

// Response interfaces
interface Material {
  materialName: string;
  isPrecious: boolean;
  estimatedQuantityGrams: number;
  marketRatePerGram: number;
  currency: string;
  foundIn: string;
}

interface PlatformLink {
  platformName: string;
  link: string;
  icon: string | null;
  displayOrder: number | null;
}

interface DevicePricing {
  currentMarketPrice: number | null;
  currency: string | null;
  platformLinks: PlatformLink[];
}

interface RecyclingEstimate {
  totalMaterialValue: number;
  suggestedRecyclingPrice: number;
  suggestedBuybackPrice: number | null;
  conditionImpact: string | null;
  currency: string;
  priceBreakdown: string | null;
}

interface AnalysisData {
  brand: {
    id: string;
    name: string;
  };
  category: {
    id: string;
    name: string;
  };
  model: {
    id: string;
    name: string;
  };
  country: string;
  analysisDescription: string;
  materials: Material[];
  devicePricing: DevicePricing | null;
  recyclingEstimate: RecyclingEstimate;
  metadata: {
    llmModel: string;
    analysisTimestamp: string;
  };
}

interface MaterialAnalysisResponse {
  success: boolean;
  timestamp: string;
  processingTimeMs: number;
  data: AnalysisData | null;
  error: {
    code: string;
    message: string;
    details?: any;
  } | null;
}
```


## UI Display Examples

### Materials Table
```jsx
function MaterialsTable({ materials }) {
  const preciousMaterials = materials.filter(m => m.isPrecious);
  const otherMaterials = materials.filter(m => !m.isPrecious);

  return (
    <div>
      <h3>Precious Metals</h3>
      <table>
        <thead>
          <tr>
            <th>Material</th>
            <th>Quantity (g)</th>
            <th>Rate/g</th>
            <th>Value</th>
            <th>Found In</th>
          </tr>
        </thead>
        <tbody>
          {preciousMaterials.map((material, index) => (
            <tr key={index}>
              <td>{material.materialName}</td>
              <td>{material.estimatedQuantityGrams}</td>
              <td>{material.currency} {material.marketRatePerGram}</td>
              <td>{material.currency} {(material.estimatedQuantityGrams * material.marketRatePerGram).toFixed(2)}</td>
              <td>{material.foundIn}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Other Materials</h3>
      <table>
        <thead>
          <tr>
            <th>Material</th>
            <th>Quantity (g)</th>
            <th>Rate/g</th>
            <th>Value</th>
            <th>Found In</th>
          </tr>
        </thead>
        <tbody>
          {otherMaterials.map((material, index) => (
            <tr key={index}>
              <td>{material.materialName}</td>
              <td>{material.estimatedQuantityGrams}</td>
              <td>{material.currency} {material.marketRatePerGram}</td>
              <td>{material.currency} {(material.estimatedQuantityGrams * material.marketRatePerGram).toFixed(2)}</td>
              <td>{material.foundIn}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### Platform Links Grid
```jsx
function PlatformLinksGrid({ platformLinks }) {
  return (
    <div className="platform-grid">
      {platformLinks.map((platform) => (
        <a
          key={platform.platformName}
          href={platform.link}
          target="_blank"
          rel="noopener noreferrer"
          className="platform-card"
        >
          {platform.icon && (
            <img
              src={platform.icon}
              alt={`${platform.platformName} logo`}
              className="platform-icon"
              loading="lazy"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          )}
          <span className="platform-name">{platform.platformName}</span>
        </a>
      ))}
    </div>
  );
}
```

### Pricing Summary Card
```jsx
function PricingSummary({ recyclingEstimate }) {
  const { 
    totalMaterialValue, 
    suggestedRecyclingPrice, 
    suggestedBuybackPrice,
    conditionImpact,
    currency 
  } = recyclingEstimate;

  const buybackMultiplier = suggestedBuybackPrice 
    ? (suggestedBuybackPrice / suggestedRecyclingPrice).toFixed(1)
    : null;

  return (
    <div className="pricing-summary">
      <div className="price-card">
        <h4>Material Value</h4>
        <p className="price">{currency} {totalMaterialValue.toFixed(2)}</p>
        <small>Total value of all materials</small>
      </div>

      <div className="price-card">
        <h4>Recycling Price</h4>
        <p className="price">{currency} {suggestedRecyclingPrice.toFixed(2)}</p>
        <small>{conditionImpact}</small>
      </div>

      {suggestedBuybackPrice && (
        <div className="price-card highlight">
          <h4>Buyback Price</h4>
          <p className="price">{currency} {suggestedBuybackPrice.toFixed(2)}</p>
          <small>
            {buybackMultiplier}x better than recycling
          </small>
        </div>
      )}
    </div>
  );
}
```


## Testing with cURL

### Basic Request
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-materials" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_id": "mock",
    "brand_name": "Apple",
    "category_id": "mock",
    "category_name": "Laptop",
    "model_id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
    "model_name": "MacBook Pro 16 (M4)",
    "country": "IN"
  }'
```

### With Device Condition
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-materials" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_id": "mock",
    "brand_name": "Apple",
    "category_id": "mock",
    "category_name": "Laptop",
    "model_id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
    "model_name": "MacBook Pro 16 (M4)",
    "country": "IN",
    "deviceCondition": "GOOD",
    "conditionNotes": "Minor scratches, fully functional, battery 85%"
  }'
```

### Pretty Print Response
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-materials" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_id": "mock",
    "brand_name": "Apple",
    "category_id": "mock",
    "category_name": "Laptop",
    "model_id": "754d5a16-6d13-4478-97aa-9072cf6d2c9b",
    "model_name": "MacBook Pro 16 (M4)",
    "country": "IN",
    "deviceCondition": "EXCELLENT"
  }' | python -m json.tool
```


## Performance & Best Practices

### Expected Response Times
- Typical: 1.5 - 2.5 seconds
- With condition: 1.8 - 3.0 seconds
- Includes LLM analysis + pricing calculation
- Device pricing fetch is non-blocking

### Rate Limiting
- Limit: 10 requests per minute per IP
- Header: `X-RateLimit-Remaining`
- On exceed: HTTP 429 with `retryAfter` in seconds

### Caching Recommendations
- Cache responses for same device + condition for 24 hours
- Material rates update daily
- Platform links are static (can cache longer)

### Error Handling Best Practices
```javascript
async function analyzeWithRetry(deviceData, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch('/api/v1/analyze-materials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deviceData)
      });

      const result = await response.json();

      if (response.status === 429) {
        // Rate limited
        const retryAfter = result.error?.retryAfter || 60;
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        continue;
      }

      if (!result.success) {
        throw new Error(result.error?.message || 'Analysis failed');
      }

      return result.data;
    } catch (error) {
      if (attempt === maxRetries) {
        throw error;
      }
      // Exponential backoff
      await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
    }
  }
}
```

### Loading States
```jsx
function AnalysisLoadingState() {
  return (
    <div className="loading-state">
      <div className="spinner"></div>
      <p>Analyzing device materials...</p>
      <small>This may take 2-3 seconds</small>
    </div>
  );
}
```

### Validation Before API Call
```javascript
function validateDeviceData(data) {
  const errors = [];

  if (!data.brand_name?.trim()) {
    errors.push('Brand name is required');
  }

  if (!data.model_name?.trim()) {
    errors.push('Model name is required');
  }

  if (!data.category_name?.trim()) {
    errors.push('Category name is required');
  }

  if (!['IN', 'US', 'UK', 'AU'].includes(data.country)) {
    errors.push('Invalid country code');
  }

  if (data.deviceCondition && !['EXCELLENT', 'GOOD', 'FAIR', 'POOR'].includes(data.deviceCondition)) {
    errors.push('Invalid device condition');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}
```


## Quick Reference

### Condition Codes
| Code | Recycling % | Buyback % | Description |
|------|-------------|-----------|-------------|
| EXCELLENT | 65% | 70% | Pristine, fully functional |
| GOOD | 55% | 55% | Minor wear, working |
| FAIR | 45% | 35% | Partial functionality |
| POOR | 30% | None | Non-functional |

### Key Response Fields
- `data.materials[]` - Array of materials with quantities and rates
- `data.recyclingEstimate.suggestedRecyclingPrice` - Offer this for recycling
- `data.recyclingEstimate.suggestedBuybackPrice` - Offer this for buyback (if not null)
- `data.devicePricing.platformLinks[]` - E-commerce links with icons
- `data.recyclingEstimate.priceBreakdown` - Show this to explain pricing

### Common Scenarios

**Scenario 1: User wants to recycle**
- Show: `suggestedRecyclingPrice`
- Display: Materials breakdown
- Action: "Recycle for ₹X"

**Scenario 2: Device is functional**
- Show: Both `suggestedRecyclingPrice` and `suggestedBuybackPrice`
- Highlight: Buyback is better (usually 5-15x more)
- Action: "Sell for ₹X" (buyback) or "Recycle for ₹Y"

**Scenario 3: User wants to check market price**
- Show: `platformLinks` as clickable cards with icons
- Action: Open links in new tab

**Scenario 4: User wants material details**
- Show: `materials` array in table format
- Group by: `isPrecious` (precious metals vs others)
- Calculate: Individual material values

