"""
PyTest 설정 및 공통 픽스처
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from PIL import Image
import io

from src.config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """테스트용 설정 모크"""
    settings = Mock()
    settings.google_ai_api_key = "test_api_key"
    settings.google_genai_use_vertexai = False
    settings.google_cloud_project = None
    settings.google_cloud_location = "global"
    settings.output_dir = Path("./test_outputs")
    settings.temp_dir = Path("./test_temp")
    settings.cache_dir = Path("./test_cache")
    settings.max_image_size = 10
    settings.default_quality = "high"
    settings.default_format = "png"
    settings.optimize_prompts = True
    settings.auto_translate = True
    settings.safety_level = "moderate"
    settings.enable_cache = True
    settings.cache_expiry = 24
    settings.max_cache_size = 1000
    settings.max_concurrent_requests = 3
    settings.request_timeout = 300
    settings.max_retries = 3
    settings.retry_delay = 1.0
    settings.server_name = "nanobanana-test"
    settings.server_version = "1.0.0-test"
    settings.dev_mode = True
    settings.debug = True
    settings.host = "localhost"
    settings.port = 8000
    
    # 메소드 모킹
    settings.get_safety_settings.return_value = [
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        }
    ]
    
    return settings


@pytest.fixture
def temp_dir():
    """임시 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image():
    """샘플 이미지 생성"""
    # 100x100 RGB 이미지 생성
    image = Image.new('RGB', (100, 100), color='red')
    
    # 바이트로 변환
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    image_bytes = buffer.getvalue()
    
    return {
        'image': image,
        'bytes': image_bytes,
        'size': (100, 100),
        'format': 'PNG'
    }


@pytest.fixture
def sample_image_file(temp_dir, sample_image):
    """샘플 이미지 파일"""
    image_path = temp_dir / "sample.png"
    
    with open(image_path, 'wb') as f:
        f.write(sample_image['bytes'])
    
    yield image_path
    
    # 정리는 temp_dir에서 자동으로 됨


@pytest.fixture
def multiple_sample_images(temp_dir, sample_image):
    """여러 샘플 이미지 파일들"""
    image_paths = []
    
    for i in range(3):
        image_path = temp_dir / f"sample_{i}.png"
        
        # 각각 다른 색상으로 생성
        colors = ['red', 'green', 'blue']
        image = Image.new('RGB', (100, 100), color=colors[i])
        
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        
        with open(image_path, 'wb') as f:
            f.write(buffer.getvalue())
        
        image_paths.append(image_path)
    
    yield image_paths


@pytest.fixture
def mock_gemini_response():
    """모킹된 Gemini API 응답"""
    def create_response(image_count=1, include_text=True):
        response = Mock()
        response.candidates = []
        
        candidate = Mock()
        candidate.content.parts = []
        
        if include_text:
            text_part = Mock()
            text_part.text = "Generated image description"
            text_part.inline_data = None
            candidate.content.parts.append(text_part)
        
        for i in range(image_count):
            image_part = Mock()
            image_part.text = None
            image_part.inline_data = Mock()
            image_part.inline_data.data = f"fake_image_data_{i}".encode()
            candidate.content.parts.append(image_part)
        
        response.candidates.append(candidate)
        return response
    
    return create_response


@pytest.fixture(autouse=True)
def mock_logging():
    """로깅 모킹 (자동 적용)"""
    with patch('src.config.setup_logging'), \
         patch('logging.getLogger'):
        yield


@pytest.fixture
def mock_file_system(temp_dir):
    """파일 시스템 모킹"""
    def create_mock_file(name: str, size: int = 1024, content: bytes = None):
        """모킹 파일 생성"""
        file_path = temp_dir / name
        
        if content is None:
            content = b"x" * size
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return file_path
    
    return create_mock_file


@pytest.fixture
def mock_async_context():
    """비동기 컨텍스트 매니저 모킹"""
    class MockAsyncContext:
        def __init__(self, return_value=None):
            self.return_value = return_value
        
        async def __aenter__(self):
            return self.return_value
        
        async def __aexiter__(self, exc_type, exc_val, exc_tb):
            pass
    
    return MockAsyncContext


# 테스트 마커 설정
pytest_plugins = []

def pytest_configure(config):
    """PyTest 설정"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )


def pytest_collection_modifyitems(config, items):
    """테스트 항목 수정"""
    for item in items:
        # 비동기 테스트 마킹
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # 파일 이름별 마킹
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        if "test_server" in item.nodeid:
            item.add_marker(pytest.mark.integration)


class MockHTTPResponse:
    """HTTP 응답 모킹 클래스"""
    
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_http_response():
    """HTTP 응답 모킹 팩토리"""
    return MockHTTPResponse