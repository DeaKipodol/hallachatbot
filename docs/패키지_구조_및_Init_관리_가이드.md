# 패키지 구조 및 `__init__.py` 관리 가이드

> **작성일**: 2025-01-10  
> **목적**: 프로젝트의 모든 패키지를 분석하고 올바른 `__init__.py` 관리 전략 수립

---

## 📋 목차

1. [패키지 개념 이해](#1-패키지-개념-이해)
2. [프로젝트 전체 패키지 현황](#2-프로젝트-전체-패키지-현황)
3. [패키지화 전략](#3-패키지화-전략)
4. [패키지화하면 안 되는 것들](#4-패키지화하면-안-되는-것들)
5. [작업 우선순위](#5-작업-우선순위)
6. [실전 예제](#6-실전-예제)

---

## 1. 패키지 개념 이해

### 1.1 패키지란?

**정의**: 여러 Python 모듈(`.py` 파일)을 담는 디렉토리로, `__init__.py` 파일이 있으면 Python 패키지로 인식됨

```
ai/
├── __init__.py      ← 이게 있으면 패키지!
├── chatbot/
│   ├── __init__.py
│   └── stream.py
└── rag/
    ├── __init__.py
    └── service.py
```

---

### 1.2 `__init__.py`의 역할

#### **역할 1: 디렉토리를 패키지로 선언**
```python
# 폴더만 있음 → 일반 폴더
docs/
├── README.md

# __init__.py 있음 → 패키지 (import 가능!)
ai/
├── __init__.py
└── chatbot.py
```

#### **역할 2: 공개 API 정의 (노출)**
```python
# ai/rag/__init__.py
from .service import RagService
from .gate import RegulationGate

__all__ = ["RagService", "RegulationGate"]
```

**효과**:
```python
# Before (파일명까지 써야 함)
from ai.rag.service import RagService

# After (패키지명만으로 가능!)
from ai.rag import RagService
```

#### **역할 3: 패키지 초기화**
```python
# ai/__init__.py
print("AI 패키지 로드됨!")
__version__ = "1.0.0"

# 다른 파일에서
import ai  # → "AI 패키지 로드됨!" 출력
```

---

### 1.3 `__all__`의 중요성

**용도**: 와일드카드 import(`*`) 제어 및 공식 API 명시

```python
# ai/rag/__init__.py
from .service import RagService
from .gate import RegulationGate
from ._internal import _helper  # 내부용

__all__ = ["RagService", "RegulationGate"]  # 공개 API만!
```

**효과**:
```python
# routes.py
from ai.rag import *  # RagService, RegulationGate만 import (_helper 제외)
```

---

## 2. 프로젝트 전체 패키지 현황

### 2.1 패키지 트리

```
app/
├── __init__.py                     [상태: 비어있음]
├── api/                            (패키지 아님 - __init__.py 없음)
│   └── routes.py
├── ai/                             ⭐ 신규 모듈
│   ├── __init__.py                 [상태: 문서만]
│   ├── chatbot/
│   │   └── __init__.py             [상태: ✅ 완료]
│   ├── rag/
│   │   └── __init__.py             [상태: ✅ 완료]
│   ├── functions/
│   │   └── __init__.py             [상태: 주석 (작업 예정)]
│   └── data/
│       └── __init__.py             [상태: 주석 (작업 예정)]
├── chatbotDirectory/               🔶 레거시
│   ├── __init__.py                 [상태: 비어있음]
│   └── rag/
│       └── __init__.py             [상태: 비어있음]
├── loding/                         🔶 레거시
│   └── __init__.py                 [상태: 비어있음]
├── tests/
│   └── __init__.py                 [상태: 문서만]
├── docs/                           (패키지 아님 - 문서 폴더)
└── pdfs/                           (패키지 아님 - 데이터 폴더)
```

---

### 2.2 패키지별 상태 분석

| 패키지 | 경로 | `__init__.py` 상태 | 패키지화 필요 | 우선순위 |
|--------|------|-------------------|-------------|---------|
| **app** | `/` | 비어있음 | ❌ 불필요 | - |
| **ai** | `/ai` | 문서만 | ⚠️ 선택 | 낮음 |
| **ai.chatbot** | `/ai/chatbot` | ✅ 완료 | ✅ 필요 | - |
| **ai.rag** | `/ai/rag` | ✅ 완료 | ✅ 필요 | - |
| **ai.functions** | `/ai/functions` | 주석 (작업 예정) | ✅ 필요 | **높음** |
| **ai.data** | `/ai/data` | 주석 (작업 예정) | ✅ 필요 | **높음** |
| **chatbotDirectory** | `/chatbotDirectory` | 비어있음 | ⚠️ 레거시 | 낮음 |
| **chatbotDirectory.rag** | `/chatbotDirectory/rag` | 비어있음 | ⚠️ 레거시 | 낮음 |
| **loding** | `/loding` | 비어있음 | ⚠️ 레거시 | 낮음 |
| **tests** | `/tests` | 문서만 | ⚠️ 선택 | 낮음 |
| **api** | `/api` | 없음 | ❌ 불필요 | - |
| **docs** | `/docs` | 없음 | ❌ 불필요 | - |
| **pdfs** | `/pdfs` | 없음 | ❌ 불필요 | - |

---

## 3. 패키지화 전략

### 3.1 패키지화 해야 하는 것 ✅

#### **기준**:
1. ✅ **여러 모듈을 포함**하는 디렉토리
2. ✅ **다른 파일에서 import**되는 코드
3. ✅ **재사용 가능한** 로직

#### **대상**:

##### **1. `/ai/functions` - 함수 호출 모듈** 🔥 **우선순위 1**

**현재 상태**:
```python
# ai/functions/__init__.py
"""
함수 호출 모듈

웹 검색, 학식 메뉴, 공지사항 등 외부 함수 호출을 관리합니다.
"""

# 추후 여기에 FunctionCalling과 tools를 import하여 노출
# from .analyzer import FunctionCalling  ← 주석 처리됨
# from .tools import tools
```

---

**📍 현재 실제 사용 현황** (프로젝트 전체 검색 결과):

```python
# ❌ 현재: ai/chatbot/stream.py (9번 줄)
from app.ai.functions.analyzer import FunctionCalling, tools
#                     ^^^^^^^^ 파일명까지 써야 함

# ❌ 현재: api/routes.backup.py, api/routes.old.py
from app.ai.functions.analyzer import tools, FunctionCalling
#                     ^^^^^^^^ 파일명까지 써야 함
```

**영향받는 파일**:
- ✅ `ai/chatbot/stream.py` - 핵심 파일 (수정 필요)
- ⚠️ `api/routes.backup.py` - 백업 파일 (수정 선택)
- ⚠️ `api/routes.old.py` - 레거시 파일 (수정 선택)

---

**작업 필요**:
```python
# ai/functions/__init__.py
"""
함수 호출 모듈

웹 검색, 학식 메뉴, 공지사항 등 외부 함수 호출을 관리합니다.
"""

from .analyzer import FunctionCalling, tools

__all__ = ["FunctionCalling", "tools"]
```

---

**개선 후 변경 사항**:

```python
# ai/chatbot/stream.py (수정 전)
from app.ai.functions.analyzer import FunctionCalling, tools
#                     ^^^^^^^^ 파일명

# ai/chatbot/stream.py (수정 후) ✅
from app.ai.functions import FunctionCalling, tools
#                     ^^^^^^^ 패키지명만!
```

**개선 효과**:
1. ✅ **간결함**: 파일명 불필요
2. ✅ **안정성**: `analyzer.py` 파일명 변경되어도 영향 없음
3. ✅ **명확성**: "functions 패키지의 공식 API" 명시

---

##### **2. `/ai/data` - 데이터 처리 모듈** 🔥 **우선순위 2**

**현재 상태**:
```python
# ai/data/__init__.py
"""
데이터 처리 모듈

문서 로딩, MongoDB 연결, 벡터 DB 업로드 등을 담당합니다.
"""

# 추후 여기에 데이터 관련 클래스들을 import하여 노출
# from .mongodb_client import collection  ← 주석 처리됨
# from .vector_uploader import get_embedding, index
```

---

**📍 현재 실제 사용 현황** (프로젝트 전체 검색 결과):

```python
# ❌ 현재: ai/rag/repository.py (9번 줄)
from app.ai.data.mongodb_client import MONGO_AVAILABLE, collection
#              ^^^^^^^^^^^^^^^ 파일명까지

# ❌ 현재: ai/rag/retriever.py (13번 줄)
from app.ai.data.vector_uploader import get_embedding, index
#              ^^^^^^^^^^^^^^^^ 파일명까지
```

**영향받는 파일**:
- ✅ `ai/rag/repository.py` - MongoDB 저장소 (수정 필요)
- ✅ `ai/rag/retriever.py` - Pinecone 검색기 (수정 필요)
- ⚠️ `loding/vector_db_upload.py` - 레거시 업로드 (마이그레이션 대상)

---

**작업 필요**:
```python
# ai/data/__init__.py
"""
데이터 처리 모듈

문서 로딩, MongoDB 연결, 벡터 DB 업로드 등을 담당합니다.
"""

from .mongodb_client import collection, MONGO_AVAILABLE
from .vector_uploader import get_embedding, index

__all__ = ["collection", "MONGO_AVAILABLE", "get_embedding", "index"]
```

---

**개선 후 변경 사항**:

**1️⃣ repository.py 개선**:
```python
# ai/rag/repository.py (수정 전)
from app.ai.data.mongodb_client import MONGO_AVAILABLE, collection
#              ^^^^^^^^^^^^^^^ 파일명

# ai/rag/repository.py (수정 후) ✅
from app.ai.data import MONGO_AVAILABLE, collection
#              ^^^^^^^ 패키지명만!
```

**2️⃣ retriever.py 개선**:
```python
# ai/rag/retriever.py (수정 전)
from app.ai.data.vector_uploader import get_embedding, index
#              ^^^^^^^^^^^^^^^^ 파일명

# ai/rag/retriever.py (수정 후) ✅
from app.ai.data import get_embedding, index
#              ^^^^^^^ 패키지명만!
```

---

**개선 효과**:
1. ✅ **간결함**: 파일명 불필요 (한 줄로 통일)
2. ✅ **안정성**: 파일 구조 변경되어도 영향 없음
3. ✅ **일관성**: RAG 모듈 전체 import 스타일 통일
4. ✅ **명확성**: "data 패키지의 공식 API" 명시

**리팩토링 예시**:
```python
# Before: 파일별로 흩어져 있음
from app.ai.data.mongodb_client import collection
from app.ai.data.vector_uploader import get_embedding

# After: 한 줄로 통합 ✅
from app.ai.data import collection, get_embedding
```

---

##### **3. `/ai` - AI 통합 패키지** ⚠️ **선택 사항**

**현재 상태**:
```python
# ai/__init__.py
"""AI 관련 모듈 통합 패키지"""
__version__ = "1.0.0"
```

**선택 1: 서브패키지 노출 (권장)**
```python
# ai/__init__.py
"""AI 관련 모듈 통합 패키지"""

from .chatbot import ChatbotStream
from .rag import RagService
from .functions import FunctionCalling
from .data import collection

__all__ = ["ChatbotStream", "RagService", "FunctionCalling", "collection"]
__version__ = "1.0.0"
```

**효과**:
```python
# 최상위 레벨에서 import 가능!
from ai import ChatbotStream, RagService
```

**선택 2: 현재 유지 (비권장)**
- 서브패키지만 사용
- `from ai.chatbot import ChatbotStream` 형태 유지

---

### 3.2 패키지화 선택 사항 ⚠️

#### **1. `/tests` - 테스트 패키지**

**판단 기준**:
- 테스트 코드가 **많지 않으면** 비어있어도 됨
- 테스트 헬퍼 함수를 **공유하면** 패키지화 권장

**예시**:
```python
# tests/__init__.py
"""테스트 패키지"""

# 선택 1: 비어있음 (테스트가 적을 때)
# (현재 상태 유지)

# 선택 2: 헬퍼 함수 제공 (테스트가 많을 때)
from .helpers import create_test_user, mock_rag_result

__all__ = ["create_test_user", "mock_rag_result"]
```

---

### 3.3 레거시 패키지 처리 🔶

#### **1. `/chatbotDirectory` - 레거시 챗봇**

**상태**: 점진적으로 `/ai`로 마이그레이션 중

**전략**:
- ❌ **패키지화 불필요** (마이그레이션 대상)
- ⚠️ 기존 코드 호환성 유지만 하면 됨

```python
# chatbotDirectory/__init__.py
# (비어있음 유지 - 작업 불필요)
```

---

#### **2. `/loding` - 레거시 데이터 로딩**

**상태**: `/ai/data`로 통합 예정

**전략**:
- ❌ **패키지화 불필요** (마이그레이션 대상)

```python
# loding/__init__.py
# (비어있음 유지 - 작업 불필요)
```

---

## 4. 패키지화하면 안 되는 것들 ❌

### 4.1 절대 패키지화하면 안 되는 것

#### **1. 데이터 폴더**

```
❌ pdfs/
   ├── __init__.py  ← 추가하면 안 됨!
   └── 규정.pdf
```

**이유**:
- PDF 파일은 Python 모듈 아님
- import할 필요 없음
- 단순 데이터 저장용

---

#### **2. 문서 폴더**

```
❌ docs/
   ├── __init__.py  ← 추가하면 안 됨!
   └── README.md
```

**이유**:
- 마크다운 파일은 Python 코드 아님
- import할 수 없음
- 사람이 읽는 문서

---

#### **3. 설정 파일만 있는 폴더**

```
❌ config/
   ├── __init__.py  ← 추가하면 안 됨!
   └── settings.json
```

**이유**:
- JSON/YAML은 Python 모듈 아님
- 직접 읽어서 사용

---

### 4.2 패키지화 불필요한 것

#### **1. `/api` - API 라우터**

**현재**:
```
api/
└── routes.py  (단일 파일)
```

**판단**:
- ❌ **패키지화 불필요**
- 파일이 하나만 있으면 패키지로 만들 필요 없음

**예외**: 파일이 많아지면 패키지화 고려
```
api/
├── __init__.py       ← 파일 많아지면 추가
├── routes.py
├── dependencies.py
├── middleware.py
└── auth.py
```

---

#### **2. `/app` (루트)**

**현재**:
```python
# app/__init__.py
# (비어있음)
```

**판단**:
- ❌ **패키지화 불필요**
- FastAPI 애플리케이션 루트는 패키지화 안 해도 됨
- `main.py`가 진입점 역할

---

### 4.3 패키지화 주의사항 ⚠️

#### **주의 1: 순환 import 위험**

```python
# ❌ 나쁜 예: 순환 import
# ai/__init__.py
from .chatbot import ChatbotStream
from .rag import RagService

# ai/chatbot/stream.py
from ai.rag import RagService  # ← 순환 import 발생 가능!
```

**해결책**:
```python
# ✅ 좋은 예: 서브패키지만 노출
# ai/__init__.py
# (비어있거나 최소화)

# ai/chatbot/stream.py
from ai.rag import RagService  # ← 안전
```

---

#### **주의 2: 불필요한 노출**

```python
# ❌ 나쁜 예: 내부 변수까지 노출
# ai/rag/__init__.py
from .service import RagService
import os
DEBUG = True

# __all__ 없음 → os, DEBUG까지 노출됨!
```

```python
# ✅ 좋은 예: __all__로 제어
# ai/rag/__init__.py
from .service import RagService
import os
DEBUG = True

__all__ = ["RagService"]  # RagService만 노출!
```

---

## 5. 작업 우선순위

### 5.1 즉시 작업 필요 🔥

#### **우선순위 1: `/ai/functions/__init__.py`**

**현재 문제**:
```python
# ai/chatbot/stream.py
from app.ai.functions.analyzer import FunctionCalling, tools
#                     ^^^^^^^^ 파일명까지 써야 함 (복잡)
```

---

**작업 내용**:
```python
# ai/functions/__init__.py
"""
함수 호출 모듈

웹 검색, 학식 메뉴, 공지사항 등 외부 함수 호출을 관리합니다.
"""

from .analyzer import FunctionCalling, tools

__all__ = ["FunctionCalling", "tools"]
```

---

**영향받는 파일 및 수정 방법**:

**1️⃣ `ai/chatbot/stream.py` (필수 수정)**:
```python
# Before (9번 줄)
from app.ai.functions.analyzer import FunctionCalling, tools

# After ✅
from app.ai.functions import FunctionCalling, tools
```

**2️⃣ `api/routes.backup.py`, `api/routes.old.py` (선택 수정)**:
```python
# 백업/레거시 파일이므로 수정 선택 사항
# 동일한 방식으로 수정 가능
```

---

**변경 효과**:
- ✅ Import 경로 단축 (analyzer 파일명 불필요)
- ✅ 파일 구조 변경에 강함
- ✅ 코드 일관성 향상

---

#### **우선순위 2: `/ai/data/__init__.py`**

**현재 문제**:
```python
# ai/rag/repository.py
from app.ai.data.mongodb_client import MONGO_AVAILABLE, collection
#              ^^^^^^^^^^^^^^^ 파일명까지

# ai/rag/retriever.py
from app.ai.data.vector_uploader import get_embedding, index
#              ^^^^^^^^^^^^^^^^ 파일명까지
```

---

**작업 내용**:
```python
# ai/data/__init__.py
"""
데이터 처리 모듈

문서 로딩, MongoDB 연결, 벡터 DB 업로드 등을 담당합니다.
"""

from .mongodb_client import collection, MONGO_AVAILABLE
from .vector_uploader import get_embedding, index

__all__ = ["collection", "MONGO_AVAILABLE", "get_embedding", "index"]
```

---

**영향받는 파일 및 수정 방법**:

**1️⃣ `ai/rag/repository.py` (필수 수정)**:
```python
# Before (9번 줄)
from app.ai.data.mongodb_client import MONGO_AVAILABLE, collection

# After ✅
from app.ai.data import MONGO_AVAILABLE, collection
```

**2️⃣ `ai/rag/retriever.py` (필수 수정)**:
```python
# Before (13번 줄)
from app.ai.data.vector_uploader import get_embedding, index

# After ✅
from app.ai.data import get_embedding, index
```

**3️⃣ `loding/vector_db_upload.py` (선택 수정)**:
```python
# 레거시 파일이므로 마이그레이션 시 수정
# 또는 현재 패턴 유지
```

---

**변경 효과**:
- ✅ Import 경로 단축 및 통일
- ✅ 파일 2개를 1줄로 통합 가능
- ✅ RAG 모듈 전체 import 일관성 확보
- ✅ 데이터 레이어 캡슐화 강화

---

**전체 수정 요약**:

| 파일 | 수정 필요도 | 현재 상태 | 수정 후 |
|------|-----------|----------|---------|
| `ai/chatbot/stream.py` | 🔥 필수 | `from ...analyzer import` | `from ...functions import` |
| `ai/rag/repository.py` | 🔥 필수 | `from ...mongodb_client import` | `from ...data import` |
| `ai/rag/retriever.py` | 🔥 필수 | `from ...vector_uploader import` | `from ...data import` |
| `api/routes.backup.py` | ⚠️ 선택 | 백업 파일 | (수정 선택) |
| `loding/vector_db_upload.py` | ⚠️ 선택 | 레거시 | (마이그레이션 시) |

---

### 5.2 선택 작업 ⚠️

#### **선택 1: `/ai/__init__.py` 서브패키지 노출**

**작업 내용**:
```python
# ai/__init__.py
"""
AI 관련 모듈 통합 패키지
"""

from .chatbot import ChatbotStream
from .rag import RagService
from .functions import FunctionCalling

__all__ = ["ChatbotStream", "RagService", "FunctionCalling"]
__version__ = "1.0.0"
```

**효과**:
```python
# 최상위 레벨 import 가능
from ai import ChatbotStream, RagService
```

**장점**: 간결한 import
**단점**: 순환 import 위험 증가

---

#### **선택 2: `/tests/__init__.py` 테스트 헬퍼**

**조건**: 테스트 파일이 많을 때만

**작업 내용**:
```python
# tests/__init__.py
"""
테스트 패키지
"""

from .helpers import create_test_user, mock_rag_result

__all__ = ["create_test_user", "mock_rag_result"]
```

---

### 5.3 작업 불필요 ❌

| 패키지 | 이유 |
|--------|------|
| `/chatbotDirectory` | 레거시 (마이그레이션 대상) |
| `/loding` | 레거시 (마이그레이션 대상) |
| `/app` | FastAPI 루트 (패키지화 불필요) |
| `/api` | 단일 파일 (패키지화 불필요) |
| `/docs` | 문서 폴더 (Python 코드 아님) |
| `/pdfs` | 데이터 폴더 (Python 코드 아님) |

---

## 6. 실전 예제

### 6.1 패키지화 Before/After (실제 파일 기준)

#### **예제 1: `FunctionCalling` 사용 (ai/chatbot/stream.py)**

**📍 파일 위치**: `ai/chatbot/stream.py` (9번 줄)

**Before** (`__init__.py` 주석 처리됨):
```python
# ai/chatbot/stream.py
from app.ai.functions.analyzer import FunctionCalling, tools
#    ^^^ ^^^ ^^^^^^^^^ ^^^^^^^^ 
#    app.ai.functions.analyzer 까지 전체 경로
```

**After** (`/ai/functions/__init__.py` 작업 후):
```python
# ai/functions/__init__.py (주석 해제)
from .analyzer import FunctionCalling, tools
__all__ = ["FunctionCalling", "tools"]
```

```python
# ai/chatbot/stream.py (수정)
from app.ai.functions import FunctionCalling, tools
#    ^^^ ^^^ ^^^^^^^^^
#    app.ai.functions 까지만! (analyzer 불필요)
```

**개선 효과**:
- ✅ 경로 단축: `analyzer` 파일명 제거
- ✅ 캡슐화: analyzer.py → utils.py 로 이름 바뀌어도 영향 없음
- ✅ 명확성: "functions 패키지의 공식 API 사용" 명시

---

#### **예제 2: MongoDB 사용 (ai/rag/repository.py)**

**📍 파일 위치**: `ai/rag/repository.py` (9번 줄)

**Before** (`__init__.py` 주석 처리됨):
```python
# ai/rag/repository.py
from app.ai.data.mongodb_client import MONGO_AVAILABLE, collection
#    ^^^ ^^^ ^^^^ ^^^^^^^^^^^^^^
#    app.ai.data.mongodb_client 까지 전체 경로
```

**After** (`/ai/data/__init__.py` 작업 후):
```python
# ai/data/__init__.py (주석 해제)
from .mongodb_client import collection, MONGO_AVAILABLE
__all__ = ["collection", "MONGO_AVAILABLE", "get_embedding", "index"]
```

```python
# ai/rag/repository.py (수정)
from app.ai.data import MONGO_AVAILABLE, collection
#    ^^^ ^^^ ^^^^
#    app.ai.data 까지만! (mongodb_client 불필요)
```

**개선 효과**:
- ✅ 경로 단축: `mongodb_client` 파일명 제거
- ✅ 일관성: data 패키지 내 모든 항목 동일 방식 import
- ✅ 유지보수: 내부 파일 구조 변경 시 영향 최소화

---

#### **예제 3: 임베딩 함수 사용 (ai/rag/retriever.py)**

**📍 파일 위치**: `ai/rag/retriever.py` (13번 줄)

**Before** (`__init__.py` 주석 처리됨):
```python
# ai/rag/retriever.py
from app.ai.data.vector_uploader import get_embedding, index
#    ^^^ ^^^ ^^^^ ^^^^^^^^^^^^^^^^
#    app.ai.data.vector_uploader 까지 전체 경로
```

**After** (`/ai/data/__init__.py` 작업 후):
```python
# ai/data/__init__.py (이미 작업됨)
from .vector_uploader import get_embedding, index
__all__ = ["collection", "MONGO_AVAILABLE", "get_embedding", "index"]
```

```python
# ai/rag/retriever.py (수정)
from app.ai.data import get_embedding, index
#    ^^^ ^^^ ^^^^
#    app.ai.data 까지만! (vector_uploader 불필요)
```

**추가 개선: 통합 import**:
```python
# Before: 파일별로 2줄
from app.ai.data.mongodb_client import collection
from app.ai.data.vector_uploader import get_embedding

# After: 한 줄로 통합 ✅
from app.ai.data import collection, get_embedding
```

---

#### **예제 4: 실제 코드 리팩토링 시나리오**

**시나리오**: `ai/rag/repository.py`와 `ai/rag/retriever.py` 동시 리팩토링

**Before**:
```python
# ai/rag/repository.py
from app.ai.data.mongodb_client import MONGO_AVAILABLE, collection

# ai/rag/retriever.py  
from app.ai.data.vector_uploader import get_embedding, index

# 문제점:
# - 파일명까지 명시 (mongodb_client, vector_uploader)
# - 2개 파일에서 data 모듈 사용하는데 경로 중복
# - 파일 구조 변경 시 2곳 모두 수정 필요
```

**After** (`/ai/data/__init__.py` 작업 후):
```python
# ai/data/__init__.py
from .mongodb_client import collection, MONGO_AVAILABLE
from .vector_uploader import get_embedding, index
__all__ = ["collection", "MONGO_AVAILABLE", "get_embedding", "index"]

# ai/rag/repository.py
from app.ai.data import MONGO_AVAILABLE, collection

# ai/rag/retriever.py
from app.ai.data import get_embedding, index

# 개선 효과:
# ✅ 파일명 제거 (간결)
# ✅ 경로 통일 (app.ai.data만 기억)
# ✅ 캡슐화 (내부 파일 구조 숨김)
```

---

### 6.2 파일별 수정 체크리스트

#### **수정 필요 파일 목록 및 상세 가이드**

##### **1️⃣ `ai/chatbot/stream.py` (9번 줄)** 🔥 필수

**현재**:
```python
from app.ai.functions.analyzer import FunctionCalling, tools
```

**수정 방법**:
1. `ai/functions/__init__.py` 주석 해제
2. 위 줄을 다음으로 변경:
```python
from app.ai.functions import FunctionCalling, tools
```

---

##### **2️⃣ `ai/rag/repository.py` (9번 줄)** 🔥 필수

**현재**:
```python
from app.ai.data.mongodb_client import MONGO_AVAILABLE, collection
```

**수정 방법**:
1. `ai/data/__init__.py` 주석 해제 (MONGO_AVAILABLE 추가 필요)
2. 위 줄을 다음으로 변경:
```python
from app.ai.data import MONGO_AVAILABLE, collection
```

---

##### **3️⃣ `ai/rag/retriever.py` (13번 줄)** 🔥 필수

**현재**:
```python
from app.ai.data.vector_uploader import get_embedding, index
```

**수정 방법**:
1. `ai/data/__init__.py` 주석 해제 (이미 작업된 상태 확인)
2. 위 줄을 다음으로 변경:
```python
from app.ai.data import get_embedding, index
```

---

##### **4️⃣ `api/routes.backup.py`, `api/routes.old.py`** ⚠️ 선택

**현재**:
```python
from app.ai.functions.analyzer import tools, FunctionCalling
```

**수정 여부**: 선택 사항 (백업/레거시 파일)
- ✅ 수정하려면: `from app.ai.functions import tools, FunctionCalling`
- ⏸️ 유지하려면: 현재 상태 유지

---

### 6.3 작업 순서 가이드

**단계별 작업 순서**:

```
1️⃣ __init__.py 파일 수정
   ├─ ai/functions/__init__.py 주석 해제
   └─ ai/data/__init__.py 주석 해제 (MONGO_AVAILABLE 추가)

2️⃣ Import 문 수정 (필수 파일 3개)
   ├─ ai/chatbot/stream.py (9번 줄)
   ├─ ai/rag/repository.py (9번 줄)
   └─ ai/rag/retriever.py (13번 줄)

3️⃣ 테스트
   ├─ Python 서버 실행 (uvicorn main:app)
   ├─ Import 에러 확인
   └─ 기능 정상 작동 확인

4️⃣ 선택 작업 (백업 파일)
   └─ api/routes.backup.py, api/routes.old.py (필요 시)
```

---

### 6.2 잘못된 패키지화 예제 ❌

#### **잘못된 예 1: 데이터 폴더 패키지화**

```python
# ❌ 절대 하지 마세요!
# pdfs/__init__.py
from pathlib import Path

# PDF 파일 목록
pdf_files = list(Path(__file__).parent.glob("*.pdf"))

__all__ = ["pdf_files"]
```

**왜 안 되나?**:
- PDF는 Python 모듈 아님
- import할 필요 없음
- 파일 시스템으로 접근하면 됨

---

#### **잘못된 예 2: 순환 import**

```python
# ❌ 순환 import 발생!
# ai/__init__.py
from .chatbot import ChatbotStream
from .rag import RagService

# ai/chatbot/stream.py
from ai import RagService  # ← 순환 import!
```

**해결책**:
```python
# ✅ 직접 서브패키지 import
# ai/chatbot/stream.py
from ai.rag import RagService
```

---

## 7. 체크리스트 ✅

### 7.1 패키지화 결정 체크리스트

**다음 질문에 **모두 Yes**면 패키지화하세요:**

- [ ] Python 코드 파일(`.py`)이 2개 이상인가?
- [ ] 다른 파일에서 import되는가?
- [ ] 재사용 가능한 로직인가?
- [ ] 레거시가 아닌가?

**하나라도 No면 패키지화 불필요:**

- [ ] 데이터 파일(PDF, JSON 등)만 있는가?
- [ ] 문서 파일만 있는가?
- [ ] 단일 파일만 있는가?
- [ ] 마이그레이션 예정인가?

---

### 7.2 `__init__.py` 작성 체크리스트

**필수 항목:**

- [ ] 문서 문자열 (docstring) 작성
- [ ] `from .module import Class` 형태로 import
- [ ] `__all__` 리스트 정의

**선택 항목:**

- [ ] `__version__` 정의
- [ ] 패키지 초기화 로직

**금지 항목:**

- [ ] ❌ 복잡한 로직 실행
- [ ] ❌ 외부 API 호출
- [ ] ❌ 파일 I/O 작업
- [ ] ❌ 순환 import 유발

---

## 8. 요약

### 8.1 패키지화 우선순위 요약

| 우선순위 | 패키지 | 작업 | 이유 |
|---------|--------|------|------|
| 🔥 **높음** | `/ai/functions` | 주석 해제 | FunctionCalling 노출 필요 |
| 🔥 **높음** | `/ai/data` | 주석 해제 | collection, get_embedding 노출 필요 |
| ⚠️ **중간** | `/ai` | 선택 작업 | 최상위 import 편의성 |
| 📝 **낮음** | `/tests` | 선택 작업 | 테스트 헬퍼 공유 시 |
| ❌ **불필요** | 레거시, 데이터 폴더 | 작업 안 함 | 패키지화 부적합 |

---

### 8.2 핵심 원칙

1. ✅ **Python 코드만** 패키지화
2. ✅ **재사용 로직만** 노출
3. ✅ **`__all__`로** 공개 API 명시
4. ❌ **데이터/문서 폴더** 패키지화 금지
5. ❌ **순환 import** 주의

---

## 9. 다음 단계

### 9.1 즉시 작업

1. `/ai/functions/__init__.py` 주석 해제
2. `/ai/data/__init__.py` 주석 해제
3. 영향받는 파일 import 문 정리

### 9.2 장기 작업

1. 레거시 코드 마이그레이션 완료
2. `/ai/__init__.py` 서브패키지 노출 검토
3. 테스트 패키지 정리

---

**관련 문서**:
- [프로젝트 구조](프로젝트_구조.md)
- [핵심 클래스 함수](핵심_클래스_함수.md)
- [프론트엔드 API 통합 가이드](프론트엔드_API_통합_가이드.md)
