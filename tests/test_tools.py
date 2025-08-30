"""
MCP 도구들 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from src.tools import generate, edit, blend, status
from src.models.schemas import (
    GenerateImageRequest,
    EditImageRequest, 
    BlendImagesRequest
)


class TestGenerateTool:
    """nanobanana_generate 도구 테스트"""
    
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """이미지 생성 성공 테스트"""
        with patch('src.tools.generate.get_gemini_client') as mock_client, \
             patch('src.tools.generate.get_prompt_optimizer') as mock_optimizer, \
             patch('src.tools.generate.get_image_handler') as mock_handler, \
             patch('src.tools.generate.get_file_manager') as mock_file_manager:
            
            # 모킹 설정
            mock_gemini = Mock()
            mock_gemini.generate_image = AsyncMock(return_value={
                "images": [b"fake_image_data"],
                "metadata": {"request_id": "test_123"}
            })
            mock_client.return_value = mock_gemini
            
            mock_opt = Mock()
            mock_opt.optimize_prompt.return_value = "optimized test prompt"
            mock_optimizer.return_value = mock_opt
            
            mock_fm = Mock()
            mock_fm.save_image_with_metadata.return_value = {
                "success": True,
                "filename": "test.png",
                "filepath": "/test/test.png",
                "metadata": {
                    "created_at": "2025-01-01T00:00:00",
                    "file_size": 1024,
                    "hash": "abcd1234"
                }
            }
            mock_file_manager.return_value = mock_fm
            
            # 테스트 실행
            result = await generate.nanobanana_generate(
                prompt="test prompt",
                quality="high"
            )
            
            # 검증
            assert result["success"] is True
            assert "images" in result
            assert len(result["images"]) == 1
            mock_gemini.generate_image.assert_called_once()
            mock_fm.save_image_with_metadata.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_validation_error(self):
        """이미지 생성 검증 오류 테스트"""
        result = await generate.nanobanana_generate(
            prompt="",  # 빈 프롬프트
            quality="invalid"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_generate_api_error(self):
        """이미지 생성 API 오류 테스트"""
        with patch('src.tools.generate.get_gemini_client') as mock_client:
            mock_gemini = Mock()
            mock_gemini.generate_image = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_client.return_value = mock_gemini
            
            result = await generate.nanobanana_generate(
                prompt="test prompt"
            )
            
            assert result["success"] is False
            assert "API Error" in result["message"] or "API Error" in result.get("error", {}).get("message", "")


class TestEditTool:
    """nanobanana_edit 도구 테스트"""
    
    @pytest.mark.asyncio
    async def test_edit_success(self):
        """이미지 편집 성공 테스트"""
        with patch('src.tools.edit.get_gemini_client') as mock_client, \
             patch('src.tools.edit.get_image_handler') as mock_handler, \
             patch('src.tools.edit.get_file_manager') as mock_file_manager, \
             patch('pathlib.Path') as mock_path:
            
            # Path 모킹
            mock_path_instance = Mock()
            mock_path_instance.absolute.return_value = "/test/input.png"
            mock_path.return_value = mock_path_instance
            
            # 이미지 핸들러 모킹
            mock_img_handler = Mock()
            mock_image = Mock()
            mock_img_handler.load_image.return_value = mock_image
            mock_img_handler.get_image_info.return_value = {
                "size": (1024, 1024),
                "format": "PNG",
                "mode": "RGB"
            }
            mock_handler.return_value = mock_img_handler
            
            # Gemini 클라이언트 모킹
            mock_gemini = Mock()
            mock_gemini.edit_image = AsyncMock(return_value={
                "images": [b"edited_image_data"],
                "metadata": {"request_id": "test_123"}
            })
            mock_client.return_value = mock_gemini
            
            # 파일 매니저 모킹
            mock_fm = Mock()
            mock_fm.save_image_with_metadata.return_value = {
                "success": True,
                "filename": "edited.png",
                "filepath": "/test/edited.png",
                "metadata": {
                    "created_at": "2025-01-01T00:00:00",
                    "file_size": 1024,
                    "hash": "abcd1234"
                }
            }
            mock_file_manager.return_value = mock_fm
            
            # 테스트 실행
            result = await edit.nanobanana_edit(
                image_path="/test/input.png",
                edit_prompt="make it blue"
            )
            
            # 검증
            assert result["success"] is True
            assert "edited_image" in result
            mock_gemini.edit_image.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_edit_file_not_found(self):
        """이미지 편집 - 파일 없음 테스트"""
        result = await edit.nanobanana_edit(
            image_path="/nonexistent/file.png",
            edit_prompt="edit this"
        )
        
        assert result["success"] is False
        assert "error" in result


class TestBlendTool:
    """nanobanana_blend 도구 테스트"""
    
    @pytest.mark.asyncio
    async def test_blend_success(self):
        """이미지 블렌딩 성공 테스트"""
        with patch('src.tools.blend.get_gemini_client') as mock_client, \
             patch('src.tools.blend.get_image_handler') as mock_handler, \
             patch('src.tools.blend.get_file_manager') as mock_file_manager, \
             patch('pathlib.Path') as mock_path:
            
            # Path 모킹
            mock_path_instance = Mock()
            mock_path_instance.absolute.return_value = "/test/image.png"
            mock_path_instance.stat.return_value.st_size = 1024
            mock_path.return_value = mock_path_instance
            
            # 이미지 핸들러 모킹
            mock_img_handler = Mock()
            mock_image = Mock()
            mock_img_handler.load_image.return_value = mock_image
            mock_img_handler.get_image_info.return_value = {
                "size": (1024, 1024),
                "format": "PNG",
                "mode": "RGB"
            }
            mock_handler.return_value = mock_img_handler
            
            # Gemini 클라이언트 모킹
            mock_gemini = Mock()
            mock_gemini.blend_images = AsyncMock(return_value={
                "images": [b"blended_image_data"],
                "metadata": {"request_id": "test_123"}
            })
            mock_client.return_value = mock_gemini
            
            # 파일 매니저 모킹
            mock_fm = Mock()
            mock_fm.save_image_with_metadata.return_value = {
                "success": True,
                "filename": "blended.png", 
                "filepath": "/test/blended.png",
                "metadata": {
                    "created_at": "2025-01-01T00:00:00",
                    "file_size": 1024,
                    "hash": "abcd1234"
                }
            }
            mock_file_manager.return_value = mock_fm
            
            # 테스트 실행
            result = await blend.nanobanana_blend(
                image_paths=["/test/image1.png", "/test/image2.png"],
                blend_prompt="combine these images"
            )
            
            # 검증
            assert result["success"] is True
            assert "blended_image" in result
            assert "source_images" in result
            assert len(result["source_images"]) == 2
            mock_gemini.blend_images.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_blend_insufficient_images(self):
        """이미지 블렌딩 - 이미지 부족 테스트"""
        result = await blend.nanobanana_blend(
            image_paths=["/test/single.png"],  # 2개 미만
            blend_prompt="blend this"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_blend_too_many_images(self):
        """이미지 블렌딩 - 이미지 과다 테스트"""
        image_paths = [f"/test/image{i}.png" for i in range(5)]  # 4개 초과
        
        result = await blend.nanobanana_blend(
            image_paths=image_paths,
            blend_prompt="blend all these"
        )
        
        assert result["success"] is False
        assert "error" in result


class TestStatusTool:
    """nanobanana_status 도구 테스트"""
    
    @pytest.mark.asyncio
    async def test_status_basic(self):
        """기본 상태 확인 테스트"""
        with patch('src.tools.status.collect_api_status') as mock_api, \
             patch('src.tools.status.collect_server_info') as mock_server, \
             patch('src.tools.status.collect_performance_stats') as mock_perf, \
             patch('src.tools.status.collect_storage_stats') as mock_storage, \
             patch('src.tools.status.collect_system_info') as mock_system:
            
            # 모킹 설정
            mock_api.return_value = {"api_accessible": True, "status": "healthy"}
            mock_server.return_value = {
                "name": "nanobanana",
                "version": "1.0.0",
                "uptime": 3600
            }
            mock_perf.return_value = {"total_operations": 10}
            mock_storage.return_value = {"total_files": 5}
            mock_system.return_value = {"platform": "test"}
            
            # 테스트 실행
            result = await status.nanobanana_status()
            
            # 검증
            assert result["success"] is True
            assert "server_name" in result
            assert "version" in result
            assert "uptime" in result
            assert "api_status" in result
    
    @pytest.mark.asyncio
    async def test_status_with_history(self):
        """히스토리 포함 상태 확인 테스트"""
        with patch('src.tools.status.collect_api_status'), \
             patch('src.tools.status.collect_server_info'), \
             patch('src.tools.status.collect_performance_stats'), \
             patch('src.tools.status.collect_storage_stats'), \
             patch('src.tools.status.collect_system_info'), \
             patch('src.tools.status.collect_recent_history') as mock_history:
            
            mock_history.return_value = {
                "recent_generated": [],
                "recent_edited": [],
                "recent_blended": []
            }
            
            result = await status.nanobanana_status(include_history=True)
            
            assert result["success"] is True
            assert "recent_history" in result
    
    @pytest.mark.asyncio
    async def test_status_reset_stats(self):
        """통계 초기화 상태 확인 테스트"""
        with patch('src.tools.status.get_gemini_client') as mock_client, \
             patch('src.tools.status.collect_api_status'), \
             patch('src.tools.status.collect_server_info'), \
             patch('src.tools.status.collect_performance_stats'), \
             patch('src.tools.status.collect_storage_stats'), \
             patch('src.tools.status.collect_system_info'):
            
            mock_gemini = Mock()
            mock_gemini.reset_statistics = Mock()
            mock_client.return_value = mock_gemini
            
            result = await status.nanobanana_status(reset_stats=True)
            
            assert result["success"] is True
            assert result.get("stats_reset") is True
            mock_gemini.reset_statistics.assert_called_once()


class TestToolValidation:
    """도구 검증 함수 테스트"""
    
    def test_validate_generation_request_success(self):
        """생성 요청 검증 성공 테스트"""
        data = {
            "prompt": "test prompt",
            "quality": "high",
            "output_format": "png"
        }
        
        result = generate.validate_generation_request(data)
        
        assert isinstance(result, GenerateImageRequest)
        assert result.prompt == "test prompt"
    
    def test_validate_generation_request_failure(self):
        """생성 요청 검증 실패 테스트"""
        data = {
            "prompt": "",  # 빈 프롬프트
            "quality": "invalid"
        }
        
        with pytest.raises(ValueError):
            generate.validate_generation_request(data)
    
    def test_validate_edit_request_success(self):
        """편집 요청 검증 성공 테스트"""
        with patch('pathlib.Path') as mock_path:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.absolute.return_value = "/test/image.png"
            mock_path.return_value = mock_path_instance
            
            data = {
                "image_path": "/test/image.png",
                "edit_prompt": "make it blue"
            }
            
            result = edit.validate_edit_request(data)
            
            assert isinstance(result, EditImageRequest)
            assert result.edit_prompt == "make it blue"
    
    def test_validate_blend_request_success(self):
        """블렌딩 요청 검증 성공 테스트"""
        with patch('pathlib.Path') as mock_path:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.absolute.return_value = "/test/image.png"
            mock_path.return_value = mock_path_instance
            
            data = {
                "image_paths": ["/test/image1.png", "/test/image2.png"],
                "blend_prompt": "combine these"
            }
            
            result = blend.validate_blend_request(data)
            
            assert isinstance(result, BlendImagesRequest)
            assert len(result.image_paths) == 2


class TestToolStatistics:
    """도구 통계 함수 테스트"""
    
    def test_get_generation_statistics(self):
        """생성 통계 테스트"""
        with patch('src.tools.generate.get_gemini_client') as mock_client, \
             patch('src.tools.generate.get_file_manager') as mock_file_manager:
            
            mock_gemini = Mock()
            mock_gemini.get_statistics.return_value = {
                "request_count": 5,
                "total_images_generated": 10,
                "total_cost_usd": 0.39
            }
            mock_client.return_value = mock_gemini
            
            mock_fm = Mock()
            mock_fm.get_image_history.return_value = []
            mock_fm.get_storage_stats.return_value = {"output_stats": {}}
            mock_file_manager.return_value = mock_fm
            
            result = generate.get_generation_statistics()
            
            assert "total_requests" in result
            assert "total_images_generated" in result
            assert "total_cost_usd" in result
    
    def test_get_edit_statistics(self):
        """편집 통계 테스트"""
        with patch('src.tools.edit.get_file_manager') as mock_file_manager:
            mock_fm = Mock()
            mock_fm.get_image_history.return_value = [
                {
                    "created_at": "2025-01-01T12:00:00",
                    "prompt": "test edit",
                    "format": "png"
                }
            ]
            mock_fm.get_storage_stats.return_value = {"output_stats": {}}
            mock_file_manager.return_value = mock_fm
            
            result = edit.get_edit_statistics()
            
            assert "total_edits" in result
            assert "format_distribution" in result
    
    def test_get_blend_statistics(self):
        """블렌딩 통계 테스트"""
        with patch('src.tools.blend.get_file_manager') as mock_file_manager:
            mock_fm = Mock()
            mock_fm.get_image_history.return_value = [
                {
                    "created_at": "2025-01-01T12:00:00",
                    "prompt": "test blend",
                    "blend_complexity": 3,
                    "maintain_consistency": True
                }
            ]
            mock_fm.get_storage_stats.return_value = {"output_stats": {}}
            mock_file_manager.return_value = mock_fm
            
            result = blend.get_blend_statistics()
            
            assert "total_blends" in result
            assert "complexity_distribution" in result
            assert "consistency_usage_rate" in result