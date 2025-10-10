import requests
import json

# 언어 선택 매핑
language_map = {
    "1": ("KOR", "한국어"),
    "2": ("ENG", "영어"),
    "3": ("VI", "베트남어"),
    "4": ("JPN", "일본어"),
    "5": ("CHN", "중국어"),
}

def select_language():
    print("언어를 선택하세요:")
    for k, v in language_map.items():
        print(f"{k}. {v[1]}")
    while True:
        choice = input("번호 입력: ").strip()
        if choice in language_map:
            return language_map[choice][0]
        print("잘못된 입력입니다. 다시 선택하세요.")

def main():
    # FastAPI 라우터는 prefix="/api"로 등록되어 있으며, 현재 서버 엔드포인트는 /api/chat 입니다.
    url = "http://127.0.0.1:8000/api/chat"
    language = select_language()
    print(f"선택된 언어: {language}")
    
    # 마지막 RAG 메타데이터 저장
    last_rag_metadata = None

    while True:
        # RAG 원문 안내 표시
        prompt = "\n질문 입력 (종료: exit, 언어변경: /lang"
        if last_rag_metadata:
            prompt += ", RAG 원문: /rag"
        prompt += "): "
        
        msg = input(prompt).strip()
        
        if msg.lower() == "exit":
            print("테스트 종료.")
            break
        if msg.lower() in ["/lang", "/언어"]:
            language = select_language()
            print(f"언어가 변경되었습니다: {language}")
            continue
        
        # RAG 원문 보기 명령어
        if msg.lower() == "/rag":
            if not last_rag_metadata:
                print("⚠️ 아직 RAG 검색 결과가 없습니다. 먼저 질문을 입력하세요.")
                continue
            
            print("\n" + "=" * 80)
            print("📄 RAG 검색 원문 (마지막 질문)")
            print("=" * 80)
            print(f"규정 여부: {'예' if last_rag_metadata.get('is_regulation', False) else '아니오'}")
            print(f"검색 소스: {last_rag_metadata.get('context_source', 'N/A')}")
            print(f"검색 문서 수: {last_rag_metadata.get('hits_count', 0)}개")
            print(f"MongoDB 문서: {last_rag_metadata.get('document_count', 0)}개")
            print(f"프리뷰 문서: {last_rag_metadata.get('preview_count', 0)}개")
            
            # 출처 문서 정보 표시
            source_docs = last_rag_metadata.get("source_documents", [])
            if source_docs:
                # 유효한 문서만 필터링 (모든 필드가 비어있지 않은 문서)
                valid_docs = [
                    doc for doc in source_docs 
                    if doc.get("title") or doc.get("law_article_id") or doc.get("source_file")
                ]
                
                if valid_docs:
                    print("\n--- 📚 검색된 문서 출처 정보 ---")
                    for idx, doc in enumerate(valid_docs, 1):
                        print(f"\n[문서 {idx}]")
                        if doc.get("title"):
                            print(f"  제목: {doc['title']}")
                        if doc.get("law_article_id"):
                            print(f"  조항 ID: {doc['law_article_id']}")
                        if doc.get("source_file"):
                            print(f"  원본 파일: {doc['source_file']}")
                else:
                    print("\n⚠️ 출처 문서 메타데이터가 비어있습니다.")
            else:
                print("\n⚠️ 출처 문서 정보가 없습니다.")
            
            # 요약된 컨텍스트 우선 표시 (LLM이 <반영> 태그로 가공한 버전)
            if last_rag_metadata.get("condensed_context"):
                print("\n--- 📝 요약된 원문 (<반영> 태그 포함) ---")
                print(last_rag_metadata["condensed_context"])
            elif last_rag_metadata.get("raw_context"):
                print("\n--- 📄 원본 RAG 컨텍스트 (MongoDB) ---")
                print(last_rag_metadata["raw_context"])
            else:
                print("\n⚠️ 컨텍스트 정보가 없습니다.")
            
            print("=" * 80)
            continue

        payload = {"message": msg, "language": language}
        try:
            with requests.post(url, json=payload, stream=True, timeout=120) as resp:
                print("\n응답:")
                print("-" * 60)
                
                # JSON Lines 형식 파싱
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        msg_type = data.get("type")
                        
                        if msg_type == "delta":
                            # 텍스트 델타 출력 (줄바꿈 없이)
                            print(data.get("content", ""), end="", flush=True)
                        
                        elif msg_type == "metadata":
                            # 메타데이터 출력 (줄바꿈 후)
                            print("\n\n" + "=" * 60)
                            print("📊 프론트 정적데이터 전송 디버그:메타데이터:")
                            metadata = data.get("data", {})
                            
                            # RAG 정보 저장 및 출력
                            if "rag" in metadata and metadata["rag"]:
                                rag = metadata["rag"]
                                last_rag_metadata = rag  # RAG 메타데이터 저장
                                print(f"  🔍 RAG 검색:")
                                print(f"    - 규정 여부: {'예' if rag.get('is_regulation', False) else '아니오'}")
                                print(f"    - 검색 결과: {rag.get('hits_count', 0)}개 문서")
                                print(f"    - 소스: {rag.get('context_source', 'N/A')}")
                                if rag.get("has_condensed_context", False):
                                    print(f"    - 요약됨: {rag.get('condensed_context_length', 0)}자")
                                print(f"    💡 '/rag' 입력 시 검색된 원문을 확인할 수 있습니다.")
                            else:
                                # RAG 검색이 없었다면 초기화
                                last_rag_metadata = None
                            
                            # 함수 호출 정보
                            if "functions" in metadata and metadata["functions"]:
                                funcs = metadata["functions"]
                                print(f"  ⚙️  함수 호출: {len(funcs)}개")
                                for func in funcs:
                                    print(f"    - {func.get('name', 'Unknown')}")
                            
                            # 웹 검색 정보
                            if "web_search_status" in metadata:
                                status = metadata["web_search_status"]
                                print(f"  🌐 웹 검색: {status}")
                            
                            print("=" * 60)
                        
                        elif msg_type == "done":
                            # 완료 신호
                            print("\n\n✅ 응답 완료")
                    
                    except json.JSONDecodeError as e:
                        print(f"\n⚠️ JSON 파싱 오류: {e}")
                        print(f"   원본: {line[:100]}...")
                
                print("-" * 60)
        except Exception as e:
            print(f"❌ 요청 실패: {e}")

if __name__ == "__main__":
    main()