"""
이미지 처리 유틸리티

이미지 로딩, 변환, 저장, 검증 등의 기능을 제공합니다.
"""

import hashlib
import logging
import mimetypes
import os
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple, Union, Dict, Any, List
import base64

from PIL import Image, ImageOps, ImageFilter
from PIL.ExifTags import TAGS
import httpx

from ..config import get_settings
from ..constants import (
    SUPPORTED_INPUT_FORMATS,
    SUPPORTED_OUTPUT_FORMATS, 
    IMAGE_QUALITY_LEVELS,
    DEFAULT_MAX_IMAGE_SIZE,
    GEMINI_MAX_IMAGE_SIZE_MB,
    ERROR_CODES,
    GEMINI_DEFAULT_RESOLUTION
)

logger = logging.getLogger(__name__)


class ImageHandlerError(Exception):
    """이미지 처리 관련 예외"""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(message)


class ImageHandler:
    """이미지 처리 유틸리티 클래스"""
    
    def __init__(self, settings=None):
        """
        이미지 핸들러 초기화
        
        Args:
            settings: 설정 객체
        """
        self.settings = settings or get_settings()
        logger.info("Image handler initialized")
    
    def load_image(self, source: Union[str, Path, bytes, BytesIO]) -> Image.Image:
        """
        이미지 로딩
        
        Args:
            source: 이미지 소스 (파일 경로, 바이트, BytesIO)
            
        Returns:
            PIL.Image.Image: 로드된 이미지
            
        Raises:
            ImageHandlerError: 로딩 실패 시
        """
        try:
            if isinstance(source, (str, Path)):
                # 파일 경로에서 로딩
                path = Path(source)
                if not path.exists():
                    raise ImageHandlerError(
                        f"Image file not found: {path}",
                        ERROR_CODES["IMAGE_CORRUPT"]["code"]
                    )
                
                # 파일 크기 검증
                size_mb = path.stat().st_size / (1024 * 1024)
                if size_mb > GEMINI_MAX_IMAGE_SIZE_MB:
                    raise ImageHandlerError(
                        f"Image file too large: {size_mb:.2f}MB (max: {GEMINI_MAX_IMAGE_SIZE_MB}MB)",
                        ERROR_CODES["IMAGE_TOO_LARGE"]["code"]
                    )
                
                # 형식 검증
                if path.suffix.lower() not in SUPPORTED_INPUT_FORMATS:
                    raise ImageHandlerError(
                        f"Unsupported image format: {path.suffix}",
                        ERROR_CODES["IMAGE_FORMAT_UNSUPPORTED"]["code"]
                    )
                
                image = Image.open(path)
                logger.info(f"Loaded image from {path}: {image.size}")
                
            elif isinstance(source, bytes):
                # 바이트에서 로딩
                if len(source) > GEMINI_MAX_IMAGE_SIZE_MB * 1024 * 1024:
                    raise ImageHandlerError(
                        f"Image data too large: {len(source) / 1024 / 1024:.2f}MB",
                        ERROR_CODES["IMAGE_TOO_LARGE"]["code"]
                    )
                
                image = Image.open(BytesIO(source))
                logger.info(f"Loaded image from bytes: {image.size}")
                
            elif isinstance(source, BytesIO):
                # BytesIO에서 로딩
                image = Image.open(source)
                logger.info(f"Loaded image from BytesIO: {image.size}")
                
            else:
                raise ImageHandlerError(
                    f"Unsupported source type: {type(source)}",
                    ERROR_CODES["IMAGE_FORMAT_UNSUPPORTED"]["code"]
                )
            
            # 이미지 검증
            image.verify()
            
            # 다시 열기 (verify()는 이미지를 닫음)
            if isinstance(source, (str, Path)):
                image = Image.open(source)
            elif isinstance(source, bytes):
                image = Image.open(BytesIO(source))
            else:
                source.seek(0)
                image = Image.open(source)
            
            # RGB 변환 (필요시)
            if image.mode not in ['RGB', 'RGBA']:
                image = image.convert('RGB')
                logger.debug(f"Converted image mode to RGB")
            
            return image
            
        except Exception as e:
            if isinstance(e, ImageHandlerError):
                raise
            logger.error(f"Failed to load image: {e}")
            raise ImageHandlerError(
                f"Failed to load image: {str(e)}",
                ERROR_CODES["IMAGE_CORRUPT"]["code"]
            )
    
    def save_image(
        self,
        image: Image.Image,
        output_path: Union[str, Path],
        format: str = None,
        quality: Union[str, int] = None,
        remove_metadata: bool = True,
        **kwargs
    ) -> Path:
        """
        이미지 저장 (메타데이터 정리 및 호환성 개선)
        
        Args:
            image: 저장할 이미지
            output_path: 출력 경로
            format: 이미지 형식 (png, jpeg, webp)
            quality: 품질 설정
            remove_metadata: 메타데이터 제거 여부 (호환성 향상)
            **kwargs: 추가 저장 옵션
            
        Returns:
            Path: 저장된 파일 경로
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 형식 결정
            if not format:
                format = self.settings.default_format
            
            format = format.lower()
            if format not in SUPPORTED_OUTPUT_FORMATS:
                raise ImageHandlerError(
                    f"Unsupported output format: {format}",
                    ERROR_CODES["IMAGE_FORMAT_UNSUPPORTED"]["code"]
                )
            
            # 메타데이터 제거 (호환성 문제 해결)
            if remove_metadata:
                try:
                    # 이미지 데이터만 복사하여 깨끗한 이미지 생성
                    clean_image = Image.new(image.mode, image.size)
                    clean_image.putdata(list(image.getdata()))
                    image = clean_image
                    logger.debug("Removed image metadata for better compatibility")
                except Exception as meta_error:
                    logger.warning(f"Failed to remove metadata: {meta_error}, continuing with original")
            
            # 품질 설정
            save_kwargs = kwargs.copy()
            if quality:
                if isinstance(quality, str):
                    quality_value = IMAGE_QUALITY_LEVELS.get(quality, IMAGE_QUALITY_LEVELS["auto"])
                else:
                    quality_value = quality
                
                if format in ["jpeg", "webp"]:
                    save_kwargs["quality"] = quality_value
                    save_kwargs["optimize"] = True
            
            # PNG의 경우 압축 레벨 설정
            if format == "png":
                save_kwargs["optimize"] = True
                save_kwargs["compress_level"] = 6
                # PNG 호환성을 위한 추가 설정
                save_kwargs.setdefault("pnginfo", None)  # EXIF 정보 제거
            
            # 이미지 모드 조정
            if format == "jpeg" and image.mode in ["RGBA", "LA"]:
                # JPEG는 투명도를 지원하지 않으므로 RGB로 변환
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == "RGBA":
                    background.paste(image, mask=image.split()[-1])
                else:
                    background.paste(image)
                image = background
                logger.debug("Converted RGBA to RGB for JPEG compatibility")
            
            # 저장
            image.save(output_path, format=format.upper(), **save_kwargs)
            
            # 저장 후 검증
            if output_path.exists():
                file_size = output_path.stat().st_size
                logger.info(f"Saved image to {output_path} (format: {format}, size: {file_size} bytes)")
                
                # 저장된 파일 검증
                try:
                    with Image.open(output_path) as saved_img:
                        saved_img.verify()
                        logger.debug(f"Saved image verification passed")
                except Exception as verify_error:
                    logger.warning(f"Saved image verification failed: {verify_error}")
            else:
                raise ImageHandlerError("File was not created after save operation")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            raise ImageHandlerError(f"Failed to save image: {str(e)}")
    
    def save_bytes_as_image(
        self,
        image_bytes: bytes,
        output_path: Union[str, Path],
        format: str = None,
        quality: Union[str, int] = None,
        process_with_pillow: bool = True
    ) -> Path:
        """
        바이트 데이터를 이미지 파일로 저장 (Pillow 처리 옵션)
        
        Args:
            image_bytes: 이미지 바이트 데이터
            output_path: 출력 경로
            format: 원하는 출력 형식
            quality: 품질 설정
            process_with_pillow: Pillow로 재처리하여 호환성 개선
            
        Returns:
            Path: 저장된 파일 경로
        """
        try:
            output_path = Path(output_path)
            
            if process_with_pillow:
                # Pillow로 재처리하여 메타데이터 정리 및 호환성 개선
                with Image.open(BytesIO(image_bytes)) as img:
                    return self.save_image(
                        image=img,
                        output_path=output_path,
                        format=format,
                        quality=quality,
                        remove_metadata=True
                    )
            else:
                # 직접 바이너리 저장 (빠르지만 호환성 문제 가능)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)
                
                logger.info(f"Saved raw bytes to {output_path} ({len(image_bytes)} bytes)")
                return output_path
                
        except Exception as e:
            logger.error(f"Failed to save bytes as image: {e}")
            raise ImageHandlerError(f"Failed to save bytes as image: {str(e)}")
    
    def resize_image(
        self,
        image: Image.Image,
        target_size: Optional[Tuple[int, int]] = None,
        max_size: Optional[int] = None,
        maintain_aspect: bool = True
    ) -> Image.Image:
        """
        이미지 크기 조정
        
        Args:
            image: 원본 이미지
            target_size: 목표 크기 (width, height)
            max_size: 최대 크기 (한 변의 최대 길이)
            maintain_aspect: 비율 유지 여부
            
        Returns:
            PIL.Image.Image: 크기 조정된 이미지
        """
        try:
            original_size = image.size
            
            if target_size:
                new_size = target_size
                if maintain_aspect:
                    image = ImageOps.fit(image, new_size, Image.LANCZOS)
                else:
                    image = image.resize(new_size, Image.LANCZOS)
                    
            elif max_size:
                # 한 변의 최대 길이로 조정
                ratio = min(max_size / original_size[0], max_size / original_size[1])
                if ratio < 1:
                    new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
                    image = image.resize(new_size, Image.LANCZOS)
            
            logger.debug(f"Resized image from {original_size} to {image.size}")
            return image
            
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            raise ImageHandlerError(f"Failed to resize image: {str(e)}")
    
    def optimize_for_gemini(self, image: Image.Image) -> Image.Image:
        """
        Gemini API에 최적화된 이미지로 변환
        
        Args:
            image: 원본 이미지
            
        Returns:
            PIL.Image.Image: 최적화된 이미지
        """
        try:
            # Gemini 권장 해상도로 조정
            max_dimension = max(GEMINI_DEFAULT_RESOLUTION)
            if max(image.size) > max_dimension:
                image = self.resize_image(image, max_size=max_dimension)
            
            # RGB 모드로 변환
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 메타데이터 제거 (파일 크기 감소)
            data = list(image.getdata())
            clean_image = Image.new(image.mode, image.size)
            clean_image.putdata(data)
            
            logger.debug(f"Optimized image for Gemini: {clean_image.size}")
            return clean_image
            
        except Exception as e:
            logger.error(f"Failed to optimize image for Gemini: {e}")
            raise ImageHandlerError(f"Failed to optimize image: {str(e)}")
    
    def image_to_bytes(
        self,
        image: Image.Image,
        format: str = "PNG",
        quality: Union[str, int] = "high"
    ) -> bytes:
        """
        이미지를 바이트로 변환
        
        Args:
            image: 변환할 이미지
            format: 출력 형식
            quality: 품질 설정
            
        Returns:
            bytes: 이미지 바이트 데이터
        """
        try:
            buffer = BytesIO()
            
            # 품질 설정
            save_kwargs = {}
            if isinstance(quality, str):
                quality_value = IMAGE_QUALITY_LEVELS.get(quality, IMAGE_QUALITY_LEVELS["high"])
            else:
                quality_value = quality
                
            if format.upper() in ["JPEG", "WEBP"]:
                save_kwargs["quality"] = quality_value
                save_kwargs["optimize"] = True
            
            image.save(buffer, format=format.upper(), **save_kwargs)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to convert image to bytes: {e}")
            raise ImageHandlerError(f"Failed to convert image to bytes: {str(e)}")
    
    def bytes_to_base64(self, image_bytes: bytes) -> str:
        """
        바이트를 base64 문자열로 변환
        
        Args:
            image_bytes: 이미지 바이트 데이터
            
        Returns:
            str: base64 인코딩된 문자열
        """
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def base64_to_bytes(self, base64_string: Union[str, bytes]) -> bytes:
        """
        base64 문자열을 바이트로 변환 (URL-safe 형식 지원)
        
        Args:
            base64_string: base64 인코딩된 문자열 또는 바이트
            
        Returns:
            bytes: 디코딩된 바이트 데이터
        """
        try:
            # 타입 체크 및 변환
            if isinstance(base64_string, bytes):
                try:
                    base64_string = base64_string.decode('utf-8')
                except UnicodeDecodeError:
                    # 이미 바이너리 데이터인 경우 그대로 반환
                    return base64_string
            elif not isinstance(base64_string, str):
                raise ImageHandlerError(f"Invalid base64 input type: {type(base64_string)}")
            
            # 문자열 전처리
            clean_string = base64_string.strip()
            
            # URL-safe base64를 표준 base64로 변환
            if '-' in clean_string or '_' in clean_string:
                logger.debug("Detected URL-safe base64, converting to standard format")
                # URL-safe base64 문자를 표준 base64 문자로 변환
                clean_string = clean_string.replace('-', '+').replace('_', '/')
            
            # 패딩 추가 (필요한 경우)
            padding_needed = len(clean_string) % 4
            if padding_needed:
                clean_string += '=' * (4 - padding_needed)
                logger.debug(f"Added {4 - padding_needed} padding characters")
            
            # 첫 번째 디코딩 시도 (표준 base64)
            try:
                decoded_bytes = base64.b64decode(clean_string)
                logger.debug(f"Successfully decoded base64 string ({len(decoded_bytes)} bytes)")
                return decoded_bytes
            except Exception as decode_error:
                logger.warning(f"Standard base64 decode failed: {decode_error}, trying urlsafe decode")
                
                # 두 번째 시도: URL-safe 디코딩
                try:
                    decoded_bytes = base64.urlsafe_b64decode(clean_string)
                    logger.debug(f"Successfully decoded URL-safe base64 string ({len(decoded_bytes)} bytes)")
                    return decoded_bytes
                except Exception as urlsafe_error:
                    logger.error(f"Both standard and URL-safe base64 decode failed: {urlsafe_error}")
                    raise decode_error  # 원래 에러를 다시 발생시킴
                    
        except Exception as e:
            logger.error(f"Failed to decode base64: {e}")
            raise ImageHandlerError(f"Invalid base64 data: {str(e)}")
    
    def validate_image_data(self, data: bytes) -> Dict[str, Any]:
        """
        이미지 데이터 검증 및 포맷 감지
        
        Args:
            data: 검증할 바이너리 데이터
            
        Returns:
            Dict: 검증 결과 및 감지된 정보
        """
        try:
            # 파일 시그니처 확인
            signatures = {
                'png': b'\x89PNG\r\n\x1a\n',
                'jpeg': b'\xff\xd8\xff',
                'webp': b'RIFF',
                'gif': b'GIF8',
                'bmp': b'BM'
            }
            
            detected_format = None
            for fmt, signature in signatures.items():
                if data.startswith(signature):
                    detected_format = fmt
                    break
                    
            # WebP 추가 검증
            if detected_format == 'webp' and len(data) > 12:
                if data[8:12] != b'WEBP':
                    detected_format = None
            
            # 크기 검증
            size_mb = len(data) / (1024 * 1024)
            
            # Pillow로 추가 검증 시도
            pillow_valid = False
            pillow_format = None
            try:
                with Image.open(BytesIO(data)) as img:
                    pillow_valid = True
                    pillow_format = img.format.lower() if img.format else None
            except Exception as pillow_error:
                logger.warning(f"Pillow validation failed: {pillow_error}")
            
            result = {
                'is_valid': detected_format is not None and pillow_valid,
                'detected_format': detected_format,
                'pillow_format': pillow_format,
                'size_bytes': len(data),
                'size_mb': round(size_mb, 2),
                'has_signature': detected_format is not None,
                'pillow_validates': pillow_valid
            }
            
            if result['is_valid']:
                logger.debug(f"Image validation passed: {result}")
            else:
                logger.warning(f"Image validation failed: {result}")
                
            return result
            
        except Exception as e:
            logger.error(f"Image data validation error: {e}")
            return {
                'is_valid': False,
                'error': str(e),
                'size_bytes': len(data),
                'size_mb': round(len(data) / (1024 * 1024), 2)
            }
    
    def is_base64_string(self, data: str) -> bool:
        """
        문자열이 Base64 인코딩되었는지 확인
        
        Args:
            data: 확인할 문자열
            
        Returns:
            bool: Base64 문자열 여부
        """
        try:
            # Base64 문자만 포함하는지 확인
            import re
            base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
            url_safe_pattern = re.compile(r'^[A-Za-z0-9_-]*={0,2}$')
            
            clean_data = data.strip()
            
            # 최소 길이 확인 (실제 이미지 데이터면 상당히 길어야 함)
            if len(clean_data) < 100:
                return False
                
            # 패턴 매칭
            is_standard_base64 = base64_pattern.match(clean_data) is not None
            is_url_safe_base64 = url_safe_pattern.match(clean_data) is not None
            
            if is_standard_base64 or is_url_safe_base64:
                # 실제 디코딩이 가능한지 테스트
                try:
                    test_decode = self.base64_to_bytes(clean_data)
                    # 디코딩된 데이터가 이미지 시그니처를 가지는지 확인
                    validation = self.validate_image_data(test_decode)
                    return validation.get('has_signature', False)
                except:
                    return False
            
            return False
            
        except Exception as e:
            logger.debug(f"Base64 string detection failed: {e}")
            return False
    
    def get_image_info(self, image: Image.Image) -> Dict[str, Any]:
        """
        이미지 정보 추출
        
        Args:
            image: 분석할 이미지
            
        Returns:
            Dict: 이미지 정보
        """
        try:
            info = {
                "size": image.size,
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "format": image.format,
                "has_transparency": image.mode in ["RGBA", "LA"] or "transparency" in image.info
            }
            
            # EXIF 데이터 추출 (가능한 경우)
            if hasattr(image, '_getexif') and image._getexif():
                exif = {}
                for tag_id, value in image._getexif().items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif[tag] = value
                info["exif"] = exif
            
            return info
            
        except Exception as e:
            logger.warning(f"Failed to extract image info: {e}")
            return {"size": image.size, "mode": image.mode}
    
    def create_thumbnail(
        self,
        image: Image.Image,
        size: Tuple[int, int] = (256, 256)
    ) -> Image.Image:
        """
        썸네일 생성
        
        Args:
            image: 원본 이미지
            size: 썸네일 크기
            
        Returns:
            PIL.Image.Image: 썸네일 이미지
        """
        try:
            thumbnail = image.copy()
            thumbnail.thumbnail(size, Image.LANCZOS)
            logger.debug(f"Created thumbnail: {thumbnail.size}")
            return thumbnail
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            raise ImageHandlerError(f"Failed to create thumbnail: {str(e)}")
    
    def validate_image_size(self, image: Image.Image) -> bool:
        """
        이미지 크기 검증
        
        Args:
            image: 검증할 이미지
            
        Returns:
            bool: 검증 결과
        """
        max_pixels = GEMINI_DEFAULT_RESOLUTION[0] * GEMINI_DEFAULT_RESOLUTION[1] * 4  # 4배 여유
        total_pixels = image.width * image.height
        
        return total_pixels <= max_pixels
    
    def calculate_image_hash(self, image: Image.Image) -> str:
        """
        이미지 해시 계산 (중복 검사용)
        
        Args:
            image: 해시를 계산할 이미지
            
        Returns:
            str: 이미지 해시값
        """
        try:
            # 이미지를 작은 크기로 축소하고 그레이스케일로 변환
            small_image = image.resize((8, 8), Image.LANCZOS).convert('L')
            
            # 픽셀 데이터를 바이트로 변환
            pixels = small_image.tobytes()
            
            # SHA-256 해시 계산
            hash_value = hashlib.sha256(pixels).hexdigest()
            
            return hash_value[:16]  # 16자리 단축 해시
            
        except Exception as e:
            logger.error(f"Failed to calculate image hash: {e}")
            return hashlib.sha256(str(image.size).encode()).hexdigest()[:16]
    
    async def download_image(self, url: str, timeout: int = 30) -> Image.Image:
        """
        URL에서 이미지 다운로드
        
        Args:
            url: 이미지 URL
            timeout: 타임아웃 (초)
            
        Returns:
            PIL.Image.Image: 다운로드된 이미지
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Content-Type 검증
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    raise ImageHandlerError(f"Invalid content type: {content_type}")
                
                # 크기 검증
                if len(response.content) > GEMINI_MAX_IMAGE_SIZE_MB * 1024 * 1024:
                    raise ImageHandlerError(
                        "Downloaded image too large",
                        ERROR_CODES["IMAGE_TOO_LARGE"]["code"]
                    )
                
                image = Image.open(BytesIO(response.content))
                logger.info(f"Downloaded image from {url}: {image.size}")
                return image
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise ImageHandlerError(f"Failed to download image: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to process downloaded image: {e}")
            raise ImageHandlerError(f"Failed to process downloaded image: {str(e)}")
    
    def apply_basic_filters(self, image: Image.Image, filter_name: str) -> Image.Image:
        """
        기본 필터 적용
        
        Args:
            image: 원본 이미지
            filter_name: 필터 이름 (blur, sharpen, smooth, detail)
            
        Returns:
            PIL.Image.Image: 필터가 적용된 이미지
        """
        try:
            filters = {
                "blur": ImageFilter.BLUR,
                "sharpen": ImageFilter.SHARPEN,
                "smooth": ImageFilter.SMOOTH,
                "detail": ImageFilter.DETAIL,
                "edge_enhance": ImageFilter.EDGE_ENHANCE,
                "emboss": ImageFilter.EMBOSS
            }
            
            if filter_name not in filters:
                raise ImageHandlerError(f"Unknown filter: {filter_name}")
            
            filtered_image = image.filter(filters[filter_name])
            logger.debug(f"Applied filter '{filter_name}' to image")
            return filtered_image
            
        except Exception as e:
            logger.error(f"Failed to apply filter: {e}")
            raise ImageHandlerError(f"Failed to apply filter: {str(e)}")


# 전역 이미지 핸들러 인스턴스 (싱글톤)
_image_handler: Optional[ImageHandler] = None


def get_image_handler() -> ImageHandler:
    """
    이미지 핸들러 인스턴스 반환 (싱글톤 패턴)
    
    Returns:
        ImageHandler: 핸들러 인스턴스
    """
    global _image_handler
    if _image_handler is None:
        _image_handler = ImageHandler()
    return _image_handler