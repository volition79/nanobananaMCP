"""
API 키 로더 모듈

터미널 환경변수는 전혀 사용하지 않고, 오직 .env 파일 또는 MCP 설정에서만 키를 읽어 
명시적으로 SDK에 전달하는 보안 강화 모듈입니다.

우선순위: MCP 설정(env) > .env > (없으면 에러)
"""

from pathlib import Path
import json
from typing import Optional, Dict, Any
from dotenv import dotenv_values  # DOES NOT touch process env
import logging

logger = logging.getLogger(__name__)


def load_from_env_file(env_path: str = ".env") -> Dict[str, str]:
    """
    .env 파일에서 키-값 쌍을 로드합니다.
    중요: 프로세스 환경변수를 건드리지 않습니다.
    
    Args:
        env_path: .env 파일 경로 (기본: ".env")
        
    Returns:
        Dict[str, str]: 환경변수 딕셔너리
    """
    env_file = Path(env_path)
    
    if not env_file.exists():
        logger.debug(f"Env file not found: {env_path}")
        return {}
    
    try:
        env_vars = dotenv_values(str(env_file))
        logger.debug(f"Loaded {len(env_vars)} variables from {env_path}")
        return {k: v for k, v in env_vars.items() if v is not None}
    except Exception as e:
        logger.warning(f"Failed to load env file {env_path}: {e}")
        return {}


def load_from_mcp_settings(
    settings_path: Optional[str] = None,
    server_name: Optional[str] = None
) -> Dict[str, str]:
    """
    MCP 설정 파일에서 환경변수를 로드합니다.
    
    Args:
        settings_path: MCP 설정 파일 경로 (예: ~/.config/Claude/claude_desktop_config.json)
        server_name: mcpServers에서 사용할 서버 이름 (예: "nanobanana")
        
    Returns:
        Dict[str, str]: 환경변수 딕셔너리
    """
    if not settings_path:
        # 기본 Claude Desktop 설정 경로들 시도
        possible_paths = [
            Path.home() / ".config" / "Claude" / "claude_desktop_config.json",
            Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
            Path(".claude") / "settings.local.json",
            Path("claude_desktop_config.json")
        ]
        
        for path in possible_paths:
            if path.exists():
                settings_path = str(path)
                logger.debug(f"Found MCP settings at: {settings_path}")
                break
        else:
            logger.debug("No MCP settings file found")
            return {}
    
    settings_file = Path(settings_path)
    if not settings_file.exists():
        logger.debug(f"MCP settings file not found: {settings_path}")
        return {}
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        servers = data.get("mcpServers", {})
        if not servers:
            logger.debug("No mcpServers section found in settings")
            return {}
        
        # 특정 서버 이름이 주어진 경우
        if server_name and server_name in servers:
            env_vars = servers[server_name].get("env", {}) or {}
            logger.debug(f"Loaded {len(env_vars)} variables from MCP server '{server_name}'")
            return {k: str(v) for k, v in env_vars.items()}
        
        # 서버명이 주어지지 않은 경우 전체 env merge (뒤가 우선)
        merged = {}
        for srv_name, srv_config in servers.items():
            srv_env = srv_config.get("env", {}) or {}
            merged.update(srv_env)
            if srv_env:
                logger.debug(f"Merged {len(srv_env)} variables from server '{srv_name}'")
        
        return {k: str(v) for k, v in merged.items()}
        
    except Exception as e:
        logger.warning(f"Failed to load MCP settings {settings_path}: {e}")
        return {}


def pick_gemini_key(*sources: Dict[str, str]) -> Optional[str]:
    """
    여러 소스에서 Gemini API 키를 우선순위에 따라 선택합니다.
    
    우선순위:
    1. GEMINI_API_KEY
    2. GOOGLE_API_KEY  
    3. GOOGLE_AI_API_KEY
    
    Args:
        *sources: 키-값 딕셔너리들 (앞쪽이 우선순위 높음)
        
    Returns:
        Optional[str]: 발견된 API 키 또는 None
    """
    CANDIDATES = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"]
    
    for source_idx, source in enumerate(sources):
        if not source:
            continue
            
        for key_name in CANDIDATES:
            val = (source.get(key_name) or "").strip()
            if val:
                logger.debug(f"Found API key '{key_name}' from source {source_idx}")
                return val
    
    logger.debug("No API key found in any source")
    return None


def get_key_source_info(*sources: Dict[str, str]) -> Dict[str, Any]:
    """
    키의 출처 정보를 반환합니다 (디버깅/검증용).
    
    Args:
        *sources: 키-값 딕셔너리들
        
    Returns:
        Dict[str, Any]: 키 출처 정보
    """
    CANDIDATES = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"]
    SOURCE_NAMES = ["MCP_Settings", ".env_File", "Unknown"]
    
    info = {
        "found_key": None,
        "key_name": None,
        "source_name": None,
        "source_index": None,
        "masked_key": None
    }
    
    for source_idx, source in enumerate(sources):
        if not source:
            continue
            
        for key_name in CANDIDATES:
            val = (source.get(key_name) or "").strip()
            if val:
                info.update({
                    "found_key": True,
                    "key_name": key_name,
                    "source_name": SOURCE_NAMES[source_idx] if source_idx < len(SOURCE_NAMES) else "Unknown",
                    "source_index": source_idx,
                    "masked_key": f"{val[:10]}..." if len(val) > 10 else f"{val[:4]}..."
                })
                return info
    
    info["found_key"] = False
    return info


class SecureKeyLoader:
    """
    보안 강화 API 키 로더 클래스
    """
    
    def __init__(
        self,
        mcp_settings_path: Optional[str] = None,
        mcp_server_name: str = "nanobanana",
        env_file: str = ".env"
    ):
        """
        Args:
            mcp_settings_path: MCP 설정 파일 경로
            mcp_server_name: MCP 서버 이름
            env_file: .env 파일 경로
        """
        self.mcp_settings_path = mcp_settings_path
        self.mcp_server_name = mcp_server_name
        self.env_file = env_file
        
        # 키 로드
        self.mcp_env = load_from_mcp_settings(mcp_settings_path, mcp_server_name)
        self.file_env = load_from_env_file(env_file)
        
        # 키 선택 (MCP 우선)
        self.api_key = pick_gemini_key(self.mcp_env, self.file_env)
        self.key_info = get_key_source_info(self.mcp_env, self.file_env)
        
        logger.info(f"Key loader initialized - Found key: {self.key_info['found_key']}")
        if self.key_info['found_key']:
            logger.info(f"Key source: {self.key_info['source_name']} ({self.key_info['key_name']})")
    
    def get_api_key(self) -> Optional[str]:
        """API 키 반환"""
        return self.api_key
    
    def has_key(self) -> bool:
        """API 키 존재 여부"""
        return bool(self.api_key)
    
    def get_debug_info(self) -> Dict[str, Any]:
        """디버그 정보 반환"""
        return {
            "key_info": self.key_info,
            "mcp_env_count": len(self.mcp_env),
            "file_env_count": len(self.file_env),
            "settings_path": self.mcp_settings_path,
            "server_name": self.mcp_server_name,
            "env_file": self.env_file
        }
    
    def verify_no_os_env_pollution(self) -> Dict[str, Any]:
        """
        OS 환경변수 오염이 없는지 검증합니다.
        
        Returns:
            Dict[str, Any]: 검증 결과
        """
        import os
        
        CANDIDATES = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"]
        os_env_keys = []
        
        for key_name in CANDIDATES:
            if key_name in os.environ:
                os_env_keys.append({
                    "name": key_name,
                    "masked_value": f"{os.environ[key_name][:10]}..." if len(os.environ[key_name]) > 10 else "***"
                })
        
        return {
            "os_env_keys_found": len(os_env_keys),
            "os_env_keys": os_env_keys,
            "our_key_source": self.key_info['source_name'],
            "pollution_risk": len(os_env_keys) > 0 and not self.has_key(),
            "message": "✅ Clean - No OS env pollution" if len(os_env_keys) == 0 or self.has_key() else "⚠️  OS env keys present but ignored"
        }