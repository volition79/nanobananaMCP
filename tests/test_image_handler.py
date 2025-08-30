"""
이미지 핸들러 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from io import BytesIO
from PIL import Image

from src.utils.image_handler import (
    ImageHandler,
    ImageHandlerError,
    get_image_handler
)
from src.constants import GEMINI_MAX_IMAGE_SIZE_MB, SUPPORTED_INPUT_FORMATS


class TestImageHandler:
    """ImageHandler 클래스 테스트"""
    
    @pytest.fixture
    def mock_settings(self):
        """테스트용 설정 모크"""
        settings = Mock()
        settings.default_format = "png"
        return settings
    
    @pytest.fixture
    def handler(self, mock_settings):
        """테스트용 핸들러 인스턴스"""
        return ImageHandler(mock_settings)
    
    @pytest.fixture
    def mock_image(self):
        """테스트용 PIL 이미지 모크"""
        image = Mock(spec=Image.Image)
        image.size = (1024, 1024)
        image.width = 1024
        image.height = 1024
        image.mode = "RGB"
        image.format = "PNG"
        image.verify = Mock()
        image.save = Mock()
        image.copy = Mock(return_value=image)
        image.convert = Mock(return_value=image)
        image.resize = Mock(return_value=image)
        image.thumbnail = Mock()
        image.getdata = Mock(return_value=[(255, 255, 255)] * 100)
        image.putdata = Mock()
        image.tobytes = Mock(return_value=b"test_bytes")
        return image
    
    def test_handler_initialization(self, mock_settings):
        """핸들러 초기화 테스트"""
        handler = ImageHandler(mock_settings)
        assert handler.settings == mock_settings
    
    def test_load_image_from_path_success(self, handler, mock_image):
        """파일 경로에서 이미지 로드 성공 테스트"""
        test_path = Path("test_image.png")
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('PIL.Image.open', return_value=mock_image):
            
            mock_stat.return_value.st_size = 1024 * 1024  # 1MB
            
            result = handler.load_image(test_path)
            
            assert result == mock_image
            mock_image.verify.assert_called_once()
    
    def test_load_image_from_path_not_found(self, handler):
        """파일 경로 - 파일 없음 테스트"""
        test_path = Path("nonexistent.png")
        
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(ImageHandlerError) as exc_info:
                handler.load_image(test_path)
            
            assert "not found" in str(exc_info.value)
    
    def test_load_image_from_path_too_large(self, handler):
        """파일 경로 - 파일 크기 초과 테스트"""
        test_path = Path("large_image.png")
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            # 파일 크기를 제한보다 크게 설정
            mock_stat.return_value.st_size = (GEMINI_MAX_IMAGE_SIZE_MB + 1) * 1024 * 1024
            
            with pytest.raises(ImageHandlerError) as exc_info:
                handler.load_image(test_path)
            
            assert "too large" in str(exc_info.value)
    
    def test_load_image_from_path_unsupported_format(self, handler):
        """파일 경로 - 지원하지 않는 형식 테스트"""
        test_path = Path("test_image.xyz")
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat:
            
            mock_stat.return_value.st_size = 1024
            
            with pytest.raises(ImageHandlerError) as exc_info:
                handler.load_image(test_path)
            
            assert "Unsupported image format" in str(exc_info.value)
    
    def test_load_image_from_bytes_success(self, handler, mock_image):
        """바이트에서 이미지 로드 성공 테스트"""
        test_bytes = b"fake_image_data" * 100
        
        with patch('PIL.Image.open', return_value=mock_image):
            result = handler.load_image(test_bytes)
            
            assert result == mock_image
            mock_image.verify.assert_called_once()
    
    def test_load_image_from_bytes_too_large(self, handler):
        """바이트 - 크기 초과 테스트"""
        test_bytes = b"x" * (GEMINI_MAX_IMAGE_SIZE_MB * 1024 * 1024 + 1)
        
        with pytest.raises(ImageHandlerError) as exc_info:
            handler.load_image(test_bytes)
        
        assert "too large" in str(exc_info.value)
    
    def test_load_image_mode_conversion(self, handler, mock_image):
        """이미지 모드 변환 테스트"""
        mock_image.mode = "RGBA"
        mock_image.convert.return_value = mock_image
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('PIL.Image.open', return_value=mock_image):
            
            mock_stat.return_value.st_size = 1024
            
            result = handler.load_image("test.png")
            
            # RGBA는 RGB로 변환되지 않아야 함
            assert result == mock_image
    
    def test_save_image_success(self, handler, mock_image):
        """이미지 저장 성공 테스트"""
        output_path = Path("output.png")
        
        with patch('pathlib.Path.mkdir'), \
             patch('builtins.open', mock_open()):
            
            result = handler.save_image(
                mock_image,
                output_path,
                format="png",
                quality="high"
            )
            
            assert result == output_path
            mock_image.save.assert_called_once()
    
    def test_save_image_unsupported_format(self, handler, mock_image):
        """이미지 저장 - 지원하지 않는 형식 테스트"""
        with pytest.raises(ImageHandlerError) as exc_info:
            handler.save_image(
                mock_image,
                "output.xyz",
                format="xyz"
            )
        
        assert "Unsupported output format" in str(exc_info.value)
    
    def test_save_image_jpeg_mode_conversion(self, handler, mock_image):
        """JPEG 저장 시 모드 변환 테스트"""
        mock_image.mode = "RGBA"
        mock_image.split.return_value = [Mock(), Mock(), Mock(), Mock()]  # RGBA 채널들
        
        # RGB 배경 이미지 생성 모킹
        background_image = Mock()
        background_image.paste = Mock()
        
        with patch('PIL.Image.new', return_value=background_image), \
             patch('pathlib.Path.mkdir'):
            
            handler.save_image(
                mock_image,
                "output.jpg",
                format="jpeg"
            )
            
            # 배경 이미지 생성 확인
            background_image.paste.assert_called()
    
    def test_resize_image_with_target_size(self, handler, mock_image):
        """이미지 크기 조정 - 목표 크기 테스트"""
        with patch('PIL.ImageOps.fit', return_value=mock_image) as mock_fit:
            result = handler.resize_image(
                mock_image,
                target_size=(512, 512),
                maintain_aspect=True
            )
            
            assert result == mock_image
            mock_fit.assert_called_once()
    
    def test_resize_image_with_max_size(self, handler, mock_image):
        """이미지 크기 조정 - 최대 크기 테스트"""
        result = handler.resize_image(
            mock_image,
            max_size=512
        )
        
        assert result == mock_image
        mock_image.resize.assert_called_once()
    
    def test_optimize_for_gemini(self, handler, mock_image):
        """Gemini 최적화 테스트"""
        result = handler.optimize_for_gemini(mock_image)
        
        assert result is not None
    
    def test_image_to_bytes(self, handler, mock_image):
        """이미지를 바이트로 변환 테스트"""
        with patch('io.BytesIO') as mock_bytesio:
            mock_buffer = Mock()
            mock_buffer.getvalue.return_value = b"fake_image_bytes"
            mock_bytesio.return_value = mock_buffer
            
            result = handler.image_to_bytes(mock_image, "PNG", "high")
            
            assert result == b"fake_image_bytes"
            mock_image.save.assert_called_once()
    
    def test_bytes_to_base64(self, handler):
        """바이트를 base64로 변환 테스트"""
        test_bytes = b"test_data"
        result = handler.bytes_to_base64(test_bytes)
        
        import base64
        expected = base64.b64encode(test_bytes).decode('utf-8')
        assert result == expected
    
    def test_base64_to_bytes_success(self, handler):
        """base64를 바이트로 변환 성공 테스트"""
        import base64
        test_bytes = b"test_data"
        base64_string = base64.b64encode(test_bytes).decode('utf-8')
        
        result = handler.base64_to_bytes(base64_string)
        
        assert result == test_bytes
    
    def test_base64_to_bytes_invalid(self, handler):
        """base64를 바이트로 변환 실패 테스트"""
        invalid_base64 = "invalid_base64!@#"
        
        with pytest.raises(ImageHandlerError):
            handler.base64_to_bytes(invalid_base64)
    
    def test_get_image_info(self, handler, mock_image):
        """이미지 정보 추출 테스트"""
        mock_image._getexif = Mock(return_value={
            271: "Test Camera",
            272: "Test Model"
        })
        
        with patch('PIL.ExifTags.TAGS', {271: "Make", 272: "Model"}):
            result = handler.get_image_info(mock_image)
            
            assert result["size"] == (1024, 1024)
            assert result["width"] == 1024
            assert result["height"] == 1024
            assert result["mode"] == "RGB"
            assert "exif" in result
    
    def test_create_thumbnail(self, handler, mock_image):
        """썸네일 생성 테스트"""
        result = handler.create_thumbnail(mock_image, (256, 256))
        
        assert result == mock_image
        mock_image.thumbnail.assert_called_once_with((256, 256), Image.LANCZOS)
    
    def test_validate_image_size(self, handler, mock_image):
        """이미지 크기 검증 테스트"""
        # 정상 크기
        result = handler.validate_image_size(mock_image)
        assert result is True
        
        # 너무 큰 이미지
        mock_image.width = 10000
        mock_image.height = 10000
        result = handler.validate_image_size(mock_image)
        assert result is False
    
    def test_calculate_image_hash(self, handler, mock_image):
        """이미지 해시 계산 테스트"""
        result = handler.calculate_image_hash(mock_image)
        
        assert isinstance(result, str)
        assert len(result) == 16  # 16자리 단축 해시
        mock_image.resize.assert_called_once()
        mock_image.convert.assert_called_once()
        mock_image.tobytes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_download_image_success(self, handler, mock_image):
        """이미지 다운로드 성공 테스트"""
        mock_response = Mock()
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client, \
             patch('PIL.Image.open', return_value=mock_image):
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await handler.download_image("https://example.com/image.png")
            
            assert result == mock_image
    
    @pytest.mark.asyncio
    async def test_download_image_invalid_content_type(self, handler):
        """이미지 다운로드 - 잘못된 컨텐츠 타입 테스트"""
        mock_response = Mock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            with pytest.raises(ImageHandlerError) as exc_info:
                await handler.download_image("https://example.com/image.png")
            
            assert "Invalid content type" in str(exc_info.value)
    
    def test_apply_basic_filters(self, handler, mock_image):
        """기본 필터 적용 테스트"""
        mock_image.filter = Mock(return_value=mock_image)
        
        result = handler.apply_basic_filters(mock_image, "blur")
        
        assert result == mock_image
        mock_image.filter.assert_called_once()
    
    def test_apply_basic_filters_unknown(self, handler, mock_image):
        """기본 필터 적용 - 알 수 없는 필터 테스트"""
        with pytest.raises(ImageHandlerError) as exc_info:
            handler.apply_basic_filters(mock_image, "unknown_filter")
        
        assert "Unknown filter" in str(exc_info.value)


class TestImageHandlerFunctions:
    """이미지 핸들러 전역 함수 테스트"""
    
    def test_get_image_handler_singleton(self):
        """싱글톤 핸들러 테스트"""
        with patch('src.utils.image_handler.ImageHandler') as mock_handler:
            handler1 = get_image_handler()
            handler2 = get_image_handler()
            
            assert handler1 == handler2
            mock_handler.assert_called_once()