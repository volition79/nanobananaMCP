# 🍌 나노바나나 MCP (NanoBanana MCP)

**Google의 Gemini 2.5 Flash Image를 Claude Code에서 사용할 수 있는 Model Context Protocol (MCP) 서버**

[설치](#-설치) • [설정](#-claude-code-연동) • [사용법](#-사용법) • [문제해결](#-문제해결)


---

## 📋 개요

**나노바나나 MCP**는 Google의 **Gemini 2.5 Flash Image** (코드네임: "나노바나나")를 Claude Code/Desktop, 제미나이 CLI 등에서 원활하게 사용할 수 있게 해주는 MCP 서버입니다.

### 🎯 주요 기능

- 🎨 **텍스트-이미지 생성**: 자연어 설명으로 고품질 이미지 생성
- ✏️ **이미지 편집**: 기존 이미지를 자연어 명령으로 편집
- 🔄 **이미지 블렌딩**: 여러 이미지를 합성하여 새로운 작품 생성
- 📊 **상태 모니터링**: API 사용량 및 서버 상태 실시간 확인

### 🔧 기술 사양

- **모델**: `gemini-2.5-flash-image-preview`
- **해상도**: 최대 1024×1024 픽셀
- **지원 형식**: PNG, JPEG, WebP
- **비용**: 이미지당 약 $0.039 (1290 토큰)
- **Python**: 3.8 이상 필요

---

## 🚀 설치

### 방법 1: pipx로 설치 (권장)

```bash
# pipx가 없다면 먼저 설치
python -m pip install --user pipx
pipx ensurepath

# 나노바나나 MCP 설치
pipx install nanobanana-mcp
```

### 방법 2: pip로 가상환경 설치

```bash
# 가상환경 생성 및 활성화
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux  
source .venv/bin/activate

# 패키지 설치
pip install nanobanana-mcp
```

### 방법 3: 개발 버전 설치 (최신 기능)

```bash
# TestPyPI에서 설치
pip install --index-url https://test.pypi.org/simple/ nanobanana-mcp
```

---

## 🔧 Claude Code 연동

### 1. API 키 준비

[Google AI Studio](https://aistudio.google.com/app/apikey)에서 Gemini API 키를 발급받으세요.

### 2. MCP 설정

Claude Desktop의 설정 파일(`claude_desktop_config.json`)을 열고 `mcpServers` 섹션에 다음 중 하나를 추가하세요:

#### A. 콘솔 스크립트 실행 (간단/권장)

```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "nanobanana-mcp",
      "args": [],
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

#### B. Python 모듈 실행 (현행 호환)

```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/your/nanobanana-mcp",
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

#### C. 가상환경 경로 지정

```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "/path/to/.venv/bin/nanobanana-mcp",
      "args": [],
      "env": {
        "GEMINI_API_KEY": "YOUR_API_KEY_HERE"
      }
    }
  }
}
```

### 3. 환경변수 파일 설정 (선택사항)

프로젝트 루트에 `.env` 파일을 생성할 수 있습니다:

```bash
# .env 파일 내용
GEMINI_API_KEY=your-api-key-here
GOOGLE_AI_API_KEY=your-api-key-here  # 대체 키명
```

---

## 💡 사용법

Claude Code, 제미나이 CLI, Claude Desktop 등에서 자연어로 요청하면 자동으로 적절한 MCP 도구가 호출됩니다.

### 🎨 이미지 생성

```
선글라스를 쓴 고양이를 해변에서 그려줘
```

```
16:9 비율로 일몰이 지는 산 위의 성을 사실적으로 그려줘
```

### ✏️ 이미지 편집

```
이 사진의 배경을 밤하늘로 바꿔줘
```

```
이 이미지에서 차 색을 빨간색으로 바꿔줘
```

### 🔄 이미지 블렌딩

```
이 두 풍경 사진을 하나의 환상적인 장면으로 합쳐줘
```

```
산과 성 이미지를 블렌딩해서 판타지 풍경을 만들어줘
```

### 📊 상태 확인

```
나노바나나 서버 상태 확인해줘
```

```
이미지 생성기 사용량 통계 보여줘
```

---

## 🛠️ MCP 도구 상세

### 1. `nanobanana_generate` - 이미지 생성

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `prompt` | **필수** string | - | 이미지 생성을 위한 텍스트 설명 |
| `aspect_ratio` | string | `null` | `"1:1"`, `"16:9"`, `"9:16"`, `"4:3"` |
| `style` | string | `null` | `"photorealistic"`, `"digital_art"`, `"anime"` 등 |
| `quality` | string | `"high"` | `"auto"`, `"low"`, `"medium"`, `"high"` |
| `output_format` | string | `"png"` | `"png"`, `"jpeg"`, `"webp"` |
| `candidate_count` | int | `1` | 생성할 이미지 수 (1-4) |

### 2. `nanobanana_edit` - 이미지 편집

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `image_path` | **필수** string | - | 편집할 이미지 파일 경로 |
| `edit_prompt` | **필수** string | - | 편집 지시사항 |
| `mask_path` | string | `null` | 편집 영역 지정 마스크 (선택) |

### 3. `nanobanana_blend` - 이미지 블렌딩

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `image_paths` | **필수** array | - | 블렌딩할 이미지 경로들 (2-4개) |
| `blend_prompt` | **필수** string | - | 블렌딩 지시사항 |
| `maintain_consistency` | bool | `true` | 캐릭터 일관성 유지 여부 |

### 4. `nanobanana_status` - 상태 확인

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `detailed` | bool | `true` | 상세 정보 포함 여부 |
| `include_history` | bool | `false` | 사용 히스토리 포함 |
| `reset_stats` | bool | `false` | 통계 초기화 여부 |

---

## 🎨 스타일 & 비율 가이드

### 🎨 지원 스타일

| 스타일 | 키워드 | 특징 |
|--------|--------|------|
| `photorealistic` | 사실적, 포토 | 실제 사진 같은 사실적 스타일 |
| `digital_art` | 디지털아트 | 디지털 일러스트레이션 |
| `anime` | 아니메, 만화 | 일본 애니메이션 스타일 |
| `oil_painting` | 유화 | 전통 유화 스타일 |
| `watercolor` | 수채화 | 부드러운 수채화 스타일 |
| `sketch` | 스케치 | 연필 스케치 스타일 |

### 📏 종횡비 옵션

| 비율 | 용도 | 예시 |
|------|------|------|
| `1:1` | 정사각형, SNS 포스트 | Instagram 피드 |
| `16:9` | 가로형, 배경화면 | 유튜브 썸네일 |
| `9:16` | 세로형, 스토리 | 스마트폰 배경 |
| `4:3` | 전통 사진 비율 | 프레젠테이션 |

---

## 📁 출력 구조

생성된 이미지들은 다음과 같이 저장됩니다:

```
outputs/
├── generated/     # 생성된 이미지
├── edited/        # 편집된 이미지  
├── blended/       # 블렌딩된 이미지
└── metadata.json  # 메타데이터
```

각 이미지와 함께 다음 정보가 포함됩니다:
- 원본/최적화 프롬프트
- 생성 시간 및 비용
- 사용된 모델과 설정값
- 파일 크기 및 형식

---

## 🔧 문제해결

### 일반적인 문제

#### ❌ 서버가 즉시 종료됨
**원인**: API 키가 설정되지 않았거나 잘못됨

**해결책**:
1. `claude_desktop_config.json`에서 `GEMINI_API_KEY` 확인
2. [Google AI Studio](https://aistudio.google.com/app/apikey)에서 유효한 키 발급
3. Claude Desktop 재시작

#### ❌ `Input validation error`
**원인**: MCP 서버가 새로운 코드를 반영하지 못함

**해결책**:
1. Claude Desktop에서 `/mcp` 명령 실행
2. 또는 Claude Desktop 완전 재시작

#### ❌ 이미지가 표시되지 않음
**원인**: MCP 응답 형식 문제 또는 파일 경로 오류

**해결책**:
1. 이미지 경로가 올바른지 확인 (절대/상대 경로)
2. 서버 작업 디렉토리(`cwd`) 설정 확인
3. 파일 권한 및 존재 여부 확인

#### ❌ Windows에서 pipx 실행 불가
**해결책**:
```bash
pipx ensurepath
# 터미널 재시작 후 다시 시도
```

### 디버깅 모드

상세한 로그를 보려면:

```bash
# 환경변수 설정 후 실행
NANOBANANA_LOG_LEVEL=DEBUG nanobanana-mcp
```

또는 설정 파일에서:

```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "nanobanana-mcp",
      "env": {
        "GEMINI_API_KEY": "your-key",
        "NANOBANANA_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

---

## 🔄 업데이트

### 패키지 업데이트

```bash
# pip 사용자
pip install --upgrade nanobanana-mcp

# pipx 사용자  
pipx upgrade nanobanana-mcp
```

### 주요 변경사항 확인

- [CHANGELOG.md](CHANGELOG.md) - 버전별 변경사항
- [GitHub Releases](https://github.com/volition79/nanobananaMCP/releases) - 공식 릴리스

---

## 📚 참고 자료

### 공식 문서
- [Gemini API 문서](https://ai.google.dev/gemini-api/docs/models)
- [Model Context Protocol](https://github.com/modelcontextprotocol/specification)
- [Claude Code MCP 가이드](https://docs.anthropic.com/en/docs/build-with-claude/mcp)

### 커뮤니티
- [GitHub Issues](https://github.com/volition79/nanobananaMCP/issues) - 버그 리포트 및 기능 요청
- [GitHub Discussions](https://github.com/volition79/nanobananaMCP/discussions) - 질문 및 토론

---

## 🤝 기여하기

1. **Fork** 이 리포지토리
2. **브랜치 생성**: `git checkout -b feature/amazing-feature`
3. **변경사항 커밋**: `git commit -m 'Add amazing feature'`  
4. **브랜치 푸시**: `git push origin feature/amazing-feature`
5. **Pull Request 생성**

### 개발 환경 설정

```bash
# 리포지토리 클론
git clone https://github.com/volition79/nanobananaMCP.git
cd nanobananaMCP

# 개발 의존성 설치
pip install -e ".[dev]"

# 테스트 실행
pytest

# 코드 포맷팅
black src/ tests/
isort src/ tests/

# 타입 검사
mypy src/
```

---

## 📄 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)하에 배포됩니다.

```
MIT License


Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```


**🍌 나노바나나 MCP로 창의성의 새로운 차원을 경험하세요! 🍌**


