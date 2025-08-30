"""
나노바나나 MCP 서버 Claude 통합 예제

이 예제는 나노바나나 MCP 서버를 Claude Code와 통합하는 방법을 보여줍니다.
Claude Desktop 설정, MCP 서버 실행, 그리고 Claude Code에서의 사용법을 다룹니다.

주요 내용:
    1. Claude Desktop 설정 방법
    2. MCP 서버 실행 및 관리
    3. Claude Code에서의 사용 패턴
    4. 문제 해결 및 디버깅

사용 방법:
    python examples/claude_integration.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import get_settings
from src.server import get_server_info, list_available_tools


def main():
    """메인 실행 함수"""
    print("🍌 나노바나나 MCP 서버 Claude 통합 가이드")
    print("=" * 60)
    
    # 1. Claude Desktop 설정 가이드
    print_claude_desktop_config()
    
    # 2. 서버 정보 확인
    print_server_info()
    
    # 3. MCP 도구 목록
    print_available_tools()
    
    # 4. 사용 패턴 예제
    print_usage_patterns()
    
    # 5. 문제 해결 가이드
    print_troubleshooting_guide()
    
    # 6. 설정 파일 생성 옵션
    offer_config_generation()


def print_claude_desktop_config():
    """Claude Desktop 설정 방법 안내"""
    print("\n1️⃣ Claude Desktop 설정")
    print("-" * 30)
    
    # 현재 프로젝트 경로
    project_path = Path(__file__).parent.parent.absolute()
    
    # 플랫폼별 설정 파일 경로
    config_paths = {
        "Windows": "~\\AppData\\Roaming\\Claude\\claude_desktop_config.json",
        "macOS": "~/Library/Application Support/Claude/claude_desktop_config.json",
        "Linux": "~/.config/Claude/claude_desktop_config.json"
    }
    
    print("📁 Claude Desktop 설정 파일 위치:")
    for platform, path in config_paths.items():
        print(f"   {platform}: {path}")
    
    print(f"\n🔧 설정할 내용 (claude_desktop_config.json):")
    
    # 기본 MCP 설정
    config = {
        "mcpServers": {
            "nanobanana": {
                "command": "python",
                "args": ["-m", "src.server"],
                "cwd": str(project_path),
                "env": {
                    "GOOGLE_AI_API_KEY": "your_google_ai_api_key_here"
                }
            }
        }
    }
    
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    # 고급 설정 옵션
    print(f"\n⚙️ 고급 설정 옵션:")
    advanced_config = {
        "mcpServers": {
            "nanobanana": {
                "command": "python",
                "args": ["-m", "src.server", "--dev", "--debug"],
                "cwd": str(project_path),
                "env": {
                    "GOOGLE_AI_API_KEY": "your_google_ai_api_key_here",
                    "NANOBANANA_OUTPUT_DIR": "./outputs",
                    "NANOBANANA_MAX_IMAGE_SIZE": "10",
                    "NANOBANANA_OPTIMIZE_PROMPTS": "true",
                    "NANOBANANA_LOG_LEVEL": "DEBUG"
                }
            }
        }
    }
    
    print(json.dumps(advanced_config, indent=2, ensure_ascii=False))


def print_server_info():
    """서버 정보 출력"""
    print("\n2️⃣ 서버 정보")
    print("-" * 30)
    
    try:
        info = get_server_info()
        print(f"📌 서버명: {info['name']}")
        print(f"🏷️ 버전: {info['version']}")
        print(f"📡 MCP 버전: {info['mcp_version']}")
        print(f"🌐 호스트: {info['settings']['host']}:{info['settings']['port']}")
        print(f"🔧 개발 모드: {info['settings']['dev_mode']}")
        print(f"🐛 디버그 모드: {info['settings']['debug']}")
        
    except Exception as e:
        print(f"❌ 서버 정보 조회 실패: {e}")


def print_available_tools():
    """사용 가능한 도구 목록 출력"""
    print("\n3️⃣ 사용 가능한 MCP 도구")
    print("-" * 30)
    
    try:
        tools = list_available_tools()
        
        for tool in tools:
            print(f"\n🔧 {tool['name']}")
            print(f"   📝 설명: {tool['description']}")
            
            # 파라미터 정보
            if 'parameters' in tool:
                print("   📋 파라미터:")
                for param_name, param_info in tool['parameters'].items():
                    required = " (필수)" if param_info.get('required', False) else " (선택)"
                    print(f"      • {param_name}{required}: {param_info.get('description', '')}")
                    
                    # 기본값 표시
                    if 'default' in param_info:
                        print(f"        기본값: {param_info['default']}")
            
    except Exception as e:
        print(f"❌ 도구 목록 조회 실패: {e}")


def print_usage_patterns():
    """Claude Code에서의 사용 패턴 예제"""
    print("\n4️⃣ Claude Code에서의 사용 패턴")
    print("-" * 30)
    
    patterns = [
        {
            "title": "기본 이미지 생성",
            "description": "텍스트 프롬프트로 이미지 생성",
            "claude_command": "나노바나나를 사용해서 '고양이가 모자를 쓰고 있는 사진'을 생성해줘",
            "mcp_call": "nanobanana_generate(prompt='A cat wearing a hat, photorealistic style')"
        },
        {
            "title": "이미지 편집",
            "description": "기존 이미지를 자연어로 편집",
            "claude_command": "이 이미지의 배경을 바다로 바꿔줘",
            "mcp_call": "nanobanana_edit(image_path='./image.png', edit_prompt='Change background to ocean')"
        },
        {
            "title": "다중 이미지 블렌딩",
            "description": "여러 이미지를 합성",
            "claude_command": "이 두 이미지를 합성해서 환상적인 풍경을 만들어줘",
            "mcp_call": "nanobanana_blend(image_paths=['./img1.png', './img2.png'], blend_prompt='Create fantasy landscape')"
        },
        {
            "title": "서버 상태 확인",
            "description": "MCP 서버 및 API 상태 모니터링",
            "claude_command": "나노바나나 서버 상태를 확인해줘",
            "mcp_call": "nanobanana_status(detailed=True)"
        }
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"\n📝 패턴 {i}: {pattern['title']}")
        print(f"   설명: {pattern['description']}")
        print(f"   Claude 명령: \"{pattern['claude_command']}\"")
        print(f"   MCP 호출: {pattern['mcp_call']}")


def print_troubleshooting_guide():
    """문제 해결 가이드"""
    print("\n5️⃣ 문제 해결 가이드")
    print("-" * 30)
    
    issues = [
        {
            "problem": "MCP 서버가 Claude Code에 나타나지 않음",
            "solutions": [
                "Claude Desktop을 완전히 종료 후 재시작",
                "claude_desktop_config.json 파일 경로 및 내용 확인",
                "프로젝트 경로(cwd) 올바른지 확인",
                "Python 경로가 올바른지 확인"
            ]
        },
        {
            "problem": "API 키 관련 오류",
            "solutions": [
                "GOOGLE_AI_API_KEY 환경 변수 설정 확인",
                "API 키 유효성 확인 (Google AI Studio에서)",
                ".env 파일 위치 및 내용 확인",
                "API 할당량 및 사용량 확인"
            ]
        },
        {
            "problem": "이미지 생성 실패",
            "solutions": [
                "프롬프트가 Google 안전 가이드라인 준수하는지 확인",
                "영어 프롬프트로 재시도",
                "이미지 크기 제한 확인",
                "네트워크 연결 상태 확인"
            ]
        },
        {
            "problem": "파일 저장 오류",
            "solutions": [
                "출력 디렉토리 권한 확인",
                "디스크 공간 충분한지 확인",
                "파일명 특수문자 포함 여부 확인",
                "동시 생성 요청 수 제한 확인"
            ]
        }
    ]
    
    for issue in issues:
        print(f"\n❓ 문제: {issue['problem']}")
        print("   해결방안:")
        for solution in issue['solutions']:
            print(f"   • {solution}")


def print_debug_commands():
    """디버깅 명령어 가이드"""
    print("\n🔍 디버깅 명령어")
    print("-" * 20)
    
    commands = [
        ("서버 상태 확인", "python -m src.server --check-health"),
        ("디버그 모드 실행", "python -m src.server --dev --debug"),
        ("통계 초기화", "python -m src.server --reset-stats"),
        ("로그 파일 확인", "tail -f logs/nanobanana_mcp.log"),
        ("수동 테스트", "python examples/basic_usage.py")
    ]
    
    for desc, command in commands:
        print(f"   {desc}:")
        print(f"   $ {command}")
        print()


def offer_config_generation():
    """설정 파일 생성 제안"""
    print("\n6️⃣ 설정 파일 생성")
    print("-" * 30)
    
    try:
        response = input("\nClaude Desktop 설정 파일을 생성하시겠습니까? (y/n): ").lower().strip()
        
        if response == 'y':
            generate_claude_config()
        else:
            print("설정 파일 생성을 건너뜁니다.")
            
    except KeyboardInterrupt:
        print("\n설정 생성이 중단되었습니다.")
    except Exception as e:
        print(f"❌ 설정 생성 중 오류: {e}")


def generate_claude_config():
    """Claude Desktop 설정 파일 생성"""
    print("\n🔧 Claude Desktop 설정 파일 생성")
    
    # API 키 입력받기
    api_key = input("Google AI API 키를 입력하세요: ").strip()
    if not api_key:
        print("❌ API 키가 필요합니다.")
        return
    
    # 프로젝트 경로
    project_path = Path(__file__).parent.parent.absolute()
    
    # 설정 생성
    config = {
        "mcpServers": {
            "nanobanana": {
                "command": "python",
                "args": ["-m", "src.server"],
                "cwd": str(project_path),
                "env": {
                    "GOOGLE_AI_API_KEY": api_key
                }
            }
        }
    }
    
    # 설정 파일 저장
    config_file = project_path / "claude_desktop_config.json"
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 설정 파일 생성됨: {config_file}")
        print("\n📋 다음 단계:")
        print("1. 위 파일 내용을 복사하세요")
        print("2. Claude Desktop 설정 파일에 붙여넣으세요")
        
        # 플랫폼별 경로 안내
        import platform
        system = platform.system()
        if system == "Windows":
            config_path = "~\\AppData\\Roaming\\Claude\\claude_desktop_config.json"
        elif system == "Darwin":
            config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
        else:
            config_path = "~/.config/Claude/claude_desktop_config.json"
        
        print(f"3. 설정 파일 위치: {config_path}")
        print("4. Claude Desktop을 재시작하세요")
        
    except Exception as e:
        print(f"❌ 설정 파일 생성 실패: {e}")


def print_best_practices():
    """모범 사례 가이드"""
    print("\n7️⃣ 모범 사례")
    print("-" * 30)
    
    practices = [
        {
            "category": "프롬프트 작성",
            "tips": [
                "구체적이고 서술적인 표현 사용",
                "영어 프롬프트 권장 (더 나은 결과)",
                "원하는 스타일과 품질 명시",
                "부정적 요소는 'no ...' 형태로 제외"
            ]
        },
        {
            "category": "파일 관리",
            "tips": [
                "정기적인 출력 디렉토리 정리",
                "의미 있는 파일명 사용",
                "중요한 이미지는 별도 백업",
                "캐시 크기 모니터링"
            ]
        },
        {
            "category": "성능 최적화",
            "tips": [
                "배치 처리로 여러 이미지 동시 생성",
                "캐시 기능 활용으로 중복 생성 방지",
                "적절한 이미지 크기 설정",
                "동시 요청 수 제한 준수"
            ]
        },
        {
            "category": "보안",
            "tips": [
                "API 키를 코드에 직접 포함하지 않기",
                "환경 변수나 .env 파일 사용",
                ".env 파일을 git에 커밋하지 않기",
                "정기적인 API 키 순환"
            ]
        }
    ]
    
    for practice in practices:
        print(f"\n📚 {practice['category']}:")
        for tip in practice['tips']:
            print(f"   • {tip}")


if __name__ == "__main__":
    try:
        main()
        print_debug_commands()
        print_best_practices()
        
        print("\n" + "=" * 60)
        print("🎉 Claude 통합 가이드 완료!")
        print("이제 Claude Code에서 나노바나나 MCP 서버를 사용할 수 있습니다.")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n👋 가이드가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        sys.exit(1)