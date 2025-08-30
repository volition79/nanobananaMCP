"""
나노바나나 이미지 생성 MCP 서버

Google의 Gemini 2.5 Flash Image (코드네임: 나노바나나)를 
Claude Code에서 사용할 수 있게 해주는 Model Context Protocol 서버입니다.
"""

__version__ = "1.0.0"
__author__ = "Claude Code Assistant"
__email__ = "support@anthropic.com"

from .server import main

__all__ = ["main"]