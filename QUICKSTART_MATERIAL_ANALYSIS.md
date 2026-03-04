# Quick Start Guide - Material Analysis Endpoint

## 🚀 Get Started in 3 Steps

### Step 1: Start the Server
```bash
python run.py
```

The server will start on `http://localhost:8000`

### Step 2: Test the Endpoint

Choose your preferred method:

#### Option A: Web Interface (Easiest)
Open in your browser:
```
http://localhost:8000/static/material_analysis_test.html
```

Fill in the form and click "Analyze Materials"

#### Option B: Python Script
```bash
python test_material_analysis.py
```

#### Option C: Interactive API Docs
```
http://localhost:8000/docs
```

Find the `/api/v1/analyze-materials` endpoint and try it out

### Step 3: Integrate into Your App

#### Python Example
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/analyze-materials",
    json={
        "brand_id": "BR001",
        "brand_name": "Samsung",
        "category_id": "CAT001",
        "category_name": "Smartphone",
        "model_id": "MOD001",
        "model_name": "Galaxy S21",
        "country": "India"
    }
)

data = response.json()
if data["success"]:
    for material in data["data"]["materials"]:
        print(f"{material['materialName']}: {material['estimatedQuantityGrams']}g @ {material['marketRatePerGram']} {material['currency']}/g")
```

#### JavaScript Example
```javascript
fetch("http://localhost:8000/api/v1/analyze-materials", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
        brand_id: "BR001",
        brand_name: "Samsung",
        category_id: "CAT001",
        category_name: "Smartphone",
        model_id: "MOD001",
        model_name: "Galaxy S21",
        country: "India"
    })
})
.then(res => res.json())
.then(data => console.log(data));
```

## 📋 What You'll Get

The endpoint returns:
- List of materials (Gold, Silver, Copper, Lithium, etc.)
- Estimated quantity in grams for each material
- Current market rate per gram
- Currency for the specified country
- Whether each material is precious or not

## 🔑 Key Points

- **No calculations needed**: You get quantity and rate separately
- **Country-specific**: Market rates are for the country you specify
- **Comprehensive**: Includes precious metals, base metals, battery materials, and rare earth elements
- **Fast**: Typically responds in 1-3 seconds
- **Rate limited**: 10 requests per minute

## 📚 Full Documentation

For complete details, see:
- `MATERIAL_ANALYSIS_API.md` - Full API documentation
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- `http://localhost:8000/docs` - Interactive API documentation

## ❓ Troubleshooting

**Server won't start?**
- Check that port 8000 is available
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify your `.env` file has required API keys

**Getting errors?**
- Check the error code in the response
- See `MATERIAL_ANALYSIS_API.md` for error code meanings
- Ensure LLM API keys are configured in `.env`

**Need help?**
- Check server logs for detailed error messages
- Review the example requests in `MATERIAL_ANALYSIS_API.md`
- Test with the web interface first to verify the endpoint works

## 🎯 Example Response

```json
{
  "success": true,
  "data": {
    "materials": [
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.034,
        "marketRatePerGram": 6500,
        "currency": "INR"
      },
      {
        "materialName": "Copper",
        "isPrecious": false,
        "estimatedQuantityGrams": 15,
        "marketRatePerGram": 0.85,
        "currency": "INR"
      }
    ]
  }
}
```

Happy analyzing! 🔬
