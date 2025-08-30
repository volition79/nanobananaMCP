"""
Gemini 클라이언트 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
from typing import Dict, Any

from src.gemini_client import (
    GeminiClient,
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiQuotaExceededError,
    get_gemini_client,
    create_gemini_client
)
from src.config import get_settings


class TestGeminiClient:
    """GeminiClient 클래스 테스트"""
    
    @pytest.fixture
    def mock_settings(self):
        """테스트용 설정 모크"""
        settings = Mock()
        settings.google_ai_api_key = "test_api_key"
        settings.google_genai_use_vertexai = False
        settings.google_cloud_project = None
        settings.google_cloud_location = "global"
        settings.get_safety_settings.return_value = []
        return settings
    
    @pytest.fixture
    def client(self, mock_settings):
        """테스트용 클라이언트 인스턴스"""
        with patch('src.gemini_client.genai.Client'):
            return GeminiClient(mock_settings)
    
    def test_client_initialization(self, mock_settings):
        """클라이언트 초기화 테스트"""
        with patch('src.gemini_client.genai.Client') as mock_genai:
            client = GeminiClient(mock_settings)
            
            assert client.settings == mock_settings
            assert client._request_count == 0
            assert client._total_images_generated == 0
            assert client._total_cost == 0.0
            mock_genai.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """건강 상태 확인 성공 테스트"""
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock()]
        mock_response.candidates[0].content.parts[0].text = "Test response"
        
        client._make_request = AsyncMock(return_value=mock_response)
        
        result = await client.health_check()
        
        assert result["status"] == "healthy"
        assert result["api_accessible"] is True
        assert "model" in result
        assert "test_response_length" in result
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """건강 상태 확인 실패 테스트"""
        client._make_request = AsyncMock(side_effect=Exception("API Error"))
        
        result = await client.health_check()
        
        assert result["status"] == "unhealthy"
        assert result["api_accessible"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self, client):
        """이미지 생성 성공 테스트"""
        mock_response = Mock()
        mock_response.candidates = [Mock()]
        mock_response.candidates[0].content.parts = [Mock(), Mock()]
        mock_response.candidates[0].content.parts[0].text = "Generated image"
        mock_response.candidates[0].content.parts[1].inline_data = Mock()
        mock_response.candidates[0].content.parts[1].inline_data.data = b"fake_image_data"
        
        client._make_request = AsyncMock(return_value=mock_response)
        client._process_image_response = AsyncMock(return_value={
            "images": [b"fake_image_data"],
            "captions": ["Generated image"],
            "metadata": {"request_id": "test_123"}
        })
        
        result = await client.generate_image(
            prompt="Test prompt",
            aspect_ratio="1:1",
            quality="high"
        )
        
        assert "images" in result
        assert "captions" in result
        assert len(result["images"]) == 1
        assert client._total_images_generated == 1
    
    @pytest.mark.asyncio
    async def test_generate_image_api_error(self, client):
        """이미지 생성 API 에러 테스트"""
        client._make_request = AsyncMock(side_effect=Exception("Rate limit exceeded"))
        client._handle_api_error = Mock(return_value=GeminiRateLimitError("Rate limit", "E002"))
        
        with pytest.raises(GeminiRateLimitError):
            await client.generate_image("Test prompt")
    
    @pytest.mark.asyncio
    async def test_edit_image_success(self, client):
        """이미지 편집 성공 테스트"""
        with patch('src.gemini_client.Image.open') as mock_image_open:
            mock_image = Mock()
            mock_image_open.return_value = mock_image
            
            mock_response = Mock()
            client._make_request = AsyncMock(return_value=mock_response)
            client._process_image_response = AsyncMock(return_value={
                "images": [b"edited_image_data"],
                "captions": ["Edited image"],
                "metadata": {}
            })
            
            result = await client.edit_image(
                image_path="test_image.png",
                edit_prompt="Make it blue"
            )
            
            assert "images" in result
            assert len(result["images"]) == 1
    
    @pytest.mark.asyncio
    async def test_blend_images_success(self, client):
        """이미지 블렌딩 성공 테스트"""
        with patch('src.gemini_client.Image.open') as mock_image_open:
            mock_image1 = Mock()
            mock_image2 = Mock()
            mock_image_open.side_effect = [mock_image1, mock_image2]
            
            mock_response = Mock()
            client._make_request = AsyncMock(return_value=mock_response)
            client._process_image_response = AsyncMock(return_value={
                "images": [b"blended_image_data"],
                "captions": ["Blended image"],
                "metadata": {}
            })
            
            result = await client.blend_images(
                image_paths=["image1.png", "image2.png"],
                blend_prompt="Combine these images"
            )
            
            assert "images" in result
            assert len(result["images"]) == 1
    
    def test_enhance_prompt(self, client):
        """프롬프트 개선 테스트"""
        original = "A cat"
        enhanced = client._enhance_prompt(original, "16:9")
        
        assert "16:9 aspect ratio" in enhanced
        assert "high quality" in enhanced or "detailed" in enhanced
    
    def test_handle_api_error_rate_limit(self, client):
        """API 에러 처리 - 요청 제한 테스트"""
        error = Exception("rate limit exceeded")
        result = client._handle_api_error(error)
        
        assert isinstance(result, GeminiRateLimitError)
    
    def test_handle_api_error_quota_exceeded(self, client):
        """API 에러 처리 - 할당량 초과 테스트"""
        error = Exception("quota exceeded")
        result = client._handle_api_error(error)
        
        assert isinstance(result, GeminiQuotaExceededError)
    
    def test_get_statistics(self, client):
        """통계 정보 테스트"""
        client._request_count = 5
        client._total_images_generated = 10
        client._total_cost = 0.39
        
        stats = client.get_statistics()
        
        assert stats["request_count"] == 5
        assert stats["total_images_generated"] == 10
        assert stats["total_cost_usd"] == 0.39
        assert stats["average_images_per_request"] == 2.0
    
    def test_reset_statistics(self, client):
        """통계 초기화 테스트"""
        client._request_count = 5
        client._total_images_generated = 10
        client._total_cost = 0.39
        
        client.reset_statistics()
        
        assert client._request_count == 0
        assert client._total_images_generated == 0
        assert client._total_cost == 0.0


class TestGeminiClientFunctions:
    """Gemini 클라이언트 전역 함수 테스트"""
    
    def test_get_gemini_client_singleton(self):
        """싱글톤 클라이언트 테스트"""
        with patch('src.gemini_client.GeminiClient') as mock_client:
            client1 = get_gemini_client()
            client2 = get_gemini_client()
            
            assert client1 == client2
            mock_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_gemini_client(self):
        """새 클라이언트 생성 테스트"""
        mock_settings = Mock()
        
        with patch('src.gemini_client.GeminiClient') as mock_client_class:
            mock_client = Mock()
            mock_client.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_client_class.return_value = mock_client
            
            result = await create_gemini_client(mock_settings)
            
            assert result == mock_client
            mock_client.health_check.assert_called_once()


class TestGeminiAPIErrors:
    """Gemini API 에러 클래스 테스트"""
    
    def test_gemini_api_error(self):
        """기본 API 에러 테스트"""
        error = GeminiAPIError("Test error", "E001", {"detail": "test"})
        
        assert error.message == "Test error"
        assert error.code == "E001"
        assert error.details == {"detail": "test"}
        assert str(error) == "Test error"
    
    def test_rate_limit_error(self):
        """요청 제한 에러 테스트"""
        error = GeminiRateLimitError("Rate limit", "E002")
        
        assert isinstance(error, GeminiAPIError)
        assert error.message == "Rate limit"
        assert error.code == "E002"
    
    def test_quota_exceeded_error(self):
        """할당량 초과 에러 테스트"""
        error = GeminiQuotaExceededError("Quota exceeded", "E003")
        
        assert isinstance(error, GeminiAPIError)
        assert error.message == "Quota exceeded"
        assert error.code == "E003"