# 관리자용 RAG 검색 모니터링 페이지 계획

> 버전: 2025-10-08 · 상태: 초안 · 작성자: GitHub Copilot
>
> 목적: 챗봇이 RAG 검색을 수행할 때마다 남기는 메타데이터를 관리자 전용 페이지에서 조회하고, 실제로 참조한 규정 원문 위치(몇 조, 몇 항 등)를 빠르게 확인할 수 있도록 한다.

---

## 1. 배경과 목표

- **배경**: 챗봇은 Pinecone / MongoDB 를 통해 규정 문서를 검색하고, `_last_rag_hits`, `_last_rag_chunk_ids`, `_last_rag_reason` 등의 메타데이터를 보관 중이다.
- **요구 사항**:
  1. 검색 로그를 별도 관리자 화면에서 확인.
  2. 각 검색 결과에 대해 "몇 조 / 몇 항" 등 법령 위치 정보를 노출.
  3. 필요 시 원문 전문으로 이동하거나 파일 다운로드(예: HWP) 링크 제공.
- **성과 지표**: 관리자 페이지에서 최근 검색 50건 이상을 조회하고, 각 검색 건마다 근거 문서를 클릭해 세부 내용을 확인할 수 있어야 한다.

## 2. 저장 구조 제안

| 필드 | 타입 | 설명 | 비고 |
| --- | --- | --- | --- |
| `_id` | ObjectId | Mongo 기본 키 | 자동 생성 |
| `queried_at` | datetime | 검색 시각 | UTC 기준 |
| `user_question` | string | 사용자 질문 전문 | 최대 1024자 저장 |
| `gate_decision` | bool | 규정 여부 판정 결과 | `False` 인 경우에도 로그로 남김 |
| `gate_reason` | string | LLM이 제공한 판정 사유 | 최대 512자 |
| `hits` | array | Pinecone match 목록 | 각 요소에 score, namespace 포함 |
| `chunk_ids` | array | Mongo `_id` (문자열) | 빠른 조회용 |
| `resolved_chunks` | array<object> | MongoDB에서 조회한 문서 요약 | `law_article_id`, `title`, `source_file`, `category`, `text_preview` 포함 |
| `created_by` | string | 챗봇 인스턴스 정보 | 멀티 인스턴스 대비 |

> `resolved_chunks` 는 이미 Mongo 문서 메타데이터(`law_article_id`, `title`, `source_file`, `category`, `referenced_tables`)를 포함하고 있어, 조/항 표기를 프론트엔드에서 바로 사용할 수 있다.

## 3. API 및 라우팅 설계

### 3.1 REST 엔드포인트

| 메서드 | 경로 | 설명 | 응답 예 |
| --- | --- | --- | --- |
| `GET` | `/admin/rag/searches` | 최근 RAG 검색 로그 조회 (페이지네이션) | JSON (기본 20건) |
| `GET` | `/admin/rag/searches/{log_id}` | 특정 로그 상세 | JSON (Mongo 문서) |
| `GET` | `/admin/rag/searches/{log_id}/document/{chunk_id}` | Mongo 문서 원문 조회 | JSON 또는 HTML |
| `GET` | `/admin/rag/files/{filename}` | 원본 규정 파일 다운로드/프록시 | 파일 스트리밍 |

- **권한**: 관리자 토큰 또는 IP 화이트리스트 기반 보호 (Phase 1에서는 간단한 Basic Auth 고려).
- **응답 포맷**: JSON 을 기본으로 하되, 브라우저 접근 편의를 위해 `text/html` 템플릿(간단한 표)도 제공 가능.

### 3.2 서비스 계층 연동

- `RagService` 가 검색 수행 후 `RagLogRepository` (신규) 를 통해 위 로그 스키마로 MongoDB에 저장.
- 라우트(`/api/routes.py`)에서 `RagService` 를 주입 받아 검색 로그 API에 재사용.

## 4. UI 구성안

### 4.1 리스트 뷰

- 상단 필터: 날짜 범위, 규정 여부(Yes/No), namespace(law_articles / appendix_tables).
- 테이블 컬럼: 검색 시각, 사용자 질문 요약(최대 50자), 규정 여부, 참조 문서 수, 판정 이유.
- 각 행 클릭 시 오른쪽 패널 또는 상세 페이지로 이동.

### 4.2 상세 뷰

- 제목: 사용자 질문 전문.
- 섹션 1: 규정 여부 판정 이유 + Pinecone score 차트(간단한 bar chart 옵션).
- 섹션 2: 참조 문서 카드 목록.
  - 카드 내용: `law_article_id`, `title`, `source_file`, `category`, `text_preview`.
  - "문서 열기" 버튼: `/admin/rag/searches/{log_id}/document/{chunk_id}` 링크.
- 섹션 3: 조/항 위치 강조. `law_article_id` 가 `제1조`, `제1조(목적)` 등으로 저장되어 있으므로 그대로 표기.

### 4.3 문서 상세/다운로드 뷰

- 텍스트 프리뷰를 보여주고, 필요 시 전문 파일 다운로드 링크 제공 (`/admin/rag/files/...`).
- HWP/HWXP 파일은 브라우저 미리보기 대신 다운로드로 처리하거나, 추후 변환 서비스 도입 검토.

## 5. 구현 로드맵

| 단계 | 작업 | 담당 | 비고 |
| --- | --- | --- | --- |
| 1 | `RagLogRepository` 추가 및 로그 저장 로직 구현 | 백엔드 | `RagService` 내부에서 호출 |
| 2 | REST API 라우트 작성 (`/admin/rag/...`) | 백엔드 | FastAPI Router 사용 |
| 3 | 기본 HTML 템플릿 or React 페이지 초기 버전 | 프론트엔드 | 서버 렌더/SPA 중 선택 |
| 4 | 인증/인가 적용 | 백엔드 | 관리자 전용 |
| 5 | 배포/운영 문서 업데이트 | 공통 | README + 운영 문서 |

## 6. 테스트 계획

- **단위 테스트**: `RagLogRepository` 가 MongoDB에 expected schema로 저장하는지 검증.
- **Integration 테스트**: 검색 흐름에서 로그 기록 → `/admin/rag/searches` 호출 결과 필드 검증.
- **E2E 시나리오**: 관리자 페이지에서 특정 검색 건을 클릭해 문서 세부 정보 확인.

## 7. 향후 확장 포인트

- 검색 결과를 CSV/Excel로 내보내기.
- 규정 업데이트 이력과 연동하여 "최신/폐기" 여부 표시.
- 사용자별 검색 패턴 분석 대시보드.
- 알림 시스템: 특정 규정 조회가 많은 경우 Slack/Email로 알림.

---

## 8. 다음 액션

1. MongoDB에 `rag_search_logs` 컬렉션 생성 및 인덱스 (`queried_at` 역순).
2. `RagService` 에 로그 호출 삽입.
3. `/api/routes.py` 에 관리자용 라우터 초안 작성.
4. UI 목업 확정 후 구현 착수.

> **비고**: 현재 Mongo 문서 메타데이터에 `law_article_id`, `title`, `source_file` 등이 이미 구축되어 있으므로, 별도 추가 작업 없이 관리자 화면에서 조/항을 바로 표시할 수 있습니다.
