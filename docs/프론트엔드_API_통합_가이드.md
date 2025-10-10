# 챗봇 스트리밍 API - 프론트엔드 통합 가이드

> **대상**: 프론트엔드 개발자  
> **작성일**: 2025-10-10  
> **API 버전**: v1.0  
> **엔드포인트**: `POST /api/chat`

---

## 📋 목차

1. [API 개요](#1-api-개요)
2. [요청 방식](#2-요청-방식)
3. [응답 데이터 구조](#3-응답-데이터-구조)
4. [데이터 처리 방식](#4-데이터-처리-방식)
5. [메타데이터 활용 가이드](#5-메타데이터-활용-가이드)
6. [구현 예제](#6-구현-예제)
7. [에러 처리](#7-에러-처리)
8. [FAQ](#8-faq)

---

## 1. API 개요

### 📡 **기본 정보**

```
엔드포인트: POST /api/chat
Content-Type: application/json (요청)
Content-Type: application/x-ndjson (응답)
방식: Server-Sent Events (스트리밍)
```

### 🎯 **특징**

- **실시간 스트리밍**: 텍스트가 생성되는 즉시 전송
- **메타데이터 포함**: RAG 검색 결과, 함수 호출 정보 등
- **JSON Lines 포맷**: 한 줄에 하나의 JSON 객체
- **순서 보장**: delta → metadata → done 순서로 전송

---

## 2. 요청 방식

### 📤 **요청 형식**

```http
POST /api/chat HTTP/1.1
Host: your-domain.com
Content-Type: application/json

{
  "message": "졸업 규정이 뭐야?",
  "language": "KOR"
}
```

### 📝 **요청 필드**

| 필드 | 타입 | 필수 | 설명 | 기본값 |
|------|------|------|------|--------|
| `message` | string | ✅ | 사용자 질문 | - |
| `language` | string | ❌ | 응답 언어 코드 | `"KOR"` |

### 🌐 **지원 언어**

| 코드 | 언어 |
|------|------|
| `KOR` | 한국어 |
| `ENG` | 영어 |
| `VI` | 베트남어 |
| `JPN` | 일본어 |
| `CHN` | 중국어 |
| `UZB` | 우즈베크어 |
| `MNG` | 몽골어 |
| `IDN` | 인도네시아어 |

---

## 3. 응답 데이터 구조

### 📊 **전체 구조 (JSON Lines 형식)**

응답은 **여러 줄의 JSON 객체**로 구성됩니다. 각 줄은 독립적인 JSON 객체입니다.

```json
{"type":"delta","content":"안녕하세요"}
{"type":"delta","content":" 졸업"}
{"type":"delta","content":" 규정은"}
...
{"type":"metadata","data":{...}}
{"type":"done"}
```

---

### 🔹 **메시지 타입 3가지**

#### 1️⃣ **`delta` - 텍스트 청크 (실시간)**

```json
{
  "type": "delta",
  "content": "안녕하세요"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `type` | `"delta"` | 메시지 타입 (고정값) |
| `content` | string | 텍스트 조각 (한 단어~여러 단어) |

**특징**:
- OpenAI가 생성한 텍스트를 **실시간으로 전달**
- 여러 개의 delta가 연속으로 옴
- 화면에 **즉시 표시** (줄바꿈 없이 이어서)

---

#### 2️⃣ **`metadata` - 메타데이터 (텍스트 완료 후)**

```json
{
  "type": "metadata",
  "data": {
    "rag": {
      "is_regulation": true,
      "gate_reason": "LLM 판단: 졸업 규정 관련 질문",
      "context_source": "mongo",
      "hits_count": 5,
      "document_count": 3,
      "preview_count": 0,
      "chunk_ids": ["673abc123...", "673def456..."],
      "raw_context": "제1조 졸업 요건 ① 학생은...",
      "condensed_context": "<반영>...</반영>",
      "source_documents": [
        {
          "title": "졸업 규정",
          "law_article_id": "제3조",
          "source_file": "3-4-1 졸업규정.pdf"
        }
      ]
    },
    "functions": [
      {
        "name": "search_internet",
        "arguments": {"query": "한라대 졸업 요건"},
        "output": "검색 결과: ...",
        "call_id": "call_123",
        "is_fallback": false
      }
    ],
    "web_search_status": "ok"
  }
}
```

| 최상위 필드 | 타입 | 설명 |
|------------|------|------|
| `type` | `"metadata"` | 메시지 타입 (고정값) |
| `data` | object | 메타데이터 객체 |
| `data.rag` | object\|null | RAG 검색 정보 |
| `data.functions` | array | 호출된 함수 목록 |
| `data.web_search_status` | string | 웹검색 상태 |

---

##### 📚 **`data.rag` 구조 (RAG 검색 정보)**

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `is_regulation` | boolean | 규정 질문 여부 | `true` |
| `gate_reason` | string | 규정 판단 근거 | `"LLM 판단: 졸업 규정..."` |
| `context_source` | string | 컨텍스트 출처 | `"mongo"` / `"preview"` / `"none"` |
| `hits_count` | number | Pinecone 검색 히트 수 | `5` |
| `document_count` | number | MongoDB 문서 수 | `3` |
| `preview_count` | number | Pinecone 미리보기 사용 수 | `0` |
| `chunk_ids` | string[] | MongoDB 청크 ID 목록 | `["673abc...", ...]` |
| `raw_context` | string | 원본 RAG 컨텍스트 (MongoDB) | `"제1조 졸업 요건..."` |
| `condensed_context` | string | 요약된 컨텍스트 (`<반영>` 태그) | `"<반영>...</반영>"` |
| `source_documents` | array | 검색된 문서 출처 정보 | (아래 참조) |

**`context_source` 값 설명**:
- `"mongo"`: MongoDB에서 실제 문서 본문을 가져옴 (정상)
- `"preview"`: MongoDB에서 못 찾아서 Pinecone 미리보기 사용 (fallback)
- `"none"`: 검색 결과 없음 또는 규정 질문이 아님

---

##### 📄 **`source_documents` 구조 (출처 문서 정보)**

```json
{
  "source_documents": [
    {
      "title": "졸업 규정",
      "law_article_id": "제3조",
      "source_file": "3-4-1 졸업규정.pdf"
    },
    {
      "title": "학사 규정",
      "law_article_id": "제5조",
      "source_file": "3-2-1 학사규정.pdf"
    }
  ]
}
```

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `title` | string | 문서 제목 | `"졸업 규정"` |
| `law_article_id` | string | 조항 ID | `"제3조"` |
| `source_file` | string | 원본 파일명 | `"3-4-1 졸업규정.pdf"` |

---

##### ⚙️ **`data.functions` 구조 (함수 호출 정보)**

```json
{
  "functions": [
    {
      "name": "search_internet",
      "arguments": {"query": "한라대 졸업 요건"},
      "output": "검색 결과: 한라대학교 졸업 요건은...",
      "call_id": "call_abc123",
      "is_fallback": false
    },
    {
      "name": "get_halla_cafeteria_menu",
      "arguments": {"date": "오늘", "meal": "중식"},
      "output": "🍽️ 오늘의 중식 메뉴: 김치찌개, 불고기...",
      "call_id": "cafeteria_auto",
      "is_fallback": true
    }
  ]
}
```

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `name` | string | 함수 이름 | `"search_internet"` |
| `arguments` | object | 함수 인자 | `{"query": "..."}` |
| `output` | string | 함수 실행 결과 | `"검색 결과: ..."` |
| `call_id` | string | 호출 ID (디버깅용) | `"call_abc123"` |
| `is_fallback` | boolean | 보강 호출 여부 (규칙 기반) | `false` |

**주요 함수**:
- `search_internet`: 웹검색 (DuckDuckGo)
- `get_halla_cafeteria_menu`: 학식 메뉴 조회
- `get_notice`: 공지사항 조회

---

##### 🌐 **`web_search_status` 값**

| 값 | 설명 |
|----|------|
| `"ok"` | 웹검색 정상 완료 |
| `"empty-or-error"` | 검색 결과 없음 또는 오류 |
| `"not-run"` | 웹검색 실행 안 함 |

---

#### 3️⃣ **`done` - 완료 신호**

```json
{
  "type": "done"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `type` | `"done"` | 메시지 타입 (고정값) |

**특징**:
- 스트리밍 **종료 신호**
- 이 메시지 이후 더 이상 데이터 없음
- 연결 닫기 또는 다음 질문 대기

---

## 4. 데이터 처리 방식

### 🔄 **전체 흐름**

```
1. 요청 전송
   POST /api/chat
   {"message": "졸업규정이 뭐야?", "language": "KOR"}
          ↓
2. 연결 성공
   Response 객체 생성
   스트림 읽기 시작
          ↓
3. 텍스트 스트리밍 (실시간)
   {"type":"delta","content":"안녕하세요"} → 화면 출력
   {"type":"delta","content":" 졸업"}      → 화면 출력
   {"type":"delta","content":" 규정은"}    → 화면 출력
   ...
          ↓
4. 메타데이터 수신 (텍스트 완료 후)
   {"type":"metadata","data":{...}}
   → RAG 정보 저장
   → 요약 배지 표시
          ↓
5. 완료 신호
   {"type":"done"}
   → 스트림 종료
   → 연결 닫기
```

---

### 📝 **처리 단계별 상세**

#### **Step 1: HTTP 요청 전송**

```javascript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: '졸업 규정이 뭐야?',
    language: 'KOR'
  })
});
```

---

#### **Step 2: 스트림 읽기 시작**

```javascript
const reader = response.body
  .pipeThrough(new TextDecoderStream())  // UTF-8 디코딩
  .getReader();

let buffer = '';
```

**주의사항**:
- **반드시 `TextDecoderStream()` 사용** (UTF-8 한글 깨짐 방지)
- `buffer` 변수로 불완전한 줄 임시 저장

---

#### **Step 3: 한 줄씩 파싱**

```javascript
while (true) {
  const { value, done } = await reader.read();
  
  if (done) break;  // 스트림 종료
  
  buffer += value;
  const lines = buffer.split('\n');
  buffer = lines.pop() || '';  // 마지막 불완전한 줄 보관
  
  for (const line of lines) {
    if (!line.trim()) continue;  // 빈 줄 무시
    
    const message = JSON.parse(line);
    
    // 타입별 처리
    if (message.type === 'delta') {
      // 텍스트 청크 처리
    } else if (message.type === 'metadata') {
      // 메타데이터 처리
    } else if (message.type === 'done') {
      // 완료 처리
    }
  }
}
```

**왜 `buffer`가 필요한가?**
- 네트워크는 임의의 크기로 데이터를 보냄
- 한 줄의 중간에서 끊길 수 있음
- 예: `{"type":"delta","con` ← 불완전
- `buffer`에 저장 후 다음 청크와 합침

---

#### **Step 4: 타입별 처리**

##### ✅ **delta 처리**

```javascript
if (message.type === 'delta') {
  // 실시간 텍스트 출력
  fullText += message.content;
  updateChatUI(fullText);  // UI 즉시 업데이트
}
```

##### ✅ **metadata 처리**

```javascript
if (message.type === 'metadata') {
  const metadata = message.data;
  
  // 1. RAG 정보 저장
  if (metadata.rag) {
    currentRagMetadata = metadata.rag;
    
    // 2. UI 배지 표시
    if (metadata.rag.is_regulation) {
      showBadge('📚 규정 문서 참조');
    }
  }
  
  // 3. 웹검색 정보 표시
  if (metadata.web_search_status === 'ok') {
    showBadge('🔍 웹검색 결과 포함');
  }
  
  // 4. 함수 호출 정보 표시
  metadata.functions?.forEach(func => {
    if (func.name === 'get_halla_cafeteria_menu') {
      showBadge('🍽️ 학식 메뉴 조회');
    }
  });
}
```

##### ✅ **done 처리**

```javascript
if (message.type === 'done') {
  console.log('✅ 응답 완료');
  break;  // 루프 종료
}
```

---

## 5. 메타데이터 활용 가이드

### 🎯 **메타데이터로 할 수 있는 것**

#### 1️⃣ **RAG 검색 결과 표시**

```javascript
if (metadata.rag?.is_regulation) {
  // ✅ 규정 질문임을 사용자에게 알림
  showBadge('📚 규정 문서 참조');
  
  // 문서 개수 표시
  showInfo(`${metadata.rag.document_count}개 문서 참조`);
}
```

---

#### 2️⃣ **출처 문서 정보 표시**

```javascript
const sourceDocs = metadata.rag?.source_documents || [];

if (sourceDocs.length > 0) {
  const sourceList = sourceDocs.map(doc => `
    <div class="source-doc">
      <h4>${doc.title}</h4>
      <p>조항: ${doc.law_article_id}</p>
      <p>파일: ${doc.source_file}</p>
    </div>
  `).join('');
  
  showSourcesModal(sourceList);
}
```

**UI 예시**:
```
┌─────────────────────────────────┐
│ 📚 참조 문서 (3개)              │
├─────────────────────────────────┤
│ 📄 졸업 규정                    │
│    조항: 제3조                  │
│    파일: 3-4-1 졸업규정.pdf     │
├─────────────────────────────────┤
│ 📄 학사 규정                    │
│    조항: 제5조                  │
│    파일: 3-2-1 학사규정.pdf     │
└─────────────────────────────────┘
```

---

#### 3️⃣ **원문 보기 기능**

```javascript
// 버튼 클릭 시
function showRawContext() {
  if (!currentRagMetadata) {
    alert('RAG 검색 결과가 없습니다.');
    return;
  }
  
  // 요약본 우선 표시
  const context = currentRagMetadata.condensed_context 
    || currentRagMetadata.raw_context;
  
  showModal({
    title: '📄 검색된 원문',
    content: context,
    sources: currentRagMetadata.source_documents
  });
}
```

**UI 예시**:
```
┌─────────────────────────────────────────────┐
│ 📄 검색된 원문                              │
├─────────────────────────────────────────────┤
│ <반영>                                      │
│ 제3조(졸업 요건) ① 학생은 다음 각 호의     │
│ 요건을 모두 충족하여야 한다:                │
│ 1. 총 140학점 이상 이수                     │
│ 2. 전공 60학점 이상 이수                    │
│ 3. 교양 30학점 이상 이수                    │
│ </반영>                                     │
├─────────────────────────────────────────────┤
│ 📚 출처: 졸업 규정 (제3조)                  │
│ 📁 파일: 3-4-1 졸업규정.pdf                 │
└─────────────────────────────────────────────┘
```

---

#### 4️⃣ **신뢰도 표시**

```javascript
function calculateTrustScore(metadata) {
  let score = 0;
  
  // RAG 검색 성공
  if (metadata.rag?.context_source === 'mongo') {
    score += 50;  // MongoDB 문서 사용 (높은 신뢰도)
  } else if (metadata.rag?.context_source === 'preview') {
    score += 20;  // 미리보기 사용 (낮은 신뢰도)
  }
  
  // 웹검색 성공
  if (metadata.web_search_status === 'ok') {
    score += 30;
  }
  
  // 함수 호출 성공
  if (metadata.functions?.length > 0) {
    score += 20;
  }
  
  return Math.min(score, 100);
}

const trustScore = calculateTrustScore(metadata);
showTrustBadge(trustScore);  // "신뢰도: 80%" 표시
```

---

#### 5️⃣ **디버깅/로깅**

```javascript
// 개발자 콘솔용 상세 정보
console.group('📊 RAG 메타데이터');
console.log('규정 여부:', metadata.rag?.is_regulation);
console.log('판단 근거:', metadata.rag?.gate_reason);
console.log('검색 소스:', metadata.rag?.context_source);
console.log('문서 수:', metadata.rag?.document_count);
console.log('청크 ID:', metadata.rag?.chunk_ids);
console.log('웹검색 상태:', metadata.web_search_status);
console.log('함수 호출:', metadata.functions?.map(f => f.name));
console.groupEnd();

// 사용자 피드백 수집
sendAnalytics({
  is_regulation: metadata.rag?.is_regulation,
  document_count: metadata.rag?.document_count,
  web_search_used: metadata.web_search_status === 'ok',
  functions_used: metadata.functions?.map(f => f.name)
});
```

---

#### 6️⃣ **조건부 UI 렌더링**

```javascript
function renderChatResponse(text, metadata) {
  const container = document.createElement('div');
  
  // 1. 텍스트 영역
  const textArea = document.createElement('p');
  textArea.textContent = text;
  container.appendChild(textArea);
  
  // 2. 배지 영역
  const badgeArea = document.createElement('div');
  badgeArea.className = 'badges';
  
  if (metadata.rag?.is_regulation) {
    badgeArea.innerHTML += '<span class="badge">📚 규정 참조</span>';
  }
  
  if (metadata.web_search_status === 'ok') {
    badgeArea.innerHTML += '<span class="badge">🔍 웹검색</span>';
  }
  
  if (metadata.functions?.some(f => f.name === 'get_halla_cafeteria_menu')) {
    badgeArea.innerHTML += '<span class="badge">🍽️ 학식</span>';
  }
  
  container.appendChild(badgeArea);
  
  // 3. 출처 버튼 (RAG 검색 시에만)
  if (metadata.rag?.source_documents?.length > 0) {
    const sourceBtn = document.createElement('button');
    sourceBtn.textContent = '📄 출처 보기';
    sourceBtn.onclick = () => showSourcesModal(metadata.rag.source_documents);
    container.appendChild(sourceBtn);
  }
  
  return container;
}
```

---

## 6. 구현 예제

### 🔥 **React (완전한 예제)**

```jsx
import { useState } from 'react';

function ChatBot() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [metadata, setMetadata] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setResponse('');
    setMetadata(null);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          language: 'KOR'
        })
      });

      const reader = res.body
        .pipeThrough(new TextDecoderStream())
        .getReader();

      let buffer = '';
      let fullText = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += value;
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          
          const msg = JSON.parse(line);

          if (msg.type === 'delta') {
            fullText += msg.content;
            setResponse(fullText);  // 실시간 업데이트
            
          } else if (msg.type === 'metadata') {
            setMetadata(msg.data);
            
          } else if (msg.type === 'done') {
            setIsLoading(false);
          }
        }
      }
    } catch (error) {
      console.error('스트리밍 에러:', error);
      setIsLoading(false);
    }
  };

  return (
    <div className="chatbot">
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="질문을 입력하세요"
        />
        <button type="submit" disabled={isLoading}>
          전송
        </button>
      </form>

      {/* 답변 영역 */}
      <div className="response">
        {response}
      </div>

      {/* 메타데이터 배지 */}
      {metadata && (
        <div className="metadata-badges">
          {metadata.rag?.is_regulation && (
            <span className="badge">📚 규정 문서 참조</span>
          )}
          {metadata.web_search_status === 'ok' && (
            <span className="badge">🔍 웹검색 결과</span>
          )}
          {metadata.functions?.some(f => f.name === 'get_halla_cafeteria_menu') && (
            <span className="badge">🍽️ 학식 메뉴</span>
          )}
        </div>
      )}

      {/* 출처 버튼 */}
      {metadata?.rag?.source_documents?.length > 0 && (
        <button onClick={() => alert('출처 모달 구현 필요')}>
          📄 출처 보기 ({metadata.rag.source_documents.length}개)
        </button>
      )}
    </div>
  );
}

export default ChatBot;
```

---

### 🌟 **Vue.js (완전한 예제)**

```vue
<template>
  <div class="chatbot">
    <form @submit.prevent="handleSubmit">
      <input
        v-model="message"
        type="text"
        placeholder="질문을 입력하세요"
      />
      <button type="submit" :disabled="isLoading">전송</button>
    </form>

    <!-- 답변 영역 -->
    <div class="response">{{ response }}</div>

    <!-- 메타데이터 배지 -->
    <div v-if="metadata" class="metadata-badges">
      <span v-if="metadata.rag?.is_regulation" class="badge">
        📚 규정 문서 참조
      </span>
      <span v-if="metadata.web_search_status === 'ok'" class="badge">
        🔍 웹검색 결과
      </span>
      <span
        v-if="metadata.functions?.some(f => f.name === 'get_halla_cafeteria_menu')"
        class="badge"
      >
        🍽️ 학식 메뉴
      </span>
    </div>

    <!-- 출처 버튼 -->
    <button
      v-if="metadata?.rag?.source_documents?.length > 0"
      @click="showSources"
    >
      📄 출처 보기 ({{ metadata.rag.source_documents.length }}개)
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const message = ref('');
const response = ref('');
const metadata = ref(null);
const isLoading = ref(false);

const handleSubmit = async () => {
  isLoading.value = true;
  response.value = '';
  metadata.value = null;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message.value,
        language: 'KOR'
      })
    });

    const reader = res.body
      .pipeThrough(new TextDecoderStream())
      .getReader();

    let buffer = '';
    let fullText = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += value;
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        
        const msg = JSON.parse(line);

        if (msg.type === 'delta') {
          fullText += msg.content;
          response.value = fullText;
          
        } else if (msg.type === 'metadata') {
          metadata.value = msg.data;
          
        } else if (msg.type === 'done') {
          isLoading.value = false;
        }
      }
    }
  } catch (error) {
    console.error('스트리밍 에러:', error);
    isLoading.value = false;
  }
};

const showSources = () => {
  alert('출처 모달 구현 필요');
};
</script>
```

---

### 💻 **Vanilla JavaScript (완전한 예제)**

```html
<!DOCTYPE html>
<html>
<head>
  <title>챗봇 테스트</title>
  <style>
    .badge {
      background: #e3f2fd;
      padding: 4px 8px;
      border-radius: 4px;
      margin: 4px;
      display: inline-block;
    }
    .response {
      background: #f5f5f5;
      padding: 16px;
      margin: 16px 0;
      border-radius: 8px;
      min-height: 100px;
    }
    .source-btn {
      background: #2196F3;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <h1>챗봇 스트리밍 테스트</h1>
  
  <form id="chat-form">
    <input type="text" id="message" placeholder="질문을 입력하세요" />
    <button type="submit">전송</button>
  </form>

  <div id="response" class="response"></div>
  <div id="badges"></div>
  <div id="source-btn-container"></div>

  <script>
    let currentMetadata = null;

    document.getElementById('chat-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const message = document.getElementById('message').value;
      const responseDiv = document.getElementById('response');
      const badgesDiv = document.getElementById('badges');
      const sourceBtnContainer = document.getElementById('source-btn-container');
      
      responseDiv.textContent = '';
      badgesDiv.innerHTML = '';
      sourceBtnContainer.innerHTML = '';
      currentMetadata = null;

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, language: 'KOR' })
      });

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      
      let buffer = '';
      let fullText = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += value;
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          
          const msg = JSON.parse(line);

          if (msg.type === 'delta') {
            fullText += msg.content;
            responseDiv.textContent = fullText;
            
          } else if (msg.type === 'metadata') {
            currentMetadata = msg.data;
            
            // 배지 표시
            if (currentMetadata.rag?.is_regulation) {
              badgesDiv.innerHTML += '<span class="badge">📚 규정 문서 참조</span>';
            }
            if (currentMetadata.web_search_status === 'ok') {
              badgesDiv.innerHTML += '<span class="badge">🔍 웹검색 결과</span>';
            }
            if (currentMetadata.functions?.some(f => f.name === 'get_halla_cafeteria_menu')) {
              badgesDiv.innerHTML += '<span class="badge">🍽️ 학식 메뉴</span>';
            }
            
            // 출처 버튼
            if (currentMetadata.rag?.source_documents?.length > 0) {
              const btn = document.createElement('button');
              btn.className = 'source-btn';
              btn.textContent = `📄 출처 보기 (${currentMetadata.rag.source_documents.length}개)`;
              btn.onclick = showSources;
              sourceBtnContainer.appendChild(btn);
            }
          }
        }
      }
    });

    function showSources() {
      if (!currentMetadata?.rag?.source_documents) return;
      
      const sources = currentMetadata.rag.source_documents
        .map((doc, idx) => `
          [문서 ${idx + 1}]
          제목: ${doc.title}
          조항: ${doc.law_article_id}
          파일: ${doc.source_file}
        `)
        .join('\n\n');
      
      alert('📚 참조 문서\n\n' + sources);
    }
  </script>
</body>
</html>
```

---

## 7. 에러 처리

### ⚠️ **주요 에러 케이스**

#### 1️⃣ **네트워크 에러**

```javascript
try {
  const res = await fetch('/api/chat', {...});
  
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  }
  
  // 스트리밍 처리...
  
} catch (error) {
  if (error.name === 'TypeError' && error.message.includes('fetch')) {
    console.error('네트워크 연결 실패:', error);
    showError('서버에 연결할 수 없습니다. 네트워크를 확인해주세요.');
  } else {
    console.error('알 수 없는 에러:', error);
    showError('오류가 발생했습니다. 다시 시도해주세요.');
  }
}
```

---

#### 2️⃣ **JSON 파싱 에러**

```javascript
for (const line of lines) {
  if (!line.trim()) continue;
  
  try {
    const msg = JSON.parse(line);
    // 처리...
  } catch (e) {
    console.error('JSON 파싱 에러:', e);
    console.log('원본 데이터:', line.substring(0, 100));
    // 파싱 실패한 줄은 건너뛰고 계속 진행
    continue;
  }
}
```

---

#### 3️⃣ **타임아웃 처리**

```javascript
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 60000);  // 60초

try {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, language }),
    signal: controller.signal  // 타임아웃 신호
  });
  
  // 스트리밍 처리...
  
  clearTimeout(timeout);
  
} catch (error) {
  if (error.name === 'AbortError') {
    console.error('요청 타임아웃');
    showError('응답 시간이 초과되었습니다. 다시 시도해주세요.');
  }
}
```

---

#### 4️⃣ **UTF-8 깨짐 방지**

```javascript
// ✅ 올바른 방법
const reader = response.body
  .pipeThrough(new TextDecoderStream())  // UTF-8 디코딩
  .getReader();

// ❌ 잘못된 방법
const reader = response.body.getReader();  // Uint8Array 반환 (깨짐)
```

---

## 8. FAQ

### Q1. 스트리밍 중간에 연결이 끊기면?

**A**: 이미 받은 텍스트는 유효합니다. 에러 처리로 사용자에게 알려주세요.

```javascript
try {
  // 스트리밍...
} catch (error) {
  console.error('연결 끊김:', error);
  showWarning('연결이 끊어졌습니다. 여기까지의 답변만 표시됩니다.');
  // 이미 받은 response는 그대로 표시
}
```

---

### Q2. 메타데이터가 없는 경우도 있나요?

**A**: 네, 있습니다.

```javascript
// RAG 검색 안 됨 (일반 대화)
{
  "type": "metadata",
  "data": {
    "rag": null,  // ← 없음
    "functions": [],
    "web_search_status": "not-run"
  }
}
```

**처리 방법**:
```javascript
if (metadata.rag) {
  // RAG 정보 표시
} else {
  // 일반 대화 (메타데이터 없음)
}
```

---

### Q3. `delta`의 `content`가 비어있을 수 있나요?

**A**: 드물지만 가능합니다. 필터링하세요.

```javascript
if (msg.type === 'delta') {
  if (msg.content) {  // 빈 문자열 체크
    fullText += msg.content;
    setResponse(fullText);
  }
}
```

---

### Q4. 여러 사용자가 동시에 질문하면?

**A**: 각 요청은 독립적입니다. 세션 관리는 프론트엔드 책임입니다.

```javascript
// 각 질문마다 별도 상태 관리
const [conversations, setConversations] = useState([
  { id: 1, messages: [...] },
  { id: 2, messages: [...] }
]);
```

---

### Q5. 모바일에서도 작동하나요?

**A**: 네, `fetch`와 `ReadableStream`은 모든 모던 브라우저에서 지원됩니다.

**브라우저 지원**:
- Chrome/Edge: ✅
- Firefox: ✅
- Safari: ✅ (iOS 14.5+)
- Opera: ✅

---

### Q6. 디버깅은 어떻게 하나요?

**A**: 각 메시지를 콘솔에 출력하세요.

```javascript
for (const line of lines) {
  if (!line.trim()) continue;
  
  const msg = JSON.parse(line);
  console.log('[STREAM]', msg.type, msg);  // 디버깅 로그
  
  // 처리 로직...
}
```

---

## 📚 관련 문서

- [백엔드 stream_chat() 구현 가이드](./챗봇_로직_분리_계획.md)
- [RAG 시스템 구조](./RAG_분리_계획.md)
- [JSON Lines 포맷 명세](https://jsonlines.org/)
- [Fetch API - Streams](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams)

---

## 🔄 변경 이력

| 날짜 | 변경 내용 |
|------|-----------|
| 2025-10-10 | 초기 문서 작성 (메타데이터 구조, 처리 방식, 활용 가이드 포함) |

---

## 📞 문의

기술 지원이 필요하시면 백엔드 팀에 문의해주세요.
