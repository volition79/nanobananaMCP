"""
텍스트-이미지 생성 도구

Gemini 2.5 Flash Image API를 사용하여 텍스트 프롬프트로부터 이미지를 생성하는 MCP 도구입니다.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from ..gemini_client import get_gemini_client, create_gemini_client, GeminiAPIError
from ..utils.prompt_optimizer import get_prompt_optimizer, PromptCategory
from ..utils.image_handler import get_image_handler
from ..utils.file_manager import get_file_manager
from ..models.schemas import (
    GenerateImageRequest,
    GenerateImageResponse,
    ImageMetadata,
    create_error_response,
    OperationType
)
from ..constants import GEMINI_MODEL_NAME, GEMINI_COST_PER_IMAGE
from ..config import get_settings

logger = logging.getLogger(__name__)


async def nanobanana_generate(
    prompt: str,
    aspect_ratio: Optional[str] = None,
    style: Optional[str] = None,
    quality: Optional[str] = "high",
    output_format: Optional[str] = "png",
    candidate_count: Optional[int] = 1,
    additional_keywords: Optional[List[str]] = None,
    optimize_prompt: Optional[bool] = True,
    **kwargs
) -> Dict[str, Any]:
    """
    텍스트 프롬프트로부터 이미지 생성
    
    Args:
        prompt: 이미지 생성을 위한 텍스트 설명
        aspect_ratio: 이미지 비율 (예: "16:9", "1:1", "9:16")
        style: 스타일 지정 (예: "photorealistic", "digital_art")
        quality: 이미지 품질 ("auto", "high", "medium", "low")
        output_format: 출력 이미지 형식 ("png", "jpeg", "webp")
        candidate_count: 생성할 이미지 수 (1-4, 기본값: 1)
        additional_keywords: 추가 키워드 리스트
        optimize_prompt: 프롬프트 자동 최적화 여부 (기본값: True)
        **kwargs: 추가 설정
        
    Returns:
        Dict: MCP 응답 형식의 생성 결과
    """
    start_time = time.time()
    settings = get_settings()
    
    try:
        logger.info(f"Starting image generation with prompt: '{prompt[:100]}...'")
        
        # 1. 요청 파라미터 검증
        try:
            request_data = {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "style": style,
                "quality": quality,
                "output_format": output_format,
                "candidate_count": candidate_count or 1,
                "additional_keywords": additional_keywords or [],
                "optimize_prompt": optimize_prompt if optimize_prompt is not None else True
            }
            
            # Pydantic 모델로 검증
            request = GenerateImageRequest(**request_data)
            logger.debug("Request validation successful")
            
        except Exception as e:
            logger.error(f"Request validation failed: {e}")
            return create_error_response(
                f"Invalid request parameters: {str(e)}",
                "VALIDATION_ERROR"
            ).dict()
        
        # 2. 프롬프트 최적화
        optimized_prompt = request.prompt
        if request.optimize_prompt:
            try:
                optimizer = get_prompt_optimizer()
                optimized_prompt = optimizer.optimize_prompt(
                    prompt=request.prompt,
                    category=PromptCategory.GENERATION,
                    aspect_ratio=request.aspect_ratio,
                    style=request.style,
                    quality_level=request.quality,
                    additional_keywords=request.additional_keywords
                )
                logger.info(f"Prompt optimized: '{request.prompt}' -> '{optimized_prompt}'")
                
            except Exception as e:
                logger.warning(f"Prompt optimization failed, using original: {e}")
                optimized_prompt = request.prompt
        
        # 3. Gemini API를 통한 이미지 생성
        try:
            gemini_client = get_gemini_client()
            logger.info(f"DEBUG: gemini_client type: {type(gemini_client)}, is None: {gemini_client is None}")
            
            # MCP 호출 시 클라이언트가 None인 경우 새로 생성
            if gemini_client is None:
                logger.info("Creating new Gemini client for MCP call")
                gemini_client = await create_gemini_client()
            
            logger.info(f"DEBUG: final gemini_client type: {type(gemini_client)}, has generate_image: {hasattr(gemini_client, 'generate_image')}")
            
            # API 호출
            api_result = await gemini_client.generate_image(
                prompt=optimized_prompt,
                aspect_ratio=request.aspect_ratio,
                quality=request.quality,
                candidate_count=request.candidate_count,
                **kwargs
            )
            
            # API 응답 검증
            if not api_result.get("success", False):
                logger.error(f"Gemini API returned unsuccessful result: {api_result}")
                return create_error_response(
                    f"API request unsuccessful: {api_result.get('error', 'Unknown error')}",
                    "API_ERROR"
                ).dict()
            
            if not api_result.get("images"):
                logger.error("Gemini API returned no images")
                return create_error_response(
                    "No images returned from API",
                    "NO_IMAGES_ERROR"
                ).dict()
            
            logger.info(f"Generated {len(api_result.get('images', []))} image(s) from Gemini API")
            
        except GeminiAPIError as e:
            logger.error(f"Gemini API error: {e}")
            # 상세 에러 정보 로깅
            if hasattr(e, 'details') and e.details:
                logger.error(f"API error details: {e.details}")
            return create_error_response(
                f"Image generation failed: {e.message}",
                e.code or "API_ERROR"
            ).dict()
        
        except Exception as e:
            logger.error(f"Unexpected error during image generation: {e}")
            # 디버그 정보 추가
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            return create_error_response(
                f"Image generation failed: {str(e)}",
                "GENERATION_ERROR"
            ).dict()
        
        # 4. 생성된 이미지들 처리 및 저장
        try:
            image_handler = get_image_handler()
            file_manager = get_file_manager()
            processed_images = []
            
            for i, image_data in enumerate(api_result.get("images", [])):
                logger.debug(f"Processing image {i+1}/{len(api_result['images'])}")
                
                # MIME 타입 추출 (파일 포맷 감지용)
                actual_mime_type = None
                
                # 이미지 데이터가 bytes가 아닌 경우 변환
                if not isinstance(image_data, bytes):
                    # dict 형태인 경우 실제 데이터 추출
                    if isinstance(image_data, dict):
                        # Gemini API 응답에서 base64 데이터 및 MIME 타입 추출
                        base64_data = image_data.get('data') or image_data.get('bytes') or image_data.get('image_data')
                        actual_mime_type = image_data.get('mime_type')  # 실제 포맷 정보 추출
                        
                        if base64_data:
                            # Base64 문자열인지 확인
                            if isinstance(base64_data, str) and image_handler.is_base64_string(base64_data):
                                logger.debug(f"Converting base64 string to bytes for image {i+1}")
                                image_data = image_handler.base64_to_bytes(base64_data)
                            else:
                                logger.warning(f"Base64 data validation failed for image {i+1}")
                                image_data = image_handler.base64_to_bytes(base64_data)  # 시도해봄
                        else:
                            logger.error(f"No valid image data found in dict for image {i+1}: {list(image_data.keys())}")
                            continue
                    elif isinstance(image_data, str):
                        # 직접 base64 문자열인 경우 - 검증 후 변환
                        if image_handler.is_base64_string(image_data):
                            logger.debug(f"Converting base64 string to bytes for image {i+1}")
                            image_data = image_handler.base64_to_bytes(image_data)
                        else:
                            logger.warning(f"String data doesn't appear to be valid base64 for image {i+1}")
                            # 그래도 시도해봄
                            try:
                                image_data = image_handler.base64_to_bytes(image_data)
                            except Exception as decode_error:
                                logger.error(f"Failed to decode string data for image {i+1}: {decode_error}")
                                continue
                    else:
                        logger.error(f"Invalid image data format for image {i+1}: {type(image_data)}")
                        continue
                
                # 변환된 바이너리 데이터 검증
                validation_result = image_handler.validate_image_data(image_data)
                if not validation_result.get('is_valid', False):
                    logger.error(f"Image {i+1} validation failed: {validation_result}")
                    # 검증 실패해도 계속 진행 (일부 뷰어에서만 문제일 수 있음)
                    logger.warning(f"Proceeding with potentially invalid image {i+1}")
                else:
                    logger.debug(f"Image {i+1} validation passed: {validation_result.get('detected_format')}")
                
                # MIME 타입이 없는 경우 검증 결과에서 가져오기
                if not actual_mime_type and validation_result.get('detected_format'):
                    detected_format = validation_result['detected_format']
                    actual_mime_type = f"image/{detected_format}"
                    logger.info(f"MIME type inferred from image signature for image {i+1}: {actual_mime_type}")
                
                # 실제 파일 포맷 결정 (MIME 타입 우선, 사용자 요청 포맷 대체)
                if actual_mime_type:
                    # MIME 타입에서 확장자 추출 (image/webp → webp, image/jpeg → jpeg)
                    actual_format = actual_mime_type.split('/')[-1].lower().replace('jpg', 'jpeg')
                    
                    # 사용자 요청 포맷과 다른 경우 로깅
                    if actual_format != request.output_format:
                        logger.info(f"Format adjusted for image {i+1}: requested '{request.output_format}' → actual '{actual_format}' (API returned {actual_mime_type})")
                    
                    final_output_format = actual_format
                else:
                    # MIME 타입이 없으면 사용자 요청 포맷 사용
                    final_output_format = request.output_format
                    logger.debug(f"Using requested format '{request.output_format}' for image {i+1} (no MIME type from API)")
                
                # 메타데이터 준비
                from datetime import datetime
                metadata = {
                    "model_used": GEMINI_MODEL_NAME,
                    "original_prompt": request.prompt,
                    "optimized_prompt": optimized_prompt,
                    "aspect_ratio": request.aspect_ratio,
                    "style": request.style,
                    "quality": request.quality,
                    "generation_time": time.time() - start_time,
                    "cost_usd": GEMINI_COST_PER_IMAGE,
                    "request_id": api_result.get("metadata", {}).get("request_id"),
                    "created_at": datetime.now().isoformat()
                }
                
                # Pillow를 통한 재처리 및 저장 (호환성 개선)
                try:
                    # 방법 1: Pillow로 재처리하여 메타데이터 정리 및 호환성 개선
                    processed_path = image_handler.save_bytes_as_image(
                        image_bytes=image_data,
                        output_path=file_manager.output_dir / "generated" / file_manager.generate_filename(
                            operation_type="generated",
                            prompt=request.prompt,
                            extension=final_output_format
                        ),
                        format=final_output_format,
                        quality=request.quality,
                        process_with_pillow=True  # 호환성을 위해 Pillow 재처리 사용
                    )
                    
                    # 메타데이터와 함께 저장 결과 구성
                    save_result = {
                        "success": True,
                        "filepath": str(processed_path),
                        "filename": processed_path.name,
                        "metadata": {
                            **metadata,
                            "processed_with_pillow": True,
                            "file_size": processed_path.stat().st_size if processed_path.exists() else len(image_data),
                            "created_at": metadata.get("created_at"),
                            "filename": processed_path.name,
                            "filepath": str(processed_path)
                        }
                    }
                    
                    logger.info(f"Image {i+1} processed with Pillow for better compatibility: {processed_path}")
                    
                except Exception as pillow_error:
                    logger.warning(f"Pillow processing failed for image {i+1}: {pillow_error}")
                    logger.info(f"Falling back to direct binary save for image {i+1}")
                    
                    # 방법 2: 직접 바이너리 저장 (폴백)
                    save_result = file_manager.save_image_with_metadata(
                        image_data=image_data,
                        operation_type="generated",
                        metadata=metadata,
                        prompt=request.prompt,
                        output_format=final_output_format
                    )
                
                if save_result["success"]:
                    # ImageMetadata 객체 생성 (실제 저장된 포맷 사용)
                    from datetime import datetime
                    
                    # created_at이 문자열이면 datetime 객체로 변환
                    created_at_value = save_result["metadata"]["created_at"]
                    if isinstance(created_at_value, str):
                        try:
                            created_at_value = datetime.fromisoformat(created_at_value.replace('Z', '+00:00'))
                        except:
                            created_at_value = datetime.now()
                    elif not isinstance(created_at_value, datetime):
                        created_at_value = datetime.now()
                    
                    image_metadata = ImageMetadata(
                        filename=save_result["filename"],
                        filepath=save_result["filepath"],
                        operation_type=OperationType.GENERATION,
                        created_at=created_at_value,
                        file_size=save_result["metadata"]["file_size"],
                        format=final_output_format,  # 실제 저장된 포맷
                        width=None,  # 실제 이미지에서 추출하면 더 좋음
                        height=None,
                        prompt=request.prompt,
                        optimized_prompt=optimized_prompt,
                        model_used=GEMINI_MODEL_NAME,
                        generation_time=metadata["generation_time"],
                        cost_usd=GEMINI_COST_PER_IMAGE,
                        hash=save_result["metadata"].get("hash", "")
                    )
                    
                    processed_images.append(image_metadata)
                    logger.info(f"Successfully saved image {i+1}: {save_result['filepath']}")
                else:
                    logger.error(f"Failed to save image {i+1}")
            
            if not processed_images:
                logger.error("No images were successfully processed and saved")
                # 디버그 정보 추가
                logger.error(f"API returned {len(api_result.get('images', []))} images")
                logger.error(f"Processing attempted on {len(api_result.get('images', []))} images")
                
                # 진단 정보 추가
                from ..utils.debug_tools import validate_base64_string
                for i, img_data in enumerate(api_result.get('images', [])):
                    if isinstance(img_data, str):
                        validation = validate_base64_string(img_data)
                        logger.error(f"Image {i+1} base64 validation: {validation}")
                    elif isinstance(img_data, dict):
                        base64_data = img_data.get('data', '')
                        if isinstance(base64_data, str):
                            validation = validate_base64_string(base64_data)
                            logger.error(f"Image {i+1} base64 validation: {validation}")
                
                return create_error_response(
                    "Failed to save generated images - see logs for details",
                    "SAVE_ERROR"
                ).dict()
            
        except Exception as e:
            logger.error(f"Image processing and saving failed: {e}")
            # 상세 디버그 정보
            import traceback
            logger.debug(f"Processing error traceback: {traceback.format_exc()}")
            logger.error(f"API result structure: {type(api_result)} - {list(api_result.keys()) if isinstance(api_result, dict) else 'Not a dict'}")
            
            return create_error_response(
                f"Failed to process generated images: {str(e)}",
                "PROCESSING_ERROR"
            ).dict()
        
        # 5. 응답 생성
        total_time = time.time() - start_time
        total_cost = len(processed_images) * GEMINI_COST_PER_IMAGE
        
        try:
            response = GenerateImageResponse(
                success=True,
                message=f"Successfully generated {len(processed_images)} image(s)",
                images=processed_images,
                original_prompt=request.prompt,
                optimized_prompt=optimized_prompt,
                generation_time=total_time,
                total_cost=total_cost,
                model_info={
                    "model_name": GEMINI_MODEL_NAME,
                    "version": "2.5-flash-image-preview",
                    "provider": "Google"
                }
            )
            
            logger.info(
                f"Image generation completed successfully. "
                f"Generated {len(processed_images)} images in {total_time:.2f}s. "
                f"Cost: ${total_cost:.4f}"
            )
            
            return response.dict()
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return create_error_response(
                "Failed to generate response",
                "RESPONSE_ERROR"
            ).dict()
    
    except Exception as e:
        logger.error(f"Unexpected error in nanobanana_generate: {e}")
        return create_error_response(
            f"Unexpected error: {str(e)}",
            "INTERNAL_ERROR"
        ).dict()


async def batch_generate_images(
    requests: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    배치 이미지 생성
    
    Args:
        requests: 생성 요청 리스트
        
    Returns:
        List[Dict]: 생성 결과 리스트
    """
    try:
        logger.info(f"Starting batch image generation for {len(requests)} requests")
        
        # 동시 실행 제한
        settings = get_settings()
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
        async def generate_with_semaphore(request_data: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await nanobanana_generate(**request_data)
        
        # 모든 요청을 병렬로 실행
        tasks = [generate_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch request {i+1} failed: {result}")
                error_response = create_error_response(
                    f"Batch request {i+1} failed: {str(result)}",
                    "BATCH_ERROR"
                )
                processed_results.append(error_response.dict())
            else:
                processed_results.append(result)
        
        successful_count = sum(1 for r in processed_results if r.get("success", False))
        logger.info(f"Batch generation completed: {successful_count}/{len(requests)} successful")
        
        return processed_results
        
    except Exception as e:
        logger.error(f"Batch generation failed: {e}")
        error_response = create_error_response(
            f"Batch generation failed: {str(e)}",
            "BATCH_PROCESSING_ERROR"
        )
        return [error_response.dict()]


def validate_generation_request(data: Dict[str, Any]) -> GenerateImageRequest:
    """
    생성 요청 데이터 검증
    
    Args:
        data: 요청 데이터
        
    Returns:
        GenerateImageRequest: 검증된 요청 객체
        
    Raises:
        ValueError: 검증 실패 시
    """
    try:
        return GenerateImageRequest(**data)
    except Exception as e:
        logger.error(f"Request validation failed: {e}")
        raise ValueError(f"Invalid request data: {str(e)}")


def get_generation_statistics() -> Dict[str, Any]:
    """
    이미지 생성 통계 반환
    
    Returns:
        Dict: 생성 통계 정보
    """
    try:
        gemini_client = get_gemini_client()
        if gemini_client is None:
            logger.warning("Gemini client not initialized, returning empty statistics")
            client_stats = {"requests_made": 0, "images_generated": 0, "estimated_cost": 0.0}
        else:
            client_stats = gemini_client.get_statistics()
        
        file_manager = get_file_manager()
        storage_stats = file_manager.get_storage_stats()
        
        # 생성된 이미지 히스토리
        generated_images = file_manager.get_image_history(
            operation_type="generated",
            limit=1000
        )
        
        return {
            "total_requests": client_stats["request_count"],
            "total_images_generated": client_stats["total_images_generated"],
            "total_cost_usd": client_stats["total_cost_usd"],
            "average_images_per_request": client_stats["average_images_per_request"],
            "recent_generations": len(generated_images),
            "storage_info": storage_stats.get("output_stats", {}),
            "cost_per_image": GEMINI_COST_PER_IMAGE,
            "model_info": {
                "name": GEMINI_MODEL_NAME,
                "provider": "Google"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get generation statistics: {e}")
        return {"error": str(e)}


# MCP 도구 메타데이터
TOOL_METADATA = {
    "name": "nanobanana_generate",
    "description": "Generate images from text prompts using Gemini 2.5 Flash Image",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description for image generation",
                "minLength": 3,
                "maxLength": 2000
            },
            "aspect_ratio": {
                "type": "string",
                "description": "Image aspect ratio (e.g., '16:9', '1:1', '9:16')",
                "enum": ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9", "2.39:1"]
            },
            "style": {
                "type": "string",
                "description": "Style preset",
                "enum": ["photorealistic", "digital_art", "oil_painting", "watercolor", "cartoon", "anime", "sketch", "vintage"]
            },
            "quality": {
                "type": "string",
                "description": "Image quality level",
                "enum": ["auto", "high", "medium", "low"],
                "default": "high"
            },
            "output_format": {
                "type": "string",
                "description": "Output image format",
                "enum": ["png", "jpeg", "webp"],
                "default": "png"
            },
            "candidate_count": {
                "type": "integer",
                "description": "Number of images to generate",
                "minimum": 1,
                "maximum": 4,
                "default": 1
            },
            "additional_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional keywords to enhance the prompt"
            },
            "optimize_prompt": {
                "type": "boolean",
                "description": "Enable automatic prompt optimization",
                "default": True
            }
        },
        "required": ["prompt"]
    },
    "returns": {
        "type": "object",
        "description": "Generation result with image metadata and file paths"
    }
}