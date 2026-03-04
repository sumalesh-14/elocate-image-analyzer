# Material Analysis Endpoint - Architecture

## System Flow

```
┌─────────────┐
│   Client    │
│ Application │
└──────┬──────┘
       │
       │ POST /api/v1/analyze-materials
       │ {brand, category, model, country}
       │
       ▼
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  ┌───────────────────────────────────┐  │
│  │     app/api/routes.py             │  │
│  │  analyze_materials() endpoint     │  │
│  │  - Rate limiting (10/min)         │  │
│  │  - Request validation             │  │
│  │  - Error handling                 │  │
│  └──────────────┬────────────────────┘  │
│                 │                        │
│                 ▼                        │
│  ┌───────────────────────────────────┐  │
│  │  app/services/material_analyzer.py│  │
│  │  MaterialAnalyzerService          │  │
│  │  - Build LLM prompt               │  │
│  │  - Parse LLM response             │  │
│  │  - Validate materials             │  │
│  └──────────────┬────────────────────┘  │
│                 │                        │
│                 ▼                        │
│  ┌───────────────────────────────────┐  │
│  │   app/services/llm_router.py      │  │
│  │   LLM Service (existing)          │  │
│  │   - Route to available LLM        │  │
│  │   - Handle API calls              │  │
│  └──────────────┬────────────────────┘  │
└─────────────────┼────────────────────────┘
                  │
                  ▼
         ┌────────────────┐
         │  LLM Provider  │
         │  (Gemini/      │
         │   OpenAI/Groq) │
         └────────┬───────┘
                  │
                  │ Returns JSON with materials
                  │
                  ▼
         ┌────────────────┐
         │  Parse & Build │
         │  Response      │
         └────────┬───────┘
                  │
                  ▼
         ┌────────────────┐
         │  Return to     │
         │  Client        │
         └────────────────┘
```

## Component Breakdown

### 1. API Layer (`app/api/routes.py`)
**Responsibilities:**
- Receive HTTP requests
- Validate request format
- Apply rate limiting
- Handle errors
- Return standardized responses

**Key Function:**
```python
@router.post("/api/v1/analyze-materials")
async def analyze_materials(request, analysis_request)
```

### 2. Service Layer (`app/services/material_analyzer.py`)
**Responsibilities:**
- Build LLM prompts with device context
- Call LLM service
- Parse and validate LLM responses
- Extract material data
- Handle service-level errors

**Key Function:**
```python
async def analyze_materials(request) -> tuple[List[MaterialData], str, str]
```

### 3. LLM Router (`app/services/llm_router.py`)
**Responsibilities:**
- Route requests to available LLM providers
- Handle API authentication
- Manage retries and failover
- Return standardized responses

**Existing Service** - No changes needed

### 4. Data Models (`app/models/material_analysis.py`)
**Responsibilities:**
- Define request/response schemas
- Validate data types and constraints
- Serialize/deserialize JSON

**Key Models:**
- `MaterialAnalysisRequest`: Input validation
- `MaterialAnalysisResponse`: Output format
- `MaterialData`: Individual material info

## Data Flow

### Request Flow
```
1. Client sends JSON request
   ↓
2. Pydantic validates request (MaterialAnalysisRequest)
   ↓
3. Rate limiter checks request count
   ↓
4. MaterialAnalyzerService builds prompt
   ↓
5. LLM Router sends to available LLM
   ↓
6. LLM analyzes device and returns JSON
   ↓
7. Service parses and validates response
   ↓
8. Pydantic builds response (MaterialAnalysisResponse)
   ↓
9. FastAPI returns JSON to client
```

### Prompt Structure
```
Device Information:
- Brand: Samsung
- Category: Smartphone
- Model: Galaxy S21
- Country: India

Task:
1. Identify ALL recyclable materials
2. Estimate quantity in grams
3. Provide market rate per gram
4. Include precious and base metals

Return JSON:
{
  "materials": [...],
  "analysisDescription": "..."
}
```

### Response Structure
```json
{
  "success": true,
  "timestamp": "ISO-8601",
  "processingTimeMs": 1234,
  "data": {
    "brand": {...},
    "category": {...},
    "model": {...},
    "country": "India",
    "analysisDescription": "...",
    "materials": [
      {
        "materialName": "Gold",
        "isPrecious": true,
        "estimatedQuantityGrams": 0.034,
        "marketRatePerGram": 6500,
        "currency": "INR"
      }
    ],
    "metadata": {
      "llmModel": "gemini-1.5-flash",
      "analysisTimestamp": "ISO-8601"
    }
  }
}
```

## Error Handling

### Error Flow
```
Error Occurs
    ↓
MaterialAnalysisError raised
    ↓
Caught in endpoint handler
    ↓
Logged with context
    ↓
Converted to error response
    ↓
Returned to client with error code
```

### Error Types
- **Validation Errors**: Invalid request format (400)
- **LLM Errors**: No response or invalid format (500)
- **Service Errors**: Analysis failures (500)
- **Rate Limit Errors**: Too many requests (429)

## Security Considerations

1. **Rate Limiting**: 10 requests/minute per IP
2. **Input Validation**: Pydantic validates all inputs
3. **Output Sanitization**: Structured JSON responses only
4. **Error Messages**: No sensitive data in errors
5. **API Authentication**: Uses existing middleware

## Performance Characteristics

- **Average Response Time**: 1-3 seconds
- **LLM Call**: ~1-2 seconds
- **Parsing/Validation**: <100ms
- **Rate Limit**: 10 requests/minute
- **Concurrent Requests**: Handled by FastAPI async

## Scalability

### Current Design
- Stateless endpoint (easy to scale horizontally)
- Async/await for non-blocking I/O
- LLM router handles multiple providers
- No database dependencies

### Future Enhancements
- Cache common device analyses
- Batch processing for multiple devices
- Real-time commodity price integration
- Historical price tracking
- Material composition database

## Integration Points

### Existing Services Used
1. **LLM Router**: For AI analysis
2. **Rate Limiter**: For request throttling
3. **Logger**: For monitoring and debugging
4. **Config**: For environment settings

### New Services Added
1. **Material Analyzer**: Core analysis logic
2. **Material Models**: Data validation

## Testing Strategy

### Unit Tests
- Model validation
- Prompt building
- Response parsing
- Error handling

### Integration Tests
- End-to-end API calls
- LLM integration
- Error scenarios
- Rate limiting

### Manual Testing
- Web interface
- Python script
- API documentation UI
- cURL commands

## Monitoring & Logging

### Logged Events
- Request received (with device info)
- LLM call initiated
- Materials parsed (count)
- Response sent (processing time)
- Errors (with context)

### Metrics to Track
- Request count
- Success rate
- Average processing time
- Error rates by type
- LLM provider usage
