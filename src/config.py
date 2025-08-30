"""
나노바나나 MCP 서버 설정 관리

환경 변수와 기본값을 통합 관리하는 설정 모듈입니다.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Literal
from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class NanobananaSettings(BaseSettings):
    """나노바나나 MCP 서버 설정"""
    
    # ================================
    # Google AI API 설정
    # ================================
    google_ai_api_key: Optional[str] = Field(None, description="Google AI API key for Gemini image generation")
    google_cloud_project: Optional[str] = Field(None, description="Google Cloud project ID for Vertex AI")
    google_cloud_location: str = Field("global", description="Google Cloud location for Vertex AI")
    google_genai_use_vertexai: bool = Field(False, description="Whether to use Vertex AI instead of direct Gemini API")
    
    # ================================
    # 서버 설정
    # ================================
    port: int = Field(8000, description="Port number for MCP server")
    host: str = Field("localhost", description="Host address for MCP server")
    dev_mode: bool = Field(True, description="Enable development mode features")
    
    # ================================
    # 이미지 생성 설정
    # ================================
    output_dir: Path = Field(Path("./outputs"), description="Directory for generated images")
    temp_dir: Path = Field(Path("./temp"), description="Temporary files directory")
    max_image_size: int = Field(10, description="Maximum image size in MB")
    default_quality: Literal["auto", "high", "medium", "low"] = Field(
        "high", description="Default image quality setting"
    )
    default_format: Literal["png", "jpeg", "webp"] = Field(
        "png", description="Default image format"
    )
    
    # ================================
    # 프롬프트 최적화 설정
    # ================================
    optimize_prompts: bool = Field(True, description="Enable automatic prompt optimization")
    auto_translate: bool = Field(True, description="Automatically translate Korean prompts to English")
    safety_level: Literal["strict", "moderate", "permissive"] = Field(
        "moderate", description="Content safety filtering level"
    )
    
    # ================================
    # 캐싱 설정
    # ================================
    enable_cache: bool = Field(True, description="Enable image caching")
    cache_expiry: int = Field(24, description="Cache expiry time in hours")
    cache_dir: Path = Field(Path("./cache"), description="Cache directory path")
    max_cache_size: int = Field(1000, description="Maximum cache size in MB")
    
    # ================================
    # 로깅 설정
    # ================================
    log_level: str = Field("INFO", description="Logging level")
    log_file: Path = Field(
        Path("./logs/nanobanana_mcp.log"), description="Log file path"
    )
    log_max_size: int = Field(10, description="Maximum log file size in MB")
    log_backup_count: int = Field(5, description="Number of backup log files")
    
    # ================================
    # 성능 설정
    # ================================
    max_concurrent_requests: int = Field(3, description="Maximum concurrent API requests")
    request_timeout: int = Field(300, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")
    
    # ================================
    # MCP 설정
    # ================================
    server_name: str = Field("nanobanana", description="MCP server name")
    server_version: str = Field("1.0.0", description="MCP server version")
    debug: bool = Field(False, description="Enable debug mode")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
        
    @field_validator("output_dir", "temp_dir", "cache_dir", "log_file")
    def create_directories(cls, v):
        """디렉토리 자동 생성"""
        if isinstance(v, Path):
            if v.suffix:  # 파일인 경우 부모 디렉토리만 생성
                v.parent.mkdir(parents=True, exist_ok=True)
            else:  # 디렉토리인 경우 직접 생성
                v.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("log_level")
    def validate_log_level(cls, v):
        """로그 레벨 검증"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("max_image_size", "max_cache_size")
    def validate_size_limits(cls, v):
        """크기 제한 검증"""
        if v <= 0:
            raise ValueError("Size limits must be positive")
        return v
    
    def get_gemini_model_name(self) -> str:
        """Gemini 모델명 반환"""
        return "gemini-2.5-flash-image-preview"
    
    def get_safety_settings(self) -> dict:
        """안전 설정 반환"""
        level_mapping = {
            "strict": "BLOCK_LOW_AND_ABOVE",
            "moderate": "BLOCK_MEDIUM_AND_ABOVE", 
            "permissive": "BLOCK_ONLY_HIGH"
        }
        
        return [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": level_mapping[self.safety_level]
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH", 
                "threshold": level_mapping[self.safety_level]
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": level_mapping[self.safety_level]
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": level_mapping[self.safety_level]
            }
        ]


def get_settings() -> NanobananaSettings:
    """설정 인스턴스 반환 (싱글톤 패턴)"""
    if not hasattr(get_settings, "_instance"):
        get_settings._instance = NanobananaSettings()
    return get_settings._instance


def setup_logging(settings: Optional[NanobananaSettings] = None) -> None:
    """로깅 설정"""
    if settings is None:
        settings = get_settings()
    
    # 로그 레벨 설정
    log_level = getattr(logging, settings.log_level)
    
    # 로그 포맷 설정
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(message)s"
    )
    
    # 핸들러 설정
    handlers = []
    
    # 파일 핸들러 (로테이션 포함)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=settings.log_max_size * 1024 * 1024,  # MB to bytes
        backupCount=settings.log_backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    handlers.append(file_handler)
    
    # 콘솔 핸들러 (개발 모드에서만)
    if settings.dev_mode or settings.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        handlers.append(console_handler)
    
    # 로깅 설정 적용
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers,
        force=True
    )
    
    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


# 전역 설정 인스턴스
settings = get_settings()

# 로깅 설정 자동 적용
setup_logging(settings)