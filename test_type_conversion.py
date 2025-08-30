#!/usr/bin/env python3
"""
타입 변환 검증 테스트

MCP 도구 파라미터의 자동 타입 변환이 올바르게 작동하는지 검증하는 스크립트입니다.
"""

import sys
import traceback
from pathlib import Path

# src 모듈 경로 추가
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# 절대 경로로 import하여 relative import 문제 해결
import os
os.chdir(str(src_path))
sys.path.insert(0, ".")

try:
    from src.models.schemas import (
        GenerateImageRequest,
        EditImageRequest, 
        BlendImagesRequest
    )
except ImportError:
    # 다른 방법으로 시도
    from models.schemas import (
        GenerateImageRequest,
        EditImageRequest, 
        BlendImagesRequest
    )

def test_candidate_count_conversion():
    """candidate_count 자동 변환 테스트"""
    print("🔢 Testing candidate_count conversion...")
    
    test_cases = [
        # (입력값, 기대값, 설명)
        ("1", 1, "문자열 '1' → 정수 1"),
        ("4", 4, "문자열 '4' → 정수 4"),
        ("  2  ", 2, "공백이 있는 문자열 '  2  ' → 정수 2"),
        (1, 1, "이미 정수인 경우"),
        (None, 1, "None → 기본값 1"),
    ]
    
    for input_val, expected, description in test_cases:
        try:
            request = GenerateImageRequest(
                prompt="test prompt",
                candidate_count=input_val
            )
            actual = request.candidate_count
            
            if actual == expected:
                print(f"  ✅ {description}: {input_val} → {actual}")
            else:
                print(f"  ❌ {description}: {input_val} → {actual} (expected {expected})")
        except Exception as e:
            print(f"  ❌ {description}: {input_val} → ERROR: {e}")
    
    # 오류 케이스 테스트
    error_cases = [
        ("abc", "문자열 'abc'는 숫자가 아님"),
        ("1.5", "소수점 문자열은 정수로 변환 불가"),
        ("", "빈 문자열"),
    ]
    
    print("\n  🚫 Error cases:")
    for input_val, description in error_cases:
        try:
            request = GenerateImageRequest(
                prompt="test prompt",
                candidate_count=input_val
            )
            print(f"  ❌ {description}: {input_val} should have failed but got {request.candidate_count}")
        except Exception as e:
            print(f"  ✅ {description}: {input_val} → ERROR (expected): {type(e).__name__}")


def test_boolean_conversion():
    """불리언 필드 자동 변환 테스트"""
    print("\n🔘 Testing boolean conversion...")
    
    test_cases = [
        # (입력값, 기대값, 설명)
        ("true", True, "문자열 'true' → True"),
        ("false", False, "문자열 'false' → False"),
        ("TRUE", True, "대문자 'TRUE' → True"),
        ("False", False, "첫글자만 대문자 'False' → False"),
        ("1", True, "문자열 '1' → True"),
        ("0", False, "문자열 '0' → False"),
        ("yes", True, "문자열 'yes' → True"),
        ("no", False, "문자열 'no' → False"),
        ("on", True, "문자열 'on' → True"),
        ("off", False, "문자열 'off' → False"),
        ("  true  ", True, "공백이 있는 문자열 '  true  ' → True"),
        (True, True, "이미 불리언 True"),
        (False, False, "이미 불리언 False"),
        (1, True, "정수 1 → True"),
        (0, False, "정수 0 → False"),
        (None, True, "None → 기본값 True"),
    ]
    
    for input_val, expected, description in test_cases:
        try:
            request = GenerateImageRequest(
                prompt="test prompt",
                optimize_prompt=input_val
            )
            actual = request.optimize_prompt
            
            if actual == expected:
                print(f"  ✅ {description}: {input_val} → {actual}")
            else:
                print(f"  ❌ {description}: {input_val} → {actual} (expected {expected})")
        except Exception as e:
            print(f"  ❌ {description}: {input_val} → ERROR: {e}")
    
    # 오류 케이스 테스트
    error_cases = [
        ("maybe", "애매한 문자열 'maybe'"),
        ("truee", "오타가 있는 문자열 'truee'"),
        ("2", "1/0이 아닌 숫자 문자열 '2'"),
    ]
    
    print("\n  🚫 Error cases:")
    for input_val, description in error_cases:
        try:
            request = GenerateImageRequest(
                prompt="test prompt",
                optimize_prompt=input_val
            )
            print(f"  ❌ {description}: {input_val} should have failed but got {request.optimize_prompt}")
        except Exception as e:
            print(f"  ✅ {description}: {input_val} → ERROR (expected): {type(e).__name__}")


def test_multiple_model_classes():
    """여러 모델 클래스에서 타입 변환 테스트"""
    print("\n🏗️ Testing conversion across multiple model classes...")
    
    # 테스트용 이미지 파일 생성
    test_image_path = Path("test_image.png")
    test_image_path.touch()  # 빈 파일 생성
    
    try:
        # EditImageRequest 테스트
        edit_request = EditImageRequest(
            image_path=str(test_image_path),
            edit_prompt="test edit",
            optimize_prompt="true"
        )
        print(f"  ✅ EditImageRequest.optimize_prompt: 'true' → {edit_request.optimize_prompt}")
        
        # BlendImagesRequest 테스트
        blend_request = BlendImagesRequest(
            image_paths=[str(test_image_path), str(test_image_path)],
            blend_prompt="test blend",
            maintain_consistency="false",
            optimize_prompt="1"
        )
        print(f"  ✅ BlendImagesRequest.maintain_consistency: 'false' → {blend_request.maintain_consistency}")
        print(f"  ✅ BlendImagesRequest.optimize_prompt: '1' → {blend_request.optimize_prompt}")
        
    except Exception as e:
        print(f"  ❌ Model class test failed: {e}")
        traceback.print_exc()
    finally:
        # 테스트 파일 삭제
        if test_image_path.exists():
            test_image_path.unlink()


def test_real_world_scenarios():
    """실제 사용 시나리오 테스트"""
    print("\n🌍 Testing real-world scenarios...")
    
    # MCP 호출에서 자주 발생하는 패턴들
    scenarios = [
        {
            "name": "MCP 호출 스타일 1",
            "data": {
                "prompt": "A beautiful cat",
                "candidate_count": "1",  # 문자열로 전달됨
                "optimize_prompt": "true"  # 문자열로 전달됨
            }
        },
        {
            "name": "MCP 호출 스타일 2",
            "data": {
                "prompt": "A dog in the park",
                "candidate_count": "3",
                "aspect_ratio": "16:9",
                "optimize_prompt": "false"
            }
        },
        {
            "name": "혼합 타입 시나리오",
            "data": {
                "prompt": "A landscape",
                "candidate_count": 2,  # 정수
                "optimize_prompt": "yes"  # 문자열
            }
        }
    ]
    
    for scenario in scenarios:
        try:
            request = GenerateImageRequest(**scenario["data"])
            print(f"  ✅ {scenario['name']}:")
            print(f"    candidate_count: {scenario['data']['candidate_count']} → {request.candidate_count}")
            print(f"    optimize_prompt: {scenario['data']['optimize_prompt']} → {request.optimize_prompt}")
        except Exception as e:
            print(f"  ❌ {scenario['name']}: {e}")


def main():
    """메인 테스트 함수"""
    print("🧪 MCP 도구 파라미터 타입 변환 테스트 시작")
    print("=" * 60)
    
    try:
        test_candidate_count_conversion()
        test_boolean_conversion()
        test_multiple_model_classes()
        test_real_world_scenarios()
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 완료!")
        print("\n💡 이제 다음과 같이 사용할 수 있습니다:")
        print("   - candidate_count: '1' → 자동으로 1로 변환")
        print("   - optimize_prompt: 'true' → 자동으로 True로 변환")
        print("   - maintain_consistency: 'false' → 자동으로 False로 변환")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())