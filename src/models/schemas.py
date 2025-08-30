"""
Pydantic 데이터 모델 스키마

나노바나나 MCP 서버에서 사용하는 모든 요청/응답 데이터 모델을 정의합니다.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from ..constants import (
    SUPPORTED_OUTPUT_FORMATS,
    ASPECT_RATIOS,
    IMAGE_QUALITY_LEVELS,
    STYLE_PRESETS,
    MAX_PROMPT_LENGTH,
    MIN_PROMPT_LENGTH,
    MAX_BATCH_SIZE
)


# ================================
# 열거형 정의
# ================================

class ImageFormat(str, Enum):
    """지원되는 이미지 형식"""
    PNG = "png"
    JPEG = "jpeg" 
    WEBP = "webp"


class QualityLevel(str, Enum):
    """이미지 품질 레벨"""
    AUTO = "auto"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AspectRatio(str, Enum):
    """종횡비 프리셋"""
    SQUARE = "1:1"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    WIDESCREEN = "21:9"
    CINEMA = "2.39:1"
    PHOTO = "4:3"


class StylePreset(str, Enum):
    """스타일 프리셋"""
    PHOTOREALISTIC = "photorealistic"
    DIGITAL_ART = "digital_art"
    OIL_PAINTING = "oil_painting"
    WATERCOLOR = "watercolor"
    CARTOON = "cartoon"
    ANIME = "anime"
    SKETCH = "sketch"
    VINTAGE = "vintage"


class OperationType(str, Enum):
    """작업 유형"""
    GENERATION = "generated"
    EDITING = "edited"
    BLENDING = "blended"


# ================================
# 기본 모델
# ================================

class BaseRequest(BaseModel):
    """기본 요청 모델"""
    
    class Config:
        """Pydantic 설정"""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class BaseResponse(BaseModel):
    """기본 응답 모델"""
    
    success: bool = Field(..., description="작업 성공 여부")
    message: Optional[str] = Field(None, description="응답 메시지")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")
    
    class Config:
        """Pydantic 설정"""
        use_enum_values = True


# ================================
# 이미지 생성 관련 모델
# ================================

class GenerateImageRequest(BaseRequest):
    """이미지 생성 요청"""
    
    prompt: str = Field(
        ..., 
        min_length=MIN_PROMPT_LENGTH,
        max_length=MAX_PROMPT_LENGTH,
        description="이미지 생성을 위한 텍스트 설명"
    )
    aspect_ratio: Optional[Union[AspectRatio, str]] = Field(
        None, 
        description="이미지 비율 (예: '16:9', '1:1')"
    )
    style: Optional[StylePreset] = Field(
        None,
        description="스타일 프리셋"
    )
    quality: Optional[QualityLevel] = Field(
        QualityLevel.HIGH,
        description="이미지 품질 레벨"
    )
    output_format: Optional[ImageFormat] = Field(
        ImageFormat.PNG,
        description="출력 이미지 형식"
    )
    candidate_count: Optional[int] = Field(
        1,
        ge=1,
        le=MAX_BATCH_SIZE,
        description="생성할 이미지 수"
    )
    additional_keywords: Optional[List[str]] = Field(
        None,
        description="추가 키워드 리스트"
    )
    optimize_prompt: Optional[bool] = Field(
        True,
        description="프롬프트 자동 최적화 여부"
    )
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v):
        """프롬프트 유효성 검사"""
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty")
        return v.strip()
    
    @field_validator('aspect_ratio')
    @classmethod
    def validate_aspect_ratio(cls, v):
        """종횡비 유효성 검사"""
        if v is None:
            return v
        
        if isinstance(v, str):
            # 커스텀 비율 검증 (예: "4:3", "21:9")
            if ":" in v:
                try:
                    w, h = v.split(":")
                    float(w), float(h)
                    return v
                except ValueError:
                    raise ValueError(f"Invalid aspect ratio format: {v}")
        return v
    
    @field_validator('candidate_count', mode='before')
    @classmethod
    def validate_candidate_count(cls, v):
        """후보 이미지 수 유효성 검사 및 자동 타입 변환"""
        if v is None:
            return 1  # 기본값
        
        # 문자열을 정수로 변환 시도
        if isinstance(v, str):
            try:
                v = int(v.strip())
            except ValueError:
                raise ValueError(f"candidate_count must be a valid integer, got: '{v}'")
        
        # 이미 정수라면 그대로 반환
        if isinstance(v, int):
            return v
        
        raise ValueError(f"candidate_count must be an integer or string number, got: {type(v)}")
    
    @field_validator('optimize_prompt', mode='before')
    @classmethod
    def validate_optimize_prompt(cls, v):
        """프롬프트 최적화 옵션 유효성 검사 및 자동 타입 변환"""
        if v is None:
            return True  # 기본값
        
        # 문자열을 불리언으로 변환 시도
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ('true', '1', 'yes', 'on'):
                return True
            elif v_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"optimize_prompt must be a valid boolean string, got: '{v}'")
        
        # 이미 불리언이라면 그대로 반환
        if isinstance(v, bool):
            return v
        
        # 숫자를 불리언으로 변환
        if isinstance(v, (int, float)):
            return bool(v)
        
        raise ValueError(f"optimize_prompt must be a boolean or string boolean, got: {type(v)}")


class ImageMetadata(BaseModel):
    """이미지 메타데이터"""
    
    filename: str = Field(..., description="파일명")
    filepath: str = Field(..., description="파일 경로")
    operation_type: OperationType = Field(..., description="작업 유형")
    created_at: datetime = Field(..., description="생성 시간")
    file_size: int = Field(..., description="파일 크기 (바이트)")
    format: ImageFormat = Field(..., description="이미지 형식")
    width: Optional[int] = Field(None, description="이미지 너비")
    height: Optional[int] = Field(None, description="이미지 높이")
    prompt: Optional[str] = Field(None, description="원본 프롬프트")
    optimized_prompt: Optional[str] = Field(None, description="최적화된 프롬프트")
    model_used: str = Field(..., description="사용된 AI 모델")
    generation_time: Optional[float] = Field(None, description="생성 소요 시간 (초)")
    cost_usd: Optional[float] = Field(None, description="예상 비용 (USD)")
    hash: Optional[str] = Field(None, description="이미지 해시")


class GenerateImageResponse(BaseResponse):
    """이미지 생성 응답"""
    
    images: List[ImageMetadata] = Field(default_factory=list, description="생성된 이미지들")
    original_prompt: Optional[str] = Field(None, description="원본 프롬프트")
    optimized_prompt: Optional[str] = Field(None, description="최적화된 프롬프트")
    generation_time: Optional[float] = Field(None, description="총 생성 시간 (초)")
    total_cost: Optional[float] = Field(None, description="총 비용 (USD)")
    model_info: Optional[Dict[str, Any]] = Field(None, description="모델 정보")


# ================================
# 이미지 편집 관련 모델
# ================================

class EditImageRequest(BaseRequest):
    """이미지 편집 요청"""
    
    image_path: str = Field(..., description="편집할 이미지 파일 경로")
    edit_prompt: str = Field(
        ...,
        min_length=MIN_PROMPT_LENGTH,
        max_length=MAX_PROMPT_LENGTH,
        description="편집 지시사항"
    )
    mask_path: Optional[str] = Field(None, description="마스크 이미지 경로 (선택사항)")
    output_format: Optional[ImageFormat] = Field(
        ImageFormat.PNG,
        description="출력 이미지 형식"
    )
    quality: Optional[QualityLevel] = Field(
        QualityLevel.HIGH,
        description="출력 품질"
    )
    optimize_prompt: Optional[bool] = Field(
        True,
        description="프롬프트 자동 최적화 여부"
    )
    
    @field_validator('image_path')
    @classmethod
    def validate_image_path(cls, v):
        """이미지 경로 유효성 검사"""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Image file not found: {v}")
        return str(path.absolute())
    
    @field_validator('mask_path')
    @classmethod
    def validate_mask_path(cls, v):
        """마스크 경로 유효성 검사"""
        if v is None:
            return v
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Mask file not found: {v}")
        return str(path.absolute())
    
    @field_validator('optimize_prompt', mode='before')
    @classmethod
    def validate_optimize_prompt(cls, v):
        """프롬프트 최적화 옵션 유효성 검사 및 자동 타입 변환"""
        if v is None:
            return True  # 기본값
        
        # 문자열을 불리언으로 변환 시도
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ('true', '1', 'yes', 'on'):
                return True
            elif v_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"optimize_prompt must be a valid boolean string, got: '{v}'")
        
        # 이미 불리언이라면 그대로 반환
        if isinstance(v, bool):
            return v
        
        # 숫자를 불리언으로 변환
        if isinstance(v, (int, float)):
            return bool(v)
        
        raise ValueError(f"optimize_prompt must be a boolean or string boolean, got: {type(v)}")


class EditImageResponse(BaseResponse):
    """이미지 편집 응답"""
    
    original_image: str = Field(..., description="원본 이미지 경로")
    edited_image: Optional[ImageMetadata] = Field(None, description="편집된 이미지")
    edit_prompt: str = Field(..., description="편집 프롬프트")
    optimized_prompt: Optional[str] = Field(None, description="최적화된 프롬프트")
    processing_time: Optional[float] = Field(None, description="처리 시간 (초)")


# ================================
# 이미지 블렌딩 관련 모델
# ================================

class BlendImagesRequest(BaseRequest):
    """이미지 블렌딩 요청"""
    
    image_paths: List[str] = Field(
        ...,
        min_length=2,
        max_length=4,
        description="블렌딩할 이미지 경로들"
    )
    blend_prompt: str = Field(
        ...,
        min_length=MIN_PROMPT_LENGTH,
        max_length=MAX_PROMPT_LENGTH,
        description="블렌딩 지시사항"
    )
    maintain_consistency: Optional[bool] = Field(
        True,
        description="캐릭터 일관성 유지 여부"
    )
    output_format: Optional[ImageFormat] = Field(
        ImageFormat.PNG,
        description="출력 이미지 형식"
    )
    quality: Optional[QualityLevel] = Field(
        QualityLevel.HIGH,
        description="출력 품질"
    )
    optimize_prompt: Optional[bool] = Field(
        True,
        description="프롬프트 자동 최적화 여부"
    )
    
    @field_validator('image_paths')
    @classmethod
    def validate_image_paths(cls, v):
        """이미지 경로들 유효성 검사"""
        validated_paths = []
        for path_str in v:
            path = Path(path_str)
            if not path.exists():
                raise ValueError(f"Image file not found: {path_str}")
            validated_paths.append(str(path.absolute()))
        return validated_paths
    
    @field_validator('maintain_consistency', mode='before')
    @classmethod
    def validate_maintain_consistency(cls, v):
        """캐릭터 일관성 유지 옵션 유효성 검사 및 자동 타입 변환"""
        if v is None:
            return True  # 기본값
        
        # 문자열을 불리언으로 변환 시도
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ('true', '1', 'yes', 'on'):
                return True
            elif v_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"maintain_consistency must be a valid boolean string, got: '{v}'")
        
        # 이미 불리언이라면 그대로 반환
        if isinstance(v, bool):
            return v
        
        # 숫자를 불리언으로 변환
        if isinstance(v, (int, float)):
            return bool(v)
        
        raise ValueError(f"maintain_consistency must be a boolean or string boolean, got: {type(v)}")
    
    @field_validator('optimize_prompt', mode='before')
    @classmethod
    def validate_optimize_prompt(cls, v):
        """프롬프트 최적화 옵션 유효성 검사 및 자동 타입 변환"""
        if v is None:
            return True  # 기본값
        
        # 문자열을 불리언으로 변환 시도
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ('true', '1', 'yes', 'on'):
                return True
            elif v_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"optimize_prompt must be a valid boolean string, got: '{v}'")
        
        # 이미 불리언이라면 그대로 반환
        if isinstance(v, bool):
            return v
        
        # 숫자를 불리언으로 변환
        if isinstance(v, (int, float)):
            return bool(v)
        
        raise ValueError(f"optimize_prompt must be a boolean or string boolean, got: {type(v)}")


class BlendImagesResponse(BaseResponse):
    """이미지 블렌딩 응답"""
    
    source_images: List[str] = Field(..., description="원본 이미지 경로들")
    blended_image: Optional[ImageMetadata] = Field(None, description="블렌딩된 이미지")
    blend_prompt: str = Field(..., description="블렌딩 프롬프트")
    optimized_prompt: Optional[str] = Field(None, description="최적화된 프롬프트")
    processing_time: Optional[float] = Field(None, description="처리 시간 (초)")


# ================================
# 서버 상태 관련 모델
# ================================

class ServerStatusResponse(BaseResponse):
    """서버 상태 응답"""
    
    server_name: str = Field(..., description="서버 이름")
    version: str = Field(..., description="서버 버전")
    uptime: float = Field(..., description="가동 시간 (초)")
    api_status: Dict[str, Any] = Field(..., description="API 상태 정보")
    storage_stats: Dict[str, Any] = Field(..., description="스토리지 통계")
    performance_stats: Dict[str, Any] = Field(..., description="성능 통계")
    system_info: Dict[str, Any] = Field(..., description="시스템 정보")


# ================================
# 히스토리 및 검색 모델
# ================================

class ImageHistoryRequest(BaseRequest):
    """이미지 히스토리 조회 요청"""
    
    limit: Optional[int] = Field(50, ge=1, le=500, description="최대 반환 개수")
    operation_type: Optional[OperationType] = Field(None, description="작업 유형 필터")
    start_date: Optional[datetime] = Field(None, description="시작 날짜")
    end_date: Optional[datetime] = Field(None, description="종료 날짜")


class ImageHistoryResponse(BaseResponse):
    """이미지 히스토리 조회 응답"""
    
    images: List[ImageMetadata] = Field(..., description="이미지 목록")
    total_count: int = Field(..., description="전체 이미지 수")
    filtered_count: int = Field(..., description="필터 적용 후 이미지 수")


class SearchImagesRequest(BaseRequest):
    """이미지 검색 요청"""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="검색 쿼리"
    )
    similarity_threshold: Optional[float] = Field(
        0.8,
        ge=0.0,
        le=1.0,
        description="유사도 임계값"
    )
    limit: Optional[int] = Field(20, ge=1, le=100, description="최대 결과 수")


class SearchImagesResponse(BaseResponse):
    """이미지 검색 응답"""
    
    query: str = Field(..., description="검색 쿼리")
    results: List[Dict[str, Any]] = Field(..., description="검색 결과")
    total_matches: int = Field(..., description="총 매칭 수")


# ================================
# 캐시 및 관리 모델
# ================================

class CacheManagementResponse(BaseResponse):
    """캐시 관리 응답"""
    
    status: str = Field(..., description="관리 상태")
    deleted_files: int = Field(..., description="삭제된 파일 수")
    freed_space_mb: float = Field(..., description="해제된 공간 (MB)")
    current_size_mb: float = Field(..., description="현재 캐시 크기 (MB)")
    max_size_mb: float = Field(..., description="최대 캐시 크기 (MB)")


class CleanupRequest(BaseRequest):
    """정리 요청"""
    
    cleanup_temp: Optional[bool] = Field(True, description="임시 파일 정리")
    cleanup_cache: Optional[bool] = Field(True, description="캐시 정리")
    max_age_hours: Optional[int] = Field(24, ge=1, le=168, description="최대 보존 시간")


class CleanupResponse(BaseResponse):
    """정리 응답"""
    
    temp_files_deleted: int = Field(..., description="삭제된 임시 파일 수")
    cache_files_deleted: int = Field(..., description="삭제된 캐시 파일 수")
    total_space_freed_mb: float = Field(..., description="총 해제된 공간 (MB)")


# ================================
# 에러 모델
# ================================

class ErrorDetail(BaseModel):
    """에러 상세 정보"""
    
    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    field: Optional[str] = Field(None, description="관련 필드")
    value: Optional[Any] = Field(None, description="문제가 된 값")


class ErrorResponse(BaseResponse):
    """에러 응답"""
    
    success: bool = Field(False, description="항상 False")
    error: ErrorDetail = Field(..., description="에러 상세 정보")
    request_id: Optional[str] = Field(None, description="요청 ID")


# ================================
# MCP 도구 관련 모델
# ================================

class ToolParameter(BaseModel):
    """MCP 도구 파라미터 정의"""
    
    name: str = Field(..., description="파라미터 이름")
    type: str = Field(..., description="파라미터 타입")
    description: str = Field(..., description="파라미터 설명")
    required: bool = Field(True, description="필수 여부")
    default: Optional[Any] = Field(None, description="기본값")


class ToolDefinition(BaseModel):
    """MCP 도구 정의"""
    
    name: str = Field(..., description="도구 이름")
    description: str = Field(..., description="도구 설명")
    parameters: List[ToolParameter] = Field(..., description="파라미터 목록")
    category: str = Field(..., description="도구 카테고리")


# ================================
# 설정 검증 모델
# ================================

class ValidationResult(BaseModel):
    """검증 결과"""
    
    is_valid: bool = Field(..., description="검증 통과 여부")
    errors: List[str] = Field(default_factory=list, description="에러 목록")
    warnings: List[str] = Field(default_factory=list, description="경고 목록")
    suggestions: List[str] = Field(default_factory=list, description="개선 제안")


# ================================
# 배치 처리 모델
# ================================

class BatchRequest(BaseRequest):
    """배치 처리 요청"""
    
    requests: List[Union[GenerateImageRequest, EditImageRequest, BlendImagesRequest]] = Field(
        ...,
        min_length=1,
        max_length=MAX_BATCH_SIZE,
        description="배치 요청 목록"
    )
    
    @field_validator('requests')
    @classmethod
    def validate_requests(cls, v):
        """배치 요청 유효성 검사"""
        if len(v) > MAX_BATCH_SIZE:
            raise ValueError(f"Too many requests. Maximum: {MAX_BATCH_SIZE}")
        return v


class BatchResponse(BaseResponse):
    """배치 처리 응답"""
    
    results: List[Union[GenerateImageResponse, EditImageResponse, BlendImagesResponse]] = Field(
        ...,
        description="배치 결과 목록"
    )
    total_requests: int = Field(..., description="총 요청 수")
    successful_requests: int = Field(..., description="성공한 요청 수")
    failed_requests: int = Field(..., description="실패한 요청 수")
    total_processing_time: float = Field(..., description="총 처리 시간 (초)")


# ================================
# 유틸리티 함수
# ================================

def create_error_response(
    message: str,
    code: str = "UNKNOWN_ERROR",
    field: Optional[str] = None,
    value: Optional[Any] = None,
    request_id: Optional[str] = None
) -> ErrorResponse:
    """에러 응답 생성 헬퍼 함수"""
    
    return ErrorResponse(
        message=message,
        error=ErrorDetail(
            code=code,
            message=message,
            field=field,
            value=value
        ),
        request_id=request_id
    )


def validate_model_data(model_class: BaseModel, data: Dict[str, Any]) -> ValidationResult:
    """모델 데이터 검증 헬퍼 함수"""
    
    try:
        model_class(**data)
        return ValidationResult(is_valid=True)
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[str(e)]
        )