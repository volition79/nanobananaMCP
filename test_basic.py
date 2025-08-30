#!/usr/bin/env python3
"""
나노바나나 MCP 서버 기본 테스트
"""

import os
import asyncio
from dotenv import load_dotenv

# 환경 변수 로딩
load_dotenv()

async def test_basic_functionality():
    """기본 기능 테스트"""
    
    print("🔍 나노바나나 MCP 서버 기본 테스트 시작\n")
    
    # 1. 환경 변수 테스트
    print("1. 환경 설정 테스트")
    api_key = os.getenv('GOOGLE_AI_API_KEY')
    if api_key:
        print(f"   ✅ API 키 로드 성공: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("   ❌ API 키 로드 실패")
        return
    
    # 2. 패키지 import 테스트  
    print("\n2. 패키지 Import 테스트")
    try:
        import google.genai
        print("   ✅ google.genai import 성공")
        
        import fastmcp
        print("   ✅ fastmcp import 성공")
        
        import pydantic
        print("   ✅ pydantic import 성공")
        
        from PIL import Image
        print("   ✅ PIL import 성공")
        
    except ImportError as e:
        print(f"   ❌ Package import 실패: {e}")
        return
    
    # 3. Gemini API 연결 테스트
    print("\n3. Gemini API 연결 테스트")
    try:
        client = google.genai.Client(api_key=api_key)
        
        # 기본 텍스트 생성 테스트
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents='Say hello in one word'
        )
        print("   ✅ Gemini 텍스트 생성 API 연결 성공")
        
        # 이미지 생성 모델 테스트  
        response = client.models.generate_content(
            model='gemini-2.5-flash-image-preview',
            contents='Create a simple red circle image'
        )
        print("   ✅ Gemini 이미지 생성 API 연결 성공")
        
    except Exception as e:
        print(f"   ❌ Gemini API 연결 실패: {e}")
        return
    
    # 4. 출력 디렉토리 생성 테스트
    print("\n4. 디렉토리 구조 테스트")
    try:
        output_dir = "./outputs"
        temp_dir = "./temp" 
        cache_dir = "./cache"
        logs_dir = "./logs"
        
        for dir_path in [output_dir, temp_dir, cache_dir, logs_dir]:
            os.makedirs(dir_path, exist_ok=True)
            print(f"   ✅ {dir_path} 디렉토리 생성/확인 완료")
            
    except Exception as e:
        print(f"   ❌ 디렉토리 생성 실패: {e}")
        return
    
    print("\n🎉 모든 기본 테스트 통과!")
    print("\n📋 테스트 결과 요약:")
    print("   ✅ 환경 설정: 정상")
    print("   ✅ 패키지 Import: 정상") 
    print("   ✅ Gemini API 연결: 정상")
    print("   ✅ 디렉토리 구조: 정상")
    print("\n🚀 나노바나나 MCP 서버가 정상적으로 작동할 준비가 되었습니다!")

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())