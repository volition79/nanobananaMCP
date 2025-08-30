"""
프롬프트 최적화 유틸리티

PDF 가이드의 권장사항을 바탕으로 Gemini 2.5 Flash Image에 최적화된 
프롬프트를 생성하고 개선하는 기능을 제공합니다.
"""

import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from ..config import get_settings
from ..constants import (
    QUALITY_KEYWORDS,
    STYLE_PRESETS,
    PROHIBITED_KEYWORDS,
    ASPECT_RATIOS,
    SUPPORTED_LANGUAGES,
    TRANSLATION_RECOMMENDED,
    MAX_PROMPT_LENGTH,
    MIN_PROMPT_LENGTH,
    ERROR_CODES
)

logger = logging.getLogger(__name__)


class PromptCategory(Enum):
    """프롬프트 카테고리"""
    GENERATION = "generation"      # 이미지 생성
    EDITING = "editing"           # 이미지 편집
    BLENDING = "blending"         # 이미지 블렌딩
    STYLE_TRANSFER = "style_transfer"  # 스타일 전송


class PromptOptimizerError(Exception):
    """프롬프트 최적화 관련 예외"""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(message)


class PromptOptimizer:
    """
    프롬프트 최적화 클래스
    
    PDF 가이드의 모범 사례를 따라 Gemini에 최적화된 프롬프트를 생성합니다.
    """
    
    def __init__(self, settings=None):
        """
        프롬프트 최적화기 초기화
        
        Args:
            settings: 설정 객체
        """
        self.settings = settings or get_settings()
        
        # 번역 캐시 (간단한 인메모리 캐시)
        self._translation_cache = {}
        
        logger.info("Prompt optimizer initialized")
    
    def optimize_prompt(
        self,
        prompt: str,
        category: PromptCategory = PromptCategory.GENERATION,
        aspect_ratio: Optional[str] = None,
        style: Optional[str] = None,
        quality_level: Optional[str] = None,
        additional_keywords: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        프롬프트 최적화
        
        Args:
            prompt: 원본 프롬프트
            category: 프롬프트 카테고리
            aspect_ratio: 종횡비 (예: "16:9", "1:1")
            style: 스타일 프리셋
            quality_level: 품질 레벨
            additional_keywords: 추가 키워드 리스트
            **kwargs: 추가 설정
            
        Returns:
            str: 최적화된 프롬프트
            
        Raises:
            PromptOptimizerError: 최적화 실패 시
        """
        try:
            # 1. 기본 검증
            self._validate_prompt(prompt)
            
            # 2. 언어 감지 및 번역 (필요시)
            optimized = prompt
            if self.settings.auto_translate:
                optimized = self._translate_if_needed(optimized)
            
            # 3. 안전성 검사
            self._check_safety(optimized)
            
            # 4. 카테고리별 최적화
            optimized = self._apply_category_optimization(optimized, category)
            
            # 5. 스타일 적용
            if style:
                optimized = self._apply_style(optimized, style)
            
            # 6. 품질 키워드 추가
            optimized = self._enhance_quality(optimized, quality_level)
            
            # 7. 종횡비 추가
            if aspect_ratio:
                optimized = self._add_aspect_ratio(optimized, aspect_ratio)
            
            # 8. 추가 키워드 적용
            if additional_keywords:
                optimized = self._add_keywords(optimized, additional_keywords)
            
            # 9. 구조 최적화
            optimized = self._optimize_structure(optimized)
            
            # 10. 최종 검증
            self._validate_final_prompt(optimized)
            
            logger.info(f"Optimized prompt: '{prompt[:50]}...' -> '{optimized[:50]}...'")
            return optimized
            
        except Exception as e:
            if isinstance(e, PromptOptimizerError):
                raise
            logger.error(f"Failed to optimize prompt: {e}")
            raise PromptOptimizerError(f"Prompt optimization failed: {str(e)}")
    
    def _validate_prompt(self, prompt: str) -> None:
        """
        프롬프트 기본 검증
        
        Args:
            prompt: 검증할 프롬프트
            
        Raises:
            PromptOptimizerError: 검증 실패 시
        """
        if not prompt or not prompt.strip():
            raise PromptOptimizerError(
                "Prompt cannot be empty",
                ERROR_CODES["PROMPT_EMPTY"]["code"]
            )
        
        if len(prompt) < MIN_PROMPT_LENGTH:
            raise PromptOptimizerError(
                f"Prompt too short (minimum {MIN_PROMPT_LENGTH} characters)",
                ERROR_CODES["PROMPT_EMPTY"]["code"]
            )
        
        if len(prompt) > MAX_PROMPT_LENGTH:
            raise PromptOptimizerError(
                f"Prompt too long (maximum {MAX_PROMPT_LENGTH} characters)",
                ERROR_CODES["PROMPT_TOO_LONG"]["code"]
            )
    
    def _check_safety(self, prompt: str) -> None:
        """
        안전성 검사
        
        Args:
            prompt: 검사할 프롬프트
            
        Raises:
            PromptOptimizerError: 안전하지 않은 내용 발견 시
        """
        prompt_lower = prompt.lower()
        
        for keyword in PROHIBITED_KEYWORDS:
            if keyword in prompt_lower:
                logger.warning(f"Prohibited keyword detected: {keyword}")
                raise PromptOptimizerError(
                    f"Prompt contains unsafe content: {keyword}",
                    ERROR_CODES["PROMPT_UNSAFE"]["code"]
                )
    
    def _detect_language(self, text: str) -> str:
        """
        텍스트 언어 감지 (간단한 휴리스틱)
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            str: 언어 코드
        """
        # 한글 패턴
        if re.search(r'[ㄱ-ㅎㅏ-ㅣ가-힣]', text):
            return "ko"
        
        # 일본어 패턴
        if re.search(r'[ひらがなカタカナ]', text):
            return "ja"
        
        # 중국어 패턴 (간체/번체)
        if re.search(r'[\u4e00-\u9fff]', text):
            return "zh"
        
        # 러시아어 패턴
        if re.search(r'[а-яё]', text):
            return "ru"
        
        # 기본적으로 영어로 간주
        return "en"
    
    def _translate_if_needed(self, prompt: str) -> str:
        """
        필요시 프롬프트를 영어로 번역
        
        Args:
            prompt: 원본 프롬프트
            
        Returns:
            str: 번역된 프롬프트 (필요시) 또는 원본
        """
        detected_lang = self._detect_language(prompt)
        
        if detected_lang == "en":
            return prompt
        
        if detected_lang not in TRANSLATION_RECOMMENDED:
            return prompt
        
        # 캐시 확인
        if prompt in self._translation_cache:
            logger.debug("Using cached translation")
            return self._translation_cache[prompt]
        
        # 간단한 번역 (실제로는 외부 번역 API를 사용해야 함)
        translated = self._simple_translate(prompt, detected_lang)
        
        # 캐시 저장
        self._translation_cache[prompt] = translated
        
        logger.info(f"Translated prompt from {detected_lang} to English")
        return translated
    
    def _simple_translate(self, text: str, source_lang: str) -> str:
        """
        간단한 번역 (실제로는 Google Translate API 등을 사용)
        
        Args:
            text: 번역할 텍스트
            source_lang: 원본 언어 코드
            
        Returns:
            str: 번역된 텍스트
        """
        # 일반적인 한국어 -> 영어 번역 예시
        korean_translations = {
            "고양이": "cat",
            "강아지": "dog", 
            "꽃": "flower",
            "나무": "tree",
            "하늘": "sky",
            "바다": "ocean",
            "산": "mountain",
            "집": "house",
            "자동차": "car",
            "사람": "person",
            "아름다운": "beautiful",
            "예쁜": "pretty",
            "멋진": "cool",
            "큰": "big",
            "작은": "small"
        }
        
        if source_lang == "ko":
            translated = text
            for ko_word, en_word in korean_translations.items():
                translated = translated.replace(ko_word, en_word)
            return translated
        
        # 다른 언어는 원본 반환 (실제로는 번역 API 사용)
        return text
    
    def _apply_category_optimization(self, prompt: str, category: PromptCategory) -> str:
        """
        카테고리별 최적화 적용
        
        Args:
            prompt: 원본 프롬프트
            category: 프롬프트 카테고리
            
        Returns:
            str: 카테고리 최적화된 프롬프트
        """
        category_prefixes = {
            PromptCategory.GENERATION: "Generate an image of",
            PromptCategory.EDITING: "Edit this image to",
            PromptCategory.BLENDING: "Blend these images to create",
            PromptCategory.STYLE_TRANSFER: "Apply the style of"
        }
        
        # 이미 적절한 시작 구문이 있는지 확인
        prompt_lower = prompt.lower()
        has_prefix = any(
            prompt_lower.startswith(prefix.lower()) 
            for prefix in category_prefixes.values()
        )
        
        if not has_prefix and category in category_prefixes:
            prefix = category_prefixes[category]
            prompt = f"{prefix} {prompt}"
        
        return prompt
    
    def _apply_style(self, prompt: str, style: str) -> str:
        """
        스타일 프리셋 적용
        
        Args:
            prompt: 원본 프롬프트
            style: 스타일 이름
            
        Returns:
            str: 스타일이 적용된 프롬프트
        """
        if style in STYLE_PRESETS:
            style_keywords = STYLE_PRESETS[style]
            
            # 이미 스타일 키워드가 포함되어 있는지 확인
            prompt_lower = prompt.lower()
            style_words = style_keywords.lower().split(", ")
            
            missing_words = [
                word for word in style_words 
                if word not in prompt_lower
            ]
            
            if missing_words:
                prompt = f"{prompt}, {', '.join(missing_words)}"
        
        return prompt
    
    def _enhance_quality(self, prompt: str, quality_level: Optional[str] = None) -> str:
        """
        품질 키워드 추가
        
        Args:
            prompt: 원본 프롬프트
            quality_level: 품질 레벨
            
        Returns:
            str: 품질이 향상된 프롬프트
        """
        # 이미 품질 키워드가 있는지 확인
        prompt_lower = prompt.lower()
        has_quality = any(keyword in prompt_lower for keyword in QUALITY_KEYWORDS)
        
        if not has_quality:
            if quality_level == "high":
                quality_additions = "high quality, detailed, professional"
            elif quality_level == "medium":
                quality_additions = "good quality, clear"
            else:  # auto or default
                quality_additions = "high quality, detailed"
            
            prompt = f"{prompt}, {quality_additions}"
        
        return prompt
    
    def _add_aspect_ratio(self, prompt: str, aspect_ratio: str) -> str:
        """
        종횡비 추가
        
        Args:
            prompt: 원본 프롬프트
            aspect_ratio: 종횡비
            
        Returns:
            str: 종횡비가 추가된 프롬프트
        """
        # 이미 aspect ratio가 언급되어 있는지 확인
        if "aspect ratio" not in prompt.lower() and "ratio" not in prompt.lower():
            # 프리셋 확인
            if aspect_ratio in ASPECT_RATIOS:
                ratio_value = ASPECT_RATIOS[aspect_ratio]
            else:
                ratio_value = aspect_ratio
            
            prompt = f"{prompt}, {ratio_value} aspect ratio"
        
        return prompt
    
    def _add_keywords(self, prompt: str, keywords: List[str]) -> str:
        """
        추가 키워드 적용
        
        Args:
            prompt: 원본 프롬프트
            keywords: 추가할 키워드 리스트
            
        Returns:
            str: 키워드가 추가된 프롬프트
        """
        prompt_lower = prompt.lower()
        new_keywords = []
        
        for keyword in keywords:
            if keyword.lower() not in prompt_lower:
                new_keywords.append(keyword)
        
        if new_keywords:
            prompt = f"{prompt}, {', '.join(new_keywords)}"
        
        return prompt
    
    def _optimize_structure(self, prompt: str) -> str:
        """
        프롬프트 구조 최적화
        
        Args:
            prompt: 원본 프롬프트
            
        Returns:
            str: 구조가 최적화된 프롬프트
        """
        # 1. 불필요한 공백 제거
        prompt = re.sub(r'\s+', ' ', prompt.strip())
        
        # 2. 중복 쉼표 제거
        prompt = re.sub(r',\s*,+', ',', prompt)
        
        # 3. 쉼표 뒤 공백 정리
        prompt = re.sub(r',\s*', ', ', prompt)
        
        # 4. 마지막 쉼표 제거
        prompt = prompt.rstrip(', ')
        
        # 5. 중복 키워드 제거 (간단한 방법)
        words = [word.strip() for word in prompt.split(',')]
        unique_words = []
        seen = set()
        
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen and word:
                unique_words.append(word)
                seen.add(word_lower)
        
        prompt = ', '.join(unique_words)
        
        return prompt
    
    def _validate_final_prompt(self, prompt: str) -> None:
        """
        최종 프롬프트 검증
        
        Args:
            prompt: 검증할 최종 프롬프트
            
        Raises:
            PromptOptimizerError: 검증 실패 시
        """
        if len(prompt) > MAX_PROMPT_LENGTH:
            # 너무 길면 자동으로 잘라냄
            prompt = prompt[:MAX_PROMPT_LENGTH].rsplit(',', 1)[0]
            logger.warning(f"Prompt was too long and truncated to {len(prompt)} characters")
    
    def generate_negative_prompt(self, category: PromptCategory) -> str:
        """
        네거티브 프롬프트 생성 (원하지 않는 요소 제외용)
        
        Args:
            category: 프롬프트 카테고리
            
        Returns:
            str: 네거티브 프롬프트
        """
        base_negative = [
            "blurry", "low quality", "distorted", "deformed",
            "text", "watermark", "signature", "username"
        ]
        
        category_specific = {
            PromptCategory.GENERATION: ["bad anatomy", "extra limbs"],
            PromptCategory.EDITING: ["artifacts", "noise"],
            PromptCategory.BLENDING: ["mismatched colors", "harsh transitions"],
            PromptCategory.STYLE_TRANSFER: ["style inconsistency"]
        }
        
        negative_keywords = base_negative[:]
        if category in category_specific:
            negative_keywords.extend(category_specific[category])
        
        return ", ".join(negative_keywords)
    
    def analyze_prompt_quality(self, prompt: str) -> Dict[str, Any]:
        """
        프롬프트 품질 분석
        
        Args:
            prompt: 분석할 프롬프트
            
        Returns:
            Dict: 품질 분석 결과
        """
        analysis = {
            "length": len(prompt),
            "word_count": len(prompt.split()),
            "has_quality_keywords": any(kw in prompt.lower() for kw in QUALITY_KEYWORDS),
            "has_style_keywords": any(style in prompt.lower() for style in STYLE_PRESETS.keys()),
            "has_aspect_ratio": "aspect ratio" in prompt.lower() or "ratio" in prompt.lower(),
            "language": self._detect_language(prompt),
            "safety_score": self._calculate_safety_score(prompt),
            "optimization_suggestions": []
        }
        
        # 최적화 제안 생성
        if not analysis["has_quality_keywords"]:
            analysis["optimization_suggestions"].append("Add quality keywords (e.g., 'high quality', 'detailed')")
        
        if not analysis["has_style_keywords"]:
            analysis["optimization_suggestions"].append("Consider adding style keywords")
        
        if not analysis["has_aspect_ratio"]:
            analysis["optimization_suggestions"].append("Specify aspect ratio if needed")
        
        if analysis["language"] != "en":
            analysis["optimization_suggestions"].append("Consider translating to English for better results")
        
        return analysis
    
    def _calculate_safety_score(self, prompt: str) -> float:
        """
        안전성 점수 계산
        
        Args:
            prompt: 점수를 계산할 프롬프트
            
        Returns:
            float: 안전성 점수 (0.0-1.0)
        """
        prompt_lower = prompt.lower()
        violations = 0
        
        for keyword in PROHIBITED_KEYWORDS:
            if keyword in prompt_lower:
                violations += 1
        
        # 간단한 점수 계산 (실제로는 더 정교한 방법 사용)
        if violations == 0:
            return 1.0
        elif violations <= 2:
            return 0.7
        elif violations <= 5:
            return 0.4
        else:
            return 0.1
    
    def get_style_suggestions(self, prompt: str) -> List[str]:
        """
        프롬프트에 적합한 스타일 제안
        
        Args:
            prompt: 분석할 프롬프트
            
        Returns:
            List[str]: 추천 스타일 리스트
        """
        prompt_lower = prompt.lower()
        suggestions = []
        
        # 키워드 기반 스타일 추천
        if any(word in prompt_lower for word in ["photo", "realistic", "portrait"]):
            suggestions.append("photorealistic")
        
        if any(word in prompt_lower for word in ["art", "painting", "artistic"]):
            suggestions.append("digital_art")
        
        if any(word in prompt_lower for word in ["anime", "manga", "japanese"]):
            suggestions.append("anime")
        
        if any(word in prompt_lower for word in ["cartoon", "animated", "character"]):
            suggestions.append("cartoon")
        
        if any(word in prompt_lower for word in ["vintage", "retro", "old", "classic"]):
            suggestions.append("vintage")
        
        return suggestions[:3]  # 최대 3개까지


# 전역 프롬프트 최적화기 인스턴스 (싱글톤)
_prompt_optimizer: Optional[PromptOptimizer] = None


def get_prompt_optimizer() -> PromptOptimizer:
    """
    프롬프트 최적화기 인스턴스 반환 (싱글톤 패턴)
    
    Returns:
        PromptOptimizer: 최적화기 인스턴스
    """
    global _prompt_optimizer
    if _prompt_optimizer is None:
        _prompt_optimizer = PromptOptimizer()
    return _prompt_optimizer