# 🔐 나노바나나 MCP 서버 - 보안 강화 설정 가이드

## 📋 보안 강화 개요

이 버전의 나노바나나 MCP 서버는 **터미널 환경변수를 사용하지 않고**, 오직 `.env` 파일 또는 **MCP 설정**에서만 API 키를 읽어 명시적으로 SDK에 전달하는 보안 강화 버전입니다.

### 🔒 보안 원칙

1. **터미널 환경변수 차단**: `os.getenv(...)` 금지
2. **명시적 키 전달**: `genai.Client(api_key=...)` 항상 직접 전달  
3. **우선순위 관리**: MCP 설정 ▶ .env ▶ (없으면 에러)
4. **검증 로그**: 실행 전/후 "키 출처(source)"를 로그로 남겨 터미널 변수 영향이 없음을 증명

## 🚀 설정 방법

### 방법 1: MCP 서버 설정 (권장)

Claude Desktop의 설정 파일에 API 키를 직접 설정하는 방법입니다.

#### Windows 설정 파일 위치:
```
%APPDATA%\Claude\claude_desktop_config.json
```

#### macOS 설정 파일 위치:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

#### 설정 예시:
```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "C:\\MYCLAUDE_PROJECT\\nanobanana_MCP",
      "env": {
        "GEMINI_API_KEY": "AIzaSyXXXX-your-secret-key-XXXX"
      }
    }
  }
}
```

### 방법 2: .env 파일 (로컬 개발용)

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일에서 API 키 설정
GEMINI_API_KEY=your_gemini_api_key_here
```

## 🔑 지원되는 API 키 이름

우선순위에 따라 다음 키 이름들을 지원합니다:

1. `GEMINI_API_KEY` (권장)
2. `GOOGLE_API_KEY`  
3. `GOOGLE_AI_API_KEY`

## 🔍 API 키 획득 방법

1. [Google AI Studio](https://ai.google.dev/) 접속
2. "Get API Key" 클릭
3. 새 프로젝트 생성 또는 기존 프로젝트 선택
4. "Create API Key" 버튼 클릭
5. 생성된 키 복사

## ⚙️ 설정 검증

### 서버 시작 시 로그 확인

정상적으로 설정된 경우 다음과 같은 로그를 확인할 수 있습니다:

```
🔐 API Key Source: MCP_Settings
🔐 Key Name: GEMINI_API_KEY
🔐 ✅ Clean - No OS env pollution
```

### 로그 의미 설명

- **API Key Source**: 키를 읽어온 출처
  - `MCP_Settings`: MCP 서버 설정에서 로드
  - `.env_File`: .env 파일에서 로드
  - `Unknown`: 알 수 없는 출처 (오류 상황)

- **Key Name**: 실제 사용된 키 변수명

- **Pollution Check**: 터미널 환경변수 오염 검사
  - `✅ Clean - No OS env pollution`: 터미널 환경변수 없음 (정상)
  - `⚠️ OS env keys present but ignored`: 터미널 환경변수 있지만 무시됨

## 🐛 문제 해결

### 1. API 키를 찾을 수 없음
```
Gemini API key not found. Please set it in:
1. MCP server configuration (recommended): mcpServers.nanobanana.env.GEMINI_API_KEY
2. .env file: GEMINI_API_KEY, GOOGLE_API_KEY, or GOOGLE_AI_API_KEY
```

**해결방법:**
- MCP 설정 파일 확인
- .env 파일 존재 및 키 설정 확인
- 키 이름이 정확한지 확인

### 2. MCP 설정 파일을 찾을 수 없음
```
MCP settings file not found
```

**해결방법:**
- Claude Desktop 설정 파일 위치 확인
- 파일 권한 문제 확인
- 설정 파일 JSON 문법 오류 확인

### 3. API 키가 잘못됨
```
❌ Failed to create Gemini client: Client creation failed
```

**해결방법:**
- Google AI Studio에서 키 재발급
- 키 복사 시 공백이나 특수문자 포함 여부 확인
- 키 활성화 상태 확인

## 🔧 고급 설정

### Vertex AI 사용
```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "C:\\MYCLAUDE_PROJECT\\nanobanana_MCP",
      "env": {
        "GOOGLE_CLOUD_PROJECT": "your-project-id",
        "GOOGLE_CLOUD_LOCATION": "us-central1",
        "GOOGLE_GENAI_USE_VERTEXAI": "true"
      }
    }
  }
}
```

### 디버그 모드
```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "C:\\MYCLAUDE_PROJECT\\nanobanana_MCP",
      "env": {
        "GEMINI_API_KEY": "your-key",
        "NANOBANANA_DEBUG": "true",
        "NANOBANANA_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## 📝 테스트 방법

### 1. 헬스체크
```bash
python -m src.server --check-health
```

### 2. 직접 테스트
```python
from src.config_keyloader import SecureKeyLoader

# 키 로더 테스트
loader = SecureKeyLoader(mcp_server_name="nanobanana")
print(f"Has key: {loader.has_key()}")
print(f"Debug info: {loader.get_debug_info()}")
print(f"Pollution check: {loader.verify_no_os_env_pollution()}")
```

## 🔒 보안 모범 사례

1. **MCP 설정 우선**: .env 파일보다 MCP 설정에 키 저장
2. **키 권한 관리**: 설정 파일 접근 권한 제한
3. **키 로테이션**: 정기적으로 API 키 교체
4. **로그 모니터링**: 키 출처 로그 정기 확인
5. **버전 관리**: .env 파일은 절대 Git에 커밋하지 않음

## 📚 참고 자료

- [Google AI Studio](https://ai.google.dev/)
- [Claude Desktop MCP 문서](https://claude.ai/mcp)
- [Model Context Protocol 사양](https://github.com/modelcontextprotocol/specification)

---

**버전**: 1.0.0-secure  
**업데이트**: 2025-08-29  
**작성자**: Claude Code Assistant