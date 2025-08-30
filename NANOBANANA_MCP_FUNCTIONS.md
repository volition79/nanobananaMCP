# 나노바나나 MCP 기능 목록

Claude Code에서 나노바나나 MCP 서버를 통해 실행 가능한 모든 기능들의 상세 가이드입니다.

## 📋 개요

**나노바나나 MCP 서버**는 Google의 Gemini 2.5 Flash Image (코드네임: "나노바나나")를 Claude Code에서 사용할 수 있게 하는 Model Context Protocol (MCP) 서버입니다.

- **모델**: `gemini-2.5-flash-image-preview`
- **기본 해상도**: 1024×1024 픽셀
- **지원 형식**: PNG, JPEG, WebP
- **비용**: 이미지당 약 $0.039 (1290 토큰)

---

## 🛠️ 사용 가능한 MCP 도구 (4개)

### 1. `nanobanana_generate` - 이미지 생성
텍스트 프롬프트로부터 새로운 이미지를 생성합니다.

#### 📝 사용법
```
나노바나나로 [설명] 이미지 생성해줘
```

#### 🔧 파라미터
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `prompt` | **필수** string | - | 이미지 생성을 위한 텍스트 설명 (3-2000자) |
| `aspect_ratio` | 선택 string | `null` | 이미지 비율 (`"1:1"`, `"16:9"`, `"9:16"`, `"4:3"`, `"21:9"`) |
| `style` | 선택 string | `null` | 스타일 (`"photorealistic"`, `"digital_art"`, `"anime"`, `"cartoon"` 등) |
| `quality` | 선택 string | `"high"` | 품질 (`"auto"`, `"low"`, `"medium"`, `"high"`) |
| `output_format` | 선택 string | `"png"` | 출력 형식 (`"png"`, `"jpeg"`, `"webp"`) |
| `candidate_count` | 선택 int | `1` | 생성할 이미지 수 (1-4개) |
| `additional_keywords` | 선택 array | `[]` | 추가 키워드 리스트 |
| `optimize_prompt` | 선택 bool | `true` | 프롬프트 자동 최적화 여부 |

#### 💡 사용 예시
```
# 기본 생성
나노바나나로 귀여운 고양이 그려줘

# 상세한 옵션 지정
나노바나나로 일몰이 지는 산 위의 성을 사실적인 스타일로 16:9 비율로 생성해줘

# 여러 개 생성
나노바나나로 미래도시 이미지를 3개 생성해줘
```

---

### 2. `nanobanana_edit` - 이미지 편집
기존 이미지를 자연어 명령으로 편집합니다.

#### 📝 사용법
```
나노바나나로 [이미지 경로]를 [편집 지시사항]으로 편집해줘
```

#### 🔧 파라미터
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `image_path` | **필수** string | - | 편집할 이미지 파일의 절대/상대 경로 |
| `edit_prompt` | **필수** string | - | 편집 지시사항 (3-2000자) |
| `mask_path` | 선택 string | `null` | 마스크 이미지 경로 (편집 영역 지정) |
| `output_format` | 선택 string | `"png"` | 출력 형식 (`"png"`, `"jpeg"`, `"webp"`) |
| `quality` | 선택 string | `"high"` | 출력 품질 |
| `optimize_prompt` | 선택 bool | `true` | 프롬프트 자동 최적화 여부 |

#### 💡 사용 예시
```
# 배경 변경
나노바나나로 "./cat.png"의 배경을 바다로 바꿔줘

# 색상 변경
나노바나나로 이 이미지의 차를 빨간색으로 바꿔줘

# 객체 추가
나노바나나로 이 풍경에 무지개를 추가해줘
```

---

### 3. `nanobanana_blend` - 이미지 블렌딩
여러 이미지를 합성하여 새로운 이미지를 생성합니다.

#### 📝 사용법
```
나노바나나로 [이미지1, 이미지2, ...]를 [합성 지시사항]으로 블렌딩해줘
```

#### 🔧 파라미터
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `image_paths` | **필수** array | - | 블렌딩할 이미지 경로들 (2-4개) |
| `blend_prompt` | **필수** string | - | 블렌딩 지시사항 (3-2000자) |
| `maintain_consistency` | 선택 bool | `true` | 캐릭터/객체 일관성 유지 여부 |
| `output_format` | 선택 string | `"png"` | 출력 형식 |
| `quality` | 선택 string | `"high"` | 출력 품질 |
| `optimize_prompt` | 선택 bool | `true` | 프롬프트 자동 최적화 여부 |

#### 💡 사용 예시
```
# 풍경 합성
나노바나나로 ["./mountain.jpg", "./castle.png"]를 환상적인 풍경으로 블렌딩해줘

# 캐릭터 합성
나노바나나로 여러 이미지를 하나의 장면으로 합성해줘

# 스타일 믹스
나노바나나로 이 두 이미지의 스타일을 섞어서 새로운 작품을 만들어줘
```

---

### 4. `nanobanana_status` - 서버 상태 확인
MCP 서버와 Gemini API의 연결 상태를 확인합니다.

#### 📝 사용법
```
나노바나나 상태 확인해줘
```

#### 🔧 파라미터
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `detailed` | 선택 bool | `true` | 상세 정보 포함 여부 |
| `include_history` | 선택 bool | `false` | 사용 히스토리 포함 여부 |
| `reset_stats` | 선택 bool | `false` | 통계 초기화 여부 |

#### 💡 사용 예시
```
# 기본 상태 확인
나노바나나 상태 확인해줘

# 상세 정보 포함
나노바나나 서버 상태와 통계를 자세히 보여줘

# 히스토리 포함
나노바나나 상태와 사용 기록을 보여줘
```

---

## 🎨 스타일 프리셋

나노바나나 MCP에서 사용할 수 있는 스타일 프리셋들:

| 스타일 | 키워드 | 설명 |
|--------|--------|------|
| `photorealistic` | 사실적, 포토리얼리스틱 | 실제 사진과 같은 사실적인 스타일 |
| `digital_art` | 디지털아트, 컨셉아트 | 디지털 일러스트레이션 스타일 |
| `oil_painting` | 유화, 클래식 | 전통적인 유화 스타일 |
| `watercolor` | 수채화, 부드러운 | 수채화 스타일 |
| `cartoon` | 만화, 애니메이션 | 카툰/애니메이션 스타일 |
| `anime` | 아니메, 망가 | 일본 애니메이션 스타일 |
| `sketch` | 스케치, 연필그림 | 연필 스케치 스타일 |
| `vintage` | 빈티지, 레트로 | 빈티지/레트로 스타일 |

## 📐 종횡비 프리셋

| 비율 | 키워드 | 용도 |
|------|--------|------|
| `1:1` | `square` | 정사각형 (Instagram 포스트) |
| `16:9` | `landscape` | 가로형 (유튜브 썸네일, 배경화면) |
| `9:16` | `portrait`, `story` | 세로형 (Instagram 스토리, 폰 배경) |
| `4:3` | `photo` | 전통적인 사진 비율 |
| `21:9` | `widescreen` | 울트라와이드 |
| `2.39:1` | `cinema` | 영화관 스크린 |
| `3:1` | `banner` | 배너/헤더 |

## 📊 출력 정보

모든 성공적인 요청은 다음 정보를 반환합니다:

```json
{
  "success": true,
  "message": "Successfully generated 1 image(s)",
  "images": [
    {
      "filename": "nanobanana_generated_20250830_153915_2d770c62.png",
      "filepath": "outputs/generated/nanobanana_generated_20250830_153915_2d770c62.png",
      "operation_type": "generated",
      "created_at": "2025-08-30T15:39:15.279160",
      "file_size": 1435445,
      "format": "png",
      "prompt": "원본 프롬프트",
      "optimized_prompt": "최적화된 프롬프트",
      "model_used": "gemini-2.5-flash-image-preview",
      "generation_time": 8.24,
      "cost_usd": 0.039
    }
  ],
  "total_cost": 0.039,
  "generation_time": 10.14
}
```

## 📁 파일 구조

생성된 이미지들은 다음과 같이 정리됩니다:

```
outputs/
├── generated/     # nanobanana_generate로 생성된 이미지
├── edited/        # nanobanana_edit로 편집된 이미지
├── blended/       # nanobanana_blend로 합성된 이미지
└── metadata.json  # 모든 이미지의 메타데이터
```

## ⚠️ 주의사항 및 제한사항

### 🚫 제한사항
- **프롬프트 길이**: 3-2000자
- **이미지 수**: 요청당 최대 4개
- **파일 크기**: 이미지당 최대 20MB
- **동시 요청**: 최대 3개
- **블렌딩**: 2-4개 이미지만 가능

### ⚡ 성능 최적화
- **영어 프롬프트**: 더 정확한 결과를 위해 영어 사용 권장
- **구체적 설명**: 상세하고 구체적인 프롬프트일수록 좋은 결과
- **스타일 지정**: 명확한 스타일 프리셋 사용으로 일관된 결과
- **비율 지정**: 용도에 맞는 종횡비 선택

### 🔐 안전성
- **금지 키워드**: NSFW, 폭력, 혐오 표현 등은 자동 필터링
- **메타데이터 정리**: 생성된 이미지는 호환성을 위해 메타데이터 정리
- **Base64 처리**: URL-safe Base64 자동 변환 지원

## 🛠️ 문제 해결

### 자주 발생하는 문제들

1. **`Input validation error`**: MCP 서버 재시작 필요 (`/mcp` 명령 실행)
2. **이미지가 열리지 않음**: Pillow 재처리를 통해 호환성 개선됨
3. **API 키 오류**: `.env` 파일이나 MCP 설정에서 `GEMINI_API_KEY` 확인
4. **생성 실패**: 프롬프트에 금지된 키워드가 포함되어 있는지 확인

### 디버깅 도구
나노바나나 MCP는 이미지 진단 도구를 내장하고 있어, 문제 발생 시 자동으로 상세한 디버그 정보를 제공합니다.

---

## 📞 지원 및 피드백

문제 발생 시:
1. `/mcp` 명령으로 서버 재시작
2. 로그 확인: `./logs/nanobanana_mcp.log`
3. 진단 도구 활용: `nanobanana_status` 실행

**버전**: 1.0.0  
**최종 업데이트**: 2025-08-30  
**작성자**: Claude Code Assistant