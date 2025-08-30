"""
이미지 블렌딩 도구

Gemini 2.5 Flash Image API를 사용하여 여러 이미지를 합성하여 새로운 이미지를 생성하는 MCP 도구입니다.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..gemini_client import get_gemini_client, create_gemini_client, GeminiAPIError
from ..utils.prompt_optimizer import get_prompt_optimizer, PromptCategory
from ..utils.image_handler import get_image_handler
from ..utils.file_manager import get_file_manager
from ..models.schemas import (
    BlendImagesRequest,
    BlendImagesResponse,
    ImageMetadata,
    create_error_response,
    OperationType
)
from ..constants import GEMINI_MODEL_NAME, GEMINI_COST_PER_IMAGE
from ..config import get_settings

logger = logging.getLogger(__name__)


async def nanobanana_blend(
    image_paths: List[str],
    blend_prompt: str,
    maintain_consistency: Optional[bool] = True,
    output_format: Optional[str] = "png",
    quality: Optional[str] = "high",
    optimize_prompt: Optional[bool] = True,
    **kwargs
) -> Dict[str, Any]:
    """
    여러 이미지를 블렌딩하여 새로운 이미지 생성
    
    Args:
        image_paths: 블렌딩할 이미지 파일 경로들 (2-4개)
        blend_prompt: 블렌딩 지시사항
        maintain_consistency: 캐릭터 일관성 유지 여부 (기본값: True)
        output_format: 출력 이미지 형식 ("png", "jpeg", "webp")
        quality: 이미지 품질 ("auto", "high", "medium", "low")
        optimize_prompt: 프롬프트 자동 최적화 여부 (기본값: True)
        **kwargs: 추가 설정
        
    Returns:
        Dict: MCP 응답 형식의 블렌딩 결과
    """
    start_time = time.time()
    settings = get_settings()
    
    try:
        logger.info(f"Starting image blending with {len(image_paths)} images: {blend_prompt[:100]}...")
        
        # 1. 요청 파라미터 검증
        try:
            request_data = {
                "image_paths": image_paths,
                "blend_prompt": blend_prompt,
                "maintain_consistency": maintain_consistency if maintain_consistency is not None else True,
                "output_format": output_format,
                "quality": quality,
                "optimize_prompt": optimize_prompt if optimize_prompt is not None else True
            }
            
            # Pydantic 모델로 검증
            request = BlendImagesRequest(**request_data)
            logger.debug(f"Request validation successful for {len(request.image_paths)} images")
            
        except Exception as e:
            logger.error(f"Request validation failed: {e}")
            return create_error_response(
                f"Invalid request parameters: {str(e)}",
                "VALIDATION_ERROR"
            ).dict()
        
        # 2. 소스 이미지들 검증 및 정보 수집
        try:
            image_handler = get_image_handler()
            source_images_info = []
            
            for i, image_path in enumerate(request.image_paths):
                logger.debug(f"Loading source image {i+1}/{len(request.image_paths)}: {image_path}")
                
                # 이미지 로드 및 검증
                source_image = image_handler.load_image(image_path)
                image_info = image_handler.get_image_info(source_image)
                
                source_info = {
                    "index": i + 1,
                    "path": str(Path(image_path).absolute()),
                    "size": image_info["size"],
                    "format": image_info.get("format", "unknown"),
                    "mode": image_info["mode"],
                    "file_size_mb": Path(image_path).stat().st_size / (1024 * 1024)
                }
                source_images_info.append(source_info)
                
                logger.info(f"Loaded source image {i+1}: {image_info['size']}, {image_info.get('format', 'unknown')}")
            
            # 이미지 크기 호환성 검사 (권장사항)
            sizes = [info["size"] for info in source_images_info]
            if len(set(sizes)) > 1:
                logger.warning(f"Source images have different sizes: {sizes}. Blending may produce unexpected results.")
            
        except Exception as e:
            logger.error(f"Source images validation failed: {e}")
            return create_error_response(
                f"Failed to load or validate source images: {str(e)}",
                "IMAGE_LOAD_ERROR"
            ).dict()
        
        # 3. 프롬프트 최적화
        optimized_prompt = request.blend_prompt
        if request.optimize_prompt:
            try:
                optimizer = get_prompt_optimizer()
                
                # 일관성 유지 키워드 추가
                additional_keywords = []
                if request.maintain_consistency:
                    additional_keywords.extend(["consistent style", "coherent composition", "unified lighting"])
                
                optimized_prompt = optimizer.optimize_prompt(
                    prompt=request.blend_prompt,
                    category=PromptCategory.BLENDING,
                    quality_level=request.quality,
                    additional_keywords=additional_keywords
                )
                logger.info(f"Prompt optimized: '{request.blend_prompt}' -> '{optimized_prompt}'")
                
            except Exception as e:
                logger.warning(f"Prompt optimization failed, using original: {e}")
                optimized_prompt = request.blend_prompt
        
        # 4. Gemini API를 통한 이미지 블렌딩
        try:
            gemini_client = get_gemini_client()
            
            # MCP 호출 시 클라이언트가 None인 경우 새로 생성
            if gemini_client is None:
                logger.info("Creating new Gemini client for MCP call")
                gemini_client = await create_gemini_client()
            
            # API 호출
            api_result = await gemini_client.blend_images(
                image_paths=request.image_paths,
                blend_prompt=optimized_prompt,
                **kwargs
            )
            
            logger.info(f"Successfully blended {len(request.image_paths)} images via Gemini API")
            
        except GeminiAPIError as e:
            logger.error(f"Gemini API error: {e}")
            return create_error_response(
                f"Image blending failed: {e.message}",
                e.code or "API_ERROR"
            ).dict()
        
        except Exception as e:
            logger.error(f"Unexpected error during image blending: {e}")
            return create_error_response(
                f"Image blending failed: {str(e)}",
                "BLENDING_ERROR"
            ).dict()
        
        # 5. 블렌딩된 이미지 처리 및 저장
        try:
            file_manager = get_file_manager()
            blended_images = api_result.get("images", [])
            
            if not blended_images:
                logger.error("No blended image returned from API")
                return create_error_response(
                    "No blended image was generated",
                    "NO_RESULT_ERROR"
                ).dict()
            
            # 첫 번째 (그리고 보통 유일한) 블렌딩된 이미지 처리
            blended_image_data = blended_images[0]
            
            # MIME 타입 추출 (파일 포맷 감지용)
            actual_mime_type = None
            
            # 이미지 데이터가 bytes가 아닌 경우 변환
            if not isinstance(blended_image_data, bytes):
                # dict 형태인 경우 실제 데이터 및 MIME 타입 추출
                if isinstance(blended_image_data, dict):
                    base64_data = blended_image_data.get('data') or blended_image_data.get('bytes') or blended_image_data.get('image_data')
                    actual_mime_type = blended_image_data.get('mime_type')  # 실제 포맷 정보 추출
                    
                    if base64_data and hasattr(image_handler, 'base64_to_bytes'):
                        blended_image_data = image_handler.base64_to_bytes(base64_data)
                    else:
                        logger.error("No valid image data found in blended result")
                        return create_error_response(
                            "Invalid blended image data format",
                            "DATA_FORMAT_ERROR"
                        ).dict()
                elif isinstance(blended_image_data, str):
                    # 직접 base64 문자열인 경우
                    if hasattr(image_handler, 'base64_to_bytes'):
                        blended_image_data = image_handler.base64_to_bytes(blended_image_data)
                    else:
                        logger.error("Invalid blended image data format")
                        return create_error_response(
                            "Invalid blended image data format",
                            "DATA_FORMAT_ERROR"
                        ).dict()
                else:
                    logger.error(f"Invalid blended image data format: {type(blended_image_data)}")
                    return create_error_response(
                        "Invalid blended image data format",
                        "DATA_FORMAT_ERROR"
                    ).dict()
            
            # 실제 파일 포맷 결정 (MIME 타입 우선, 사용자 요청 포맷 대체)
            if actual_mime_type:
                # MIME 타입에서 확장자 추출 (image/webp → webp, image/jpeg → jpeg)
                actual_format = actual_mime_type.split('/')[-1].lower().replace('jpg', 'jpeg')
                
                # 사용자 요청 포맷과 다른 경우 로깅
                if actual_format != request.output_format:
                    logger.info(f"Format adjusted for blended image: requested '{request.output_format}' → actual '{actual_format}' (API returned {actual_mime_type})")
                
                final_output_format = actual_format
            else:
                # MIME 타입이 없으면 사용자 요청 포맷 사용
                final_output_format = request.output_format
                logger.debug(f"Using requested format '{request.output_format}' for blended image (no MIME type from API)")
            
            # 블렌딩 메타데이터 준비
            processing_time = time.time() - start_time
            metadata = {
                "model_used": GEMINI_MODEL_NAME,
                "source_images": [info["path"] for info in source_images_info],
                "source_images_info": source_images_info,
                "original_prompt": request.blend_prompt,
                "optimized_prompt": optimized_prompt,
                "maintain_consistency": request.maintain_consistency,
                "processing_time": processing_time,
                "cost_usd": GEMINI_COST_PER_IMAGE,
                "blend_complexity": len(request.image_paths),  # 복잡도 지표
                "request_id": api_result.get("metadata", {}).get("request_id")
            }
            
            # 블렌딩된 이미지 저장 (실제 포맷 사용)
            save_result = file_manager.save_image_with_metadata(
                image_data=blended_image_data,
                operation_type="blended",
                metadata=metadata,
                prompt=request.blend_prompt,
                output_format=final_output_format
            )
            
            if not save_result["success"]:
                logger.error("Failed to save blended image")
                return create_error_response(
                    "Failed to save blended image",
                    "SAVE_ERROR"
                ).dict()
            
            # ImageMetadata 객체 생성 (실제 저장된 포맷 사용)
            blended_image_metadata = ImageMetadata(
                filename=save_result["filename"],
                filepath=save_result["filepath"],
                operation_type=OperationType.BLENDING,
                created_at=save_result["metadata"]["created_at"],
                file_size=save_result["metadata"]["file_size"],
                format=final_output_format,  # 실제 저장된 포맷
                width=None,  # 실제 이미지에서 추출하면 더 좋음
                height=None,
                prompt=request.blend_prompt,
                optimized_prompt=optimized_prompt,
                model_used=GEMINI_MODEL_NAME,
                generation_time=processing_time,
                cost_usd=GEMINI_COST_PER_IMAGE,
                hash=save_result["metadata"]["hash"]
            )
            
            logger.info(f"Successfully saved blended image: {save_result['filepath']}")
            
        except Exception as e:
            logger.error(f"Image processing and saving failed: {e}")
            return create_error_response(
                f"Failed to process blended image: {str(e)}",
                "PROCESSING_ERROR"
            ).dict()
        
        # 6. 응답 생성
        try:
            response = BlendImagesResponse(
                success=True,
                message=f"Successfully blended {len(request.image_paths)} images",
                source_images=[info["path"] for info in source_images_info],
                blended_image=blended_image_metadata,
                blend_prompt=request.blend_prompt,
                optimized_prompt=optimized_prompt,
                processing_time=processing_time
            )
            
            logger.info(
                f"Image blending completed successfully in {processing_time:.2f}s. "
                f"Blended {len(request.image_paths)} images. Cost: ${GEMINI_COST_PER_IMAGE:.4f}"
            )
            
            return response.dict()
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return create_error_response(
                "Failed to generate response",
                "RESPONSE_ERROR"
            ).dict()
    
    except Exception as e:
        logger.error(f"Unexpected error in nanobanana_blend: {e}")
        return create_error_response(
            f"Unexpected error: {str(e)}",
            "INTERNAL_ERROR"
        ).dict()


async def batch_blend_images(
    requests: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    배치 이미지 블렌딩
    
    Args:
        requests: 블렌딩 요청 리스트
        
    Returns:
        List[Dict]: 블렌딩 결과 리스트
    """
    try:
        logger.info(f"Starting batch image blending for {len(requests)} requests")
        
        # 동시 실행 제한
        settings = get_settings()
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
        async def blend_with_semaphore(request_data: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await nanobanana_blend(**request_data)
        
        # 모든 요청을 병렬로 실행
        tasks = [blend_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch blend request {i+1} failed: {result}")
                error_response = create_error_response(
                    f"Batch blend request {i+1} failed: {str(result)}",
                    "BATCH_ERROR"
                )
                processed_results.append(error_response.dict())
            else:
                processed_results.append(result)
        
        successful_count = sum(1 for r in processed_results if r.get("success", False))
        logger.info(f"Batch blending completed: {successful_count}/{len(requests)} successful")
        
        return processed_results
        
    except Exception as e:
        logger.error(f"Batch blending failed: {e}")
        error_response = create_error_response(
            f"Batch blending failed: {str(e)}",
            "BATCH_PROCESSING_ERROR"
        )
        return [error_response.dict()]


def validate_blend_request(data: Dict[str, Any]) -> BlendImagesRequest:
    """
    블렌딩 요청 데이터 검증
    
    Args:
        data: 요청 데이터
        
    Returns:
        BlendImagesRequest: 검증된 요청 객체
        
    Raises:
        ValueError: 검증 실패 시
    """
    try:
        return BlendImagesRequest(**data)
    except Exception as e:
        logger.error(f"Blend request validation failed: {e}")
        raise ValueError(f"Invalid blend request data: {str(e)}")


def get_blend_statistics() -> Dict[str, Any]:
    """
    이미지 블렌딩 통계 반환
    
    Returns:
        Dict: 블렌딩 통계 정보
    """
    try:
        file_manager = get_file_manager()
        
        # 블렌딩된 이미지 히스토리
        blended_images = file_manager.get_image_history(
            operation_type="blended",
            limit=1000
        )
        
        # 블렌딩 횟수 통계
        total_blends = len(blended_images)
        
        # 최근 블렌딩 (지난 24시간)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_blends = [
            img for img in blended_images
            if datetime.fromisoformat(img.get("created_at", "1970-01-01")) > recent_cutoff
        ]
        
        # 복잡도 분석 (소스 이미지 개수별 통계)
        complexity_stats = {}
        for img in blended_images:
            complexity = img.get("blend_complexity", 2)
            complexity_stats[f"{complexity}_images"] = complexity_stats.get(f"{complexity}_images", 0) + 1
        
        # 비용 계산
        total_cost = total_blends * GEMINI_COST_PER_IMAGE
        recent_cost = len(recent_blends) * GEMINI_COST_PER_IMAGE
        
        # 사용된 프롬프트 분석
        prompt_lengths = [len(img.get("prompt", "")) for img in blended_images if img.get("prompt")]
        avg_prompt_length = sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0
        
        # 일관성 유지 사용률
        consistency_enabled = sum(
            1 for img in blended_images 
            if img.get("maintain_consistency", False)
        )
        consistency_rate = (consistency_enabled / total_blends * 100) if total_blends > 0 else 0
        
        return {
            "total_blends": total_blends,
            "recent_blends_24h": len(recent_blends),
            "total_cost_usd": round(total_cost, 4),
            "recent_cost_usd": round(recent_cost, 4),
            "cost_per_blend": GEMINI_COST_PER_IMAGE,
            "average_prompt_length": round(avg_prompt_length, 1),
            "complexity_distribution": complexity_stats,
            "consistency_usage_rate": round(consistency_rate, 1),
            "model_info": {
                "name": GEMINI_MODEL_NAME,
                "provider": "Google"
            },
            "storage_info": file_manager.get_storage_stats().get("output_stats", {})
        }
        
    except Exception as e:
        logger.error(f"Failed to get blend statistics: {e}")
        return {"error": str(e)}


def analyze_blend_combinations() -> Dict[str, Any]:
    """
    블렌딩 조합 분석 (어떤 이미지 조합이 자주 사용되는지)
    
    Returns:
        Dict: 블렌딩 조합 분석 결과
    """
    try:
        file_manager = get_file_manager()
        blended_images = file_manager.get_image_history(operation_type="blended")
        
        # 이미지 개수별 블렌딩 분포
        image_count_stats = {}
        for blend in blended_images:
            source_count = len(blend.get("source_images", []))
            key = f"{source_count}_images"
            image_count_stats[key] = image_count_stats.get(key, 0) + 1
        
        # 가장 인기 있는 조합 수
        most_common_count = max(image_count_stats.values()) if image_count_stats else 0
        most_common_combination = max(
            image_count_stats.keys(), 
            key=lambda k: image_count_stats[k]
        ) if image_count_stats else "none"
        
        # 프롬프트 패턴 분석
        prompt_keywords = {}
        for blend in blended_images:
            prompt = blend.get("prompt", "").lower()
            words = prompt.split()
            for word in words:
                if len(word) > 3:  # 3글자 이상 단어만
                    prompt_keywords[word] = prompt_keywords.get(word, 0) + 1
        
        # 상위 키워드
        top_keywords = sorted(
            prompt_keywords.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return {
            "total_blends_analyzed": len(blended_images),
            "image_count_distribution": image_count_stats,
            "most_common_combination": most_common_combination,
            "most_common_count": most_common_count,
            "top_prompt_keywords": dict(top_keywords),
            "analysis_summary": {
                "average_source_images": sum(
                    len(img.get("source_images", [])) for img in blended_images
                ) / max(len(blended_images), 1),
                "complexity_trend": "increasing" if len(blended_images) > 10 else "stable"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze blend combinations: {e}")
        return {"error": str(e)}


def find_similar_blends(source_images: List[str]) -> List[Dict[str, Any]]:
    """
    유사한 블렌딩 찾기 (같은 소스 이미지를 사용한 블렌딩들)
    
    Args:
        source_images: 비교할 소스 이미지 경로들
        
    Returns:
        List[Dict]: 유사한 블렌딩 목록
    """
    try:
        file_manager = get_file_manager()
        all_blends = file_manager.get_image_history(operation_type="blended")
        
        # 소스 이미지들을 절대 경로로 정규화
        normalized_sources = [str(Path(img).absolute()) for img in source_images]
        normalized_sources_set = set(normalized_sources)
        
        similar_blends = []
        for blend in all_blends:
            blend_sources = blend.get("source_images", [])
            blend_sources_set = set(str(Path(img).absolute()) for img in blend_sources)
            
            # 교집합 비율 계산
            intersection = normalized_sources_set.intersection(blend_sources_set)
            union = normalized_sources_set.union(blend_sources_set)
            similarity = len(intersection) / len(union) if union else 0
            
            if similarity > 0.5:  # 50% 이상 유사한 경우
                similar_blends.append({
                    "blend_info": blend,
                    "similarity": similarity,
                    "common_images": list(intersection),
                    "unique_to_query": list(normalized_sources_set - blend_sources_set),
                    "unique_to_blend": list(blend_sources_set - normalized_sources_set)
                })
        
        # 유사도순으로 정렬
        similar_blends.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similar_blends[:10]  # 상위 10개 반환
        
    except Exception as e:
        logger.error(f"Failed to find similar blends: {e}")
        return []


# MCP 도구 메타데이터
TOOL_METADATA = {
    "name": "nanobanana_blend",
    "description": "Blend multiple images into a new composition using Gemini 2.5 Flash Image",
    "parameters": {
        "type": "object",
        "properties": {
            "image_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Paths to images to blend (2-4 images)",
                "minItems": 2,
                "maxItems": 4
            },
            "blend_prompt": {
                "type": "string",
                "description": "Instructions for how to blend the images",
                "minLength": 3,
                "maxLength": 2000
            },
            "maintain_consistency": {
                "type": "boolean",
                "description": "Maintain character and style consistency across blended images",
                "default": True
            },
            "output_format": {
                "type": "string",
                "description": "Output image format",
                "enum": ["png", "jpeg", "webp"],
                "default": "png"
            },
            "quality": {
                "type": "string",
                "description": "Output quality level",
                "enum": ["auto", "high", "medium", "low"],
                "default": "high"
            },
            "optimize_prompt": {
                "type": "boolean",
                "description": "Enable automatic prompt optimization",
                "default": True
            }
        },
        "required": ["image_paths", "blend_prompt"]
    },
    "returns": {
        "type": "object",
        "description": "Blending result with source images and blended image metadata"
    }
}