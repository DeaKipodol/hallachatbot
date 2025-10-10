# RAG 모듈 분리 계획

> 버전: 2025-10-07 · 작성자: GitHub Copilot · 범위: `chatbotDirectory` 모듈 재구성
>
> **지침 준수**: 본 계획은 "과도한 변경을 피한다"는 요청을 따르며, 단계별로 안전하게 적용할 수 있도록 설계되었습니다.

---

## 1. 현황 요약

| 구성요소 | 파일 | 역할 | RAG 관련 책임 |
| --- | --- | --- | --- |
| `ChatbotStream` 클래스 | `chatbotDirectory/chatbot.py` | 대화 컨텍스트, 스트리밍 응답, 함수 호출 통합 | ✅ RAG 서비스 호출 및 최신 결과 캐시(`last_rag_result`) |
| `RagService` | `chatbotDirectory/rag/service.py` | RAG 조립자 | ✅ 규정 게이트, Pinecone 검색, Mongo 조회, 컨텍스트 조합 순서 제어 |
| `RegulationGate` | `chatbotDirectory/rag/gate.py` | 규정 여부 판별 | ✅ Responses API 기반 판단 + 키워드 폴백 |
| `PineconeRetriever` | `chatbotDirectory/rag/retriever.py` | 유사도 검색 | ✅ 임베딩 생성 후 네임스페이스별 Pinecone 질의 |
| `MongoChunkRepository` | `chatbotDirectory/rag/repository.py` | Mongo 조회 | ✅ 청크 문서 조회 및 ObjectId 변환/로깅 |
| `ContextBuilder` | `chatbotDirectory/rag/context_builder.py` | 컨텍스트 조립 | ✅ Mongo 본문 결합 + 프리뷰 폴백 구성 |
| 벡터 검색 헬퍼 | `loding/vector_db_upload.py` | Pinecone 업로드 + 유틸 | ✅ `get_embedding`, `index.query` 를 RAG 모듈이 주입 받아 사용 |
| Mongo 커넥터 | `loding/mongodbConnect.py` | Mongo 연결 | ✅ `collection`, `MONGO_AVAILABLE` 를 RAG 모듈이 주입 받아 사용 |
| 프롬프트 자원 | `chatbotDirectory/character.py` | RAG 게이트 지침 | ✅ 게이트 프롬프트 및 출력 규격 |

**문제점**
- RAG 관련 책임이 `ChatbotStream` 내부에 흩어져 있어 SRP 위반.
- Pinecone/Mongo 모듈을 직접 import 하므로 테스트/교체가 까다롭다.
- 관찰성(로그)와 폴백 정책이 챗봇 로직과 뒤섞여 있다.


## 2. 목표와 범위

| 목표 | 범위 | 비고 |
| --- | --- | --- |
| RAG 관심사 분리 | `chatbotDirectory` 내부 | 챗봇·RAG 상호 의존 최소화 |
| 단계적 리팩터 | **Phase 0~2** 우선 | 과도한 구조 변경 방지 |
| 테스트 용이성 확보 | 단위 테스트가 가능한 구조 | 목/스텁으로 Pinecone·Mongo 대체 |

> **범위 밖**: 벡터 DB/임베딩/스토어 교체, 완전한 마이크로서비스 분리는 추후 고려.


## 3. 제안 모듈 구조 (초안)

```
chatbotDirectory/
├── rag/
│   ├── __init__.py
│   ├── config.py          # RAG 설정 (namespace, top_k, threshold 등)
│   ├── gate.py            # 규정 여부 판정 로직 (Responses API)
│   ├── retriever.py       # Pinecone 검색 래퍼
│   ├── repository.py      # Mongo 청크 조회 래퍼
│   ├── context_builder.py # 컨텍스트 조립 및 프리뷰 폴백
│   └── service.py         # 위 구성요소를 오케스트레이션
└── chatbot.py             # ChatbotStream (RAG 의존 삭제 후 서비스 호출)
```

- `rag.service.RagService` 가 외부 진입점 역할.
- 기존 함수는 단계적으로 각 모듈로 옮기고, 공개 API는 `RagService.search(query: str) -> RagResult` 형식.
- `RagResult` 는 컨텍스트 텍스트 + 메타(hit, chunk_ids, reason, context_source, document/preview count 등)를 포함하는 데이터클래스로 정의.

### 3.1) 왜 "서비스"인가?
- Phase 1의 핵심은 **새로운 로직을 도입하지 않고**, 기존 함수를 감싸는 "얇은 퍼사드"를 마련하는 것입니다.
- `RagService` 는 Chatbot이 호출할 단일 포트가 되어, 이후 책임 이전 과정(Phase 2)의 정착점을 제공.
- 함수 호출/검색/LLM 스트리밍 등 다른 기능은 그대로 두고, RAG 부분만 캡슐화하여 **점진적 분리**를 가능하게 합니다.


## 4. 단계별 실행 계획

| 단계 | 목적 | 구체 작업 | 산출물 |
| --- | --- | --- | --- |
| **Phase 0: 안전망** | 현 구조 유지 · 계측 강화 | - 현재 로그/예외 케이스 확인<br>- `docs/RAG_분리_계획.md` 공유/합의<br>- (선택) 간단한 테스트 스텁 작성 | 합의된 계획, 스냅샷 테스트(선택) |
| **Phase 1: 인터페이스 도입** | 최소 변경으로 포트 정의 | - `rag/service.py` 생성, 내부에 기존 함수 래핑<br>- `RagService` 가 내부에서 기존 함수 호출<br>- `chatbot.py` 는 `self.rag_service = RagService(...)` 생성 (기본값 제공)<br>- 기존 메서드는 deprecated guide 주석만 추가하고 호출 경로는 유지 | 기존 기능 유지 + 포트 도입 |
| **Phase 2: 책임 이전** | 기능별 모듈로 이전 | - `search_similar_chunks` → `retriever.py`<br>- `fetch_chunks_from_mongo` → `repository.py`<br>- `prepare_rag_context` → `context_builder.py`<br>- `is_question_about_regulation` → `gate.py` | RAG 로직 외부화, `chatbot.py` 경량화 |
| **Phase 3~** *(선택)* | 심화 개선 | - 폴백 정책, 캐싱, 대체 전략 등 | 추후 요구 시 진행 |

> **주의**: Phase 1까지는 파일 추가/간단한 import 변경 정도로 영향도 최소화. Phase 2도 기능 동일성을 유지하며 함수 이동만 수행한다.


## 5. 의존성 및 협업 포인트

- **환경 변수**: `apikey.env` 로딩 위치가 서로 다르므로, RAG 모듈에 환경 의존을 직접 두지 말고 기존 헬퍼를 주입.
- **불변 자원**: `vector_db_upload.index` / `get_embedding`, `mongodbConnect.collection` 은 Phase 1에선 그대로 사용하되, constructor injection으로 교체 가능한 형태로 노출.
- **로그/메트릭**: `_dbg` 포맷을 `RagService` 로 이관하면서 표준화(`[RAG] ...`).


## 6. 리스크 및 완화

| 리스크 | 영향 | 완화 전략 |
| --- | --- | --- |
| 모듈 경로 변경으로 인한 import 오류 | 중간 단계 실패 가능 | 단계별 PR, `__init__.py` 에 안전한 재노출, mypy/pytest 스모크 |
| Mongo/Pinecone 전역 클라이언트 중복 생성 | 성능 저하, 커넥션 문제 | 기존 모듈의 클라이언트를 주입받아 사용 (Phase 1) |
| 기능 회귀 | 사용자 응답 실패 | 리팩터 후 `test_stream_chat.py` 스모크 실행 + 로그 비교 |


## 7. 체크리스트

- [x] Phase 1용 `rag/service.py` 골격 생성 및 기존 함수 래핑
- [x] `ChatbotStream` 생성자에서 `RagService` 주입 (기본 인스턴스 제공)
- [x] `ChatbotStream.prepare_rag_context` 제거 및 `RagService.build_context` 기반 호출로 전환
- [x] Phase 2 모듈 (`gate.py`, `retriever.py`, `repository.py`, `context_builder.py`) 도입
- [x] `docs/` 업데이트 (본 문서 포함)
- [ ] 스모크 테스트 (`uvicorn`, `python test_stream_chat.py`) 수행
- [ ] 로그 패턴 비교로 회귀 여부 확인


## 8. 다음 액션 제안

1. 본 계획을 공유하고 Phase 1 접근(인터페이스 래핑)이 허용되는지 확인.
2. 승인되면 `chatbotDirectory/rag/` 패키지 scaffold + `RagService` 스텁 생성.
3. 기존 RAG 관련 메서드 / 의존성 목록(State of the World) 을 기반으로 마이그레이션 체크리스트 작성.

> **메모**: "너무 큰 변경"을 지양하기 위해, 실제 코드 이동은 Phase 1에서 관찰성 보존을 최우선으로 하며, 필요시 안전 플래그(예: `ENABLE_RAG_SERVICE=0/1`)로 토글할 수 있도록 설계 바랍니다.

---

## 9. Phase 1 실행 지침 (세부)

### 9.1) 목표
- RAG 관련 기존 함수를 건드리지 않고, `ChatbotStream` 에서 RAG 호출 지점을 `RagService` 로 경유하도록 변경.
- 이후 Phase 2에서 모듈 분리 시, `RagService` 내부만 교체하면 되도록 진입점을 마련.

### 9.2) `rag/service.py` 역할 정의
```python
# chatbotDirectory/rag/service.py (초안)
from dataclasses import dataclass
from typing import Optional, Sequence

@dataclass
class RagResult:
	context_text: Optional[str]
	hits: Sequence[object]  # Pinecone match objects (원본 유지)
	chunk_ids: Sequence[object]
	gate_reason: Optional[str] = None

class RagService:
	"""Phase 1: 기존 ChatbotStream의 RAG 기능을 래핑하는 퍼사드."""

	def __init__(self, chatbot_stream: "ChatbotStream"):
		self.chatbot = chatbot_stream

	def build_context(self, question: str) -> RagResult:
		"""기존 prepare_rag_context 호출을 감싸고, 메타데이터를 함께 반환."""
		context = self.chatbot.prepare_rag_context(question)
		return RagResult(
			context_text=context,
			hits=getattr(self.chatbot, "_last_rag_hits", []),
			chunk_ids=getattr(self.chatbot, "_last_rag_chunk_ids", []),
			gate_reason=getattr(self.chatbot, "_last_rag_reason", None),
		)

	def is_regulation(self, question: str) -> bool:
		"""기존 is_question_about_regulation을 그대로 위임."""
		return self.chatbot.is_question_about_regulation(question)

	def search(self, question: str):
		"""Phase 1: 필요 시 별도 노출."""
		return self.chatbot.search_similar_chunks(question)
```

> **설명**: Phase 1에서는 `ChatbotStream` 내부 함수를 그대로 사용하되, `RagService` 가 포트가 되어 호출흐름을 제어합니다. 이후 Phase 2에서 `RagService` 내부 구현을 독립 모듈로 대체할 계획입니다.

### 9.3) 구현 단계 (권장 순서)
1. **파일 생성**: `chatbotDirectory/rag/__init__.py`, `chatbotDirectory/rag/service.py` 추가.
2. **래핑 필드 추가**: `ChatbotStream.__init__` 에 `self.rag_service = RagService(self)`를 추가.
   - 기존 import 순환을 피하기 위해, 지연 임포트 또는 팩토리 함수를 사용.
3. **접근자 정리**: `prepare_rag_context` 내부에서 `_last_rag_hits`, `_last_rag_chunk_ids`, `_last_rag_reason` 등을 설정하도록 보완.
4. **호출 경로 교체(옵션)**: `/api/routes.py` 혹은 테스트 코드에서 직접 `RagService`를 사용하는지 검토.
5. **토글 추가(선택)**: `ENABLE_RAG_SERVICE` 환경변수로 신경망을 켜고 끌 수 있는 토글 마련.

### 9.4) 체크리스트 확장
- [x] `chatbotDirectory/rag/__init__.py` 생성
- [x] `chatbotDirectory/rag/service.py` 생성
- [x] `ChatbotStream` 에 `RagService(debug_fn=self._dbg)` 주입 및 `last_rag_result` 캐시 추가
- [x] `ChatbotStream` 생성 시 `self.rag_service` 설정
- [x] 라우터(`/api/routes.py`)가 필요 시 `rag_service` 경유하도록 준비
- [ ] Phase 1 완료 후 스모크 테스트 및 로그 비교


## 10. Phase 2 진입 전 점검

- [x] `ChatbotStream` 내부에서 `prepare_rag_context` 직접 호출하는 잔여 경로 제거 (`RagService.build_context`만 노출)
- [ ] 스모크 테스트 (`python test_stream_chat.py`) 및 uvicorn 부팅으로 회귀 여부 확인
- [ ] 라우트/테스트 코드에서 `RagService` 메타데이터(`hits`, `chunk_ids`, `gate_reason`) 활용 요구사항 정리

	- `/api/routes.py`는 `RagService.build_context` 결과의 `hits`/`chunk_ids`를 추후 관리자 로깅(Phase 3)과 응답 근거 표시용으로 사용 예정.
	- `test_stream_chat.py` 스모크는 위 메타데이터가 채워지는지(비어 있으면 경고) 점검하도록 보강 예정.
	- Phase 2 모듈 분리 이후에도 `_last_rag_*` 필드는 RagResult에 포함되어 동일하게 노출되어야 함.

위 항목이 충족되면 Phase 2 작업을 시작할 수 있습니다.

## 11. Phase 2 상세 작업 계획

### 11.1 목표
- RAG 관련 책임(게이트, 검색, Mongo 조회, 컨텍스트 조립)을 `chatbotDirectory/rag/` 하위 모듈로 이전하여 `ChatbotStream`을 대화/스트리밍 책임에 집중시킨다.
- `RagService`가 각 책임 모듈을 주입받아 동작하는 조립자 역할을 하도록 설계한다.

### 11.2 작업 순서
1. **모듈 스캐폴드 작성**
	- `rag/retriever.py`: Pinecone 검색 어댑터 (`search(query: str, *, top_k: int = 5, threshold: float = 0.4) -> RetrieverResult`).
	- `rag/repository.py`: MongoDB 조회 래퍼 (`fetch_chunks(ids: Sequence[str]) -> list[dict]`).
	- `rag/context_builder.py`: Pinecone 매치 + Mongo 결과로 컨텍스트 생성 및 프리뷰 폴백 처리, `ContextBuildResult`로 소스/카운트 메타데이터 반환.
	- `rag/gate.py`: 규정 여부 판정 LLM 호출과 키워드 폴백 캡슐화.

2. **의존성 주입 설계**
	- `RagService` 생성자 서명을 `RagService(retriever, repository, context_builder, gate, *, logger=None)` 형태로 확장.
	- 기본 구현은 Phase 2 모듈 인스턴스를 직접 생성해 주입하고, 테스트에서는 목/스텁을 주입 가능하도록 설계한다.

3. **기능 이전 단계**
	- `search_similar_chunks` 구현을 `retriever.py`로 이동하고 `RagService`에서 새 모듈을 호출하도록 수정.
	- `fetch_chunks_from_mongo`를 `repository.py`로 이전하고 Mongo 의존성 주입을 명확히 한다.
	- `prepare_rag_context`의 컨텍스트 조합/프리뷰 폴백을 `context_builder.py`로 이전한다.
	- `is_question_about_regulation`을 `gate.py`로 이전하여 LLM 호출과 폴백을 한 곳에서 관리한다.
	- 이전 단계마다 `ChatbotStream`에서 해당 메서드를 제거하고 `RagService`만 노출하도록 정리한다.

4. **`ChatbotStream` 정리**
	- RAG 전용 메서드와 디버그 로깅을 제거하고, `RagService` 호출만 유지한다.
	- `_last_rag_*` 메타데이터를 `RagService` 혹은 별도 상태 객체에서 관리하도록 이전한다.

5. **테스트 및 검증**
	- Pinecone/Mongo를 모킹한 단위 테스트 작성 (`tests/test_rag_retriever.py`, `tests/test_rag_service.py` 등).
	- `test_stream_chat.py` 실행 결과를 기록하고 RAG 메타데이터가 동일하게 유지되는지 비교한다.
	- 간단한 통합 테스트 또는 스모크 스크립트로 실제 환경에서의 오동작 여부를 확인한다.

### 11.3 산출물
- 신규 모듈 파일: `rag/retriever.py`, `rag/repository.py`, `rag/context_builder.py`, `rag/gate.py`.
- 업데이트된 `rag/service.py` (모듈 주입 + `RagResult` 확장 필요 시).
- 경량화된 `chatbotDirectory/chatbot.py`.
- 테스트 파일 및 Phase 2 진행 로그(`docs/progress_log.md` 업데이트).

### 11.4 리스크와 대응
- **순환 import**: `TYPE_CHECKING` 가드와 지연 임포트로 해결.
- **성능 회귀**: 초기에는 기존 로직을 그대로 이동하므로 영향 최소, 로그 비교로 감시.
- **에러 핸들링 누락**: 모듈 분리 시 예외 처리 경로를 명시적으로 테스트한다.

## 12. 흔한 질문(FAQ)

**Q. 왜 기존 메서드를 즉시 제거하지 않나요?**  
A. Phase 1 목표는 관측 가능한 변경을 최소화하여 위험을 줄이는 것입니다. 기존 메서드를 유지한 채 래핑하면 회귀 시 빠르게 원상 복귀할 수 있습니다.

**Q. `RagService` 가 결국 기존 `ChatbotStream` 을 다시 참조한다면 의미가 있나요?**  
A. 예. Phase 1에서는 단일 진입점 확보가 핵심입니다. 이후 단계에서 진입점 내부를 독립 구현으로 교체할 수 있습니다.

**Q. 향후 IDB(Embedding, Vector, Content) 포트를 도입하려면?**  
A. Phase 2에서 `RagService` 생성자 파라미터를 `embedding_port`, `vector_port`, `content_port` 형태로 확장하면 됩니다.

---

## 13. Phase 3 상세 작업 계획

> **전제 조건**: Phase 2 완료 및 검증(스모크 테스트, 로그 비교)이 완료되어야 Phase 3를 시작할 수 있습니다.

### 13.1 목표
- **테스트 커버리지 확보**: RAG 모듈의 핵심 로직에 대한 단위 테스트 작성으로 회귀 방지 및 리팩터링 안전성 확보.
- **관찰성 강화**: 관리자용 RAG 검색 모니터링 시스템 구축으로 운영 가시성 향상.
- **문서화 완성**: 로컬 개발 환경 설정, 트러블슈팅 가이드, API 문서 정비.
- **성능 최적화 기반 마련**: 캐싱 전략, 배치 처리, 비동기 호출 등 최적화 포인트 식별 및 초안 구현.

### 13.2 작업 범위

#### 13.2.1 단위 테스트 작성 (우선순위: 높음)
**목적**: RAG 모듈의 핵심 로직을 외부 의존성 없이 검증하여 안정성 확보.

**작업 항목**:
1. **테스트 인프라 구성**
	- `tests/` 디렉토리 생성 및 `pytest` 설정 (`pyproject.toml` 또는 `pytest.ini`).
	- `conftest.py` 작성: 공통 픽스처(Pinecone 목, Mongo 목, 임베딩 스텁) 정의.
	- CI/CD 파이프라인 연동 준비 (GitHub Actions 등).

2. **`tests/test_rag_gate.py`**
	- `RegulationGate.is_regulation()` 메서드 테스트.
	- 시나리오:
		- LLM이 "yes" 반환 시 `True` + reason 확인.
		- LLM이 "no" 반환 시 키워드 폴백 동작 검증.
		- LLM 호출 실패 시 키워드 폴백으로 전환 확인.
		- 키워드("졸업", "규정", "학칙" 등) 포함 질문 처리 검증.
	- 목(Mock) 대상: `openai.Client.chat.completions.create`.

3. **`tests/test_rag_retriever.py`**
	- `PineconeRetriever.search()` 메서드 테스트.
	- 시나리오:
		- 임베딩 생성 확인 (`get_embedding` 호출 검증).
		- Pinecone `index.query()` 호출 파라미터 검증 (top_k, namespace, filter 등).
		- threshold 이상 매치만 필터링 확인.
		- ID 우선순위 추출 로직 검증 (`ID_KEYS_PRIORITY` 순서대로 mongo_id → id → ID → default).
		- 빈 결과 처리 (hits=[], chunk_ids=[]).
	- 목(Mock) 대상: `get_embedding`, `index.query`.

4. **`tests/test_rag_repository.py`**
	- `MongoChunkRepository.fetch_chunks()` 메서드 테스트.
	- 시나리오:
		- 24자 hex 문자열 → ObjectId 변환 확인.
		- 일반 문자열은 그대로 사용.
		- Mongo `find()` 호출 파라미터 검증.
		- 빈 ID 리스트 처리 (빈 배열 반환).
		- Mongo 연결 실패 시 예외 처리 (MONGO_AVAILABLE=False).
	- 목(Mock) 대상: `collection.find()`.

5. **`tests/test_rag_context_builder.py`**
	- `ContextBuilder.build()` 메서드 테스트.
	- 시나리오:
		- Mongo 조회 성공 시 본문 결합 + source="mongo" 확인.
		- Mongo 조회 실패 시 Pinecone 프리뷰 폴백 + source="preview".
		- 모든 데이터 없을 때 source="none" 반환.
		- document_count / preview_count 정확성 검증.
		- 텍스트 공백 제거 (strip) 동작 확인.
	- 목(Mock) 대상: `MongoChunkRepository.fetch_chunks()`.

6. **`tests/test_rag_service.py`**
	- `RagService.build_context()` 통합 테스트.
	- 시나리오:
		- 규정 질문 아닐 때 early return (context=None, is_regulation=False).
		- 규정 질문 시 전체 플로우 (gate → retriever → repository → context_builder) 검증.
		- RagResult 필드 완전성 확인 (8개 필드 모두 채워짐).
		- 헬퍼 메서드 `_make_result()` 동작 검증.
	- 목(Mock) 대상: `RegulationGate`, `PineconeRetriever`, `ContextBuilder`.

**산출물**:
- `tests/conftest.py`: 공통 픽스처 및 모킹 유틸리티.
- `tests/test_rag_*.py`: 각 모듈별 테스트 파일 (최소 80% 코드 커버리지 목표).
- `pytest.ini` 또는 `pyproject.toml`: pytest 설정 (테스트 경로, 커버리지 옵션).

---

#### 13.2.2 관리자용 RAG 모니터링 시스템 (우선순위: 중간)
**목적**: RAG 검색 품질 모니터링 및 디버깅 지원을 위한 관리자 도구 구축.

**작업 항목**:
1. **로깅 인프라 구축**
	- RAG 검색 로그 스키마 설계:
		```python
		{
		  "timestamp": "2025-10-09T10:30:00Z",
		  "session_id": "uuid",
		  "question": "졸업 규정을 알려주세요",
		  "is_regulation": true,
		  "gate_reason": "LLM-yes",
		  "hits_count": 5,
		  "chunk_ids": ["673abc...", "673def..."],
		  "context_source": "mongo",
		  "document_count": 3,
		  "preview_count": 0,
		  "response_time_ms": 1250
		}
		```
	- MongoDB collection `rag_search_logs` 생성.
	- `RagService.build_context()` 호출 시 로그 자동 저장 기능 추가.

2. **관리자 API 엔드포인트**
	- `GET /admin/rag/logs`: 로그 목록 조회 (페이징, 필터링).
	- `GET /admin/rag/logs/{log_id}`: 상세 로그 조회 (히트 메타데이터, 문서 내용 포함).
	- `GET /admin/rag/stats`: 통계 (규정 질문 비율, 평균 응답 시간, context_source 분포).
	- 인증/인가: JWT 기반 관리자 권한 검증.

3. **관리자 UI 프로토타입 (선택)**
	- 간단한 HTML + Alpine.js 또는 React SPA.
	- 기능:
		- 로그 테이블 뷰 (시간, 질문, 규정 여부, 소스, 응답 시간).
		- 상세 모달: 히트 점수, 청크 ID, 문서 본문 미리보기.
		- 조/항 표기 (메타데이터 `sub_index` 활용).
		- 필터: 날짜 범위, context_source, is_regulation.

**산출물**:
- `api/admin_routes.py`: 관리자 전용 라우트.
- `chatbotDirectory/rag/logger.py`: RAG 로그 저장 유틸리티.
- `docs/admin_monitoring_guide.md`: 관리자 도구 사용 가이드.
- (선택) `admin_ui/`: 프론트엔드 프로토타입.

---

#### 13.2.3 문서화 및 개발자 경험 개선 (우선순위: 중간)
**목적**: 신규 개발자 온보딩 시간 단축 및 운영 트러블슈팅 효율화.

**작업 항목**:
1. **README.md 확장**
	- 로컬 개발 환경 설정:
		```markdown
		## 로컬 실행
		1. 가상환경 활성화: `source .venv/bin/activate`
		2. 서버 시작: `cd .. && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
		3. API 문서: http://127.0.0.1:8000/docs
		```
	- 흔한 오류 해결:
		- `ModuleNotFoundError: No module named 'app'` → 레포지토리 루트에서 실행.
		- `Pinecone connection timeout` → `apikey.env` PINECONE_API_KEY 확인.
		- `Mongo MONGO_AVAILABLE=False` → MongoDB Atlas 연결 문자열 검증.

2. **API 문서 자동 생성**
	- FastAPI 기본 Swagger UI 활용 (`/docs`).
	- 각 엔드포인트에 docstring 추가 (요청/응답 예시, 에러 코드).
	- RAG 관련 엔드포인트 섹션 분리 (태그 활용).

3. **아키텍처 다이어그램**
	- `docs/architecture.md` 작성:
		- 전체 시스템 구조 (FastAPI → ChatbotStream → RagService → 모듈들).
		- RAG 플로우 다이어그램 (gate → retriever → repository → context_builder).
		- 의존성 주입 관계도.
	- Mermaid 또는 PlantUML 사용.

4. **코드 스타일 가이드**
	- `docs/style_guide.md`:
		- 한국어 주석 규칙 (모듈/클래스/메서드 수준).
		- 디버그 메시지 포맷 (`[모듈명] 한국어 설명`).
		- 타입 힌트 사용 원칙.

**산출물**:
- 업데이트된 `README.md`.
- `docs/architecture.md`: 시스템 아키텍처 문서.
- `docs/style_guide.md`: 코드 스타일 가이드.
- `docs/troubleshooting.md`: 트러블슈팅 가이드.

---

#### 13.2.4 성능 최적화 초안 (우선순위: 낮음)
**목적**: 향후 트래픽 증가 대비 최적화 포인트 식별 및 PoC 구현.

**작업 항목**:
1. **캐싱 전략**
	- 임베딩 캐시: 동일 질문 반복 시 임베딩 재생성 방지.
		- Redis 또는 메모리 LRU 캐시 (cachetools).
		- 캐시 키: `hash(question)`.
	- 컨텍스트 캐시: 규정 질문 + 검색 결과 조합 캐싱.
		- TTL: 1시간 (규정 업데이트 빈도 고려).

2. **배치 처리**
	- Mongo 조회 최적화: `chunk_ids` 배치 쿼리 (`$in` 연산자).
	- Pinecone 검색: 여러 네임스페이스 병렬 쿼리 (asyncio).

3. **비동기 호출 전환**
	- `RagService.build_context()` → `async build_context()`.
	- OpenAI/Pinecone 호출을 `httpx` AsyncClient로 교체.
	- FastAPI 라우트를 `async def`로 전환.

4. **성능 프로파일링**
	- `cProfile` 또는 `py-spy`로 병목 지점 분석.
	- 메트릭 수집: 응답 시간, 임베딩 생성 시간, Pinecone 쿼리 시간, Mongo 조회 시간.

**산출물**:
- `chatbotDirectory/rag/cache.py`: 캐싱 유틸리티.
- `docs/performance_optimization.md`: 최적화 전략 및 벤치마크 결과.
- (선택) `async_rag_service.py`: 비동기 버전 PoC.

---

### 13.3 작업 순서 및 일정 (예상)

| 순서 | 작업 | 우선순위 | 예상 소요 | 의존성 |
| --- | --- | --- | --- | --- |
| 1 | Phase 2 완료 검증 (스모크 테스트, 로그 비교) | **필수** | 1일 | Phase 2 완료 |
| 2 | 테스트 인프라 구성 (pytest, conftest.py) | 높음 | 0.5일 | - |
| 3 | 단위 테스트 작성 (gate, retriever) | 높음 | 2일 | 작업 2 |
| 4 | 단위 테스트 작성 (repository, context_builder, service) | 높음 | 2일 | 작업 3 |
| 5 | RAG 로깅 인프라 구축 | 중간 | 1일 | - |
| 6 | 관리자 API 엔드포인트 구현 | 중간 | 2일 | 작업 5 |
| 7 | README 및 문서화 | 중간 | 1.5일 | - |
| 8 | 관리자 UI 프로토타입 (선택) | 낮음 | 3일 | 작업 6 |
| 9 | 성능 최적화 PoC (선택) | 낮음 | 2일 | 작업 4 |

**총 예상 기간**: 핵심 작업(1~7) 약 10일, 전체(선택 포함) 약 15일.

---

### 13.4 체크리스트

**Phase 2 완료 확인** (Phase 3 전제 조건):
- [ ] `/api/chat` 엔드포인트 스모크 테스트 통과
- [ ] RAG 디버그 로그 출력 확인 (한국어 메시지, 5단계 플로우)
- [ ] Phase 2 이전/이후 로그 패턴 비교 완료
- [ ] `docs/progress_log.md` Phase 2 완료 기록

**Phase 3 핵심 작업**:
- [ ] pytest 설정 및 `conftest.py` 작성
- [ ] `test_rag_gate.py` 작성 (최소 5개 시나리오)
- [ ] `test_rag_retriever.py` 작성 (최소 6개 시나리오)
- [ ] `test_rag_repository.py` 작성 (최소 5개 시나리오)
- [ ] `test_rag_context_builder.py` 작성 (최소 5개 시나리오)
- [ ] `test_rag_service.py` 작성 (최소 4개 시나리오)
- [ ] 전체 테스트 통과 (`pytest tests/ -v`)
- [ ] 코드 커버리지 80% 이상 확인 (`pytest --cov=chatbotDirectory/rag`)
- [ ] RAG 검색 로그 스키마 설계 및 MongoDB collection 생성
- [ ] `RagService`에 로그 저장 로직 추가
- [ ] 관리자 API 엔드포인트 3개 구현 (logs, logs/{id}, stats)
- [ ] README.md 로컬 실행 가이드 추가
- [ ] `docs/troubleshooting.md` 작성 (최소 5개 케이스)
- [ ] `docs/architecture.md` RAG 플로우 다이어그램 추가

**Phase 3 선택 작업** (리소스 여유 시):
- [ ] 관리자 UI 프로토타입 (HTML/Alpine.js 또는 React)
- [ ] 임베딩 캐시 구현 (Redis 또는 메모리 LRU)
- [ ] 비동기 RAG 서비스 PoC
- [ ] 성능 프로파일링 및 벤치마크

---

### 13.5 리스크 및 완화

| 리스크 | 영향도 | 완화 전략 |
| --- | --- | --- |
| Phase 2 미완료 상태에서 Phase 3 시작 | 높음 | **Phase 2 완료 검증을 필수 전제 조건으로 설정** (스모크 테스트, 로그 비교) |
| 단위 테스트 작성 시간 초과 | 중간 | 우선순위 높은 모듈(gate, retriever)부터 작성, 커버리지 목표를 80%로 현실적 설정 |
| 모킹 복잡도 증가 | 중간 | `conftest.py`에 재사용 가능한 픽스처 정의, `unittest.mock` 대신 `pytest-mock` 활용 |
| 관리자 인증 구현 누락 | 중간 | JWT 기반 간단한 토큰 검증만 구현, 상세 권한 관리는 추후 단계로 이관 |
| 문서화 부채 누적 | 낮음 | 각 작업 완료 시 즉시 문서화, PR 체크리스트에 문서 업데이트 포함 |
| 성능 최적화 조기 최적화(premature optimization) | 낮음 | PoC 수준으로만 구현, 실제 트래픽 데이터 수집 후 우선순위 재평가 |

---

### 13.6 성공 기준

Phase 3는 다음 조건이 모두 충족되면 완료로 간주합니다:

1. **테스트 커버리지**: RAG 모듈 코드 커버리지 80% 이상, 모든 테스트 통과.
2. **관찰성**: RAG 검색 로그가 MongoDB에 저장되고, 관리자 API로 조회 가능.
3. **문서화**: 신규 개발자가 README만으로 로컬 환경 구축 및 서버 실행 가능.
4. **회귀 방지**: Phase 2 완료 후 추가된 모든 코드 변경이 테스트로 보호됨.

**선택 작업 성공 기준**:
- 관리자 UI: 로그 테이블 뷰 + 상세 모달 동작 확인.
- 캐싱: 동일 질문 재요청 시 응답 시간 50% 이상 단축.
- 비동기: 동시 요청 처리량 2배 증가 (벤치마크 기준).

---

### 13.7 Phase 4 이후 전망 (참고용)

Phase 3 완료 후 고려할 사항:

- **벡터 DB 추상화**: Pinecone → Weaviate/Qdrant 교체 가능한 포트 도입.
- **임베딩 모델 업그레이드**: text-embedding-ada-002 → text-embedding-3-large.
- **하이브리드 검색**: 키워드(BM25) + 벡터 검색 결합.
- **재순위(Reranking)**: Cohere Rerank API 또는 Cross-Encoder 적용.
- **프로덕션 배포**: Docker/Kubernetes, 로드 밸런싱, 오토 스케일링.
- **모니터링**: Prometheus + Grafana, Sentry 에러 트래킹.

> Phase 4 이후는 실제 운영 피드백 수집 후 우선순위를 재평가합니다.
