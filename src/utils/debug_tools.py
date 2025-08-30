"""
디버깅 및 검증 도구

이미지 파일 문제 진단, Base64 검증, 파일 무결성 확인 등의 기능을 제공합니다.
"""

import base64
import hashlib
import logging
import mimetypes
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from PIL import Image
import magic  # python-magic

from ..config import get_settings

logger = logging.getLogger(__name__)


class ImageDiagnostics:
    """이미지 파일 진단 도구"""
    
    def __init__(self):
        self.settings = get_settings()
        self.signatures = {
            'png': b'\x89PNG\r\n\x1a\n',
            'jpeg': b'\xff\xd8\xff',
            'webp': b'RIFF',
            'gif': b'GIF8',
            'bmp': b'BM'
        }
    
    def diagnose_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        파일 종합 진단
        
        Args:
            file_path: 진단할 파일 경로
            
        Returns:
            Dict: 진단 결과
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    'status': 'error',
                    'error': 'File not found',
                    'file_path': str(file_path)
                }
            
            # 기본 파일 정보
            stat = file_path.stat()
            file_info = {
                'file_path': str(file_path),
                'file_size': stat.st_size,
                'file_size_mb': round(stat.st_size / 1024 / 1024, 3),
                'extension': file_path.suffix.lower(),
                'modified_time': stat.st_mtime
            }
            
            # 파일 내용 읽기
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # 진단 실행
            diagnostics = {
                **file_info,
                'signature_analysis': self._analyze_file_signature(file_data),
                'base64_analysis': self._analyze_base64_content(file_data),
                'pillow_analysis': self._analyze_with_pillow(file_data),
                'mime_analysis': self._analyze_mime_type(file_path, file_data),
                'metadata_analysis': self._analyze_metadata(file_data),
                'recommendations': []
            }
            
            # 권장사항 생성
            diagnostics['recommendations'] = self._generate_recommendations(diagnostics)
            
            return diagnostics
            
        except Exception as e:
            logger.error(f"File diagnosis failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'file_path': str(file_path) if 'file_path' in locals() else None
            }
    
    def _analyze_file_signature(self, data: bytes) -> Dict[str, Any]:
        """파일 시그니처 분석"""
        try:
            if len(data) < 8:
                return {
                    'status': 'insufficient_data',
                    'header_bytes': len(data)
                }
            
            header = data[:16]  # 16바이트 헤더
            detected_format = None
            
            for fmt, signature in self.signatures.items():
                if data.startswith(signature):
                    detected_format = fmt
                    break
            
            # WebP 추가 검증
            if detected_format == 'webp' and len(data) > 12:
                if data[8:12] != b'WEBP':
                    detected_format = None
            
            return {
                'detected_format': detected_format,
                'header_hex': header.hex(),
                'header_ascii': header.decode('ascii', errors='replace'),
                'is_valid_signature': detected_format is not None
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_base64_content(self, data: bytes) -> Dict[str, Any]:
        """Base64 내용 분석"""
        try:
            # 텍스트로 디코딩 시도
            try:
                text_content = data.decode('utf-8')
                is_text = True
            except:
                text_content = data.decode('utf-8', errors='replace')
                is_text = False
            
            # Base64 패턴 검사
            import re
            base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
            url_safe_pattern = re.compile(r'^[A-Za-z0-9_-]*={0,2}$')
            
            text_content_clean = text_content.strip()
            
            analysis = {
                'is_likely_text': is_text,
                'content_length': len(text_content_clean),
                'is_base64_pattern': base64_pattern.match(text_content_clean) is not None,
                'is_url_safe_base64': url_safe_pattern.match(text_content_clean) is not None,
                'base64_decode_test': None,
                'decoded_signature': None
            }
            
            # Base64 디코딩 테스트
            if analysis['is_base64_pattern'] or analysis['is_url_safe_base64']:
                try:
                    # URL-safe 변환
                    if '-' in text_content_clean or '_' in text_content_clean:
                        text_content_clean = text_content_clean.replace('-', '+').replace('_', '/')
                    
                    # 패딩 추가
                    padding_needed = len(text_content_clean) % 4
                    if padding_needed:
                        text_content_clean += '=' * (4 - padding_needed)
                    
                    decoded = base64.b64decode(text_content_clean)
                    analysis['base64_decode_test'] = 'success'
                    analysis['decoded_size'] = len(decoded)
                    
                    # 디코딩된 데이터의 시그니처 확인
                    if len(decoded) >= 8:
                        header = decoded[:8]
                        for fmt, signature in self.signatures.items():
                            if header.startswith(signature):
                                analysis['decoded_signature'] = fmt
                                break
                    
                except Exception as decode_error:
                    analysis['base64_decode_test'] = f'failed: {decode_error}'
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_with_pillow(self, data: bytes) -> Dict[str, Any]:
        """Pillow를 사용한 이미지 분석"""
        try:
            analysis = {
                'pillow_can_open': False,
                'format': None,
                'mode': None,
                'size': None,
                'has_transparency': None,
                'verification_status': None
            }
            
            try:
                with Image.open(BytesIO(data)) as img:
                    analysis['pillow_can_open'] = True
                    analysis['format'] = img.format
                    analysis['mode'] = img.mode
                    analysis['size'] = img.size
                    analysis['has_transparency'] = img.mode in ['RGBA', 'LA'] or 'transparency' in img.info
                    
                    # 검증 시도
                    try:
                        img_copy = img.copy()
                        img_copy.verify()
                        analysis['verification_status'] = 'passed'
                    except Exception as verify_error:
                        analysis['verification_status'] = f'failed: {verify_error}'
                        
            except Exception as pillow_error:
                analysis['pillow_error'] = str(pillow_error)
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_mime_type(self, file_path: Path, data: bytes) -> Dict[str, Any]:
        """MIME 타입 분석"""
        try:
            analysis = {}
            
            # 확장자 기반 MIME 타입
            analysis['extension_mime'] = mimetypes.guess_type(str(file_path))[0]
            
            # python-magic을 사용한 내용 기반 MIME 타입 (사용 가능한 경우)
            try:
                analysis['content_mime'] = magic.from_buffer(data, mime=True)
            except:
                analysis['content_mime'] = 'unavailable (python-magic not installed)'
            
            # 간단한 시그니처 기반 추측
            if len(data) >= 8:
                header = data[:8]
                if header.startswith(b'\x89PNG'):
                    analysis['signature_mime'] = 'image/png'
                elif header.startswith(b'\xff\xd8\xff'):
                    analysis['signature_mime'] = 'image/jpeg'
                elif header.startswith(b'RIFF') and len(data) > 12 and data[8:12] == b'WEBP':
                    analysis['signature_mime'] = 'image/webp'
                else:
                    analysis['signature_mime'] = 'unknown'
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_metadata(self, data: bytes) -> Dict[str, Any]:
        """메타데이터 분석"""
        try:
            analysis = {
                'has_exif': False,
                'metadata_size_estimate': 0,
                'problematic_chunks': []
            }
            
            try:
                with Image.open(BytesIO(data)) as img:
                    # EXIF 데이터 확인
                    if hasattr(img, '_getexif') and img._getexif():
                        analysis['has_exif'] = True
                    
                    # PIL info 확인
                    if img.info:
                        analysis['pil_info_keys'] = list(img.info.keys())
                        analysis['metadata_size_estimate'] = sum(
                            len(str(k)) + len(str(v)) 
                            for k, v in img.info.items()
                        )
                    
                    # PNG 특정 청크 확인 (문제가 될 수 있는 청크)
                    if img.format == 'PNG':
                        problematic_chunks = ['zTXt', 'iTXt', 'tEXt']  # Google이 사용하는 비표준 청크들
                        for chunk in problematic_chunks:
                            if chunk in img.info:
                                analysis['problematic_chunks'].append(chunk)
                                
            except Exception as img_error:
                analysis['image_analysis_error'] = str(img_error)
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_recommendations(self, diagnostics: Dict[str, Any]) -> List[str]:
        """진단 결과를 바탕으로 권장사항 생성"""
        recommendations = []
        
        try:
            # Base64 문제 감지
            base64_analysis = diagnostics.get('base64_analysis', {})
            if base64_analysis.get('is_likely_text') and base64_analysis.get('is_base64_pattern'):
                recommendations.append(
                    "파일이 Base64 텍스트로 저장되어 있습니다. 바이너리로 디코딩하여 다시 저장하세요."
                )
            
            # 시그니처 불일치 감지
            signature_analysis = diagnostics.get('signature_analysis', {})
            extension = diagnostics.get('extension', '').lower()
            detected_format = signature_analysis.get('detected_format')
            
            if detected_format and extension:
                extension_format = extension.replace('.', '')
                if extension_format == 'jpg':
                    extension_format = 'jpeg'
                
                if detected_format != extension_format:
                    recommendations.append(
                        f"파일 시그니처({detected_format})와 확장자({extension})가 불일치합니다. "
                        f"파일을 .{detected_format} 확장자로 변경하거나 올바른 형식으로 변환하세요."
                    )
            
            # Pillow 검증 실패
            pillow_analysis = diagnostics.get('pillow_analysis', {})
            if not pillow_analysis.get('pillow_can_open'):
                recommendations.append(
                    "Pillow가 파일을 열 수 없습니다. 파일이 손상되었거나 지원하지 않는 형식일 수 있습니다."
                )
            elif pillow_analysis.get('verification_status', '').startswith('failed'):
                recommendations.append(
                    "이미지 검증에 실패했습니다. Pillow로 재처리하여 메타데이터를 정리하세요."
                )
            
            # 메타데이터 문제
            metadata_analysis = diagnostics.get('metadata_analysis', {})
            if metadata_analysis.get('problematic_chunks'):
                recommendations.append(
                    f"문제가 될 수 있는 PNG 청크가 발견되었습니다: {metadata_analysis['problematic_chunks']}. "
                    "메타데이터를 제거하고 다시 저장하세요."
                )
            
            # 기본 권장사항
            if not recommendations:
                if pillow_analysis.get('pillow_can_open'):
                    recommendations.append("파일이 정상적으로 보입니다.")
                else:
                    recommendations.append("추가 조사가 필요합니다.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return ["진단 중 오류가 발생했습니다."]


def diagnose_image_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    이미지 파일 진단 (편의 함수)
    
    Args:
        file_path: 진단할 파일 경로
        
    Returns:
        Dict: 진단 결과
    """
    diagnostics = ImageDiagnostics()
    return diagnostics.diagnose_file(file_path)


def validate_base64_string(base64_string: str) -> Dict[str, Any]:
    """
    Base64 문자열 검증
    
    Args:
        base64_string: 검증할 Base64 문자열
        
    Returns:
        Dict: 검증 결과
    """
    try:
        import re
        
        result = {
            'is_valid_base64': False,
            'is_url_safe': False,
            'decode_success': False,
            'decoded_size': 0,
            'detected_image_format': None,
            'error': None
        }
        
        clean_string = base64_string.strip()
        
        # 패턴 검사
        base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
        url_safe_pattern = re.compile(r'^[A-Za-z0-9_-]*={0,2}$')
        
        result['is_valid_base64'] = base64_pattern.match(clean_string) is not None
        result['is_url_safe'] = url_safe_pattern.match(clean_string) is not None
        
        if result['is_valid_base64'] or result['is_url_safe']:
            try:
                # URL-safe 변환
                if result['is_url_safe']:
                    clean_string = clean_string.replace('-', '+').replace('_', '/')
                
                # 패딩 추가
                padding_needed = len(clean_string) % 4
                if padding_needed:
                    clean_string += '=' * (4 - padding_needed)
                
                decoded = base64.b64decode(clean_string)
                result['decode_success'] = True
                result['decoded_size'] = len(decoded)
                
                # 이미지 시그니처 확인
                signatures = {
                    'png': b'\x89PNG\r\n\x1a\n',
                    'jpeg': b'\xff\xd8\xff',
                    'webp': b'RIFF',
                    'gif': b'GIF8',
                    'bmp': b'BM'
                }
                
                for fmt, signature in signatures.items():
                    if decoded.startswith(signature):
                        result['detected_image_format'] = fmt
                        break
                
            except Exception as decode_error:
                result['error'] = str(decode_error)
        
        return result
        
    except Exception as e:
        return {'error': f"Validation failed: {str(e)}"}


def create_test_image_report(output_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    출력 디렉토리의 이미지들에 대한 진단 보고서 생성
    
    Args:
        output_dir: 검사할 출력 디렉토리
        
    Returns:
        Dict: 진단 보고서
    """
    try:
        output_dir = Path(output_dir)
        
        if not output_dir.exists():
            return {
                'status': 'error',
                'error': 'Output directory not found'
            }
        
        # 이미지 파일 찾기
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(output_dir.rglob(f'*{ext}'))
        
        diagnostics = ImageDiagnostics()
        results = {
            'total_files': len(image_files),
            'directory': str(output_dir),
            'files': [],
            'summary': {
                'healthy': 0,
                'problematic': 0,
                'base64_text_files': 0,
                'signature_mismatches': 0,
                'pillow_failures': 0
            }
        }
        
        for file_path in image_files:
            diagnosis = diagnostics.diagnose_file(file_path)
            results['files'].append(diagnosis)
            
            # 요약 통계 업데이트
            if len(diagnosis.get('recommendations', [])) <= 1 and 'error' not in diagnosis:
                results['summary']['healthy'] += 1
            else:
                results['summary']['problematic'] += 1
            
            # 특정 문제 카운트
            base64_analysis = diagnosis.get('base64_analysis', {})
            if (base64_analysis.get('is_likely_text') and 
                base64_analysis.get('is_base64_pattern')):
                results['summary']['base64_text_files'] += 1
            
            signature_analysis = diagnosis.get('signature_analysis', {})
            pillow_analysis = diagnosis.get('pillow_analysis', {})
            
            if not pillow_analysis.get('pillow_can_open', True):
                results['summary']['pillow_failures'] += 1
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to create test image report: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }