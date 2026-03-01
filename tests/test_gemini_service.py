"""
Unit tests for Gemini service.

Tests specific examples and edge cases for Gemini Vision API integration.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import BytesIO
from PIL import Image

from app.services.gemini_service import (
    GeminiService,
    GeminiAPIError,
    DEVICE_ANALYSIS_PROMPT
)


def create_test_image(width=100, height=100):
    """Helper to create valid test image bytes."""
    img = Image.new("RGB", (width, height), color="blue")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def create_mock_gemini_response(text_content):
    """Helper to create mock Gemini API response."""
    mock_response = Mock()
    mock_response.text = text_content
    return mock_response


class TestSuccessfulAPIResponse:
    """Test successful API response parsing."""
    
    @pytest.mark.asyncio
    async def test_successful_device_identification(self):
        """Test successful device identification with valid JSON response."""
        image_bytes = create_test_image()
        
        # Mock response with valid device data
        response_json = {
            "category": "mobile",
            "brand": "Samsung",
            "model": "Galaxy S21",
            "deviceType": "smartphone",
            "confidenceScore": 0.87,
            "attributes": {
                "color": "black",
                "condition": "good"
            }
        }
        
        mock_response = create_mock_gemini_response(json.dumps(response_json))
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            # Setup mock
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Mock the _generate_content method
            service._generate_content = AsyncMock(return_value=mock_response)
            
            # Execute
            result = await service.analyze_device_image(image_bytes)
            
            # Verify
            assert result["category"] == "mobile"
            assert result["brand"] == "Samsung"
            assert result["model"] == "Galaxy S21"
            assert result["deviceType"] == "smartphone"
            assert result["confidenceScore"] == 0.87
            assert result["attributes"]["color"] == "black"
    
    @pytest.mark.asyncio
    async def test_response_with_null_brand_model(self):
        """Test response parsing with null brand and model."""
        image_bytes = create_test_image()
        
        response_json = {
            "category": "charger",
            "brand": None,
            "model": None,
            "deviceType": "USB wall charger",
            "confidenceScore": 0.42,
            "attributes": {"color": "white"}
        }
        
        mock_response = create_mock_gemini_response(json.dumps(response_json))
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            service._generate_content = AsyncMock(return_value=mock_response)
            
            result = await service.analyze_device_image(image_bytes)
            
            assert result["brand"] is None
            assert result["model"] is None
            assert result["confidenceScore"] == 0.42
    
    @pytest.mark.asyncio
    async def test_response_with_markdown_code_blocks(self):
        """Test parsing response with markdown code blocks."""
        image_bytes = create_test_image()
        
        response_json = {
            "category": "laptop",
            "brand": "Apple",
            "model": "MacBook Pro",
            "deviceType": "laptop",
            "confidenceScore": 0.95,
            "attributes": {}
        }
        
        # Wrap JSON in markdown code blocks
        markdown_response = f"```json\n{json.dumps(response_json)}\n```"
        mock_response = create_mock_gemini_response(markdown_response)
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            service._generate_content = AsyncMock(return_value=mock_response)
            
            result = await service.analyze_device_image(image_bytes)
            
            assert result["category"] == "laptop"
            assert result["brand"] == "Apple"


class TestAPIUnavailability:
    """Test API unavailability handling."""
    
    @pytest.mark.asyncio
    async def test_api_connection_error(self):
        """Test handling of API connection errors."""
        image_bytes = create_test_image()
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Mock connection error
            service._generate_content = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            with pytest.raises(GeminiAPIError) as exc_info:
                await service.analyze_device_image(image_bytes, max_retries=1)
            
            assert "Gemini API error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_api_service_unavailable(self):
        """Test handling of 503 service unavailable."""
        image_bytes = create_test_image()
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Mock 503 error (transient, will be retried)
            service._generate_content = AsyncMock(
                side_effect=Exception("503 Service Unavailable")
            )
            
            with pytest.raises(GeminiAPIError) as exc_info:
                await service.analyze_device_image(image_bytes, max_retries=2)
            
            # Should retry and eventually fail with retry exhaustion message
            assert "failed after 2 attempts" in str(exc_info.value) or "503" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_check_api_availability_success(self):
        """Test API availability check when API is available."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Mock successful API call
            with patch.object(service.model, 'generate_content', return_value=Mock()):
                result = await service.check_api_availability()
                assert result is True
    
    @pytest.mark.asyncio
    async def test_check_api_availability_failure(self):
        """Test API availability check when API is unavailable."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Mock failed API call
            with patch.object(service.model, 'generate_content', side_effect=Exception("API Error")):
                result = await service.check_api_availability()
                assert result is False


class TestTimeoutScenarios:
    """Test timeout scenarios."""
    
    @pytest.mark.asyncio
    async def test_api_request_timeout(self):
        """Test handling of API request timeout."""
        image_bytes = create_test_image()
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Mock timeout
            service._generate_content = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            
            with pytest.raises(TimeoutError) as exc_info:
                await service.analyze_device_image(image_bytes)
            
            assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_includes_duration(self):
        """Test timeout error includes timeout duration."""
        image_bytes = create_test_image()
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            with patch('app.services.gemini_service.settings') as mock_settings:
                mock_settings.REQUEST_TIMEOUT = 30
                
                mock_model = Mock()
                mock_genai.GenerativeModel.return_value = mock_model
                
                service = GeminiService()
                service._generate_content = AsyncMock(
                    side_effect=asyncio.TimeoutError()
                )
                
                with pytest.raises(TimeoutError) as exc_info:
                    await service.analyze_device_image(image_bytes)
                
                assert "30 seconds" in str(exc_info.value)


class TestInvalidJSONResponse:
    """Test invalid JSON response handling."""
    
    @pytest.mark.asyncio
    async def test_non_json_response(self):
        """Test handling of non-JSON response."""
        image_bytes = create_test_image()
        
        mock_response = create_mock_gemini_response("This is not JSON")
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            service._generate_content = AsyncMock(return_value=mock_response)
            
            with pytest.raises(ValueError) as exc_info:
                await service.analyze_device_image(image_bytes, max_retries=1)
            
            assert "invalid JSON" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_malformed_json_response(self):
        """Test handling of malformed JSON."""
        image_bytes = create_test_image()
        
        mock_response = create_mock_gemini_response('{"category": "mobile", invalid}')
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            service._generate_content = AsyncMock(return_value=mock_response)
            
            with pytest.raises(ValueError) as exc_info:
                await service.analyze_device_image(image_bytes, max_retries=1)
            
            assert "invalid JSON" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test handling of response missing required fields."""
        image_bytes = create_test_image()
        
        # Missing 'model' and 'deviceType' fields
        incomplete_json = {
            "category": "mobile",
            "brand": "Samsung",
            "confidenceScore": 0.8,
            "attributes": {}
        }
        
        mock_response = create_mock_gemini_response(json.dumps(incomplete_json))
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            service._generate_content = AsyncMock(return_value=mock_response)
            
            # Validation errors are wrapped in GeminiAPIError
            with pytest.raises(GeminiAPIError) as exc_info:
                await service.analyze_device_image(image_bytes)
            
            assert "Missing required field" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_invalid_confidence_score(self):
        """Test handling of invalid confidence score."""
        image_bytes = create_test_image()
        
        # Confidence score out of range
        invalid_json = {
            "category": "mobile",
            "brand": "Samsung",
            "model": "Galaxy",
            "deviceType": "smartphone",
            "confidenceScore": 1.5,  # Invalid: > 1.0
            "attributes": {}
        }
        
        mock_response = create_mock_gemini_response(json.dumps(invalid_json))
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            service._generate_content = AsyncMock(return_value=mock_response)
            
            # Validation errors are wrapped in GeminiAPIError
            with pytest.raises(GeminiAPIError) as exc_info:
                await service.analyze_device_image(image_bytes)
            
            assert "Invalid confidence score" in str(exc_info.value)


class TestRetryLogic:
    """Test retry logic for transient failures."""
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Test retry on transient network error."""
        image_bytes = create_test_image()
        
        response_json = {
            "category": "mobile",
            "brand": "Samsung",
            "model": "Galaxy S21",
            "deviceType": "smartphone",
            "confidenceScore": 0.87,
            "attributes": {}
        }
        
        mock_response = create_mock_gemini_response(json.dumps(response_json))
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # First call fails with transient error, second succeeds
            service._generate_content = AsyncMock(
                side_effect=[
                    Exception("503 Service temporarily unavailable"),
                    mock_response
                ]
            )
            
            # Should succeed after retry
            result = await service.analyze_device_image(image_bytes, max_retries=3)
            
            assert result["category"] == "mobile"
            assert service._generate_content.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Test retry on rate limit error."""
        image_bytes = create_test_image()
        
        response_json = {
            "category": "laptop",
            "brand": "Apple",
            "model": "MacBook",
            "deviceType": "laptop",
            "confidenceScore": 0.9,
            "attributes": {}
        }
        
        mock_response = create_mock_gemini_response(json.dumps(response_json))
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # First call hits rate limit, second succeeds
            service._generate_content = AsyncMock(
                side_effect=[
                    Exception("429 Rate limit exceeded"),
                    mock_response
                ]
            )
            
            result = await service.analyze_device_image(image_bytes, max_retries=3)
            
            assert result["category"] == "laptop"
            assert service._generate_content.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test that retries are exhausted after max attempts."""
        image_bytes = create_test_image()
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Always fail with transient error
            service._generate_content = AsyncMock(
                side_effect=Exception("503 Service unavailable")
            )
            
            with pytest.raises(GeminiAPIError) as exc_info:
                await service.analyze_device_image(image_bytes, max_retries=3)
            
            # Should contain either retry exhaustion message or the error itself
            error_msg = str(exc_info.value)
            assert "failed after 3 attempts" in error_msg or "503" in error_msg
            assert service._generate_content.call_count == 3
    
    @pytest.mark.asyncio
    async def test_no_retry_on_non_transient_error(self):
        """Test that non-transient errors are not retried."""
        image_bytes = create_test_image()
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Non-transient error (authentication)
            service._generate_content = AsyncMock(
                side_effect=Exception("401 Unauthorized")
            )
            
            with pytest.raises(GeminiAPIError):
                await service.analyze_device_image(image_bytes, max_retries=3)
            
            # Should only be called once (no retries)
            assert service._generate_content.call_count == 1
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff between retries."""
        image_bytes = create_test_image()
        
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            # Mock sleep to track backoff times
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                service._generate_content = AsyncMock(
                    side_effect=Exception("503 Service unavailable")
                )
                
                try:
                    await service.analyze_device_image(image_bytes, max_retries=3)
                except GeminiAPIError:
                    pass
                
                # Verify exponential backoff: 1s, 2s
                assert mock_sleep.call_count == 2
                calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert calls[0] == 1  # 2^0
                assert calls[1] == 2  # 2^1


class TestIsTransientError:
    """Test the _is_transient_error method."""
    
    def test_timeout_is_transient(self):
        """Test timeout errors are considered transient."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            assert service._is_transient_error(Exception("Request timeout")) is True
            assert service._is_transient_error(Exception("Connection timeout")) is True
    
    def test_connection_errors_are_transient(self):
        """Test connection errors are considered transient."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            assert service._is_transient_error(Exception("Connection refused")) is True
            assert service._is_transient_error(Exception("Network error")) is True
    
    def test_5xx_errors_are_transient(self):
        """Test 5xx server errors are considered transient."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            assert service._is_transient_error(Exception("500 Internal Server Error")) is True
            assert service._is_transient_error(Exception("502 Bad Gateway")) is True
            assert service._is_transient_error(Exception("503 Service Unavailable")) is True
            assert service._is_transient_error(Exception("504 Gateway Timeout")) is True
    
    def test_rate_limit_is_transient(self):
        """Test rate limit errors are considered transient."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            assert service._is_transient_error(Exception("429 Rate limit exceeded")) is True
            assert service._is_transient_error(Exception("Rate limit")) is True
    
    def test_4xx_errors_are_not_transient(self):
        """Test 4xx client errors are not considered transient."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            assert service._is_transient_error(Exception("401 Unauthorized")) is False
            assert service._is_transient_error(Exception("403 Forbidden")) is False
            assert service._is_transient_error(Exception("400 Bad Request")) is False


class TestParseResponse:
    """Test the _parse_response method."""
    
    def test_parse_plain_json(self):
        """Test parsing plain JSON response."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            json_str = '{"category": "mobile", "brand": "Samsung"}'
            result = service._parse_response(json_str)
            
            assert result["category"] == "mobile"
            assert result["brand"] == "Samsung"
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            json_str = '```json\n{"category": "laptop"}\n```'
            result = service._parse_response(json_str)
            
            assert result["category"] == "laptop"
    
    def test_parse_json_with_plain_markdown(self):
        """Test parsing JSON wrapped in plain markdown blocks."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            json_str = '```\n{"category": "tablet"}\n```'
            result = service._parse_response(json_str)
            
            assert result["category"] == "tablet"


class TestValidateResponse:
    """Test the _validate_response method."""
    
    def test_valid_response_passes(self):
        """Test valid response passes validation."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            valid_response = {
                "category": "mobile",
                "brand": "Samsung",
                "model": "Galaxy",
                "deviceType": "smartphone",
                "confidenceScore": 0.8,
                "attributes": {}
            }
            
            # Should not raise
            service._validate_response(valid_response)
    
    def test_missing_field_raises_error(self):
        """Test missing required field raises ValueError."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            invalid_response = {
                "category": "mobile",
                "brand": "Samsung"
                # Missing other required fields
            }
            
            with pytest.raises(ValueError) as exc_info:
                service._validate_response(invalid_response)
            
            assert "Missing required field" in str(exc_info.value)
    
    def test_invalid_confidence_score_raises_error(self):
        """Test invalid confidence score raises ValueError."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            invalid_response = {
                "category": "mobile",
                "brand": "Samsung",
                "model": "Galaxy",
                "deviceType": "smartphone",
                "confidenceScore": 2.0,  # Invalid
                "attributes": {}
            }
            
            with pytest.raises(ValueError) as exc_info:
                service._validate_response(invalid_response)
            
            assert "Invalid confidence score" in str(exc_info.value)
    
    def test_non_dict_attributes_raises_error(self):
        """Test non-dictionary attributes raises ValueError."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            service = GeminiService()
            
            invalid_response = {
                "category": "mobile",
                "brand": "Samsung",
                "model": "Galaxy",
                "deviceType": "smartphone",
                "confidenceScore": 0.8,
                "attributes": "not a dict"  # Invalid
            }
            
            with pytest.raises(ValueError) as exc_info:
                service._validate_response(invalid_response)
            
            assert "Attributes field must be a dictionary" in str(exc_info.value)

