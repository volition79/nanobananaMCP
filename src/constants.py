"""
나노바나나 MCP 서버 상수 정의

프로젝트 전반에서 사용되는 상수들을 중앙 집중 관리합니다.
"""

from typing import Dict, List, Tuple

# ================================
# Gemini API 관련 상수
# ================================
GEMINI_MODEL_NAME = "gemini-2.5-flash-image-preview"
GEMINI_CODENAME = "nano-banana"

# 토큰 및 비용
GEMINI_TOKENS_PER_IMAGE = 1290
GEMINI_COST_PER_IMAGE = 0.039  # USD

# 이미지 해상도 및 형식
GEMINI_DEFAULT_RESOLUTION = (1024, 1024)
GEMINI_SUPPORTED_FORMATS = ["png", "jpeg", "webp"]
GEMINI_MAX_IMAGE_SIZE_MB = 20  # Gemini API 제한

# ================================
# MCP 도구 이름 및 설명
# ================================
MCP_TOOLS = {
    "nanobanana_generate": {
        "name": "nanobanana_generate",
        "description": "Generate images from text prompts using Gemini 2.5 Flash Image",
        "category": "image_generation"
    },
    "nanobanana_edit": {
        "name": "nanobanana_edit", 
        "description": "Edit existing images with natural language instructions",
        "category": "image_editing"
    },
    "nanobanana_blend": {
        "name": "nanobanana_blend",
        "description": "Blend multiple images into a new composition",
        "category": "image_blending"
    },
    "nanobanana_status": {
        "name": "nanobanana_status",
        "description": "Check server status and API connectivity",
        "category": "status"
    }
}

# ================================
# 이미지 처리 관련 상수
# ================================
# 지원되는 입력 형식
SUPPORTED_INPUT_FORMATS = [
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"
]

# 지원되는 출력 형식
SUPPORTED_OUTPUT_FORMATS = ["png", "jpeg", "webp"]

# 이미지 품질 설정
IMAGE_QUALITY_LEVELS = {
    "low": 60,
    "medium": 80, 
    "high": 95,
    "auto": 85
}

# 기본 이미지 크기 제한 (MB)
DEFAULT_MAX_IMAGE_SIZE = 10

# ================================
# 종횡비 프리셋
# ================================
ASPECT_RATIOS = {
    "square": "1:1",
    "landscape": "16:9", 
    "portrait": "9:16",
    "widescreen": "21:9",
    "cinema": "2.39:1",
    "photo": "4:3",
    "instagram": "1:1",
    "story": "9:16",
    "banner": "3:1"
}

# ================================
# 프롬프트 최적화 관련
# ================================
# 품질 향상 키워드
QUALITY_KEYWORDS = [
    "high quality", "detailed", "sharp", "crisp", "professional",
    "photorealistic", "ultra-detailed", "masterpiece", "best quality"
]

# 스타일 프리셋
STYLE_PRESETS = {
    "photorealistic": "photorealistic, professional photography, high quality",
    "digital_art": "digital art, concept art, detailed illustration",
    "oil_painting": "oil painting, classical art, brush strokes",
    "watercolor": "watercolor painting, soft colors, artistic",
    "cartoon": "cartoon style, animated, colorful, stylized",
    "anime": "anime style, manga, japanese animation",
    "sketch": "pencil sketch, black and white, hand-drawn",
    "vintage": "vintage style, retro, aged, classic"
}

# 금지 키워드 (안전성)
PROHIBITED_KEYWORDS = [
    "nsfw", "explicit", "adult", "violence", "gore", "hate",
    "discrimination", "illegal", "harmful", "dangerous"
]

# ================================
# 언어 및 번역 관련
# ================================
# 지원되는 언어 코드
SUPPORTED_LANGUAGES = {
    "ko": "Korean",
    "en": "English", 
    "ja": "Japanese",
    "zh": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian"
}

# 번역이 권장되는 언어 (영어가 아닌 경우)
TRANSLATION_RECOMMENDED = ["ko", "ja", "zh", "es", "fr", "de", "it", "pt", "ru"]

# ================================
# 캐싱 관련 상수
# ================================
# 캐시 키 프리픽스
CACHE_PREFIX = "nanobanana_"

# 캐시 만료 시간 (초)
CACHE_EXPIRY_TIMES = {
    "image": 24 * 60 * 60,      # 24시간
    "status": 5 * 60,           # 5분
    "prompt": 7 * 24 * 60 * 60  # 7일
}

# 캐시 파일 확장자
CACHE_FILE_EXTENSIONS = {
    "image": ".png",
    "metadata": ".json",
    "prompt": ".txt"
}

# ================================
# 에러 코드 및 메시지
# ================================
ERROR_CODES = {
    # API 관련 에러
    "API_KEY_MISSING": {
        "code": "E001",
        "message": "Google AI API key is missing or invalid"
    },
    "API_RATE_LIMIT": {
        "code": "E002", 
        "message": "API rate limit exceeded"
    },
    "API_QUOTA_EXCEEDED": {
        "code": "E003",
        "message": "API quota exceeded"
    },
    
    # 이미지 관련 에러
    "IMAGE_TOO_LARGE": {
        "code": "E101",
        "message": "Image file is too large"
    },
    "IMAGE_FORMAT_UNSUPPORTED": {
        "code": "E102",
        "message": "Unsupported image format"
    },
    "IMAGE_CORRUPT": {
        "code": "E103",
        "message": "Image file is corrupted or invalid"
    },
    
    # 프롬프트 관련 에러
    "PROMPT_TOO_LONG": {
        "code": "E201",
        "message": "Prompt is too long"
    },
    "PROMPT_UNSAFE": {
        "code": "E202",
        "message": "Prompt contains unsafe content"
    },
    "PROMPT_EMPTY": {
        "code": "E203",
        "message": "Prompt cannot be empty"
    },
    
    # 시스템 관련 에러
    "DISK_SPACE_LOW": {
        "code": "E301",
        "message": "Insufficient disk space"
    },
    "PERMISSION_DENIED": {
        "code": "E302",
        "message": "Permission denied for file operations"
    },
    "SERVER_OVERLOAD": {
        "code": "E303",
        "message": "Server is overloaded"
    }
}

# ================================
# 성능 및 제한 관련
# ================================
# 요청 제한
MAX_CONCURRENT_REQUESTS = 3
MAX_REQUEST_TIMEOUT = 300  # 5분
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2

# 프롬프트 길이 제한
MAX_PROMPT_LENGTH = 2000
MIN_PROMPT_LENGTH = 3

# 배치 처리 제한
MAX_BATCH_SIZE = 4
MAX_IMAGES_PER_REQUEST = 4

# ================================
# 파일명 생성 관련
# ================================
# 파일명 패턴
FILENAME_PATTERNS = {
    "generated": "nanobanana_generated_{timestamp}_{hash}",
    "edited": "nanobanana_edited_{timestamp}_{hash}",
    "blended": "nanobanana_blended_{timestamp}_{hash}",
    "temp": "temp_{timestamp}_{random}"
}

# 금지된 파일명 문자
FORBIDDEN_FILENAME_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

# 최대 파일명 길이
MAX_FILENAME_LENGTH = 255

# ================================
# 버전 및 메타데이터
# ================================
PROJECT_VERSION = "1.0.0"
PROJECT_NAME = "nanobanana-mcp"
PROJECT_DESCRIPTION = "Gemini 2.5 Flash Image MCP Server for Claude Code"
PROJECT_AUTHOR = "Claude Code Assistant"

# API 버전
MCP_VERSION = "0.1.0"
GEMINI_API_VERSION = "v1"

# 사용자 에이전트
USER_AGENT = f"{PROJECT_NAME}/{PROJECT_VERSION} (MCP/{MCP_VERSION})"