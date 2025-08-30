"""
나노바나나 MCP 서버

Google의 Gemini 2.5 Flash Image API를 Claude Code에서 사용할 수 있는 Model Context Protocol (MCP) 서버입니다.
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Any, Dict, List, Optional, Sequence, Union

from fastmcp import FastMCP
from pydantic import BaseModel

from .config import get_settings, setup_logging
from .constants import PROJECT_NAME, PROJECT_VERSION, MCP_VERSION
from .gemini_client import create_gemini_client, get_gemini_client
from .tools import generate, edit, blend, status
from .models.schemas import create_error_response

# 설정 및 로깅 초기화
settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)

# FastMCP 서버 인스턴스 생성
mcp_server = FastMCP(
    name=settings.server_name,
    version=settings.server_version
)


# ================================
# MCP 도구 등록
# ================================

@mcp_server.tool()
async def nanobanana_generate(
    prompt: str,
    aspect_ratio: Optional[str] = None,
    style: Optional[str] = None,
    quality: Optional[str] = "high",
    output_format: Optional[str] = "png",
    candidate_count: Optional[Union[int, str]] = 1,
    additional_keywords: Optional[List[str]] = None,
    optimize_prompt: Optional[Union[bool, str]] = True
) -> Dict[str, Any]:
    """Generate images from text prompts using Gemini 2.5 Flash Image"""
    try:
        return await generate.nanobanana_generate(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            style=style,
            quality=quality,
            output_format=output_format,
            candidate_count=candidate_count,
            additional_keywords=additional_keywords,
            optimize_prompt=optimize_prompt
        )
    except Exception as e:
        logger.error(f"Error in nanobanana_generate: {e}")
        return create_error_response(
            f"Generation failed: {str(e)}",
            "GENERATION_ERROR"
        ).dict()


@mcp_server.tool()
async def nanobanana_edit(
    image_path: str,
    edit_prompt: str,
    mask_path: Optional[str] = None,
    output_format: Optional[str] = "png",
    quality: Optional[str] = "high",
    optimize_prompt: Optional[Union[bool, str]] = True
) -> Dict[str, Any]:
    """Edit existing images with natural language instructions"""
    try:
        return await edit.nanobanana_edit(
            image_path=image_path,
            edit_prompt=edit_prompt,
            mask_path=mask_path,
            output_format=output_format,
            quality=quality,
            optimize_prompt=optimize_prompt
        )
    except Exception as e:
        logger.error(f"Error in nanobanana_edit: {e}")
        return create_error_response(
            f"Edit failed: {str(e)}",
            "EDIT_ERROR"
        ).dict()


@mcp_server.tool()
async def nanobanana_blend(
    image_paths: List[str],
    blend_prompt: str,
    maintain_consistency: Optional[Union[bool, str]] = True,
    output_format: Optional[str] = "png",
    quality: Optional[str] = "high",
    optimize_prompt: Optional[Union[bool, str]] = True
) -> Dict[str, Any]:
    """Blend multiple images into a new composition"""
    try:
        return await blend.nanobanana_blend(
            image_paths=image_paths,
            blend_prompt=blend_prompt,
            maintain_consistency=maintain_consistency,
            output_format=output_format,
            quality=quality,
            optimize_prompt=optimize_prompt
        )
    except Exception as e:
        logger.error(f"Error in nanobanana_blend: {e}")
        return create_error_response(
            f"Blend failed: {str(e)}",
            "BLEND_ERROR"
        ).dict()


@mcp_server.tool()
async def nanobanana_status(
    detailed: Optional[Union[bool, str]] = True,
    include_history: Optional[Union[bool, str]] = False,
    reset_stats: Optional[Union[bool, str]] = False
) -> Dict[str, Any]:
    """Check server status and API connectivity"""
    try:
        return await status.nanobanana_status(
            detailed=detailed,
            include_history=include_history,
            reset_stats=reset_stats
        )
    except Exception as e:
        logger.error(f"Error in nanobanana_status: {e}")
        return create_error_response(
            f"Status check failed: {str(e)}",
            "STATUS_ERROR"
        ).dict()


# ================================
# MCP 리소스 (선택적)
# ================================

class ServerInfoResource(BaseModel):
    """서버 정보 리소스"""
    name: str
    version: str
    mcp_version: str
    description: str
    tools: List[str]


@mcp_server.resource("server://info")
async def get_server_info() -> ServerInfoResource:
    """서버 정보 리소스 제공"""
    return ServerInfoResource(
        name=PROJECT_NAME,
        version=PROJECT_VERSION,
        mcp_version=MCP_VERSION,
        description="Gemini 2.5 Flash Image MCP Server for Claude Code",
        tools=[
            "nanobanana_generate",
            "nanobanana_edit", 
            "nanobanana_blend",
            "nanobanana_status"
        ]
    )


# ================================
# 서버 이벤트 핸들러
# ================================

async def startup():
    """서버 시작 시 초기화"""
    try:
        logger.info("Starting nanobanana-mcp MCP Server...")
        
        # Gemini 클라이언트 초기화
        gemini_client = await create_gemini_client()
        logger.info("Gemini client initialized successfully")
        
        # 출력 디렉토리 확인 및 생성
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory ready: {settings.output_dir}")
        
        logger.info("Server startup completed successfully")
        
    except Exception as e:
        logger.error(f"Server startup error: {e}")
        raise


async def shutdown():
    """서버 종료 시 정리"""
    try:
        logger.info("Shutting down Nanobanana MCP Server...")
        
        # 통계 정보 로그
        try:
            gemini_client = get_gemini_client()
            stats = gemini_client.get_statistics()
            logger.info(f"Session statistics: {stats}")
        except Exception as e:
            logger.warning(f"Could not retrieve session statistics: {e}")
        
        # 최종 정리 작업
        if settings.dev_mode:
            try:
                from .utils.file_manager import get_file_manager
                file_manager = get_file_manager()
                cache_result = file_manager.manage_cache()
                logger.info(f"Cache management: {cache_result}")
            except Exception as e:
                logger.warning(f"Cache management failed: {e}")
        
        logger.info("👋 Nanobanana MCP Server shut down gracefully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# ================================
# 시그널 핸들링 (우아한 종료)
# ================================

def signal_handler(signum: int, frame) -> None:
    """시그널 핸들러 (Ctrl+C 등)"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    
    # 비동기 종료 작업을 위한 이벤트 루프 처리
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(shutdown())
        else:
            asyncio.run(shutdown())
    except Exception as e:
        logger.error(f"Error in signal handler: {e}")
    finally:
        sys.exit(0)


# ================================
# 서버 실행 함수들
# ================================

async def run_server_async():
    """비동기 서버 실행"""
    try:
        # 시그널 핸들러 등록 (Unix 계열에서만)
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except AttributeError:
            # Windows에서는 일부 시그널이 지원되지 않을 수 있음
            logger.warning("Some signals not supported on this platform")
        
        # 서버 시작
        await startup()
        
        # 서버 실행
        if settings.dev_mode:
            logger.info("Server running in stdio mode for MCP")
            await mcp_server.run(transport="stdio")
        else:
            logger.info(f"Server listening on {settings.host}:{settings.port}")
            await mcp_server.run(
                host=settings.host,
                port=settings.port,
                transport="websocket"
            )
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        await shutdown()


def run_server():
    """동기 서버 실행 (메인 엔트리포인트)"""
    try:
        logger.info(f"Starting {PROJECT_NAME} MCP Server...")
        
        # MCP stdio 모드에서는 FastMCP가 이벤트 루프를 직접 관리
        if settings.dev_mode:
            logger.info("Starting MCP server in stdio mode...")
            # 동기적 시작 - FastMCP가 내부적으로 이벤트 루프 생성
            setup_and_run_mcp_sync()
        else:
            # WebSocket 모드에서는 기존 방식 유지
            logger.info("Starting WebSocket mode...")
            import asyncio
            asyncio.run(run_server_async())
            
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal server error: {e}")
        sys.exit(1)


def setup_and_run_mcp_sync():
    """MCP stdio 모드를 위한 동기적 설정 및 실행"""
    try:
        logger.info("Initializing MCP server synchronously...")
        
        # FastMCP가 내부적으로 asyncio.run() 처리하도록 함
        import asyncio
        
        async def init_and_run():
            await startup()
            logger.info("Server running in stdio mode for MCP")
            # 시그널 핸들러 설정
            try:
                signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(shutdown()))
                signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(shutdown()))
            except AttributeError:
                logger.warning("Some signals not supported on this platform")
            
            await mcp_server.run(transport="stdio")
        
        # 이벤트 루프를 새로 생성해서 실행
        asyncio.run(init_and_run())
        
    except Exception as e:
        logger.error(f"MCP setup error: {e}")
        raise


# ================================
# CLI 인터페이스
# ================================

def main():
    """CLI 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description=f"{PROJECT_NAME} - Gemini 2.5 Flash Image MCP Server"
    )
    
    parser.add_argument(
        "--version", 
        action="version", 
        version=f"{PROJECT_NAME} {PROJECT_VERSION}"
    )
    
    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"Host to bind to (default: {settings.host})"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to bind to (default: {settings.port})"
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        default=settings.dev_mode,
        help="Run in development mode"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        default=settings.debug,
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--check-health",
        action="store_true",
        help="Check API health and exit"
    )
    
    parser.add_argument(
        "--reset-stats",
        action="store_true", 
        help="Reset server statistics"
    )
    
    args = parser.parse_args()
    
    # 설정 오버라이드
    if args.host != settings.host:
        settings.host = args.host
    if args.port != settings.port:
        settings.port = args.port
    if args.dev:
        settings.dev_mode = True
    if args.debug:
        settings.debug = True
        # 로깅 레벨 업데이트
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # 특수 명령어 처리
    if args.check_health:
        asyncio.run(check_health_and_exit())
        return
    
    if args.reset_stats:
        asyncio.run(reset_stats_and_exit())
        return
    
    # 서버 시작
    logger.info(f"Configuration: host={settings.host}, port={settings.port}, dev={settings.dev_mode}")
    
    # MCP 모드 감지 (Claude Code에서 -m src.server로 실행될 때)
    if len(sys.argv) == 1 and not sys.stdin.isatty():
        # stdin이 터미널이 아니면 MCP 모드로 간주
        run_mcp_server()
    else:
        run_server()


async def check_health_and_exit():
    """API 상태 확인 후 종료"""
    try:
        print(f"Checking {PROJECT_NAME} health...")
        
        # Gemini 클라이언트 생성 및 테스트
        gemini_client = await create_gemini_client(settings)
        health = await gemini_client.health_check()
        
        print(f"API Status: {health['status']}")
        print(f"Model: {health.get('model', 'unknown')}")
        print(f"Accessible: {health.get('api_accessible', False)}")
        
        if health.get('error'):
            print(f"Error: {health['error']}")
            sys.exit(1)
        else:
            print("✅ Health check passed")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)


async def reset_stats_and_exit():
    """통계 초기화 후 종료"""
    try:
        print("Resetting server statistics...")
        
        gemini_client = await create_gemini_client(settings)
        gemini_client.reset_statistics()
        
        print("✅ Statistics reset successfully")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Statistics reset failed: {e}")
        sys.exit(1)


# ================================
# 개발용 헬퍼 함수들
# ================================

def get_server_info() -> Dict[str, Any]:
    """서버 정보 반환 (동기 함수)"""
    return {
        "name": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "mcp_version": MCP_VERSION,
        "settings": {
            "host": settings.host,
            "port": settings.port,
            "dev_mode": settings.dev_mode,
            "debug": settings.debug
        },
        "tools": [
            "nanobanana_generate",
            "nanobanana_edit",
            "nanobanana_blend", 
            "nanobanana_status"
        ]
    }


def list_available_tools() -> List[Dict[str, Any]]:
    """사용 가능한 도구 목록 반환"""
    return [
        generate.TOOL_METADATA,
        edit.TOOL_METADATA,
        blend.TOOL_METADATA,
        status.TOOL_METADATA
    ]


# ================================
# 엔트리포인트
# ================================

# FastMCP 서버 실행을 위한 단순한 함수
def run_mcp_server():
    """MCP 서버 실행 (Claude Code에서 호출됨)"""
    logger.info("Starting nanobanana-mcp in MCP mode...")
    
    # API 키 검증을 위한 간단한 초기 확인
    try:
        from .config_keyloader import SecureKeyLoader
        
        # 키 로더로 API 키 확인
        key_loader = SecureKeyLoader(mcp_server_name="nanobanana")
        
        if not key_loader.has_key():
            logger.error(
                "Gemini API key not found. Please set it in:\n"
                "1. MCP server configuration (recommended): mcpServers.nanobanana.env.GEMINI_API_KEY\n"
                "2. .env file: GEMINI_API_KEY, GOOGLE_API_KEY, or GOOGLE_AI_API_KEY"
            )
            return
        else:
            debug_info = key_loader.get_debug_info()
            logger.info(f"🔐 API key loaded from: {debug_info['key_info']['source_name']}")
            logger.info(f"🔐 Key name: {debug_info['key_info']['key_name']}")
            
            # 환경변수 오염 검증
            pollution_check = key_loader.verify_no_os_env_pollution()
            logger.info(f"🔐 {pollution_check['message']}")
            
    except Exception as e:
        logger.warning(f"Key validation warning: {e}")
        logger.info("Proceeding with server startup (key will be validated during first use)")
    
    # stdio 모드로 서버 실행
    mcp_server.run(transport="stdio")

if __name__ == "__main__":
    # MCP 모드 감지: stdin이 TTY가 아니면 MCP stdio 모드
    import sys
    
    if not sys.stdin.isatty():
        # MCP 모드: stdin이 파이프되어 있음 (Claude Code에서 호출)
        logger.info("Detected MCP mode (stdio transport)")
        run_mcp_server()
    else:
        # CLI 모드: 터미널에서 직접 실행
        logger.info("Detected CLI mode")
        main()
else:
    # 모듈로 import될 때 자동 실행하지 않음
    pass