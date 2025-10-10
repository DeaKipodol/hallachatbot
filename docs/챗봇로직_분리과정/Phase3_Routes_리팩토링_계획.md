# Phase 3: routes.py 리팩토링 계획 🚀

> **목표**: routes.py의 439줄 복잡한 챗봇 로직을 ChatbotStream.stream_chat()으로 완전히 위임하여 10줄 미만의 단순한 라우터로 리팩토링

**작성일**: 2025-10-10  
**상태**: 준비 단계  
**선행 작업**: Phase 2 완료 (모든 헬퍼 메서드 구현 완료)

---

## 📊 현재 상태 분석

### 1. routes.py 현황

```
파일 위치: /Users/kimdaegi/Desktop/backend/app/api/routes.py
총 라인 수: 439줄
주요 구성:
  - Import: 11줄
  - 설정/초기화: 25줄
  - /chat 엔드포인트: 403줄 (전체의 92%)
```

### 2. Phase 2 완료 상태

✅ **모든 헬퍼 메서드 구현 완료**
- `_get_language_instruction()` - 8개 언어 지원
- `_condense_rag_context()` - RAG 컨텍스트 요약 (2단계 재시도)
- `_analyze_and_execute_functions()` - 함수 호출 + 학식 fallback
- `_build_final_context()` - 7섹션 컨텍스트 구성
- `_stream_openai_response()` - OpenAI 스트리밍
- `stream_chat()` - 통합 메서드 (9단계 플로우)

✅ **메타데이터 클래스 완성**
- `RagMetadata` - RAG 검색 정보
- `FunctionCallMetadata` - 함수 호출 정보
- `ChatMetadata` - 전체 메타데이터 컨테이너

---

## 🎯 리팩토링 목표

### Before (현재 - 439줄)

```python
@router.post("/chat")
async def stream_chat(user_input: UserRequest):
    # 1. 사용자 메시지 추가 (5줄)
    chatbot.add_user_message_in_context(user_input.message)
    
    # 2. 언어별 지침 추가 (10줄)
    instruction_map = {...}
    chatbot.context[-1]["content"] += " " + instruction
    
    # 3. RAG 컨텍스트 준비 (80줄)
    rag_result = chatbot.rag_service.build_context(...)
    # ... 긴 요약 로직 ...
    
    # 4. 함수 호출 분석/실행 (120줄)
    analyzed = func_calling.analyze(...)
    # ... 함수 실행 로직 ...
    
    # 5. 학식 보강 로직 (40줄)
    # ... fallback 로직 ...
    
    # 6. 최종 컨텍스트 구성 (160줄)
    sections = []
    # ... 7개 섹션 조립 ...
    
    # 7. 스트리밍 응답 생성 (60줄)
    async def generate_with_tool():
        # ... 스트리밍 로직 ...
    
    return StreamingResponse(generate_with_tool(), ...)
```

### After (목표 - ~15줄)

```python
@router.post("/chat")
async def stream_chat(user_input: UserRequest):
    """챗봇 스트리밍 엔드포인트"""
    return StreamingResponse(
        chatbot.stream_chat(
            message=user_input.message,
            language=user_input.language
        ),
        media_type="application/x-ndjson"
    )
```

**감축률: 97% (439줄 → 15줄)**

---

## 📋 리팩토링 단계별 계획

### Phase 3.1: 현재 routes.py 로직 분석 및 백업

**목표**: 기존 로직을 완전히 이해하고 안전하게 백업

- [ ] routes.py 전체 로직 섹션별 분류
  - [ ] Import 섹션 (1-11줄)
  - [ ] 설정/초기화 섹션 (12-45줄)
  - [ ] /chat 엔드포인트 (46-439줄)
    - [ ] 2.1. 사용자 메시지 추가 (50-51줄)
    - [ ] 2.2. 언어별 지침 (52-62줄)
    - [ ] 2.3. RAG 준비 (63-145줄)
    - [ ] 2.4. 함수 호출 (146-268줄)
    - [ ] 2.5. 학식 fallback (269-310줄)
    - [ ] 2.6. 컨텍스트 구성 (311-410줄)
    - [ ] 2.7. 스트리밍 (411-439줄)

- [ ] routes.py 백업 생성
  ```bash
  cp api/routes.py api/routes.backup.py
  ```

- [ ] 각 섹션별 stream.py 메서드 매핑 확인
  ```
  routes.py 로직          → stream.py 메서드
  ================================================
  언어별 지침            → _get_language_instruction()
  RAG 준비 + 요약        → _condense_rag_context()
  함수 호출 + fallback   → _analyze_and_execute_functions()
  컨텍스트 구성          → _build_final_context()
  스트리밍              → _stream_openai_response()
  전체 통합             → stream_chat()
  ```

**검증 포인트**:
- ✅ 모든 로직이 stream.py에 이미 구현되어 있는지 확인
- ✅ 누락된 로직이 없는지 확인
- ✅ routes.py만의 고유 로직 식별 (있다면 stream.py로 이동)

---

### Phase 3.2: Import 정리

**목표**: 불필요한 import 제거, 필요한 import만 유지

**Before (11줄)**:
```python
import asyncio
import os
from openai import OpenAI
from fastapi import APIRouter, HTTPException 
from pydantic import BaseModel
from dotenv import load_dotenv  
from fastapi.responses import StreamingResponse
from app.ai.chatbot.stream import ChatbotStream
from app.ai.functions.analyzer import tools, FunctionCalling
from app.ai.chatbot.config import model
import json
```

**After (6줄)**:
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ai.chatbot.stream import ChatbotStream
from app.ai.chatbot.config import model
```

**제거할 import**:
- ❌ `asyncio` - stream.py에서 처리
- ❌ `os`, `load_dotenv` - config.py에서 처리
- ❌ `OpenAI`, `client` - stream.py에서 사용
- ❌ `tools`, `FunctionCalling` - stream.py 내부에서 처리
- ❌ `json` - stream.py에서 처리
- ❌ `HTTPException` - 현재 사용 안 함

**유지할 import**:
- ✅ `APIRouter` - 라우터 정의용
- ✅ `StreamingResponse` - 응답 타입
- ✅ `BaseModel` - 요청 스키마
- ✅ `ChatbotStream` - 챗봇 인스턴스
- ✅ `model` - 챗봇 초기화용

---

### Phase 3.3: FunctionCalling 초기화 이동

**목표**: FunctionCalling 초기화를 ChatbotStream 내부로 이동

**현재 routes.py (불필요)**:
```python
func_calling = FunctionCalling(
    model=model.basic,
    available_functions={
        # 필요시 다른 함수도 여기에 추가
    }
)
```

**이미 stream.py에 구현됨**:
```python
class ChatbotStream:
    def __init__(self, model, system_role, instruction, **kwargs):
        # ... 기존 코드 ...
        
        # Phase 2: 함수 호출 관련 인스턴스화
        self.func_calling = FunctionCalling(model=model)
        self.tools = tools
        self.available_functions = self.func_calling.available_functions
```

**조치**:
- [ ] routes.py에서 `func_calling` 초기화 제거
- [ ] stream.py의 `__init__`에서 이미 처리 중임을 확인

---

### Phase 3.4: 챗봇 인스턴스 생성 단순화

**목표**: 챗봇 초기화를 더 명확하게 정리

**Before**:
```python
chatbot = ChatbotStream(
    model=model.advanced,
    system_role="""당신은 학교 생활, 학과 정보, 행사 등 사용자가 궁금한 점이 있으면 아는 범위 안에서 대답합니다. 단 절대 거짓내용을 말하지 않습니다. 아는 범위에서 말하고 부족한 부분은 인정하세요.
    당신은 실시간으로 검색하는 기능이있습니다.
    당신은 한라대 공지사항을 탐색할 수 있습니다.
    당신은 한라대 학식메뉴를 탐색할 수 있습니다.
    당신은 한라대 학사일정을 탐색할 수 있습니다.""",
    instruction="당신은 사용자의 질문에 답변하는 역할을 합니다.",
    user="한라대 대학생",
    assistant="memmo"
)
```

**After (포맷팅 개선)**:
```python
# 챗봇 인스턴스 생성
chatbot = ChatbotStream(
    model=model.advanced,
    system_role=(
        "당신은 학교 생활, 학과 정보, 행사 등 사용자가 궁금한 점이 있으면 "
        "아는 범위 안에서 대답합니다. 단 절대 거짓내용을 말하지 않습니다. "
        "아는 범위에서 말하고 부족한 부분은 인정하세요.\n"
        "당신은 실시간으로 검색하는 기능이있습니다.\n"
        "당신은 한라대 공지사항을 탐색할 수 있습니다.\n"
        "당신은 한라대 학식메뉴를 탐색할 수 있습니다.\n"
        "당신은 한라대 학사일정을 탐색할 수 있습니다."
    ),
    instruction="당신은 사용자의 질문에 답변하는 역할을 합니다.",
    user="한라대 대학생",
    assistant="memmo"
)
```

---

### Phase 3.5: /chat 엔드포인트 리팩토링

**목표**: 403줄의 복잡한 로직을 stream_chat() 호출로 대체

**Before (403줄)**:
```python
@router.post("/chat")
async def stream_chat(user_input: UserRequest):
    # 1) 사용자 메시지를 원본 문맥에 추가
    chatbot.add_user_message_in_context(user_input.message)

    # 2) 언어 지침 추가
    instruction_map = {...}
    instruction = instruction_map.get(user_input.language, instruction_map["KOR"])
    chatbot.context[-1]["content"] += " " + instruction

    # 3) RAG 컨텍스트 준비 (80줄)
    # ...

    # 4) 함수 호출 분석 및 실행 (120줄)
    # ...

    # 5) 학식 보강 로직 (40줄)
    # ...

    # 6) 최종 컨텍스트 구성 (160줄)
    # ...

    # 7) 스트리밍 응답 생성 (60줄)
    # ...

    return StreamingResponse(generate_with_tool(), media_type="text/plain")
```

**After (8줄)**:
```python
@router.post("/chat")
async def stream_chat(user_input: UserRequest):
    """챗봇 스트리밍 엔드포인트
    
    JSON Lines 형식으로 응답을 스트리밍합니다:
    - {"type": "delta", "content": "..."} - 실시간 텍스트
    - {"type": "metadata", "data": {...}} - RAG/함수 호출 메타데이터
    - {"type": "done"} - 완료 신호
    """
    return StreamingResponse(
        chatbot.stream_chat(
            message=user_input.message,
            language=user_input.language
        ),
        media_type="application/x-ndjson"  # JSON Lines 형식
    )
```

**주요 변경사항**:
1. ✅ 모든 로직을 `chatbot.stream_chat()`에 위임
2. ✅ `media_type`을 `text/plain` → `application/x-ndjson`로 변경
3. ✅ Docstring 추가로 API 명세 문서화

---

### Phase 3.6: 응답 포맷 변경 확인

**목표**: 프론트엔드가 JSON Lines 형식을 올바르게 처리하는지 확인

**이전 응답 (text/plain)**:
```
안녕하세요 졸업 규정에 대해...
```

**새 응답 (application/x-ndjson)**:
```json
{"type": "delta", "content": "안녕하세요"}
{"type": "delta", "content": " 졸업"}
{"type": "delta", "content": " 규정에"}
{"type": "metadata", "data": {"rag": {...}, "functions": [...]}}
{"type": "done"}
```

**프론트엔드 수정 필요사항**:
- [ ] JSON Lines 파싱 로직 추가
- [ ] `delta` 타입 텍스트 누적
- [ ] `metadata` 타입 저장/표시
- [ ] `done` 타입 완료 처리

---

### Phase 3.7: 최종 routes.py 코드

**목표**: 리팩토링 완료 후 최종 코드

```python
"""
챗봇 API 라우터

FastAPI 라우터로 챗봇 스트리밍 엔드포인트를 제공합니다.
모든 비즈니스 로직은 ChatbotStream 클래스에 위임됩니다.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ai.chatbot.stream import ChatbotStream
from app.ai.chatbot.config import model


# ==================== 라우터 설정 ====================

router = APIRouter()


# ==================== 요청/응답 스키마 ====================

class UserRequest(BaseModel):
    """챗봇 요청 스키마"""
    message: str
    language: str = "KOR"  # KOR, ENG, VI, JPN, CHN, UZB, MNG, IDN


# ==================== 챗봇 인스턴스 ====================

chatbot = ChatbotStream(
    model=model.advanced,
    system_role=(
        "당신은 학교 생활, 학과 정보, 행사 등 사용자가 궁금한 점이 있으면 "
        "아는 범위 안에서 대답합니다. 단 절대 거짓내용을 말하지 않습니다. "
        "아는 범위에서 말하고 부족한 부분은 인정하세요.\n"
        "당신은 실시간으로 검색하는 기능이있습니다.\n"
        "당신은 한라대 공지사항을 탐색할 수 있습니다.\n"
        "당신은 한라대 학식메뉴를 탐색할 수 있습니다.\n"
        "당신은 한라대 학사일정을 탐색할 수 있습니다."
    ),
    instruction="당신은 사용자의 질문에 답변하는 역할을 합니다.",
    user="한라대 대학생",
    assistant="memmo"
)


# ==================== 엔드포인트 ====================

@router.post("/chat")
async def stream_chat(user_input: UserRequest):
    """챗봇 스트리밍 엔드포인트
    
    JSON Lines 형식으로 응답을 스트리밍합니다:
    - {"type": "delta", "content": "..."} - 실시간 텍스트 청크
    - {"type": "metadata", "data": {...}} - RAG/함수 호출 메타데이터
    - {"type": "done"} - 완료 신호
    
    Args:
        user_input: 사용자 요청 (message, language)
    
    Returns:
        StreamingResponse: JSON Lines 형식 스트리밍 응답
    """
    return StreamingResponse(
        chatbot.stream_chat(
            message=user_input.message,
            language=user_input.language
        ),
        media_type="application/x-ndjson"
    )
```

**최종 라인 수: 65줄 (주석 포함), 실제 코드 ~40줄**

---

## 🔍 검증 계획

### 3.7.1 단위 테스트

**테스트 파일**: `tests/test_routes.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint_basic():
    """기본 채팅 엔드포인트 테스트"""
    response = client.post(
        "/chat",
        json={"message": "안녕하세요", "language": "KOR"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"

def test_chat_endpoint_language():
    """다국어 지원 테스트"""
    for lang in ["KOR", "ENG", "VI", "JPN", "CHN"]:
        response = client.post(
            "/chat",
            json={"message": "Hello", "language": lang}
        )
        assert response.status_code == 200

def test_chat_endpoint_json_lines():
    """JSON Lines 응답 형식 테스트"""
    response = client.post(
        "/chat",
        json={"message": "졸업 규정", "language": "KOR"}
    )
    
    lines = response.text.strip().split("\n")
    for line in lines:
        data = json.loads(line)
        assert "type" in data
        assert data["type"] in ["delta", "metadata", "done"]
```

### 3.7.2 통합 테스트

- [ ] 일반 질문 테스트
  ```
  입력: "안녕하세요"
  기대: delta 타입 응답, done 신호
  ```

- [ ] RAG 질문 테스트
  ```
  입력: "졸업 규정을 알려주세요"
  기대: delta + metadata(rag) + done
  ```

- [ ] 함수 호출 테스트
  ```
  입력: "오늘 학식 메뉴"
  기대: delta + metadata(functions) + done
  ```

- [ ] 복합 질문 테스트
  ```
  입력: "졸업 규정과 오늘 학식 메뉴"
  기대: delta + metadata(rag + functions) + done
  ```

### 3.7.3 성능 테스트

- [ ] 응답 시간 측정
  - 첫 번째 delta까지 시간: < 1초
  - 전체 응답 완료: < 10초
  
- [ ] 메모리 사용량 확인
  - 스트리밍 중 메모리 누수 없음
  - 큰 컨텍스트 처리 시 안정성

- [ ] 동시 요청 처리
  - 10개 동시 요청 처리
  - 응답 품질 유지

---

## 📊 리팩토링 효과

### Before vs After 비교

| 항목 | Before (현재) | After (목표) | 개선율 |
|-----|--------------|-------------|--------|
| **총 라인 수** | 439줄 | ~40줄 | **91% 감소** |
| **복잡도** | 높음 (7단계 로직) | 낮음 (1줄 호출) | **86% 감소** |
| **결합도** | 강결합 (RAG, 함수 직접 호출) | 약결합 (인터페이스만) | **완전 분리** |
| **재사용성** | 불가능 | 가능 (다른 엔드포인트) | **100% 향상** |
| **테스트** | 어려움 (라우터 레벨만) | 쉬움 (단위 테스트 가능) | **완전 개선** |
| **유지보수** | 어려움 (로직 분산) | 쉬움 (단일 책임) | **100% 향상** |

### 개발자 경험 개선

**Before (복잡)**:
```python
# routes.py에서 챗봇 사용 시
# 1. RAG 서비스 호출
# 2. 함수 호출 분석
# 3. 컨텍스트 구성
# 4. 스트리밍 설정
# ... 총 7단계 이해 필요
```

**After (단순)**:
```python
# routes.py에서 챗봇 사용 시
chatbot.stream_chat(message, language)
# 끝! 1줄로 완료
```

---

## 🚨 주의사항

### 1. 하위 호환성

**문제**: 기존 프론트엔드가 `text/plain` 응답 기대
**해결**:
- [ ] 프론트엔드 JSON Lines 파싱 추가
- [ ] 또는 `media_type` 파라미터로 형식 선택 가능하게

```python
@router.post("/chat")
async def stream_chat(
    user_input: UserRequest,
    response_format: str = "json-lines"  # or "text"
):
    if response_format == "text":
        # 레거시 text/plain 응답
        ...
    else:
        # 새 JSON Lines 응답
        ...
```

### 2. 에러 처리

**문제**: stream_chat() 내부 에러가 라우터에 전파
**해결**:
- [ ] stream.py에서 모든 에러를 `{"type": "error"}` 이벤트로 변환
- [ ] routes.py는 단순히 스트림 반환만

### 3. 로깅

**문제**: 기존 routes.py의 디버그 로그 손실
**해결**:
- [ ] stream.py에서 `self._dbg()` 로깅 강화
- [ ] routes.py에 요청/응답 로깅 추가

```python
@router.post("/chat")
async def stream_chat(user_input: UserRequest):
    logger.info(f"[CHAT] Request: {user_input.message[:50]}...")
    return StreamingResponse(...)
```

---

## 📝 체크리스트

### Phase 3.1: 분석 및 백업
- [ ] routes.py 섹션별 분류 완료
- [ ] routes.backup.py 백업 생성
- [ ] stream.py 메서드 매핑 확인
- [ ] 누락 로직 없음 검증

### Phase 3.2: Import 정리
- [ ] 불필요한 import 11개 → 6개 감소
- [ ] import 오류 없음 확인

### Phase 3.3: FunctionCalling 이동
- [ ] routes.py에서 func_calling 제거
- [ ] stream.py에서 처리 확인

### Phase 3.4: 인스턴스 생성
- [ ] system_role 포맷팅 개선
- [ ] 주석 추가

### Phase 3.5: 엔드포인트 리팩토링
- [ ] /chat 엔드포인트 8줄로 축소
- [ ] stream_chat() 호출 구현
- [ ] Docstring 추가

### Phase 3.6: 응답 포맷
- [ ] media_type JSON Lines 변경
- [ ] 프론트엔드 파싱 로직 확인

### Phase 3.7: 검증
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 실행
- [ ] 성능 테스트 통과

---

## 🎯 성공 기준

### 필수 조건
1. ✅ routes.py 라인 수 90% 이상 감소
2. ✅ 모든 기존 기능 정상 작동
3. ✅ JSON Lines 형식 응답 정상
4. ✅ 메타데이터 정상 전송

### 선택 조건
1. 🎯 프론트엔드 하위 호환성 유지
2. 🎯 성능 저하 없음 (< 10% 허용)
3. 🎯 에러 처리 개선
4. 🎯 로깅 강화

---

## 📅 타임라인

| 단계 | 예상 시간 | 상태 |
|-----|----------|------|
| Phase 3.1 분석/백업 | 30분 | ⏳ 대기 |
| Phase 3.2 Import | 15분 | ⏳ 대기 |
| Phase 3.3 초기화 | 15분 | ⏳ 대기 |
| Phase 3.4 인스턴스 | 15분 | ⏳ 대기 |
| Phase 3.5 엔드포인트 | 30분 | ⏳ 대기 |
| Phase 3.6 응답 포맷 | 30분 | ⏳ 대기 |
| Phase 3.7 검증 | 1시간 | ⏳ 대기 |
| **총 예상 시간** | **3시간** | |

---

## 🔗 관련 문서

- [Phase 2 헬퍼 메서드 구현 계획](./챗봇_로직_분리_계획.md#phase-2-헬퍼-메서드-구현-routespy--streampy)
- [RAG 분리 계획](./RAG_분리_계획.md)
- [stream.py API 문서](../ai/chatbot/stream.py) (구현 완료)
- [metadata.py 구조](../ai/chatbot/metadata.py)

---

## 📌 다음 단계 (Phase 4)

Phase 3 완료 후:
1. **프론트엔드 통합** - JSON Lines 파싱 구현
2. **모니터링 추가** - 응답 시간, 에러율 추적
3. **문서화** - API 명세 Swagger 업데이트
4. **배포** - 운영 환경 적용

---

**작성자**: AI Assistant  
**검토자**: DeaKipodol  
**최종 수정**: 2025-10-10
