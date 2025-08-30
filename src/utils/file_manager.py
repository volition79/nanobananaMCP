"""
파일 관리 유틸리티

이미지 파일의 저장, 로딩, 캐싱, 메타데이터 관리 등을 담당합니다.
"""

import hashlib
import json
import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
import os
import tempfile

from ..config import get_settings
from ..constants import (
    FILENAME_PATTERNS,
    FORBIDDEN_FILENAME_CHARS,
    MAX_FILENAME_LENGTH,
    CACHE_PREFIX,
    CACHE_EXPIRY_TIMES,
    CACHE_FILE_EXTENSIONS,
    ERROR_CODES
)

logger = logging.getLogger(__name__)


class FileManagerError(Exception):
    """파일 관리 관련 예외"""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(message)


class FileManager:
    """
    파일 관리 유틸리티 클래스
    
    이미지 파일의 체계적인 관리, 캐싱, 메타데이터 추적을 담당합니다.
    """
    
    def __init__(self, settings=None):
        """
        파일 매니저 초기화
        
        Args:
            settings: 설정 객체
        """
        self.settings = settings or get_settings()
        
        # 디렉토리 설정
        self.output_dir = Path(self.settings.output_dir)
        self.temp_dir = Path(self.settings.temp_dir)
        self.cache_dir = Path(self.settings.cache_dir)
        
        # 디렉토리 생성
        self._ensure_directories()
        
        # 메타데이터 파일
        self.metadata_file = self.output_dir / "metadata.json"
        self.cache_index_file = self.cache_dir / "cache_index.json"
        
        logger.info("File manager initialized")
    
    def _ensure_directories(self) -> None:
        """필요한 디렉토리들을 생성"""
        directories = [
            self.output_dir,
            self.temp_dir,
            self.cache_dir,
            self.output_dir / "generated",
            self.output_dir / "edited", 
            self.output_dir / "blended",
            self.cache_dir / "images",
            self.cache_dir / "metadata"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def generate_filename(
        self,
        operation_type: str,
        prompt: Optional[str] = None,
        extension: str = "png",
        include_timestamp: bool = True,
        include_hash: bool = True
    ) -> str:
        """
        파일명 생성
        
        Args:
            operation_type: 작업 유형 (generated, edited, blended)
            prompt: 프롬프트 (해시 생성용)
            extension: 파일 확장자
            include_timestamp: 타임스탬프 포함 여부
            include_hash: 해시 포함 여부
            
        Returns:
            str: 생성된 파일명
        """
        try:
            # 기본 패턴 가져오기
            if operation_type in FILENAME_PATTERNS:
                pattern = FILENAME_PATTERNS[operation_type]
            else:
                pattern = "nanobanana_{operation}_{timestamp}_{hash}"
            
            # 파일명 구성 요소
            components = {}
            
            if include_timestamp:
                components["timestamp"] = datetime.now().strftime("%Y%m%d_%H%M%S")
            else:
                components["timestamp"] = ""
            
            if include_hash and prompt:
                # 프롬프트 기반 해시 생성
                hash_input = prompt.encode('utf-8')
                hash_value = hashlib.md5(hash_input).hexdigest()[:8]
                components["hash"] = hash_value
            else:
                components["hash"] = ""
            
            components["operation"] = operation_type
            components["random"] = str(int(time.time() * 1000) % 10000)
            
            # 패턴에 따라 파일명 생성
            filename = pattern.format(**components)
            
            # 불필요한 언더스코어 제거
            filename = filename.replace("__", "_").strip("_")
            
            # 확장자 추가
            if not filename.endswith(f".{extension}"):
                filename = f"{filename}.{extension}"
            
            # 파일명 정리
            filename = self._sanitize_filename(filename)
            
            logger.debug(f"Generated filename: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to generate filename: {e}")
            # 폴백 파일명
            fallback = f"nanobanana_{operation_type}_{int(time.time())}.{extension}"
            return self._sanitize_filename(fallback)
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        파일명 정리 (금지된 문자 제거)
        
        Args:
            filename: 원본 파일명
            
        Returns:
            str: 정리된 파일명
        """
        # 금지된 문자 제거
        for char in FORBIDDEN_FILENAME_CHARS:
            filename = filename.replace(char, "_")
        
        # 연속된 언더스코어 정리
        filename = "_".join(filter(None, filename.split("_")))
        
        # 길이 제한
        if len(filename) > MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(filename)
            max_name_length = MAX_FILENAME_LENGTH - len(ext)
            filename = name[:max_name_length] + ext
        
        return filename
    
    def save_image_with_metadata(
        self,
        image_data: bytes,
        operation_type: str,
        metadata: Dict[str, Any],
        prompt: Optional[str] = None,
        output_format: str = "png"
    ) -> Dict[str, Any]:
        """
        이미지와 메타데이터를 함께 저장
        
        Args:
            image_data: 이미지 바이트 데이터
            operation_type: 작업 유형
            metadata: 메타데이터
            prompt: 원본 프롬프트
            output_format: 출력 형식
            
        Returns:
            Dict: 저장 결과 정보
        """
        try:
            # 파일명 생성
            filename = self.generate_filename(
                operation_type=operation_type,
                prompt=prompt,
                extension=output_format
            )
            
            # 파일 경로 결정
            subdir = self.output_dir / operation_type
            subdir.mkdir(exist_ok=True)
            file_path = subdir / filename
            
            # 이미지 파일 저장 (바이너리 모드 강제)
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # 저장 후 파일 무결성 검증
            if not file_path.exists():
                raise FileManagerError("File was not created after write operation")
            
            # 파일 크기 검증
            actual_size = file_path.stat().st_size
            if actual_size != len(image_data):
                logger.warning(f"File size mismatch: expected {len(image_data)}, got {actual_size}")
            
            # 파일 시그니처 검증 (간단한 검증)
            try:
                with open(file_path, 'rb') as f:
                    file_header = f.read(8)
                    
                # 기본적인 이미지 시그니처 검증
                signatures = {
                    'png': b'\x89PNG\r\n\x1a\n',
                    'jpeg': b'\xff\xd8\xff',
                    'webp': b'RIFF'
                }
                
                signature_valid = False
                for fmt, signature in signatures.items():
                    if file_header.startswith(signature[:len(file_header)]):
                        logger.debug(f"File signature validation passed for {fmt}")
                        signature_valid = True
                        break
                
                if not signature_valid:
                    logger.warning(f"File signature validation failed for {file_path}")
                    logger.debug(f"File header: {file_header.hex()}")
                        
            except Exception as verify_error:
                logger.warning(f"File signature verification failed: {verify_error}")
            
            # 메타데이터 준비
            file_metadata = {
                "filename": filename,
                "filepath": str(file_path),
                "operation_type": operation_type,
                "created_at": datetime.now().isoformat(),
                "file_size": len(image_data),
                "format": output_format,
                "prompt": prompt,
                "hash": hashlib.sha256(image_data).hexdigest(),
                **metadata
            }
            
            # 메타데이터 저장
            self._save_metadata(file_metadata)
            
            # 캐시 정보 업데이트 (필요시)
            if self.settings.enable_cache:
                self._update_cache_index(file_path, file_metadata)
            
            logger.info(f"Saved image with metadata: {file_path}")
            
            return {
                "success": True,
                "filepath": str(file_path),
                "filename": filename,
                "metadata": file_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to save image with metadata: {e}")
            raise FileManagerError(f"Failed to save image: {str(e)}")
    
    def _save_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        메타데이터를 JSON 파일에 저장
        
        Args:
            metadata: 저장할 메타데이터
        """
        try:
            # 기존 메타데이터 로드
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
            else:
                all_metadata = {"images": [], "last_updated": None}
            
            # 새 메타데이터 추가
            all_metadata["images"].append(metadata)
            all_metadata["last_updated"] = datetime.now().isoformat()
            
            # 저장
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(all_metadata, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def get_image_history(
        self,
        limit: Optional[int] = None,
        operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        이미지 생성 기록 조회
        
        Args:
            limit: 최대 반환 개수
            operation_type: 필터링할 작업 유형
            
        Returns:
            List: 이미지 기록 리스트
        """
        try:
            if not self.metadata_file.exists():
                return []
            
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                all_metadata = json.load(f)
            
            images = all_metadata.get("images", [])
            
            # 작업 유형 필터링
            if operation_type:
                images = [img for img in images if img.get("operation_type") == operation_type]
            
            # 최신순 정렬
            images.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # 개수 제한
            if limit:
                images = images[:limit]
            
            return images
            
        except Exception as e:
            logger.error(f"Failed to get image history: {e}")
            return []
    
    def find_images_by_prompt(self, prompt: str, similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """
        프롬프트로 이미지 검색
        
        Args:
            prompt: 검색할 프롬프트
            similarity_threshold: 유사도 임계값
            
        Returns:
            List: 매칭되는 이미지 리스트
        """
        try:
            images = self.get_image_history()
            matches = []
            
            prompt_lower = prompt.lower()
            
            for image in images:
                image_prompt = image.get("prompt", "")
                if not image_prompt:
                    continue
                
                # 간단한 유사도 계산 (실제로는 더 정교한 방법 사용)
                similarity = self._calculate_prompt_similarity(prompt_lower, image_prompt.lower())
                
                if similarity >= similarity_threshold:
                    image["similarity"] = similarity
                    matches.append(image)
            
            # 유사도순 정렬
            matches.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            
            return matches
            
        except Exception as e:
            logger.error(f"Failed to find images by prompt: {e}")
            return []
    
    def _calculate_prompt_similarity(self, prompt1: str, prompt2: str) -> float:
        """
        프롬프트 유사도 계산 (간단한 방법)
        
        Args:
            prompt1: 첫 번째 프롬프트
            prompt2: 두 번째 프롬프트
            
        Returns:
            float: 유사도 (0.0-1.0)
        """
        words1 = set(prompt1.split())
        words2 = set(prompt2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        임시 파일 정리
        
        Args:
            max_age_hours: 최대 보존 시간 (시간)
            
        Returns:
            int: 삭제된 파일 수
        """
        try:
            if not self.temp_dir.exists():
                return 0
            
            deleted_count = 0
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    # 파일 생성 시간 확인
                    file_time = datetime.fromtimestamp(file_path.stat().st_ctime)
                    
                    if file_time < cutoff_time:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                            logger.debug(f"Deleted temp file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete temp file {file_path}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} temporary files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            return 0
    
    def manage_cache(self) -> Dict[str, Any]:
        """
        캐시 관리 (크기 제한, 만료 파일 삭제)
        
        Returns:
            Dict: 캐시 관리 결과
        """
        try:
            if not self.settings.enable_cache:
                return {"status": "disabled"}
            
            cache_stats = self._get_cache_stats()
            deleted_files = 0
            freed_space = 0
            
            # 만료된 파일 삭제
            expired_files = self._find_expired_cache_files()
            for file_path, size in expired_files:
                try:
                    file_path.unlink()
                    deleted_files += 1
                    freed_space += size
                    logger.debug(f"Deleted expired cache file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete cache file {file_path}: {e}")
            
            # 크기 제한 초과시 오래된 파일 삭제
            max_cache_size = self.settings.max_cache_size * 1024 * 1024  # MB to bytes
            current_size = cache_stats["total_size"] - freed_space
            
            if current_size > max_cache_size:
                old_files = self._get_oldest_cache_files(current_size - max_cache_size)
                for file_path, size in old_files:
                    try:
                        file_path.unlink()
                        deleted_files += 1
                        freed_space += size
                        current_size -= size
                        logger.debug(f"Deleted old cache file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete cache file {file_path}: {e}")
            
            # 캐시 인덱스 업데이트
            self._rebuild_cache_index()
            
            result = {
                "status": "completed",
                "deleted_files": deleted_files,
                "freed_space_mb": round(freed_space / 1024 / 1024, 2),
                "current_size_mb": round(current_size / 1024 / 1024, 2),
                "max_size_mb": self.settings.max_cache_size
            }
            
            logger.info(f"Cache management completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to manage cache: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보 반환"""
        try:
            if not self.cache_dir.exists():
                return {"total_files": 0, "total_size": 0}
            
            total_files = 0
            total_size = 0
            
            for file_path in self.cache_dir.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            return {"total_files": total_files, "total_size": total_size}
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"total_files": 0, "total_size": 0}
    
    def _find_expired_cache_files(self) -> List[Tuple[Path, int]]:
        """만료된 캐시 파일 찾기"""
        try:
            expired_files = []
            cutoff_time = datetime.now() - timedelta(hours=self.settings.cache_expiry)
            
            for file_path in self.cache_dir.rglob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        expired_files.append((file_path, file_path.stat().st_size))
            
            return expired_files
            
        except Exception as e:
            logger.error(f"Failed to find expired cache files: {e}")
            return []
    
    def _get_oldest_cache_files(self, target_size: int) -> List[Tuple[Path, int]]:
        """가장 오래된 캐시 파일들을 목표 크기만큼 반환"""
        try:
            files_with_time = []
            
            for file_path in self.cache_dir.rglob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    files_with_time.append((file_path, stat.st_size, stat.st_mtime))
            
            # 시간순 정렬 (오래된 것부터)
            files_with_time.sort(key=lambda x: x[2])
            
            # 목표 크기만큼 선택
            selected_files = []
            accumulated_size = 0
            
            for file_path, size, _ in files_with_time:
                selected_files.append((file_path, size))
                accumulated_size += size
                if accumulated_size >= target_size:
                    break
            
            return selected_files
            
        except Exception as e:
            logger.error(f"Failed to get oldest cache files: {e}")
            return []
    
    def _update_cache_index(self, file_path: Path, metadata: Dict[str, Any]) -> None:
        """캐시 인덱스 업데이트"""
        try:
            if self.cache_index_file.exists():
                with open(self.cache_index_file, 'r', encoding='utf-8') as f:
                    cache_index = json.load(f)
            else:
                cache_index = {"files": {}, "last_updated": None}
            
            cache_index["files"][str(file_path)] = {
                "added_at": datetime.now().isoformat(),
                "metadata": metadata
            }
            cache_index["last_updated"] = datetime.now().isoformat()
            
            with open(self.cache_index_file, 'w', encoding='utf-8') as f:
                json.dump(cache_index, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to update cache index: {e}")
    
    def _rebuild_cache_index(self) -> None:
        """캐시 인덱스 재구축"""
        try:
            cache_index = {"files": {}, "last_updated": datetime.now().isoformat()}
            
            # 실제 파일들을 스캔하여 인덱스 재구축
            for file_path in self.cache_dir.rglob("*"):
                if file_path.is_file():
                    cache_index["files"][str(file_path)] = {
                        "added_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                        "size": file_path.stat().st_size
                    }
            
            with open(self.cache_index_file, 'w', encoding='utf-8') as f:
                json.dump(cache_index, f, indent=2, ensure_ascii=False)
                
            logger.info("Cache index rebuilt")
            
        except Exception as e:
            logger.error(f"Failed to rebuild cache index: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        스토리지 통계 정보 반환
        
        Returns:
            Dict: 스토리지 통계
        """
        try:
            stats = {
                "output_directory": str(self.output_dir),
                "cache_directory": str(self.cache_dir),
                "temp_directory": str(self.temp_dir),
                "output_stats": self._get_directory_stats(self.output_dir),
                "cache_stats": self._get_directory_stats(self.cache_dir),
                "temp_stats": self._get_directory_stats(self.temp_dir),
                "total_images": len(self.get_image_history())
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}
    
    def _get_directory_stats(self, directory: Path) -> Dict[str, Any]:
        """디렉토리 통계 정보"""
        try:
            if not directory.exists():
                return {"files": 0, "size_mb": 0.0, "exists": False}
            
            total_files = 0
            total_size = 0
            
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_files += 1
                    total_size += file_path.stat().st_size
            
            return {
                "files": total_files,
                "size_mb": round(total_size / 1024 / 1024, 2),
                "exists": True
            }
            
        except Exception as e:
            logger.error(f"Failed to get directory stats for {directory}: {e}")
            return {"files": 0, "size_mb": 0.0, "exists": False, "error": str(e)}
    
    def create_temp_file(self, suffix: str = ".tmp", prefix: str = "nanobanana_") -> Path:
        """
        임시 파일 생성
        
        Args:
            suffix: 파일 확장자
            prefix: 파일명 접두사
            
        Returns:
            Path: 임시 파일 경로
        """
        try:
            temp_file = tempfile.NamedTemporaryFile(
                suffix=suffix,
                prefix=prefix,
                dir=self.temp_dir,
                delete=False
            )
            temp_path = Path(temp_file.name)
            temp_file.close()
            
            logger.debug(f"Created temp file: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to create temp file: {e}")
            raise FileManagerError(f"Failed to create temp file: {str(e)}")


# 전역 파일 매니저 인스턴스 (싱글톤)
_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """
    파일 매니저 인스턴스 반환 (싱글톤 패턴)
    
    Returns:
        FileManager: 파일 매니저 인스턴스
    """
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager