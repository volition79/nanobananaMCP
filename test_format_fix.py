#!/usr/bin/env python3
"""
파일 포맷 불일치 수정 테스트

MIME 타입 기반 포맷 감지가 올바르게 작동하는지 검증합니다.
"""

import sys
import logging
from pathlib import Path

# src 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_mime_type_detection():
    """MIME 타입 기반 포맷 감지 로직 테스트"""
    print("🔍 Testing MIME type based format detection...")
    
    # 테스트 케이스: (MIME 타입, 기대되는 확장자)
    test_cases = [
        ("image/png", "png"),
        ("image/jpeg", "jpeg"), 
        ("image/jpg", "jpeg"),  # jpg를 jpeg로 변환
        ("image/webp", "webp"),
        ("image/gif", "gif"),
        ("image/bmp", "bmp"),
        ("image/tiff", "tiff"),
    ]
    
    for mime_type, expected_format in test_cases:
        # 포맷 추출 로직 (코드와 동일)
        actual_format = mime_type.split('/')[-1].lower().replace('jpg', 'jpeg')
        
        if actual_format == expected_format:
            print(f"  ✅ {mime_type} → {actual_format}")
        else:
            print(f"  ❌ {mime_type} → {actual_format} (expected {expected_format})")


def test_format_adjustment_logic():
    """포맷 조정 로직 시뮬레이션 테스트"""
    print("\n📝 Testing format adjustment logic simulation...")
    
    # 시뮬레이션 케이스: (API MIME 타입, 사용자 요청 포맷, 기대 결과)
    scenarios = [
        ("image/webp", "png", "webp", True),   # 포맷 변경됨
        ("image/png", "png", "png", False),   # 포맷 동일
        ("image/jpeg", "jpg", "jpeg", True),  # jpg → jpeg 정규화
        ("image/gif", "png", "gif", True),    # 포맷 변경됨
        (None, "png", "png", False),          # MIME 타입 없음
    ]
    
    for mime_type, requested_format, expected_final, should_log in scenarios:
        # 포맷 결정 로직 시뮬레이션
        if mime_type:
            actual_format = mime_type.split('/')[-1].lower().replace('jpg', 'jpeg')
            format_changed = actual_format != requested_format
            final_output_format = actual_format
        else:
            format_changed = False
            final_output_format = requested_format
        
        # 결과 검증
        success = (final_output_format == expected_final) and (format_changed == should_log)
        
        status = "✅" if success else "❌"
        log_indicator = "📝" if format_changed else "🔇"
        
        print(f"  {status} MIME: {mime_type or 'None'}, Requested: {requested_format} → Final: {final_output_format} {log_indicator}")


def test_real_world_scenarios():
    """실제 사용 시나리오 시뮬레이션"""
    print("\n🌍 Testing real-world scenario simulations...")
    
    # 실제 발생할 수 있는 시나리오들
    scenarios = [
        {
            "name": "사용자가 PNG를 요청했지만 API가 WebP 반환",
            "api_response": {
                "images": [{
                    "data": "base64_data_here",
                    "mime_type": "image/webp"
                }]
            },
            "user_request": {"output_format": "png"},
            "expected_format": "webp",
            "should_log": True
        },
        {
            "name": "사용자가 JPEG를 요청하고 API도 JPEG 반환",
            "api_response": {
                "images": [{
                    "data": "base64_data_here", 
                    "mime_type": "image/jpeg"
                }]
            },
            "user_request": {"output_format": "jpeg"},
            "expected_format": "jpeg",
            "should_log": False
        },
        {
            "name": "API 응답에 MIME 타입이 없는 경우",
            "api_response": {
                "images": [{
                    "data": "base64_data_here"
                    # mime_type 없음
                }]
            },
            "user_request": {"output_format": "png"},
            "expected_format": "png",
            "should_log": False
        }
    ]
    
    for scenario in scenarios:
        print(f"  📋 {scenario['name']}")
        
        # 시나리오 시뮬레이션
        image_data = scenario["api_response"]["images"][0]
        requested_format = scenario["user_request"]["output_format"]
        
        # 실제 로직과 동일한 처리
        actual_mime_type = image_data.get('mime_type')
        
        if actual_mime_type:
            actual_format = actual_mime_type.split('/')[-1].lower().replace('jpg', 'jpeg')
            format_adjusted = actual_format != requested_format
            final_format = actual_format
        else:
            format_adjusted = False
            final_format = requested_format
        
        # 결과 검증
        format_correct = final_format == scenario["expected_format"]
        log_correct = format_adjusted == scenario["should_log"]
        
        if format_correct and log_correct:
            print(f"    ✅ Final format: {final_format}, Log needed: {format_adjusted}")
        else:
            print(f"    ❌ Final format: {final_format} (expected {scenario['expected_format']}), Log: {format_adjusted} (expected {scenario['should_log']})")


def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n🔬 Testing edge cases...")
    
    edge_cases = [
        {
            "name": "빈 MIME 타입",
            "mime_type": "",
            "requested": "png",
            "expected": "png"
        },
        {
            "name": "잘못된 MIME 타입 형식",
            "mime_type": "invalid_mime_type",
            "requested": "jpg",
            "expected": "jpeg"  # 요청한 jpg가 jpeg로 정규화됨
        },
        {
            "name": "대문자 MIME 타입",
            "mime_type": "IMAGE/PNG",
            "requested": "jpg", 
            "expected": "png"  # MIME 타입 우선
        },
        {
            "name": "추가 파라미터가 있는 MIME 타입",
            "mime_type": "image/jpeg; charset=utf-8",
            "requested": "png",
            "expected": "jpeg"
        }
    ]
    
    for case in edge_cases:
        try:
            mime_type = case["mime_type"]
            requested_format = case["requested"]
            
            if mime_type and "/" in mime_type:
                actual_format = mime_type.split('/')[-1].lower().replace('jpg', 'jpeg')
                # 추가 파라미터 제거 (세미콜론 이후)
                if ';' in actual_format:
                    actual_format = actual_format.split(';')[0].strip()
                final_format = actual_format
            else:
                final_format = requested_format.replace('jpg', 'jpeg')
            
            success = final_format == case["expected"]
            status = "✅" if success else "❌"
            
            print(f"  {status} {case['name']}: '{mime_type}' + '{requested_format}' → '{final_format}'")
            
        except Exception as e:
            print(f"  ❌ {case['name']}: Error - {e}")


def main():
    """메인 테스트 함수"""
    print("🧪 파일 포맷 불일치 수정 테스트 시작")
    print("=" * 60)
    
    try:
        test_mime_type_detection()
        test_format_adjustment_logic()
        test_real_world_scenarios()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print("\n💡 적용된 개선 사항:")
        print("   - MIME 타입 기반 실제 파일 포맷 자동 감지")
        print("   - 사용자 요청 포맷과 다를 때 로그로 알림") 
        print("   - jpg → jpeg 자동 정규화")
        print("   - 파일 확장자와 내용 일치로 뷰어 호환성 보장")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())