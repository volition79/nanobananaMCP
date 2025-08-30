# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 나노바나나 이미지 생성 MCP 서버

## 📋 프로젝트 개요
Google의 Gemini 2.5 Flash Image (코드네임: "나노바나나")를 Claude Code에서 사용할 수 있는 Model Context Protocol (MCP) 서버입니다.

## 🎯 주요 기능

### 1. 텍스트-이미지 생성 (`nanobanana_generate`)
- **기능**: 텍스트 프롬프트로부터 이미지 생성
- **파라미터**: 
  - `prompt` (필수): 이미지 생성을 위한 텍스트 설명
  - `aspect_ratio` (선택): 이미지 비율 (예: "16:9", "1:1", "9:16")
  - `style` (선택): 스타일 지정 (예: "photorealistic", "digital-art")
  - `candidate_count` (선택): 생성할 이미지 수 (1-4, 기본값: 1)
  - `quality` (선택): 이미지 품질 ("auto", "high", "medium", "low")

### 2. 이미지 편집 (`nanobanana_edit`)
- **기능**: 기존 이미지를 자연어 명령으로 편집
- **파라미터**:
  - `image_path` (필수): 편집할 이미지 파일 경로
  - `edit_prompt` (필수): 편집 지시사항
  - `output_format` (선택): 출력 형식 ("png", "jpeg", "webp")

### 3. 다중 이미지 블렌딩 (`nanobanana_blend`)
- **기능**: 여러 이미지를 합성하여 새로운 이미지 생성
- **파라미터**:
  - `image_paths` (필수): 블렌딩할 이미지 파일 경로 목록
  - `blend_prompt` (필수): 블렌딩 지시사항
  - `maintain_consistency` (선택): 캐릭터 일관성 유지 (기본값: true)

### 4. 서버 상태 확인 (`nanobanana_status`)
- **기능**: MCP 서버 및 Gemini API 연결 상태 확인
- **반환값**: 서버 상태, API 키 유효성, 사용 가능한 기능 목록

## 🔧 기술 사양

### API 정보
- **모델명**: `gemini-2.5-flash-image-preview`
- **기본 해상도**: 1024×1024 픽셀
- **토큰 비용**: 이미지당 1290 토큰 (약 $0.039)
- **지원 형식**: PNG, JPEG, WebP
- **최적 언어**: 영어 (한국어 프롬프트는 자동 영어 변환)

### 환경 요구사항
- **Python**: 3.8 이상
- **필수 패키지**:
  - `google-genai>=0.3.0` - Gemini API SDK
  - `fastmcp>=0.1.0` - MCP 서버 프레임워크
  - `pillow>=9.0.0` - 이미지 처리
  - `httpx>=0.24.0` - HTTP 클라이언트
  - `pydantic>=2.0.0` - 데이터 검증

### 환경 변수
```bash
# Google AI API 키 (필수)
GOOGLE_AI_API_KEY=your_api_key_here

# 이미지 출력 디렉토리 (선택, 기본값: ./outputs)
NANOBANANA_OUTPUT_DIR=./outputs

# 최대 이미지 크기 제한 (MB, 기본값: 10)
NANOBANANA_MAX_IMAGE_SIZE=10

# 프롬프트 최적화 활성화 (기본값: true)
NANOBANANA_OPTIMIZE_PROMPTS=true
```

## 📁 프로젝트 구조

```
nanobanana_mcp/
├── src/
│   ├── __init__.py
│   ├── server.py                 # MCP 서버 메인 로직
│   ├── gemini_client.py         # Gemini API 클라이언트
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── generate.py          # 텍스트-이미지 생성 도구
│   │   ├── edit.py              # 이미지 편집 도구
│   │   ├── blend.py             # 이미지 블렌딩 도구
│   │   └── status.py            # 상태 확인 도구
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── image_handler.py     # 이미지 처리 유틸리티
│   │   ├── prompt_optimizer.py  # 프롬프트 최적화
│   │   └── file_manager.py      # 파일 관리
│   └── models/
│       ├── __init__.py
│       └── schemas.py           # Pydantic 모델
├── tests/
│   ├── __init__.py
│   ├── test_server.py
│   └── test_tools.py
├── examples/
│   ├── basic_usage.py
│   └── claude_integration.py
├── requirements.txt
├── pyproject.toml
├── README.md
├── CLAUDE.md                    # 이 파일
└── .env.example
```

## 🔧 Common Development Commands

### Installation & Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your GOOGLE_AI_API_KEY
```

### Running the Server
```bash
# MCP mode (Claude Code integration)
python -m src.server

# Development mode with CLI
python -m src.server --dev

# Health check
python -m src.server --check-health

# Debug mode
python -m src.server --debug
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test files
python test_basic.py
python test_image_generation.py
python test_utilities.py
python test_api_key.py

# Unit tests only
pytest -m "not integration"

# Integration tests only  
pytest -m "integration"
```

### Code Quality
```bash
# Format code
black src/ tests/ examples/

# Lint code
flake8 src/ tests/ examples/

# Type checking
mypy src/
```

## 🏗️ Architecture Overview

### Key Components
- **`src/server.py`**: Main MCP server with FastMCP framework - registers 4 tools and handles MCP protocol
- **`src/gemini_client.py`**: Gemini API client with statistics tracking and health checks  
- **`src/tools/`**: Four MCP tools (generate, edit, blend, status) implementing core functionality
- **`src/utils/`**: Utilities for image handling, prompt optimization, and file management
- **`src/config.py`**: Settings management with environment variables and logging setup
- **`src/config_keyloader.py`**: Secure API key loading with multiple source priority

### MCP Tool Functions
The server exposes 4 tools to Claude Code:
- `nanobanana_generate()`: Text-to-image generation
- `nanobanana_edit()`: Image editing with natural language  
- `nanobanana_blend()`: Multi-image blending/composition
- `nanobanana_status()`: Server health and API connectivity

### Claude Code Integration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/nanobanana_mcp",
      "env": {
        "GOOGLE_AI_API_KEY": "your_api_key"
      }
    }
  }
}
```

## 📝 사용 예제

### 기본 이미지 생성
```python
# Claude Code에서 사용
# "나노바나나를 사용해서 고양이가 모자를 쓰고 있는 사진을 생성해줘"

result = nanobanana_generate(
    prompt="A cat wearing a hat, photorealistic style",
    aspect_ratio="1:1",
    quality="high"
)
```

### 이미지 편집
```python
# "이 이미지에서 배경을 바다로 바꿔줘"
result = nanobanana_edit(
    image_path="./cat_with_hat.png",
    edit_prompt="Change the background to ocean view"
)
```

### 다중 이미지 블렌딩
```python
# "이 두 이미지를 합성해서 환상적인 풍경을 만들어줘"
result = nanobanana_blend(
    image_paths=["./mountain.png", "./castle.png"],
    blend_prompt="Create a fantasy landscape with the castle on the mountain"
)
```

## 🔍 프롬프트 최적화 가이드

### 효과적인 프롬프트 작성법
1. **구체적이고 서술적인 표현 사용**
   - ❌ "예쁜 풍경"
   - ✅ "일몰이 지는 산 위의 성, 따뜻한 황금빛 조명, 사실적인 스타일"

2. **기술적 세부사항 포함**
   - 조명: "soft lighting", "dramatic shadows", "golden hour"
   - 스타일: "photorealistic", "digital art", "oil painting"
   - 구도: "wide shot", "close-up", "bird's eye view"

3. **비율 명시**
   - "16:9 aspect ratio" (와이드스크린)
   - "1:1 aspect ratio" (정사각형)
   - "9:16 aspect ratio" (세로형)

### 품질 향상 팁
- 영어 프롬프트 사용 (자동 번역 기능 있음)
- 구체적인 색상, 질감, 분위기 설명
- 원하지 않는 요소는 "no text", "no watermark" 등으로 제외
- 여러 후보 생성으로 최적 결과 선택

## ⚡ 성능 최적화

### 캐싱 전략
- 생성된 이미지는 로컬 캐시에 저장
- 동일한 프롬프트 재사용 시 캐시에서 반환
- 캐시 만료 시간: 24시간

### 배치 처리
- 여러 이미지 생성 요청을 배치로 처리
- 동시 처리 제한: 최대 3개 요청
- 큐 시스템으로 대기 요청 관리

### 오류 처리
- API 제한 도달 시 자동 재시도 (지수 백오프)
- 이미지 크기 제한 초과 시 자동 리사이징
- 네트워크 오류 시 로컬 백업 생성

## 🐛 문제 해결

### 일반적인 문제
1. **API 키 오류**
   - Google AI Studio에서 API 키 확인
   - 환경 변수 올바른 설정 확인

2. **이미지 생성 실패**
   - 프롬프트가 Google의 안전 가이드라인 위반 여부 확인
   - 영어 프롬프트로 재시도

3. **메모리 부족**
   - 이미지 크기 제한 설정 확인
   - 캐시 크기 조정

### 로깅
```bash
# 디버그 모드로 실행
NANOBANANA_LOG_LEVEL=DEBUG python -m src.server

# 로그 파일 위치
./logs/nanobanana_mcp.log
```

## 📚 참고 자료

### 공식 문서
- [Gemini API 문서](https://ai.google.dev/gemini-api/docs/models)
- [Google Generative AI Python SDK](https://github.com/google/generative-ai-python)
- [Model Context Protocol 사양](https://github.com/modelcontextprotocol/specification)

### 유사 프로젝트
- [qhdrl12/mcp-server-gemini-image-generator](https://github.com/qhdrl12/mcp-server-gemini-image-generator)
- [lansespirit's Image Gen MCP Server](https://github.com/lansespirit/image-gen-mcp)

## 📄 라이선스
MIT License - 자세한 내용은 LICENSE 파일 참조

---

**마지막 업데이트**: 2025-08-28
**작성자**: Claude Code Assistant
**버전**: 1.0.0


## 🛠️ Development Notes

### API Key Management
The server uses `config_keyloader.py` for secure API key loading with multiple source priority:
1. MCP server configuration (recommended): `mcpServers.nanobanana.env.GEMINI_API_KEY`
2. Environment variables: `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or `GOOGLE_AI_API_KEY`
3. `.env` file in project root

### Server Startup Flow
1. **`src/server.py`** initializes FastMCP server and registers 4 tools
2. **`startup()`** function creates Gemini client and ensures output directories exist
3. Server runs in stdio mode for MCP integration or WebSocket mode for direct access
4. **`shutdown()`** function logs statistics and performs cleanup

### Key File Locations
- **Configuration**: `src/config.py` - centralized settings with env vars
- **Main server**: `src/server.py:main()` - CLI entry point with argument parsing  
- **MCP tools**: `src/tools/` - each tool exports async functions and metadata
- **Test files**: Root-level `test_*.py` files for standalone testing
- **Outputs**: `./outputs/` - generated/edited/blended images with metadata
- **Logs**: `./logs/nanobanana_mcp.log` - server logs with rotation

### MCP 파라미터 타입 처리 지침

#### 문제점
MCP 프로토콜을 통해 전달되는 파라미터는 종종 문자열 형태로 전송됩니다 (예: `"true"`, `"1"`, `"false"`). 
하지만 FastMCP는 타입 힌트를 기반으로 엄격한 타입 검증을 수행하므로, `Optional[bool]`이나 `Optional[int]`로 정의된 파라미터는 문자열을 거부합니다.

#### 해결 패턴
**1. FastMCP 도구 정의 시 Union 타입 사용:**
```python
# ❌ 문제가 되는 패턴
optimize_prompt: Optional[bool] = True
candidate_count: Optional[int] = 1

# ✅ 올바른 패턴  
optimize_prompt: Optional[Union[bool, str]] = True
candidate_count: Optional[Union[int, str]] = 1
```

**2. Pydantic 모델에서 자동 변환 구현:**
```python
@field_validator('optimize_prompt', mode='before')
@classmethod
def validate_optimize_prompt(cls, v):
    if isinstance(v, str):
        v_lower = v.strip().lower()
        if v_lower in ('true', '1', 'yes', 'on'):
            return True
        elif v_lower in ('false', '0', 'no', 'off'):
            return False
    return v

@field_validator('candidate_count', mode='before') 
@classmethod
def validate_candidate_count(cls, v):
    if isinstance(v, str):
        try:
            return int(v.strip())
        except ValueError:
            raise ValueError(f"Invalid integer: '{v}'")
    return v
```

#### 새 파라미터 추가 시 체크리스트
1. **`src/server.py`**: FastMCP 도구 함수에서 `Union[원하는타입, str]` 타입 힌트 사용
2. **`src/models/schemas.py`**: Pydantic 모델에 `@field_validator(mode='before')` 추가
3. **타입 변환 지원**: `str → bool`, `str → int`, `str → float` 등
4. **에러 메시지**: 명확하고 도움이 되는 오류 메시지 제공
5. **테스트**: 문자열과 원래 타입 모두로 테스트
6. **⚠️ MCP 재시작**: 변경 후 반드시 MCP 서버 재연결 필요

#### 지원해야 할 문자열 값들
- **Boolean**: `"true"`, `"false"`, `"1"`, `"0"`, `"yes"`, `"no"`, `"on"`, `"off"`
- **Integer**: `"1"`, `"42"`, `"0"` 등 숫자 문자열
- **Float**: `"1.5"`, `"0.8"` 등 소수점 문자열

#### ⚠️ 중요한 주의사항: MCP 서버 재시작
**`src/server.py` 파일을 수정한 후에는 반드시 MCP 서버를 재시작해야 합니다.**

**재시작 방법:**
1. Claude Desktop에서 `/mcp` 명령 실행
2. 또는 Claude Desktop 완전 종료 후 재시작

**재시작이 필요한 변경사항:**
- FastMCP 도구 함수의 파라미터 타입 변경
- 새로운 MCP 도구 추가
- 도구 시그니처 변경
- Import 구문 변경

**재시작이 불필요한 변경사항:**
- `src/tools/` 내부 구현 로직 변경
- `src/utils/`, `src/models/` 변경
- 메타데이터, 상수 변경

**디버깅 팁:**
- 변경 후 에러 발생 시 가장 먼저 MCP 재시작 확인
- `Input validation error: 'xxx' is not valid under any of the given schemas` 에러는 대부분 타입 문제
- 타입 변환 실패 시 명확한 오류 메시지로 디버깅 지원

### 일반적인 타입 변환 이슈 해결법

#### 문제: `Input validation error: 'true' is not valid under any of the given schemas`
**원인**: FastMCP가 문자열 `"true"`를 `Optional[bool]` 파라미터로 받을 수 없음

**해결책**:
1. `src/server.py`에서 해당 파라미터를 `Optional[Union[bool, str]]`로 변경
2. `from typing import Union` import 추가
3. MCP 서버 재연결 (`/mcp` 명령어 또는 Claude Desktop 재시작)

#### 문제: `Input validation error: '1' is not valid under any of the given schemas` 
**원인**: FastMCP가 문자열 `"1"`을 `Optional[int]` 파라미터로 받을 수 없음

**해결책**:
1. `src/server.py`에서 해당 파라미터를 `Optional[Union[int, str]]`로 변경  
2. Pydantic 모델에 이미 `@field_validator`가 구현되어 있는지 확인
3. MCP 서버 재연결

#### 디버깅 팁
- 오류 메시지에서 어떤 값(`'true'`, `'1'` 등)이 문제인지 확인
- 해당 파라미터가 `src/server.py`에서 Union 타입으로 정의되어 있는지 확인
- 변경 후 반드시 MCP 서버 재연결하여 새 코드 적용

### 새 MCP 도구/파라미터 추가 가이드

#### Step 1: `src/server.py`에 MCP 도구 정의
```python
@mcp_server.tool()
async def new_tool_name(
    required_param: str,
    optional_bool: Optional[Union[bool, str]] = False,  # ✅ Union 사용
    optional_int: Optional[Union[int, str]] = 10,       # ✅ Union 사용  
    optional_float: Optional[Union[float, str]] = 1.0,  # ✅ Union 사용
    optional_str: Optional[str] = None                   # ✅ 문자열은 Union 불필요
) -> Dict[str, Any]:
    """도구 설명"""
    try:
        return await actual_implementation_function(**locals())
    except Exception as e:
        logger.error(f"Error in new_tool_name: {e}")
        return create_error_response(
            f"Operation failed: {str(e)}",
            "OPERATION_ERROR"
        ).dict()
```

#### Step 2: `src/tools/` 디렉토리에 구현 파일 생성
```python
async def new_tool_name(
    required_param: str,
    optional_bool: Optional[Union[bool, str]] = False,
    **kwargs
) -> Dict[str, Any]:
    # Pydantic 모델로 검증
    request = NewToolRequest(
        required_param=required_param,
        optional_bool=optional_bool,
        **kwargs
    )
    # 실제 구현...
```

#### Step 3: `src/models/schemas.py`에 Pydantic 모델 추가
```python
class NewToolRequest(BaseRequest):
    required_param: str = Field(..., description="필수 파라미터")
    optional_bool: Optional[bool] = Field(False, description="선택적 불린값")
    optional_int: Optional[int] = Field(10, ge=1, le=100, description="선택적 정수값")
    
    @field_validator('optional_bool', mode='before')
    @classmethod
    def validate_optional_bool(cls, v):
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ('true', '1', 'yes', 'on'):
                return True
            elif v_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"Invalid boolean string: '{v}'")
        return v
    
    @field_validator('optional_int', mode='before')
    @classmethod  
    def validate_optional_int(cls, v):
        if isinstance(v, str):
            try:
                return int(v.strip())
            except ValueError:
                raise ValueError(f"Invalid integer string: '{v}'")
        return v
```

#### Step 4: 테스트 코드 작성
```python
# 문자열 파라미터 테스트
await new_tool_name(
    required_param="test",
    optional_bool="true",    # 문자열
    optional_int="42"        # 문자열
)

# 원래 타입 파라미터 테스트  
await new_tool_name(
    required_param="test",
    optional_bool=True,      # 불린
    optional_int=42          # 정수
)
```

#### 권장사항
- **모든 비문자열 선택 파라미터는 `Union[원본타입, str]` 사용**
- **Pydantic에서 `mode='before'` validator로 문자열 변환 처리**
- **명확하고 도움이 되는 에러 메시지 제공**
- **기본값을 명확히 지정하여 호환성 보장**



소스놀이터님이 고정함
@sourcePlayground
5일 전
아래는 영상 2:04경에 나오는 CLAUDE.md에 추가할 지침 내용입니다.

## github 푸쉬를 위해 다음 정보 사용:
GIT HUB의 Personal Access Token:
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

GitHub 주소: https://github.com/volition79/nanobananaMCP

## 원격 저장소에 푸시할 때, 먼저 HTTP 버퍼 크기를 늘리고 조금 씩 나누어 푸시할 것. 에러 시 작은 변경사항만 포함하는 새커밋을 만들어 푸시할 것

## github cli설치했어. gh 명령어 사용 가능해. 이걸로 github 처리해줘. 
( https://cli.github.com 에서 github cli 설치하시면 원활히 깃허브 작동됩니다. 영상에서는 빠져있지만, 이 설정 추천드립니다.)

