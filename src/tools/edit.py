"""
이미지 편집 도구

Gemini 2.5 Flash Image API를 사용하여 기존 이미지를 자연어 명령으로 편집하는 MCP 도구입니다.
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
    EditImageRequest,
    EditImageResponse,
    ImageMetadata,
    create_error_response,
    OperationType
)
from ..constants import GEMINI_MODEL_NAME, GEMINI_COST_PER_IMAGE
from ..config import get_settings

logger = logging.getLogger(__name__)


async def nanobanana_edit(
    image_path: str,
    edit_prompt: str,
    mask_path: Optional[str] = None,
    output_format: Optional[str] = "png",
    quality: Optional[str] = "high",
    optimize_prompt: Optional[bool] = True,
    **kwargs
) -> Dict[str, Any]:
    """
    기존 이미지를 자연어 명령으로 편집
    
    Args:
        image_path: 편집할 이미지 파일 경로
        edit_prompt: 편집 지시사항
        mask_path: 마스크 이미지 경로 (선택사항)
        output_format: 출력 이미지 형식 ("png", "jpeg", "webp")
        quality: 이미지 품질 ("auto", "high", "medium", "low")
        optimize_prompt: 프롬프트 자동 최적화 여부 (기본값: True)
        **kwargs: 추가 설정
        
    Returns:
        Dict: MCP 응답 형식의 편집 결과
    """
    start_time = time.time()
    settings = get_settings()
    
    try:
        logger.info(f"Starting image editing: '{image_path}' with prompt: '{edit_prompt[:100]}...'")
        
        # 1. 요청 파라미터 검증
        try:
            request_data = {
                "image_path": image_path,
                "edit_prompt": edit_prompt,
                "mask_path": mask_path,
                "output_format": output_format,
                "quality": quality,
                "optimize_prompt": optimize_prompt if optimize_prompt is not None else True
            }
            
            # Pydantic 모델로 검증
            request = EditImageRequest(**request_data)
            logger.debug("Request validation successful")
            
        except Exception as e:
            logger.error(f"Request validation failed: {e}")
            return create_error_response(
                f"Invalid request parameters: {str(e)}",
                "VALIDATION_ERROR"
            ).dict()
        
        # 2. 이미지 파일 검증 및 정보 추출
        try:
            image_handler = get_image_handler()
            
            # 원본 이미지 로드 및 검증
            original_image = image_handler.load_image(request.image_path)
            image_info = image_handler.get_image_info(original_image)
            
            logger.info(f"Loaded original image: {image_info['size']}, format: {image_info.get('format', 'unknown')}")
            
            # 마스크 이미지 검증 (있는 경우)
            mask_image = None
            if request.mask_path:
                mask_image = image_handler.load_image(request.mask_path)
                mask_info = image_handler.get_image_info(mask_image)
                logger.info(f"Loaded mask image: {mask_info['size']}")
                
                # 마스크와 원본 이미지 크기 호환성 확인
                if mask_info['size'] != image_info['size']:
                    logger.warning(f"Mask size {mask_info['size']} differs from image size {image_info['size']}")
            
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return create_error_response(
                f"Failed to load or validate images: {str(e)}",
                "IMAGE_LOAD_ERROR"
            ).dict()
        
        # 3. 프롬프트 최적화
        optimized_prompt = request.edit_prompt
        if request.optimize_prompt:
            try:
                optimizer = get_prompt_optimizer()
                optimized_prompt = optimizer.optimize_prompt(
                    prompt=request.edit_prompt,
                    category=PromptCategory.EDITING,
                    quality_level=request.quality
                )
                logger.info(f"Prompt optimized: '{request.edit_prompt}' -> '{optimized_prompt}'")
                
            except Exception as e:
                logger.warning(f"Prompt optimization failed, using original: {e}")
                optimized_prompt = request.edit_prompt
        
        # 4. Gemini API를 통한 이미지 편집
        try:
            gemini_client = get_gemini_client()
            
            # MCP 호출 시 클라이언트가 None인 경우 새로 생성
            if gemini_client is None:
                logger.info("Creating new Gemini client for MCP call")
                gemini_client = await create_gemini_client()
            
            # API 호출
            api_result = await gemini_client.edit_image(
                image_path=request.image_path,
                edit_prompt=optimized_prompt,
                mask_path=request.mask_path if request.mask_path else None,
                **kwargs
            )
            
            logger.info(f"Successfully edited image via Gemini API")
            
        except GeminiAPIError as e:
            logger.error(f"Gemini API error: {e}")
            return create_error_response(
                f"Image editing failed: {e.message}",
                e.code or "API_ERROR"
            ).dict()
        
        except Exception as e:
            logger.error(f"Unexpected error during image editing: {e}")
            return create_error_response(
                f"Image editing failed: {str(e)}",
                "EDITING_ERROR"
            ).dict()
        
        # 5. 편집된 이미지 처리 및 저장
        try:
            file_manager = get_file_manager()
            edited_images = api_result.get("images", [])
            
            if not edited_images:
                logger.error("No edited image returned from API")
                return create_error_response(
                    "No edited image was generated",
                    "NO_RESULT_ERROR"
                ).dict()
            
            # 첫 번째 (그리고 보통 유일한) 편집된 이미지 처리
            edited_image_data = edited_images[0]
            
            # MIME 타입 추출 (파일 포맷 감지용)
            actual_mime_type = None
            
            # 이미지 데이터가 bytes가 아닌 경우 변환
            if not isinstance(edited_image_data, bytes):
                # dict 형태인 경우 실제 데이터 및 MIME 타입 추출
                if isinstance(edited_image_data, dict):
                    base64_data = edited_image_data.get('data') or edited_image_data.get('bytes') or edited_image_data.get('image_data')
                    actual_mime_type = edited_image_data.get('mime_type')  # 실제 포맷 정보 추출
                    
                    if base64_data and hasattr(image_handler, 'base64_to_bytes'):
                        edited_image_data = image_handler.base64_to_bytes(base64_data)
                    else:
                        logger.error("No valid image data found in edited result")
                        return create_error_response(
                            "Invalid edited image data format",
                            "DATA_FORMAT_ERROR"
                        ).dict()
                elif isinstance(edited_image_data, str):
                    # 직접 base64 문자열인 경우
                    if hasattr(image_handler, 'base64_to_bytes'):
                        edited_image_data = image_handler.base64_to_bytes(edited_image_data)
                    else:
                        logger.error("Invalid edited image data format")
                        return create_error_response(
                            "Invalid edited image data format",
                            "DATA_FORMAT_ERROR"
                        ).dict()
                else:
                    logger.error(f"Invalid edited image data format: {type(edited_image_data)}")
                    return create_error_response(
                        "Invalid edited image data format",
                        "DATA_FORMAT_ERROR"
                    ).dict()
            
            # 실제 파일 포맷 결정 (MIME 타입 우선, 사용자 요청 포맷 대체)
            if actual_mime_type:
                # MIME 타입에서 확장자 추출 (image/webp → webp, image/jpeg → jpeg)
                actual_format = actual_mime_type.split('/')[-1].lower().replace('jpg', 'jpeg')
                
                # 사용자 요청 포맷과 다른 경우 로깅
                if actual_format != request.output_format:
                    logger.info(f"Format adjusted for edited image: requested '{request.output_format}' → actual '{actual_format}' (API returned {actual_mime_type})")
                
                final_output_format = actual_format
            else:
                # MIME 타입이 없으면 사용자 요청 포맷 사용
                final_output_format = request.output_format
                logger.debug(f"Using requested format '{request.output_format}' for edited image (no MIME type from API)")
            
            # 편집 메타데이터 준비
            processing_time = time.time() - start_time
            metadata = {
                "model_used": GEMINI_MODEL_NAME,
                "original_image": str(Path(request.image_path).absolute()),
                "original_prompt": request.edit_prompt,
                "optimized_prompt": optimized_prompt,
                "mask_used": bool(request.mask_path),
                "mask_path": str(Path(request.mask_path).absolute()) if request.mask_path else None,
                "processing_time": processing_time,
                "cost_usd": GEMINI_COST_PER_IMAGE,
                "original_image_info": image_info,
                "request_id": api_result.get("metadata", {}).get("request_id")
            }
            
            # 편집된 이미지 저장 (실제 포맷 사용)
            save_result = file_manager.save_image_with_metadata(
                image_data=edited_image_data,
                operation_type="edited",
                metadata=metadata,
                prompt=request.edit_prompt,
                output_format=final_output_format
            )
            
            if not save_result["success"]:
                logger.error("Failed to save edited image")
                return create_error_response(
                    "Failed to save edited image",
                    "SAVE_ERROR"
                ).dict()
            
            # ImageMetadata 객체 생성 (실제 저장된 포맷 사용)
            edited_image_metadata = ImageMetadata(
                filename=save_result["filename"],
                filepath=save_result["filepath"],
                operation_type=OperationType.EDITING,
                created_at=save_result["metadata"]["created_at"],
                file_size=save_result["metadata"]["file_size"],
                format=final_output_format,  # 실제 저장된 포맷
                width=image_info.get("width"),
                height=image_info.get("height"),
                prompt=request.edit_prompt,
                optimized_prompt=optimized_prompt,
                model_used=GEMINI_MODEL_NAME,
                generation_time=processing_time,
                cost_usd=GEMINI_COST_PER_IMAGE,
                hash=save_result["metadata"]["hash"]
            )
            
            logger.info(f"Successfully saved edited image: {save_result['filepath']}")
            
        except Exception as e:
            logger.error(f"Image processing and saving failed: {e}")
            return create_error_response(
                f"Failed to process edited image: {str(e)}",
                "PROCESSING_ERROR"
            ).dict()
        
        # 6. 응답 생성
        try:
            response = EditImageResponse(
                success=True,
                message="Image editing completed successfully",
                original_image=str(Path(request.image_path).absolute()),
                edited_image=edited_image_metadata,
                edit_prompt=request.edit_prompt,
                optimized_prompt=optimized_prompt,
                processing_time=processing_time
            )
            
            logger.info(
                f"Image editing completed successfully in {processing_time:.2f}s. "
                f"Cost: ${GEMINI_COST_PER_IMAGE:.4f}"
            )
            
            return response.dict()
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return create_error_response(
                "Failed to generate response",
                "RESPONSE_ERROR"
            ).dict()
    
    except Exception as e:
        logger.error(f"Unexpected error in nanobanana_edit: {e}")
        return create_error_response(
            f"Unexpected error: {str(e)}",
            "INTERNAL_ERROR"
        ).dict()


async def batch_edit_images(
    requests: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    배치 이미지 편집
    
    Args:
        requests: 편집 요청 리스트
        
    Returns:
        List[Dict]: 편집 결과 리스트
    """
    try:
        logger.info(f"Starting batch image editing for {len(requests)} requests")
        
        # 동시 실행 제한
        settings = get_settings()
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
        async def edit_with_semaphore(request_data: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await nanobanana_edit(**request_data)
        
        # 모든 요청을 병렬로 실행
        tasks = [edit_with_semaphore(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch edit request {i+1} failed: {result}")
                error_response = create_error_response(
                    f"Batch edit request {i+1} failed: {str(result)}",
                    "BATCH_ERROR"
                )
                processed_results.append(error_response.dict())
            else:
                processed_results.append(result)
        
        successful_count = sum(1 for r in processed_results if r.get("success", False))
        logger.info(f"Batch editing completed: {successful_count}/{len(requests)} successful")
        
        return processed_results
        
    except Exception as e:
        logger.error(f"Batch editing failed: {e}")
        error_response = create_error_response(
            f"Batch editing failed: {str(e)}",
            "BATCH_PROCESSING_ERROR"
        )
        return [error_response.dict()]


def validate_edit_request(data: Dict[str, Any]) -> EditImageRequest:
    """
    편집 요청 데이터 검증
    
    Args:
        data: 요청 데이터
        
    Returns:
        EditImageRequest: 검증된 요청 객체
        
    Raises:
        ValueError: 검증 실패 시
    """
    try:
        return EditImageRequest(**data)
    except Exception as e:
        logger.error(f"Edit request validation failed: {e}")
        raise ValueError(f"Invalid edit request data: {str(e)}")


def get_edit_statistics() -> Dict[str, Any]:
    """
    이미지 편집 통계 반환
    
    Returns:
        Dict: 편집 통계 정보
    """
    try:
        file_manager = get_file_manager()
        
        # 편집된 이미지 히스토리
        edited_images = file_manager.get_image_history(
            operation_type="edited",
            limit=1000
        )
        
        # 편집 횟수 통계
        total_edits = len(edited_images)
        
        # 최근 편집 (지난 24시간)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_edits = [
            img for img in edited_images
            if datetime.fromisoformat(img.get("created_at", "1970-01-01")) > recent_cutoff
        ]
        
        # 비용 계산
        total_cost = total_edits * GEMINI_COST_PER_IMAGE
        recent_cost = len(recent_edits) * GEMINI_COST_PER_IMAGE
        
        # 사용된 프롬프트 분석
        prompt_lengths = [len(img.get("prompt", "")) for img in edited_images if img.get("prompt")]
        avg_prompt_length = sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0
        
        # 파일 형식 통계
        format_stats = {}
        for img in edited_images:
            fmt = img.get("format", "unknown")
            format_stats[fmt] = format_stats.get(fmt, 0) + 1
        
        return {
            "total_edits": total_edits,
            "recent_edits_24h": len(recent_edits),
            "total_cost_usd": round(total_cost, 4),
            "recent_cost_usd": round(recent_cost, 4),
            "cost_per_edit": GEMINI_COST_PER_IMAGE,
            "average_prompt_length": round(avg_prompt_length, 1),
            "format_distribution": format_stats,
            "model_info": {
                "name": GEMINI_MODEL_NAME,
                "provider": "Google"
            },
            "storage_info": file_manager.get_storage_stats().get("output_stats", {})
        }
        
    except Exception as e:
        logger.error(f"Failed to get edit statistics: {e}")
        return {"error": str(e)}


def analyze_edit_chain(image_path: str) -> Dict[str, Any]:
    """
    이미지 편집 체인 분석 (A→B→C 형태의 연속 편집)
    
    Args:
        image_path: 분석할 이미지 경로
        
    Returns:
        Dict: 편집 체인 정보
    """
    try:
        file_manager = get_file_manager()
        all_edits = file_manager.get_image_history(operation_type="edited")
        
        # 해당 이미지를 원본으로 사용한 편집들 찾기
        image_path = str(Path(image_path).absolute())
        
        chain = []
        current_path = image_path
        
        while True:
            # current_path를 원본으로 사용한 편집 찾기
            next_edits = [
                edit for edit in all_edits
                if edit.get("original_image") == current_path
            ]
            
            if not next_edits:
                break
                
            # 가장 최근 편집 선택 (여러 개 있을 수 있음)
            next_edit = sorted(next_edits, key=lambda x: x.get("created_at", ""))[-1]
            chain.append({
                "step": len(chain) + 1,
                "original": next_edit.get("original_image"),
                "edited": next_edit.get("filepath"),
                "prompt": next_edit.get("prompt"),
                "created_at": next_edit.get("created_at")
            })
            
            # 다음 단계를 위해 경로 업데이트
            current_path = next_edit.get("filepath")
            
            # 무한 루프 방지
            if len(chain) > 20:
                logger.warning("Edit chain too long, truncating")
                break
        
        return {
            "original_image": image_path,
            "chain_length": len(chain),
            "editing_steps": chain,
            "total_cost": len(chain) * GEMINI_COST_PER_IMAGE
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze edit chain: {e}")
        return {"error": str(e)}


# MCP 도구 메타데이터
TOOL_METADATA = {
    "name": "nanobanana_edit",
    "description": "Edit existing images with natural language instructions using Gemini 2.5 Flash Image",
    "parameters": {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the image file to edit"
            },
            "edit_prompt": {
                "type": "string",
                "description": "Natural language instructions for editing the image",
                "minLength": 3,
                "maxLength": 2000
            },
            "mask_path": {
                "type": "string",
                "description": "Optional path to mask image for selective editing"
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
        "required": ["image_path", "edit_prompt"]
    },
    "returns": {
        "type": "object",
        "description": "Edit result with original and edited image metadata"
    }
}