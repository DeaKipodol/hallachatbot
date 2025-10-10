# Phase 3.1: routes.py 분석 및 매핑

> **목표**: routes.py의 각 섹션을 분류하고 stream.py 메서드와 매핑 확인

**작성일**: 2025-10-10  
**백업 파일**: `api/routes.backup.py` ✅

---

## 📊 routes.py 섹션 분석 (총 439줄)

### 1. Import 섹션 (1-11줄)

```python
import asyncio              # ❌ 제거 예정 (stream.py에서 처리)
import os                   # ❌ 제거 예정 (config.py에서 처리)
from openai import OpenAI   # ❌ 제거 예정 (stream.py에서 사용)
from fastapi import APIRouter, HTTPException  # ✅ APIRouter만 유지
from pydantic import BaseModel  # ✅ 유지
from dotenv import load_dotenv  # ❌ 제거 예정 (config.py에서 처리)
from fastapi.responses import StreamingResponse  # ✅ 유지
from app.ai.chatbot.stream import ChatbotStream  # ✅ 유지
from app.ai.functions.analyzer import tools, FunctionCalling  # ❌ 제거 예정
from app.ai.chatbot.config import model  # ✅ 유지
import json  # ❌ 제거 예정 (stream.py에서 처리)
```

**결정**:
- **유지 (6개)**: `APIRouter`, `BaseModel`, `StreamingResponse`, `ChatbotStream`, `model`
- **제거 (6개)**: `asyncio`, `os`, `OpenAI`, `load_dotenv`, `tools`, `FunctionCalling`, `json`

---

### 2. 설정/초기화 섹션 (12-45줄)

```python
# 14-16줄: UserRequest 스키마 ✅ 유지
class UserRequest(BaseModel):
    message: str
    language: str = "KOR"

# 18-23줄: FunctionCalling 초기화 ❌ 제거 (stream.py에서 처리)
func_calling = FunctionCalling(
    model=model.basic,
    available_functions={...}
)

# 24줄: APIRouter ✅ 유지
router = APIRouter()

# 26-28줄: 환경 변수 로딩 ❌ 제거 (config.py에서 처리)
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 30-42줄: ChatbotStream 인스턴스 ✅ 유지 (포맷팅 개선)
chatbot = ChatbotStream(
    model=model.advanced,
    system_role="""...""",
    instruction="...",
    user="한라대 대학생",
    assistant="memmo"
)

# 44-46줄: Message 스키마 ❌ 제거 (사용 안 함)
class Message(BaseModel):
    message: str
```

**결정**:
- **유지**: `UserRequest`, `router`, `chatbot` 인스턴스
- **제거**: `func_calling`, 환경 변수 로딩, `Message` 클래스

---

### 3. /chat 엔드포인트 (48-439줄, 총 391줄)

#### 3.1. 사용자 메시지 추가 (50-51줄)
```python
# 1) 사용자 메시지를 원본 문맥에 추가
chatbot.add_user_message_in_context(user_input.message)
```
**→ stream.py 매핑**: `stream_chat()` 내부 1단계 ✅

---

#### 3.2. 언어별 지침 추가 (53-63줄)
```python
# 2) 언어 지침 추가
instruction_map = {
    "KOR": "한국어로 정중하고 따뜻하게 답해주세요.",
    "ENG": "Please respond kindly in English.",
    # ... 8개 언어
}
instruction = instruction_map.get(user_input.language, instruction_map["KOR"])
chatbot.context[-1]["content"] += " " + instruction
```
**→ stream.py 매핑**: `_get_language_instruction()` + `stream_chat()` 2단계 ✅

---

#### 3.3. RAG 컨텍스트 준비 (65-200줄, 약 135줄)
```python
# 3) RAG 컨텍스트 준비 (RagService 경유)
rag_result = chatbot.rag_service.build_context(user_input.message)
rag_ctx = rag_result.context_text
has_rag = bool(rag_ctx and rag_ctx.strip())

# ... 176-200줄: condense_prompt로 요약
```
**→ stream.py 매핑**: `stream_chat()` 3단계 + `_condense_rag_context()` ✅

---

#### 3.4. 함수 호출 분석/실행 (78-129줄, 약 51줄)
```python
# 4) 함수 호출 분석 및 실행
analyzed = func_calling.analyze(user_input.message, tools)
func_msgs: list[dict] = []
func_outputs: list[str] = []

for tool_call in analyzed:
    if getattr(tool_call, "type", None) != "function_call":
        continue
    # ... 함수 실행 로직
```
**→ stream.py 매핑**: `_analyze_and_execute_functions()` 일부 ✅

---

#### 3.5. 학식 fallback 로직 (131-173줄, 약 42줄)
```python
# 4-1) 학식/식단 질의 보강 호출 (LLM 누락 대비)
lowered = user_input.message.lower()
cafeteria_keywords = any(k in lowered for k in ["학식", "식단", ...])
already_called_cafeteria = ...

if cafeteria_keywords and not already_called_cafeteria:
    # ... 날짜/끼니 추출 및 실행
```
**→ stream.py 매핑**: `_analyze_and_execute_functions()` 학식 fallback 부분 ✅

---

#### 3.6. 최종 컨텍스트 구성 (175-410줄, 약 235줄)
```python
# 5) 최종 스트리밍에 사용할 컨텍스트 구성
base_context = chatbot.to_openai_context(chatbot.context[:])
temp_context = base_context[:]

sections: list[str] = []

# 5-1) 기억검색 결과 요약 (176-296줄)
if has_rag:
    condense_prompt = [...]
    # LLM으로 요약

# 5-2) 섹션 구성 (298-410줄)
sections.append("[사용자쿼리지침]...")
sections.append("[일반지침]...")
sections.append("[기억검색지침]...")
sections.append("[웹검색지침]...")
# ...
```
**→ stream.py 매핑**: 
- 요약: `_condense_rag_context()` ✅
- 섹션 구성: `_build_final_context()` ✅

---

#### 3.7. 스트리밍 응답 생성 (412-439줄, 약 27줄)
```python
# 6) 스트리밍 응답 생성
async def generate_with_tool():
    stream = client.responses.create(
        model=chatbot.model,
        input=temp_context,
        # ...
    )
    
    for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta
            completed += event.delta
        # ...
    
    chatbot.add_response_stream(completed)

return StreamingResponse(generate_with_tool(), media_type="text/plain")
```
**→ stream.py 매핑**: `_stream_openai_response()` + `stream_chat()` 6-9단계 ✅

---

## ✅ stream.py 메서드 매핑 검증

| routes.py 섹션 | 라인 범위 | stream.py 메서드 | 상태 |
|---------------|----------|------------------|------|
| 사용자 메시지 추가 | 50-51 | `stream_chat()` 1단계 | ✅ |
| 언어별 지침 | 53-63 | `_get_language_instruction()` | ✅ |
| RAG 준비 | 65-75 | `stream_chat()` 3단계 | ✅ |
| RAG 요약 | 176-296 | `_condense_rag_context()` | ✅ |
| 함수 호출 분석 | 78-129 | `_analyze_and_execute_functions()` | ✅ |
| 학식 fallback | 131-173 | `_analyze_and_execute_functions()` | ✅ |
| 컨텍스트 구성 | 298-410 | `_build_final_context()` | ✅ |
| 스트리밍 | 412-439 | `_stream_openai_response()` | ✅ |

**결론: 모든 로직이 stream.py에 구현되어 있음! ✅**

---

## 🔍 누락된 로직 확인

### 1. 검색 완료
- ✅ 모든 비즈니스 로직이 stream.py에 이미 구현됨
- ✅ routes.py만의 고유 로직 없음 (라우팅 역할만)

### 2. 추가 확인 사항

**routes.py에만 있는 코드**:
1. ❌ `client = OpenAI(api_key=...)` → stream.py/config.py로 이동됨
2. ❌ `func_calling` 인스턴스 → stream.py `__init__`에서 생성
3. ✅ `router = APIRouter()` → 유지 필요
4. ✅ `chatbot` 인스턴스 생성 → 유지 필요

---

## 📋 Phase 3.1 완료 체크리스트

- [x] routes.py 백업 생성 (`routes.backup.py`)
- [x] routes.py 섹션별 분류 완료
  - [x] Import 섹션 (11줄)
  - [x] 설정/초기화 (34줄)
  - [x] /chat 엔드포인트 (391줄)
- [x] stream.py 메서드 매핑 확인
  - [x] 8개 주요 섹션 → stream.py 메서드 완벽 매칭
- [x] 누락된 로직 없음 확인
- [x] routes.py 고유 로직 식별 (`router`, `chatbot` 인스턴스만)

---

## 🎯 다음 단계: Phase 3.2

**Import 정리 작업**:
1. 불필요한 import 6개 제거
2. 필요한 import 6개만 유지
3. import 순서 정리 (표준 라이브러리 → 서드파티 → 로컬)

**예상 결과**:
```python
# Before: 11줄
# After: 6줄 (5줄 감축)
```
