#!/usr/bin/env python3
"""
나노바나나 이미지 생성 기능 실제 테스트
"""

import os
import base64
import asyncio
from dotenv import load_dotenv
import google.genai

# 환경 변수 로딩
load_dotenv()

async def test_image_generation():
    """실제 이미지 생성 테스트"""
    
    print("🎨 나노바나나 이미지 생성 기능 테스트 시작\n")
    
    api_key = os.getenv('GOOGLE_AI_API_KEY')
    client = google.genai.Client(api_key=api_key)
    
    # 테스트 프롬프트들
    test_prompts = [
        {
            "prompt": "A cute cartoon cat wearing a red hat, simple style, white background",
            "description": "간단한 고양이 이미지"
        },
        {
            "prompt": "A beautiful sunset over mountains, photorealistic style",
            "description": "사실적인 풍경 이미지"
        }
    ]
    
    success_count = 0
    
    for i, test in enumerate(test_prompts, 1):
        print(f"{i}. {test['description']} 생성 테스트")
        print(f"   프롬프트: {test['prompt']}")
        
        try:
            # 이미지 생성 요청
            response = client.models.generate_content(
                model='gemini-2.5-flash-image-preview',
                contents=test['prompt']
            )
            
            # 응답 확인
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            # 이미지 데이터 저장
                            image_data = part.inline_data.data
                            mime_type = part.inline_data.mime_type
                            
                            # base64 디코딩 및 파일 저장
                            if isinstance(image_data, str):
                                image_bytes = base64.b64decode(image_data)
                            else:
                                image_bytes = image_data
                            
                            # 파일 확장자 결정
                            if 'png' in mime_type:
                                ext = 'png'
                            elif 'jpeg' in mime_type:
                                ext = 'jpg'
                            else:
                                ext = 'png'
                            
                            filename = f"test_image_{i}.{ext}"
                            filepath = os.path.join("outputs", filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(image_bytes)
                            
                            print(f"   ✅ 이미지 생성 성공: {filename}")
                            print(f"   📁 저장 위치: {filepath}")
                            print(f"   📊 파일 크기: {len(image_bytes):,} bytes")
                            print(f"   🎯 MIME 타입: {mime_type}")
                            success_count += 1
                            break
                    else:
                        print("   ❌ 이미지 데이터를 찾을 수 없음")
                else:
                    print("   ❌ 응답에서 컨텐츠를 찾을 수 없음")
            else:
                print("   ❌ 응답에서 후보를 찾을 수 없음")
                
        except Exception as e:
            print(f"   ❌ 이미지 생성 실패: {str(e)}")
        
        print()
    
    print(f"📋 테스트 결과: {success_count}/{len(test_prompts)} 성공")
    
    if success_count == len(test_prompts):
        print("🎉 모든 이미지 생성 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패")
    
    return success_count == len(test_prompts)

if __name__ == "__main__":
    asyncio.run(test_image_generation())