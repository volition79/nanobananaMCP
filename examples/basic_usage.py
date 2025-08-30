"""
나노바나나 MCP 서버 기본 사용 예제

이 예제는 나노바나나 MCP 서버의 기본적인 사용 방법을 보여줍니다.
직접 도구 함수들을 호출하여 이미지 생성, 편집, 블렌딩, 상태 확인 등을 수행합니다.

실행 방법:
    python examples/basic_usage.py

주의사항:
    - GOOGLE_AI_API_KEY 환경 변수가 설정되어야 합니다.
    - 생성된 이미지는 ./outputs 디렉토리에 저장됩니다.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tools import generate, edit, blend, status
from src.config import get_settings


async def main():
    """메인 실행 함수"""
    print("🍌 나노바나나 MCP 서버 기본 사용 예제")
    print("=" * 50)
    
    # 환경 확인
    if not await check_environment():
        return
    
    # 예제 실행
    await run_examples()


async def check_environment() -> bool:
    """환경 설정 및 API 연결 확인"""
    print("\n1️⃣ 환경 설정 확인")
    
    # API 키 확인
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_AI_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일을 만들거나 환경 변수를 설정해주세요.")
        return False
    
    print(f"✅ API 키 설정됨: {api_key[:10]}...")
    
    # 설정 확인
    settings = get_settings()
    print(f"✅ 출력 디렉토리: {settings.output_dir}")
    print(f"✅ 임시 디렉토리: {settings.temp_dir}")
    
    # 디렉토리 생성
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    
    # API 연결 상태 확인
    print("\n🔍 API 연결 상태 확인")
    try:
        result = await status.nanobanana_status()
        if result["success"]:
            print("✅ Gemini API 연결 성공")
            print(f"   - 상태: {result.get('api_status', {}).get('status', 'unknown')}")
            print(f"   - 모델: {result.get('api_status', {}).get('model', 'unknown')}")
        else:
            print("❌ API 연결 실패")
            print(f"   오류: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ 상태 확인 중 오류: {e}")
        return False
    
    return True


async def run_examples():
    """모든 예제 실행"""
    print("\n" + "=" * 50)
    print("📝 예제 실행 시작")
    
    # 1. 기본 이미지 생성
    await example_basic_generation()
    
    # 2. 고급 이미지 생성
    await example_advanced_generation()
    
    # 3. 이미지 편집 (생성된 이미지가 있는 경우)
    await example_image_editing()
    
    # 4. 이미지 블렌딩 (여러 이미지가 있는 경우)
    await example_image_blending()
    
    # 5. 서버 상태 확인
    await example_status_check()
    
    print("\n🎉 모든 예제 실행 완료!")


async def example_basic_generation():
    """기본 이미지 생성 예제"""
    print("\n2️⃣ 기본 이미지 생성 예제")
    
    try:
        result = await generate.nanobanana_generate(
            prompt="A cute cat wearing a red hat, sitting in a garden",
            aspect_ratio="1:1",
            quality="high"
        )
        
        if result["success"]:
            print("✅ 이미지 생성 성공!")
            for i, image_info in enumerate(result["images"]):
                print(f"   📸 이미지 {i+1}: {image_info['filepath']}")
                print(f"      - 크기: {image_info.get('size', 'unknown')}")
                print(f"      - 형식: {image_info.get('format', 'unknown')}")
        else:
            print("❌ 이미지 생성 실패")
            print(f"   오류: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")


async def example_advanced_generation():
    """고급 이미지 생성 예제"""
    print("\n3️⃣ 고급 이미지 생성 예제 (다중 생성, 스타일 지정)")
    
    try:
        result = await generate.nanobanana_generate(
            prompt="A futuristic cityscape at sunset",
            aspect_ratio="16:9",
            style="digital-art",
            quality="high",
            candidate_count=2,
            additional_keywords=["cyberpunk", "neon lights", "atmospheric"]
        )
        
        if result["success"]:
            print(f"✅ {len(result['images'])}개 이미지 생성 성공!")
            for i, image_info in enumerate(result["images"]):
                print(f"   🌆 이미지 {i+1}: {image_info['filepath']}")
        else:
            print("❌ 고급 이미지 생성 실패")
            print(f"   오류: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")


async def example_image_editing():
    """이미지 편집 예제"""
    print("\n4️⃣ 이미지 편집 예제")
    
    # 먼저 편집할 이미지를 찾음
    settings = get_settings()
    image_files = list(settings.output_dir.glob("*.png"))
    
    if not image_files:
        print("⚠️ 편집할 이미지가 없습니다. 먼저 이미지를 생성해주세요.")
        return
    
    source_image = image_files[0]
    print(f"📷 편집할 이미지: {source_image}")
    
    try:
        result = await edit.nanobanana_edit(
            image_path=str(source_image),
            edit_prompt="Change the background to a beautiful beach scene with palm trees"
        )
        
        if result["success"]:
            print("✅ 이미지 편집 성공!")
            print(f"   🎨 편집된 이미지: {result['edited_image']['filepath']}")
        else:
            print("❌ 이미지 편집 실패")
            print(f"   오류: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")


async def example_image_blending():
    """이미지 블렌딩 예제"""
    print("\n5️⃣ 이미지 블렌딩 예제")
    
    # 블렌딩할 이미지들을 찾음
    settings = get_settings()
    image_files = list(settings.output_dir.glob("*.png"))
    
    if len(image_files) < 2:
        print("⚠️ 블렌딩할 이미지가 부족합니다 (최소 2개 필요). 더 많은 이미지를 생성해주세요.")
        return
    
    # 처음 2개 이미지 선택
    blend_images = [str(img) for img in image_files[:2]]
    print(f"🖼️ 블렌딩할 이미지들: {[Path(img).name for img in blend_images]}")
    
    try:
        result = await blend.nanobanana_blend(
            image_paths=blend_images,
            blend_prompt="Create a dreamy, surreal composition combining both images",
            maintain_consistency=True
        )
        
        if result["success"]:
            print("✅ 이미지 블렌딩 성공!")
            print(f"   🎭 블렌딩된 이미지: {result['blended_image']['filepath']}")
        else:
            print("❌ 이미지 블렌딩 실패")
            print(f"   오류: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")


async def example_status_check():
    """상태 확인 예제"""
    print("\n6️⃣ 서버 상태 확인 예제")
    
    try:
        # 기본 상태 확인
        result = await status.nanobanana_status(detailed=True)
        
        if result["success"]:
            print("✅ 서버 상태 확인 성공!")
            print(f"   🖥️ 서버: {result.get('server_name')} v{result.get('version')}")
            print(f"   ⏱️ 가동시간: {result.get('uptime_seconds', 0):.0f}초")
            
            api_status = result.get('api_status', {})
            print(f"   🔗 API 상태: {api_status.get('status', 'unknown')}")
            
            perf_stats = result.get('performance_stats', {})
            if perf_stats:
                print(f"   📊 생성된 이미지: {perf_stats.get('total_images_generated', 0)}개")
                print(f"   💰 총 비용: ${perf_stats.get('total_cost_usd', 0):.3f}")
        else:
            print("❌ 상태 확인 실패")
            print(f"   오류: {result.get('error', 'Unknown error')}")
        
        # 히스토리 포함 상태 확인
        print("\n📜 히스토리 포함 상태 확인")
        history_result = await status.nanobanana_status(
            detailed=True,
            include_history=True
        )
        
        if history_result["success"]:
            recent_history = history_result.get('recent_history', {})
            print(f"   🎨 최근 생성: {len(recent_history.get('recent_generated', []))}건")
            print(f"   ✏️ 최근 편집: {len(recent_history.get('recent_edited', []))}건")
            print(f"   🎭 최근 블렌딩: {len(recent_history.get('recent_blended', []))}건")
            
    except Exception as e:
        print(f"❌ 예외 발생: {e}")


def print_results_summary():
    """결과 요약 출력"""
    settings = get_settings()
    image_files = list(settings.output_dir.glob("*.png"))
    
    print("\n" + "=" * 50)
    print("📊 결과 요약")
    print(f"   💾 생성된 파일: {len(image_files)}개")
    print(f"   📁 출력 디렉토리: {settings.output_dir}")
    
    if image_files:
        print("\n📋 생성된 파일 목록:")
        for img in image_files:
            size = img.stat().st_size / 1024  # KB
            print(f"   - {img.name} ({size:.1f} KB)")


if __name__ == "__main__":
    try:
        # 환경 변수 로딩 (.env 파일이 있다면)
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # python-dotenv 패키지가 없어도 계속 진행
        
        # 비동기 메인 실행
        asyncio.run(main())
        
        # 결과 요약
        print_results_summary()
        
    except KeyboardInterrupt:
        print("\n👋 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)