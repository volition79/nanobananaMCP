"""
Gemini API 클라이언트 (보안 강화 버전)

Google의 Gemini 2.5 Flash Image API와의 통신을 담당하는 클라이언트 클래스입니다.
터미널 환경변수를 사용하지 않고, 오직 .env 파일 또는 MCP 설정에서만 API 키를 읽습니다.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, Union, Tuple
from pathlib import Path
from io import BytesIO

from google import genai
from google.genai.types import GenerateContentConfig, Modality
from PIL import Image
import httpx

from .config import get_settings
from .config_keyloader import SecureKeyLoader
from .constants import (
    GEMINI_MODEL_NAME, 
    GEMINI_TOKENS_PER_IMAGE,
    GEMINI_COST_PER_IMAGE,
    ERROR_CODES,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR
)

logger = logging.getLogger(__name__)


class GeminiAPIError(Exception):
    """Gemini API 관련 예외"""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class GeminiRateLimitError(GeminiAPIError):
    """API 요청 제한 예외"""
    pass


class GeminiQuotaExceededError(GeminiAPIError):
    """API 할당량 초과 예외"""
    pass


class GeminiClientFactory:
    """
    보안 강화된 Gemini 클라이언트 팩토리
    
    터미널 환경변수를 사용하지 않고 명시적으로 API 키를 전달합니다.
    우선순위: MCP 설정 > .env 파일 > 오류 발생
    """
    
    def __init__(
        self,
        mcp_settings_path: Optional[str] = None,
        mcp_server_name: str = "nanobanana",
        env_file: str = ".env",
        use_vertex_ai: bool = False,
        project: str = "",
        location: str = "us-central1"
    ):
        """
        팩토리 초기화
        
        Args:
            mcp_settings_path: MCP 설정 파일 경로
            mcp_server_name: MCP 서버 이름
            env_file: .env 파일 경로
            use_vertex_ai: Vertex AI 사용 여부
            project: Google Cloud 프로젝트 ID (Vertex AI 용)
            location: Google Cloud 위치 (Vertex AI 용)
        """
        self.use_vertex_ai = use_vertex_ai
        self.project = project
        self.location = location
        
        # 보안 키 로더로 API 키 획득
        self.key_loader = SecureKeyLoader(
            mcp_settings_path=mcp_settings_path,
            mcp_server_name=mcp_server_name,
            env_file=env_file
        )
        
        self.api_key = self.key_loader.get_api_key()
        
        # API 키 검증
        if not self.api_key and not use_vertex_ai:
            raise RuntimeError(
                "Gemini API key not found. Please set it in:\n"
                "1. MCP server configuration (recommended): mcpServers.{server_name}.env.GEMINI_API_KEY\n"
                "2. .env file: GEMINI_API_KEY, GOOGLE_API_KEY, or GOOGLE_AI_API_KEY\n"
                "\nSupported key names: GEMINI_API_KEY, GOOGLE_API_KEY, GOOGLE_AI_API_KEY"
            )
        
        # Vertex AI 검증
        if use_vertex_ai and not (project and location):
            raise RuntimeError("Vertex AI mode requires both project and location parameters.")
        
        # 클라이언트 생성
        self.client = self._create_client()
        
        # 디버그 정보 로그
        debug_info = self.key_loader.get_debug_info()
        pollution_check = self.key_loader.verify_no_os_env_pollution()
        
        logger.info(f"🔐 API Key Source: {debug_info['key_info']['source_name']}")
        logger.info(f"🔐 Key Name: {debug_info['key_info']['key_name']}")
        logger.info(f"🔐 {pollution_check['message']}")
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Full debug info: {debug_info}")
            logger.debug(f"Pollution check: {pollution_check}")
    
    def _create_client(self) -> genai.Client:
        """
        Gemini 클라이언트 생성 (명시적 API 키 전달)
        
        Returns:
            genai.Client: 설정된 클라이언트
        """
        try:
            if self.use_vertex_ai:
                # Vertex AI 모드: 프로젝트와 위치 명시
                client = genai.Client(
                    vertexai=True,
                    project=self.project,
                    location=self.location,
                    api_key=self.api_key  # None이어도 Vertex AI가 ADC 사용
                )
                logger.info(f"✅ Vertex AI client created - Project: {self.project}, Location: {self.location}")
            else:
                # 일반 모드: API 키 명시적 전달
                client = genai.Client(api_key=self.api_key)
                logger.info("✅ Gemini API client created with explicit key")
            
            return client
            
        except Exception as e:
            logger.error(f"❌ Failed to create Gemini client: {e}")
            raise GeminiAPIError(f"Client creation failed: {str(e)}")
    
    def get_client(self) -> genai.Client:
        """클라이언트 반환"""
        return self.client
    
    def get_debug_source(self) -> str:
        """API 키 출처 반환 (디버깅용)"""
        return self.key_loader.key_info.get('source_name', 'unknown')
    
    def get_full_debug_info(self) -> Dict[str, Any]:
        """전체 디버그 정보 반환"""
        return {
            "client_info": {
                "use_vertex_ai": self.use_vertex_ai,
                "project": self.project,
                "location": self.location
            },
            "key_loader": self.key_loader.get_debug_info(),
            "pollution_check": self.key_loader.verify_no_os_env_pollution()
        }


class GeminiClient:
    """
    Gemini 2.5 Flash Image API 클라이언트 (보안 강화 버전)
    """
    
    def __init__(self, settings=None, client_factory: Optional[GeminiClientFactory] = None):
        """
        클라이언트 초기화
        
        Args:
            settings: 설정 객체 (선택사항)
            client_factory: 클라이언트 팩토리 (선택사항)
        """
        self.settings = settings or get_settings()
        
        # 클라이언트 팩토리 설정
        if client_factory:
            self.factory = client_factory
        else:
            self.factory = GeminiClientFactory(
                mcp_server_name="nanobanana",
                use_vertex_ai=self.settings.google_genai_use_vertexai,
                project=self.settings.google_cloud_project,
                location=self.settings.google_cloud_location
            )
        
        self._client = self.factory.get_client()
        
        # 요청 통계
        self._request_count = 0
        self._total_images_generated = 0
        self._total_cost = 0.0
        self._start_time = time.time()
        
        logger.info("🚀 Gemini client initialized with secure key loading")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        API 연결 상태 및 모델 접근성 확인
        
        Returns:
            Dict[str, Any]: 상태 정보
        """
        try:
            # 모델 목록 조회로 연결 테스트
            models = list(self._client.models.list())
            
            # 이미지 생성 모델 찾기
            image_models = [
                model for model in models 
                if 'image' in model.name.lower() or 'flash' in model.name.lower()
            ]
            
            return {
                "status": "healthy",
                "api_accessible": True,
                "total_models": len(models),
                "image_models": len(image_models),
                "target_model": GEMINI_MODEL_NAME,
                "model_available": any(GEMINI_MODEL_NAME in model.name for model in models),
                "key_source": self.factory.get_debug_source(),
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "api_accessible": False,
                "error": str(e),
                "key_source": self.factory.get_debug_source(),
                "timestamp": time.time()
            }
    
    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: Optional[str] = None,
        style: Optional[str] = None,
        quality: Optional[str] = "high",
        candidate_count: int = 1
    ) -> Dict[str, Any]:
        """
        텍스트 프롬프트로부터 이미지 생성
        
        Args:
            prompt: 이미지 생성 프롬프트
            aspect_ratio: 이미지 비율
            style: 스타일
            quality: 품질
            candidate_count: 생성할 이미지 수
            
        Returns:
            Dict[str, Any]: 생성 결과
        """
        try:
            # 요청 통계 업데이트
            self._request_count += 1
            
            # 생성 설정
            config = GenerateContentConfig(
                candidate_count=min(candidate_count, 4),
                temperature=0.7
            )
            
            # 프롬프트 구성
            full_prompt = self._build_image_prompt(prompt, aspect_ratio, style)
            
            # 이미지 생성 요청
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=GEMINI_MODEL_NAME,
                contents=[full_prompt],
                config=config
            )
            
            # 응답 처리
            if not response or not response.candidates:
                raise GeminiAPIError("No candidates returned from API")
            
            images = []
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            images.append({
                                "data": part.inline_data.data,
                                "mime_type": part.inline_data.mime_type
                            })
            
            # 통계 업데이트
            self._total_images_generated += len(images)
            self._total_cost += len(images) * GEMINI_COST_PER_IMAGE
            
            return {
                "success": True,
                "images": images,
                "count": len(images),
                "prompt_used": full_prompt,
                "tokens_consumed": len(images) * GEMINI_TOKENS_PER_IMAGE,
                "cost_estimate": len(images) * GEMINI_COST_PER_IMAGE
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "images": [],
                "count": 0
            }
    
    async def edit_image(
        self,
        image_path: str,
        edit_prompt: str,
        mask_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        기존 이미지를 자연어 명령으로 편집
        
        Args:
            image_path: 편집할 이미지 파일 경로
            edit_prompt: 편집 지시사항
            mask_path: 마스크 이미지 경로 (선택사항)
            **kwargs: 추가 설정
            
        Returns:
            Dict[str, Any]: 편집 결과
        """
        try:
            # 요청 통계 업데이트
            self._request_count += 1
            
            # 이미지 파일을 읽어서 인라인 데이터로 변환
            image_path = Path(image_path)
            if not image_path.exists():
                raise GeminiAPIError(f"Image file not found: {image_path}")
            
            # PIL Image로 읽기
            pil_image = Image.open(image_path)
            
            # 이미지를 바이트로 변환 (PNG 형식으로 저장)
            image_bytes = BytesIO()
            pil_image.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            image_data = image_bytes.getvalue()
            
            # 편집 프롬프트 구성
            full_prompt = f"Edit this image: {edit_prompt}"
            
            # 생성 설정
            config = GenerateContentConfig(
                candidate_count=1,
                temperature=0.7
            )
            
            # 이미지 편집 요청 (이미지를 첨부하여 새로운 이미지 생성)
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=GEMINI_MODEL_NAME,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": full_prompt},
                            {"inline_data": {"mime_type": "image/png", "data": image_data}}
                        ]
                    }
                ],
                config=config
            )
            
            # 응답 처리
            if not response or not response.candidates:
                raise GeminiAPIError("No candidates returned from API")
            
            images = []
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            images.append({
                                "data": part.inline_data.data,
                                "mime_type": part.inline_data.mime_type
                            })
            
            # 통계 업데이트
            self._total_images_generated += len(images)
            self._total_cost += len(images) * GEMINI_COST_PER_IMAGE
            
            return {
                "success": True,
                "images": images,
                "count": len(images),
                "prompt_used": full_prompt,
                "tokens_consumed": len(images) * GEMINI_TOKENS_PER_IMAGE,
                "cost_estimate": len(images) * GEMINI_COST_PER_IMAGE
            }
            
        except Exception as e:
            logger.error(f"Image editing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "images": [],
                "count": 0
            }

    async def blend_images(
        self,
        image_paths: List[str],
        blend_prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        여러 이미지를 블렌딩하여 새로운 이미지 생성
        
        Args:
            image_paths: 블렌딩할 이미지 파일 경로들
            blend_prompt: 블렌딩 지시사항
            **kwargs: 추가 설정
            
        Returns:
            Dict[str, Any]: 블렌딩 결과
        """
        try:
            # 요청 통계 업데이트
            self._request_count += 1
            
            # 여러 이미지를 읽어서 인라인 데이터로 변환
            image_parts = []
            for i, image_path in enumerate(image_paths):
                image_path = Path(image_path)
                if not image_path.exists():
                    raise GeminiAPIError(f"Image file not found: {image_path}")
                
                # PIL Image로 읽기
                pil_image = Image.open(image_path)
                
                # 이미지를 바이트로 변환 (PNG 형식으로 저장)
                image_bytes = BytesIO()
                pil_image.save(image_bytes, format='PNG')
                image_bytes.seek(0)
                image_data = image_bytes.getvalue()
                
                # 이미지 파트 추가
                image_parts.append({
                    "inline_data": {
                        "mime_type": "image/png", 
                        "data": image_data
                    }
                })
            
            # 블렌딩 프롬프트 구성
            full_prompt = f"Blend these {len(image_paths)} images: {blend_prompt}"
            
            # 생성 설정
            config = GenerateContentConfig(
                candidate_count=1,
                temperature=0.7
            )
            
            # 이미지 블렌딩 요청 (여러 이미지를 첨부하여 새로운 이미지 생성)
            content_parts = [{"text": full_prompt}] + image_parts
            
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=GEMINI_MODEL_NAME,
                contents=[
                    {
                        "role": "user",
                        "parts": content_parts
                    }
                ],
                config=config
            )
            
            # 응답 처리
            if not response or not response.candidates:
                raise GeminiAPIError("No candidates returned from API")
            
            images = []
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            images.append({
                                "data": part.inline_data.data,
                                "mime_type": part.inline_data.mime_type
                            })
            
            # 통계 업데이트
            self._total_images_generated += len(images)
            self._total_cost += len(images) * GEMINI_COST_PER_IMAGE
            
            return {
                "success": True,
                "images": images,
                "count": len(images),
                "prompt_used": full_prompt,
                "tokens_consumed": len(images) * GEMINI_TOKENS_PER_IMAGE,
                "cost_estimate": len(images) * GEMINI_COST_PER_IMAGE
            }
            
        except Exception as e:
            logger.error(f"Image blending failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "images": [],
                "count": 0
            }

    def _build_image_prompt(
        self, 
        prompt: str, 
        aspect_ratio: Optional[str] = None,
        style: Optional[str] = None
    ) -> str:
        """이미지 생성 프롬프트 구성"""
        parts = [prompt]
        
        if aspect_ratio:
            parts.append(f"Aspect ratio: {aspect_ratio}")
        
        if style:
            parts.append(f"Style: {style}")
        
        return ". ".join(parts)
    
    def get_statistics(self) -> Dict[str, Any]:
        """사용 통계 반환"""
        uptime = time.time() - self._start_time
        
        return {
            "requests_made": self._request_count,
            "images_generated": self._total_images_generated,
            "estimated_cost": round(self._total_cost, 4),
            "uptime_seconds": round(uptime, 2),
            "avg_images_per_request": (
                round(self._total_images_generated / self._request_count, 2)
                if self._request_count > 0 else 0
            ),
            "key_source": self.factory.get_debug_source()
        }
    
    def reset_statistics(self) -> None:
        """통계 초기화"""
        self._request_count = 0
        self._total_images_generated = 0
        self._total_cost = 0.0
        self._start_time = time.time()
        logger.info("Statistics reset")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """디버그 정보 반환"""
        return {
            "statistics": self.get_statistics(),
            "factory_debug": self.factory.get_full_debug_info(),
            "client_status": "initialized" if self._client else "not_initialized"
        }


# 전역 클라이언트 인스턴스 (싱글톤 패턴)
_global_client: Optional[GeminiClient] = None


async def create_gemini_client(settings=None) -> GeminiClient:
    """
    Gemini 클라이언트 생성 (비동기)
    
    Args:
        settings: 설정 객체
        
    Returns:
        GeminiClient: 초기화된 클라이언트
    """
    global _global_client
    
    if _global_client is None:
        logger.info("Creating new Gemini client...")
        _global_client = GeminiClient(settings=settings)
        
        # 헬스체크 실행
        health = await _global_client.health_check()
        if not health["api_accessible"]:
            logger.warning(f"API accessibility check failed: {health.get('error', 'Unknown error')}")
        else:
            logger.info("✅ Gemini API health check passed")
    
    return _global_client


def get_gemini_client() -> Optional[GeminiClient]:
    """전역 클라이언트 인스턴스 반환"""
    return _global_client


def reset_gemini_client():
    """전역 클라이언트 인스턴스 초기화"""
    global _global_client
    _global_client = None
    logger.info("Global Gemini client reset")