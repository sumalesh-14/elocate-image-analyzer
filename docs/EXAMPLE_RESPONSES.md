# Material Analysis - Example Responses

This document shows example responses for different device types to help you understand what to expect from the API.

## Example 1: Smartphone (Samsung Galaxy S21)

### Request
```json
{
  "brand_id": "BR001",
  "brand_name": "Samsung",
  "category_id": "CAT001",
  "category_name": "Smartphone",
  "model_id": "MOD001",
  "model_name": "Galaxy S21",
  "country": "India"
}
```

### Response
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
    "analysisDescription": "Material recovery estimation from smartphone based on typical flagship device composition including circuit boards, battery, display, and chassis components.",
    "materials": [
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.034,
        "marketRatePerGram": 6500,
        "currency": "INR"
      },
      {
        "materialName": "Silver",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.25,
        "marketRatePerGram": 75,
        "currency": "INR"
      },
      {
        "materialName": "Copper",
        "isPrecious": false,
        "estimatedQuantityGrams": 15,
        "marketRatePerGram": 0.85,
        "currency": "INR"
      },
      {
        "materialName": "Aluminium",
        "isPrecious": false,
        "estimatedQuantityGrams": 8,
        "marketRatePerGram": 0.25,
        "currency": "INR"
      },
      {
        "materialName": "Lithium",
        "isPrecious": false,
        "estimatedQuantityGrams": 2,
        "marketRatePerGram": 3.2,
        "currency": "INR"
      },
      {
        "materialName": "Cobalt",
        "isPrecious": false,
        "estimatedQuantityGrams": 1.5,
        "marketRatePerGram": 4.5,
        "currency": "INR"
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

## Example 2: Laptop (Dell XPS 15)

### Request
```json
{
  "brand_id": "BR002",
  "brand_name": "Dell",
  "category_id": "CAT002",
  "category_name": "Laptop",
  "model_id": "MOD002",
  "model_name": "XPS 15",
  "country": "USA"
}
```

### Response
```json
{
  "success": true,
  "timestamp": "2026-03-04T18:25:00Z",
  "processingTimeMs": 1456,
  "data": {
    "brand": {
      "id": "BR002",
      "name": "Dell"
    },
    "category": {
      "id": "CAT002",
      "name": "Laptop"
    },
    "model": {
      "id": "MOD002",
      "name": "XPS 15"
    },
    "country": "USA",
    "analysisDescription": "Material recovery estimation from laptop including motherboard, battery, display panel, cooling system, and aluminum chassis.",
    "materials": [
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.15,
        "marketRatePerGram": 65.5,
        "currency": "USD"
      },
      {
        "materialName": "Silver",
        "isPrecious": true,
        "estimatedQuantityGrams": 1.2,
        "marketRatePerGram": 0.85,
        "currency": "USD"
      },
      {
        "materialName": "Palladium",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.05,
        "marketRatePerGram": 95.0,
        "currency": "USD"
      },
      {
        "materialName": "Copper",
        "isPrecious": false,
        "estimatedQuantityGrams": 85,
        "marketRatePerGram": 0.009,
        "currency": "USD"
      },
      {
        "materialName": "Aluminium",
        "isPrecious": false,
        "estimatedQuantityGrams": 450,
        "marketRatePerGram": 0.003,
        "currency": "USD"
      },
      {
        "materialName": "Lithium",
        "isPrecious": false,
        "estimatedQuantityGrams": 12,
        "marketRatePerGram": 0.35,
        "currency": "USD"
      },
      {
        "materialName": "Cobalt",
        "isPrecious": false,
        "estimatedQuantityGrams": 8,
        "marketRatePerGram": 0.45,
        "currency": "USD"
      },
      {
        "materialName": "Neodymium",
        "isPrecious": false,
        "estimatedQuantityGrams": 2,
        "marketRatePerGram": 0.12,
        "currency": "USD"
      }
    ],
    "metadata": {
      "llmModel": "gpt-4",
      "analysisTimestamp": "2026-03-04T18:25:00Z"
    }
  },
  "error": null
}
```

## Example 3: Tablet (Apple iPad Pro)

### Request
```json
{
  "brand_id": "BR003",
  "brand_name": "Apple",
  "category_id": "CAT003",
  "category_name": "Tablet",
  "model_id": "MOD003",
  "model_name": "iPad Pro 12.9",
  "country": "UK"
}
```

### Response
```json
{
  "success": true,
  "timestamp": "2026-03-04T18:30:00Z",
  "processingTimeMs": 1123,
  "data": {
    "brand": {
      "id": "BR003",
      "name": "Apple"
    },
    "category": {
      "id": "CAT003",
      "name": "Tablet"
    },
    "model": {
      "id": "MOD003",
      "name": "iPad Pro 12.9"
    },
    "country": "UK",
    "analysisDescription": "Material recovery estimation from premium tablet including A-series chip, large battery, Liquid Retina display, and aluminum unibody.",
    "materials": [
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.08,
        "marketRatePerGram": 52.5,
        "currency": "GBP"
      },
      {
        "materialName": "Silver",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.6,
        "marketRatePerGram": 0.68,
        "currency": "GBP"
      },
      {
        "materialName": "Copper",
        "isPrecious": false,
        "estimatedQuantityGrams": 35,
        "marketRatePerGram": 0.007,
        "currency": "GBP"
      },
      {
        "materialName": "Aluminium",
        "isPrecious": false,
        "estimatedQuantityGrams": 180,
        "marketRatePerGram": 0.002,
        "currency": "GBP"
      },
      {
        "materialName": "Lithium",
        "isPrecious": false,
        "estimatedQuantityGrams": 6,
        "marketRatePerGram": 0.28,
        "currency": "GBP"
      },
      {
        "materialName": "Cobalt",
        "isPrecious": false,
        "estimatedQuantityGrams": 4,
        "marketRatePerGram": 0.38,
        "currency": "GBP"
      }
    ],
    "metadata": {
      "llmModel": "gemini-1.5-pro",
      "analysisTimestamp": "2026-03-04T18:30:00Z"
    }
  },
  "error": null
}
```

## Example 4: Desktop Computer (Custom Gaming PC)

### Request
```json
{
  "brand_id": "BR004",
  "brand_name": "Custom Build",
  "category_id": "CAT004",
  "category_name": "Desktop",
  "model_id": "MOD004",
  "model_name": "Gaming PC",
  "country": "Germany",
  "description": "High-end gaming desktop with RTX 4090, 64GB RAM, multiple storage drives"
}
```

### Response
```json
{
  "success": true,
  "timestamp": "2026-03-04T18:35:00Z",
  "processingTimeMs": 1678,
  "data": {
    "brand": {
      "id": "BR004",
      "name": "Custom Build"
    },
    "category": {
      "id": "CAT004",
      "name": "Desktop"
    },
    "model": {
      "id": "MOD004",
      "name": "Gaming PC"
    },
    "country": "Germany",
    "analysisDescription": "Material recovery estimation from high-end gaming desktop including motherboard, GPU, CPU, RAM modules, power supply, cooling system, and steel chassis.",
    "materials": [
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.35,
        "marketRatePerGram": 58.2,
        "currency": "EUR"
      },
      {
        "materialName": "Silver",
        "isPrecious": true,
        "estimatedQuantityGrams": 2.5,
        "marketRatePerGram": 0.75,
        "currency": "EUR"
      },
      {
        "materialName": "Palladium",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.12,
        "marketRatePerGram": 85.0,
        "currency": "EUR"
      },
      {
        "materialName": "Platinum",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.03,
        "marketRatePerGram": 28.5,
        "currency": "EUR"
      },
      {
        "materialName": "Copper",
        "isPrecious": false,
        "estimatedQuantityGrams": 450,
        "marketRatePerGram": 0.008,
        "currency": "EUR"
      },
      {
        "materialName": "Aluminium",
        "isPrecious": false,
        "estimatedQuantityGrams": 850,
        "marketRatePerGram": 0.002,
        "currency": "EUR"
      },
      {
        "materialName": "Steel",
        "isPrecious": false,
        "estimatedQuantityGrams": 3500,
        "marketRatePerGram": 0.0005,
        "currency": "EUR"
      },
      {
        "materialName": "Tin",
        "isPrecious": false,
        "estimatedQuantityGrams": 15,
        "marketRatePerGram": 0.025,
        "currency": "EUR"
      },
      {
        "materialName": "Tantalum",
        "isPrecious": false,
        "estimatedQuantityGrams": 0.8,
        "marketRatePerGram": 0.35,
        "currency": "EUR"
      }
    ],
    "metadata": {
      "llmModel": "groq-llama3",
      "analysisTimestamp": "2026-03-04T18:35:00Z"
    }
  },
  "error": null
}
```

## Example 5: Refrigerator (LG Smart Refrigerator)

### Request
```json
{
  "brand_id": "BR005",
  "brand_name": "LG",
  "category_id": "CAT005",
  "category_name": "Refrigerator",
  "model_id": "MOD005",
  "model_name": "Smart InstaView",
  "country": "India"
}
```

### Response
```json
{
  "success": true,
  "timestamp": "2026-03-04T18:40:00Z",
  "processingTimeMs": 1890,
  "data": {
    "brand": {
      "id": "BR005",
      "name": "LG"
    },
    "category": {
      "id": "CAT005",
      "name": "Refrigerator"
    },
    "model": {
      "id": "MOD005",
      "name": "Smart InstaView"
    },
    "country": "India",
    "analysisDescription": "Material recovery estimation from smart refrigerator including compressor, copper coils, control board, steel body, and insulation materials.",
    "materials": [
      {
        "materialName": "Copper",
        "isPrecious": false,
        "estimatedQuantityGrams": 2500,
        "marketRatePerGram": 0.85,
        "currency": "INR"
      },
      {
        "materialName": "Steel",
        "isPrecious": false,
        "estimatedQuantityGrams": 45000,
        "marketRatePerGram": 0.05,
        "currency": "INR"
      },
      {
        "materialName": "Aluminium",
        "isPrecious": false,
        "estimatedQuantityGrams": 3500,
        "marketRatePerGram": 0.25,
        "currency": "INR"
      },
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.02,
        "marketRatePerGram": 6500,
        "currency": "INR"
      },
      {
        "materialName": "Silver",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.15,
        "marketRatePerGram": 75,
        "currency": "INR"
      },
      {
        "materialName": "Plastic",
        "isPrecious": false,
        "estimatedQuantityGrams": 8000,
        "marketRatePerGram": 0.02,
        "currency": "INR"
      }
    ],
    "metadata": {
      "llmModel": "gemini-1.5-flash",
      "analysisTimestamp": "2026-03-04T18:40:00Z"
    }
  },
  "error": null
}
```

## Error Response Example

### Request with Invalid Data
```json
{
  "brand_id": "",
  "brand_name": "",
  "category_id": "CAT001",
  "category_name": "Smartphone",
  "model_id": "MOD001",
  "model_name": "Galaxy S21",
  "country": "India"
}
```

### Error Response
```json
{
  "success": false,
  "timestamp": "2026-03-04T18:45:00Z",
  "processingTimeMs": 5,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field cannot be empty"
  }
}
```

## Key Observations

### Material Quantities Vary by Device Type
- **Smartphones**: Small quantities (grams to tens of grams)
- **Laptops**: Medium quantities (tens to hundreds of grams)
- **Desktops**: Large quantities (hundreds to thousands of grams)
- **Appliances**: Very large quantities (kilograms)

### Precious Metal Content
- Higher in computing devices (more circuit boards)
- Lower in appliances (simpler electronics)
- Gold typically 0.02-0.35 grams per device
- Silver typically 0.15-2.5 grams per device

### Currency Adaptation
- Rates automatically adjusted for country
- Currency code matches country
- Market rates reflect local pricing

### Material Diversity
- Smartphones: 5-8 materials typically
- Laptops: 7-10 materials typically
- Desktops: 8-12 materials typically
- Appliances: 5-7 materials typically

## Notes

1. These are example responses - actual LLM responses may vary
2. Quantities are estimates based on typical device composition
3. Market rates are illustrative - actual rates will vary
4. The LLM may identify additional materials not shown here
5. Response times vary based on LLM provider and load
