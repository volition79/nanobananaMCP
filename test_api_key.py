#!/usr/bin/env python3
"""
Google Gemini API 키 유효성 직접 테스트 스크립트
"""

import os
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 파이썬 패스에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# API 키 설정
API_KEY = "AIzaSyDxBJagyaxv7_V_cDly1385Yq101JFNZTY"
os.environ["GOOGLE_AI_API_KEY"] = API_KEY

async def test_api_key():
    """API 키 유효성 테스트"""
    try:
        print("🔧 Google Gemini API 키 테스트 시작...")
        print(f"🔑 API 키: {API_KEY[:20]}...")
        
        # google-genai 라이브러리로 직접 테스트
        import google.genai as genai
        
        # 클라이언트 초기화
        client = genai.Client(api_key=API_KEY)
        print("✅ 클라이언트 초기화 성공")
        
        # 모델 목록 가져오기로 API 키 검증
        try:
            models = client.models.list()
            print("✅ API 키 유효 - 모델 목록 조회 성공")
            
            # Gemini 이미지 생성 모델 확인
            image_models = [m for m in models if 'image' in m.name.lower()]
            if image_models:
                print(f"✅ 이미지 생성 모델 발견: {len(image_models)}개")
                for model in image_models[:3]:  # 최대 3개만 표시
                    print(f"   - {model.name}")
            else:
                print("⚠️  이미지 생성 모델을 찾을 수 없습니다")
                
            return True
            
        except Exception as e:
            print(f"❌ API 키 검증 실패: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ 라이브러리 가져오기 실패: {e}")
        print("📦 google-genai 패키지를 설치하세요: pip install google-genai")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

async def test_with_genai_simple():
    """더 간단한 API 테스트"""
    try:
        print("\n🔧 간단한 API 테스트 시도...")
        
        import google.genai as genai
        
        # 환경변수로 클라이언트 초기화
        client = genai.Client()
        
        # 간단한 헬스체크
        response = client.models.get(name="gemini-2.5-flash-image-preview")
        print(f"✅ 모델 정보 조회 성공: {response.name}")
        return True
        
    except Exception as e:
        print(f"❌ 간단한 API 테스트 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("=" * 50)
    print("🧪 나노바나나 MCP 서버 API 키 테스트")
    print("=" * 50)
    
    # 비동기 테스트 실행
    result1 = asyncio.run(test_api_key())
    result2 = asyncio.run(test_with_genai_simple())
    
    print("\n" + "=" * 50)
    if result1 or result2:
        print("✅ API 키 테스트 통과 - 키가 유효합니다!")
        print("🔍 서버 코드 문제를 확인해야 합니다.")
    else:
        print("❌ API 키 테스트 실패 - 키에 문제가 있습니다.")
        print("🔑 Google AI Studio에서 새 키를 생성하거나 권한을 확인하세요.")
    print("=" * 50)

if __name__ == "__main__":
    main()