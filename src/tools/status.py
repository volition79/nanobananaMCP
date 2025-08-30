"""
서버 상태 확인 도구

나노바나나 MCP 서버의 전반적인 상태, API 연결, 성능 통계, 시스템 정보를 확인하는 MCP 도구입니다.
"""

import asyncio
import logging
import platform
import psutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..gemini_client import get_gemini_client, create_gemini_client
from ..utils.file_manager import get_file_manager
from ..models.schemas import (
    ServerStatusResponse,
    create_error_response
)
from ..constants import (
    GEMINI_MODEL_NAME, 
    PROJECT_NAME, 
    PROJECT_VERSION, 
    MCP_VERSION,
    GEMINI_COST_PER_IMAGE
)
from ..config import get_settings

logger = logging.getLogger(__name__)

# 서버 시작 시간 (전역 변수)
_server_start_time = time.time()


async def nanobanana_status(
    detailed: Optional[bool] = True,
    include_history: Optional[bool] = False,
    reset_stats: Optional[bool] = False,
    **kwargs
) -> Dict[str, Any]:
    """
    나노바나나 MCP 서버의 상태 정보 반환
    
    Args:
        detailed: 상세 정보 포함 여부 (기본값: True)
        include_history: 최근 작업 히스토리 포함 여부 (기본값: False)
        reset_stats: 통계 초기화 여부 (기본값: False, 관리자용)
        **kwargs: 추가 설정
        
    Returns:
        Dict: MCP 응답 형식의 서버 상태 정보
    """
    try:
        logger.info("Collecting server status information")
        start_time = time.time()
        
        # 통계 초기화 (요청된 경우)
        if reset_stats:
            try:
                gemini_client = get_gemini_client()
                if gemini_client is None:
                    logger.info("Creating new Gemini client for MCP call")
                    gemini_client = await create_gemini_client()
                gemini_client.reset_statistics()
                logger.info("Statistics reset requested and completed")
            except Exception as e:
                logger.warning(f"Failed to reset statistics: {e}")
        
        # 병렬로 상태 정보 수집
        tasks = [
            collect_api_status(),
            collect_server_info(),
            collect_performance_stats(detailed),
            collect_storage_stats(),
            collect_system_info(detailed)
        ]
        
        if include_history:
            tasks.append(collect_recent_history())
        
        # 모든 정보 동시 수집
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 처리
        api_status = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
        server_info = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
        performance_stats = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}
        storage_stats = results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])}
        system_info = results[4] if not isinstance(results[4], Exception) else {"error": str(results[4])}
        
        recent_history = {}
        if include_history and len(results) > 5:
            recent_history = results[5] if not isinstance(results[5], Exception) else {"error": str(results[5])}
        
        # 전체 상태 판정
        overall_status = calculate_overall_status(api_status, storage_stats, system_info)
        
        # 상태 수집 시간
        collection_time = time.time() - start_time
        
        # 응답 생성
        try:
            response_data = {
                "success": True,
                "message": f"Server status: {overall_status}",
                "timestamp": datetime.now().isoformat(),
                "server_name": server_info.get("name", PROJECT_NAME),
                "version": server_info.get("version", PROJECT_VERSION),
                "uptime": server_info.get("uptime", 0),
                "api_status": api_status,
                "storage_stats": storage_stats,
                "performance_stats": performance_stats,
                "system_info": system_info,
                "overall_status": overall_status,
                "collection_time": round(collection_time, 3),
                "stats_reset": reset_stats
            }
            
            # 선택적 데이터 추가
            if include_history:
                response_data["recent_history"] = recent_history
            
            if not detailed:
                # 간소화된 응답
                response_data = {
                    "success": True,
                    "message": f"Server status: {overall_status}",
                    "server_name": PROJECT_NAME,
                    "version": PROJECT_VERSION,
                    "uptime": server_info.get("uptime", 0),
                    "api_accessible": api_status.get("api_accessible", False),
                    "overall_status": overall_status,
                    "timestamp": datetime.now().isoformat()
                }
            
            response = ServerStatusResponse(**response_data)
            logger.info(f"Status collection completed in {collection_time:.3f}s. Overall status: {overall_status}")
            
            return response.dict()
            
        except Exception as e:
            logger.error(f"Failed to create status response: {e}")
            return create_error_response(
                "Failed to generate status response",
                "RESPONSE_ERROR"
            ).dict()
    
    except Exception as e:
        logger.error(f"Unexpected error in nanobanana_status: {e}")
        return create_error_response(
            f"Unexpected error: {str(e)}",
            "INTERNAL_ERROR"
        ).dict()


async def collect_api_status() -> Dict[str, Any]:
    """API 상태 정보 수집"""
    try:
        gemini_client = get_gemini_client()
        if gemini_client is None:
            logger.info("Creating new Gemini client for MCP call")
            gemini_client = await create_gemini_client()
        
        # API 연결 상태 확인
        health_result = await gemini_client.health_check()
        
        # 기본 통계 수집
        stats = gemini_client.get_statistics()
        
        return {
            "api_accessible": health_result.get("api_accessible", False),
            "model": health_result.get("model", GEMINI_MODEL_NAME),
            "status": health_result.get("status", "unknown"),
            "vertex_ai": health_result.get("vertex_ai", False),
            "last_check": datetime.now().isoformat(),
            "statistics": stats,
            "error": health_result.get("error")
        }
        
    except Exception as e:
        logger.error(f"Failed to collect API status: {e}")
        return {
            "api_accessible": False,
            "status": "error",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }


async def collect_server_info() -> Dict[str, Any]:
    """서버 정보 수집"""
    try:
        settings = get_settings()
        uptime = calculate_uptime()
        
        return {
            "name": settings.server_name or PROJECT_NAME,
            "version": settings.server_version or PROJECT_VERSION,
            "mcp_version": MCP_VERSION,
            "uptime": uptime,
            "uptime_human": format_uptime(uptime),
            "started_at": datetime.fromtimestamp(_server_start_time).isoformat(),
            "dev_mode": settings.dev_mode,
            "debug": settings.debug,
            "host": settings.host,
            "port": settings.port
        }
        
    except Exception as e:
        logger.error(f"Failed to collect server info: {e}")
        return {
            "name": PROJECT_NAME,
            "version": PROJECT_VERSION,
            "error": str(e)
        }


async def collect_performance_stats(detailed: bool = True) -> Dict[str, Any]:
    """성능 통계 수집"""
    try:
        file_manager = get_file_manager()
        
        # 기본 통계
        total_generated = len(file_manager.get_image_history(operation_type="generated", limit=10000))
        total_edited = len(file_manager.get_image_history(operation_type="edited", limit=10000))  
        total_blended = len(file_manager.get_image_history(operation_type="blended", limit=10000))
        
        total_operations = total_generated + total_edited + total_blended
        
        # 비용 계산
        total_cost = total_operations * GEMINI_COST_PER_IMAGE
        
        stats = {
            "total_operations": total_operations,
            "operations_breakdown": {
                "generated": total_generated,
                "edited": total_edited,
                "blended": total_blended
            },
            "total_cost_usd": round(total_cost, 4),
            "cost_per_operation": GEMINI_COST_PER_IMAGE
        }
        
        if detailed:
            # 최근 24시간 통계
            recent_cutoff = datetime.now() - timedelta(hours=24)
            recent_operations = 0
            
            for op_type in ["generated", "edited", "blended"]:
                recent_ops = [
                    img for img in file_manager.get_image_history(operation_type=op_type, limit=1000)
                    if datetime.fromisoformat(img.get("created_at", "1970-01-01")) > recent_cutoff
                ]
                recent_operations += len(recent_ops)
                stats["operations_breakdown"][f"recent_{op_type}_24h"] = len(recent_ops)
            
            stats["recent_operations_24h"] = recent_operations
            stats["recent_cost_24h"] = round(recent_operations * GEMINI_COST_PER_IMAGE, 4)
            
            # 평균 처리 시간 (가능한 경우)
            all_images = file_manager.get_image_history(limit=100)
            processing_times = [
                img.get("generation_time", 0) for img in all_images 
                if img.get("generation_time")
            ]
            
            if processing_times:
                stats["average_processing_time"] = round(sum(processing_times) / len(processing_times), 2)
                stats["min_processing_time"] = round(min(processing_times), 2)
                stats["max_processing_time"] = round(max(processing_times), 2)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to collect performance stats: {e}")
        return {"error": str(e)}


async def collect_storage_stats() -> Dict[str, Any]:
    """스토리지 통계 수집"""
    try:
        file_manager = get_file_manager()
        storage_info = file_manager.get_storage_stats()
        
        # 추가 디스크 공간 정보
        settings = get_settings()
        
        try:
            disk_usage = psutil.disk_usage(str(settings.output_dir))
            disk_info = {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "used_percent": round((disk_usage.used / disk_usage.total) * 100, 1)
            }
            storage_info["disk_usage"] = disk_info
        except Exception as e:
            logger.warning(f"Failed to get disk usage: {e}")
            storage_info["disk_usage"] = {"error": str(e)}
        
        return storage_info
        
    except Exception as e:
        logger.error(f"Failed to collect storage stats: {e}")
        return {"error": str(e)}


async def collect_system_info(detailed: bool = True) -> Dict[str, Any]:
    """시스템 정보 수집"""
    try:
        info = {
            "platform": platform.platform(),
            "python_version": sys.version,
            "architecture": platform.architecture()[0]
        }
        
        if detailed:
            try:
                # 메모리 정보
                memory = psutil.virtual_memory()
                info["memory"] = {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent
                }
                
                # CPU 정보
                info["cpu"] = {
                    "cores": psutil.cpu_count(logical=False),
                    "threads": psutil.cpu_count(logical=True),
                    "usage_percent": psutil.cpu_percent(interval=1)
                }
                
                # 프로세스 정보
                process = psutil.Process()
                info["process"] = {
                    "pid": process.pid,
                    "memory_mb": round(process.memory_info().rss / (1024**2), 1),
                    "cpu_percent": round(process.cpu_percent(), 1),
                    "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
                }
                
            except Exception as e:
                logger.warning(f"Failed to get detailed system info: {e}")
                info["detailed_info_error"] = str(e)
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to collect system info: {e}")
        return {"error": str(e)}


async def collect_recent_history() -> Dict[str, Any]:
    """최근 작업 히스토리 수집"""
    try:
        file_manager = get_file_manager()
        
        # 각 작업 유형별로 최근 5개씩 수집
        history = {}
        
        for op_type in ["generated", "edited", "blended"]:
            recent_items = file_manager.get_image_history(operation_type=op_type, limit=5)
            history[f"recent_{op_type}"] = [
                {
                    "filename": item.get("filename"),
                    "created_at": item.get("created_at"),
                    "prompt": item.get("prompt", "")[:100],  # 처음 100글자만
                    "file_size": item.get("file_size"),
                    "processing_time": item.get("generation_time")
                }
                for item in recent_items
            ]
        
        return history
        
    except Exception as e:
        logger.error(f"Failed to collect recent history: {e}")
        return {"error": str(e)}


def calculate_overall_status(api_status: Dict, storage_stats: Dict, system_info: Dict) -> str:
    """전체 상태 판정"""
    try:
        # API 상태 확인
        api_healthy = api_status.get("api_accessible", False)
        
        # 스토리지 상태 확인
        storage_ok = True
        disk_usage = storage_stats.get("disk_usage", {})
        if isinstance(disk_usage, dict) and "used_percent" in disk_usage:
            if disk_usage["used_percent"] > 90:  # 90% 이상 사용 시 경고
                storage_ok = False
        
        # 메모리 상태 확인
        memory_ok = True
        memory_info = system_info.get("memory", {})
        if isinstance(memory_info, dict) and "percent_used" in memory_info:
            if memory_info["percent_used"] > 85:  # 85% 이상 사용 시 경고
                memory_ok = False
        
        # 종합 판정
        if api_healthy and storage_ok and memory_ok:
            return "healthy"
        elif api_healthy:
            return "degraded"
        else:
            return "unhealthy"
            
    except Exception as e:
        logger.error(f"Failed to calculate overall status: {e}")
        return "unknown"


def calculate_uptime() -> float:
    """서버 가동 시간 계산 (초)"""
    return time.time() - _server_start_time


def format_uptime(uptime_seconds: float) -> str:
    """가동 시간을 읽기 쉬운 형식으로 변환"""
    try:
        uptime_timedelta = timedelta(seconds=int(uptime_seconds))
        days = uptime_timedelta.days
        hours, remainder = divmod(uptime_timedelta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"
        
    except Exception as e:
        logger.error(f"Failed to format uptime: {e}")
        return f"{int(uptime_seconds)}s"


def get_health_summary() -> Dict[str, Any]:
    """간단한 상태 요약 정보 (동기 함수)"""
    try:
        uptime = calculate_uptime()
        
        # 기본 정보만 수집
        summary = {
            "server_name": PROJECT_NAME,
            "version": PROJECT_VERSION,
            "uptime": uptime,
            "uptime_human": format_uptime(uptime),
            "status": "running",
            "timestamp": datetime.now().isoformat()
        }
        
        # 간단한 시스템 정보
        try:
            memory = psutil.virtual_memory()
            summary["memory_usage_percent"] = round(memory.percent, 1)
            summary["memory_available_gb"] = round(memory.available / (1024**3), 2)
        except Exception as e:
            logger.debug(f"Could not get memory info: {e}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get health summary: {e}")
        return {
            "server_name": PROJECT_NAME,
            "status": "error",
            "error": str(e)
        }


def reset_server_start_time() -> None:
    """서버 시작 시간 재설정 (서버 재시작 시 사용)"""
    global _server_start_time
    _server_start_time = time.time()
    logger.info("Server start time reset")


# MCP 도구 메타데이터
TOOL_METADATA = {
    "name": "nanobanana_status",
    "description": "Check the status and health of the Nanobanana MCP server",
    "parameters": {
        "type": "object",
        "properties": {
            "detailed": {
                "type": "boolean",
                "description": "Include detailed system and performance information",
                "default": True
            },
            "include_history": {
                "type": "boolean",
                "description": "Include recent operation history",
                "default": False
            },
            "reset_stats": {
                "type": "boolean",
                "description": "Reset server statistics (admin only)",
                "default": False
            }
        },
        "required": []
    },
    "returns": {
        "type": "object",
        "description": "Comprehensive server status including API health, performance stats, and system information"
    }
}