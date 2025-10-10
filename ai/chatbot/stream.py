import math
import os
import json
from typing import Any, Dict, List, Optional, AsyncGenerator

# 새로운 import 경로
from app.ai.chatbot.config import model, client
from app.ai.chatbot.metadata import FunctionCallMetadata, RagMetadata, ChatMetadata
from app.ai.functions import FunctionCalling, tools
from app.ai.rag.service import RagService

class ChatbotStream:
    def __init__(self, model,system_role,instruction,**kwargs):
        """
        초기화:
          - context 리스트 생성 및 시스템 역할 설정
          - sub_contexts 서브 대화방 문맥을 저장할 딕셔너리 {필드이름,문맥,요약,질문} 구성
          - current_field = 현재 대화방 추적 (기본값: 메인 대화방
          - openai.api_key 설정
          - 사용할 모델명 저장
          - 사용자 이름
        """
        self.context = [{"role": "system","content": system_role}]
               
        self.current_field = "main"
        
        self.model = model
        self.instruction=instruction

        self.max_token_size = 16 * 1024 #최대 토큰이상을 쓰면 오류가발생 따라서 토큰 용량관리가 필요.
        self.available_token_rate = 0.9#최대토큰의 90%만 쓰겠다.

        # 디버그 플래그 (환경변수 RAG_DEBUG로 제어: 기본 활성화)
        self.debug = os.getenv("RAG_DEBUG", "1") not in ("0", "false", "False")

        # Phase 2: 모듈형 RAG 서비스 인스턴스화
        self.rag_service = RagService(debug_fn=self._dbg)
        self._last_rag_result = None
        self._last_web_status: Optional[str] = None
        
        # Phase 2: 함수 호출 관련 인스턴스화
        self.func_calling = FunctionCalling(model=model)
        self.tools = tools
        self.available_functions = self.func_calling.available_functions if hasattr(self.func_calling, 'available_functions') else {}

    def _dbg(self, msg: str):
        """작은 디버그 헬퍼: RAG 관련 내부 상태를 보기 쉽게 출력."""
        if self.debug:
            print(f"[RAG-DEBUG] {msg}")

    def add_user_message_in_context(self, message: str):
        """
        사용자 메시지 추가:
          - 사용자가 입력한 message를 context에 user 역할로 추가
        """
        assistant_message = {
            "role": "user",
            "content": message,
        }
        if self.current_field == "main":
            self.context.append(assistant_message)

    #전송부
    def _send_request_Stream(self,temp_context=None):
        
        completed_text = ""

        if temp_context is None:
           current_context = self.get_current_context()
           openai_context = self.to_openai_context(current_context)
           stream = client.responses.create(
            model=self.model,
            input=openai_context,  
            top_p=1,
            stream=True,
            
            text={
                "format": {
                    "type": "text"  # 또는 "json_object" 등 (Structured Output 사용 시)
                }
            }
                )
        else:  
           stream = client.responses.create(
            model=self.model,
            input=temp_context,  # user/assistant 역할 포함된 list 구조
            top_p=1,
            stream=True,
            text={
                "format": {
                    "type": "text"  # 또는 "json_object" 등 (Structured Output 사용 시)
                }
            }
                )
        
        loading = True  # delta가 나오기 전까지 로딩 중 상태 유지       
        for event in stream:
            #print(f"event: {event}")
            match event.type:
                case "response.created":
                    print("[🤖 응답 생성 시작]")
                    loading = True
                    # 로딩 애니메이션용 대기 시작
                    print("⏳ GPT가 응답을 준비 중입니다...")
                    
                case "response.output_text.delta":
                    if loading:
                        print("\n[💬 응답 시작됨 ↓]")
                        loading = False
                    # 글자 단위 출력
                    print(event.delta, end="", flush=True)
                 

                case "response.in_progress":
                    print("[🌀 응답 생성 중...]")

                case "response.output_item.added":
                    if getattr(event.item, "type", None) == "reasoning":
                        print("[🧠 GPT가 추론을 시작합니다...]")
                    elif getattr(event.item, "type", None) == "message":
                        print("[📩 메시지 아이템 추가됨]")
                #ResponseOutputItemDoneEvent는 우리가 case "response.output_item.done"에서 잡아야 해
                case "response.output_item.done":
                    item = event.item
                    if item.type == "message" and item.role == "assistant":
                        for part in item.content:
                            if getattr(part, "type", None) == "output_text":
                                completed_text= part.text
                case "response.completed":
                    print("\n")
                    #print(f"\n📦 최종 전체 출력: \n{completed_text}")
                case "response.failed":
                    print("❌ 응답 생성 실패")
                case "error":
                    print("⚠️ 스트리밍 중 에러 발생!")
                case _:
                    
                    print(f"[📬 기타 이벤트 감지: {event.type}]")
        return completed_text
  
  
    def send_request_Stream(self):
      self.context[-1]['content']+=self.instruction
      return self._send_request_Stream()
    #챗봇에 맞게 문맥 파싱
    def add_response(self, response):
        response_message = {
            "role" : response['choices'][0]['message']["role"],
            "content" : response['choices'][0]['message']["content"],            
        }
        self.context.append(response_message)

    def add_response_stream(self, response):
            """
                챗봇 응답을 현재 대화방의 문맥에 추가합니다.
                
                Args:
                    response (str): 챗봇이 생성한 응답 텍스트.
                """
            assistant_message = {
            "role": "assistant",
            "content": response,
           
        }
            self.context.append(assistant_message)

    def get_response(self, response_text: str):
        """
        응답내용반환:
          - 메시지를 콘솔(또는 UI) 출력 후, 그대로 반환
        """
        print(response_text['choices'][0]['message']['content'])
        return response_text
#마지막 지침제거
    def clean_context(self):
        '''
        1.context리스트에 마지막 인덱스부터 처음까지 순회한다
        2."instruction:\n"을 기준으로 문자열을 나눈다..첫user을 찾으면 아래 과정을 진행한다,
        3.첫 번째 부분 [0]만 가져온다. (즉, "instruction:\n" 이전의 문자열만 남긴다.)
        4.strip()을 적용하여 앞뒤의 공백이나 개행 문자를 제거한다.
        '''
        for idx in reversed(range(len(self.context))):
            if self.context[idx]['role']=='user':
                self.context[idx]["content"]=self.context[idx]['content'].split('instruction:\n')[0].strip()
                break
#질의응답 토큰 관리
    def handle_token_limit(self, response):
        # 누적 토큰 수가 임계점을 넘지 않도록 제어한다.
        try:
            current_usage_rate = response['usage']['total_tokens'] / self.max_token_size
            exceeded_token_rate = current_usage_rate - self.available_token_rate
            if exceeded_token_rate > 0:
                remove_size = math.ceil(len(self.context) / 10)
                self.context = [self.context[0]] + self.context[remove_size+1:]
        except Exception as e:
            print(f"handle_token_limit exception:{e}")
            
    def to_openai_context(self, context):
        return [{"role":v["role"], "content":v["content"]} for v in context]

    def get_current_context(self):
        """현재 메인 컨텍스트 반환"""
        return self.context

    def get_rag_context(self, user_question: str):
        """RAG 컨텍스트만 준비하여 반환 (없으면 None). 여기서부터 사용자 메시지는 질문으로 취급."""
        result = self.rag_service.retrieve_context(user_question)
        self._last_rag_result = result
        return result.merged_documents_text

    @property
    def last_rag_result(self):
        """최근 RAG 검색 결과를 노출합니다 (없으면 None)."""
        return self._last_rag_result or self.rag_service.last_result
    def get_response_from_db_only(self, user_question: str):
        self._dbg("get_response_from_db_only: start")
        rag_result = self.rag_service.retrieve_context(user_question)
        rag_context = rag_result.merged_documents_text
        if rag_context is None:
            self._dbg("기억검색 아님")
            return False

        # LLM 호출할 context 구성: system 메시지 + DB 내용(system role) + user 질문
        context = [
            {"role": "system", "content": "당신은 학사 규정 관련 질문에 답변하는 챗봇입니다. 아래 내용을 참고하여 정확하게 답변하세요."},
            {"role": "system", "content": rag_context},
            {"role": "user", "content": user_question},
        ]
        self._dbg(
            f"get_response_from_db_only: messages=[system, system(ctx:{len(rag_context)} chars), user] model={self.model}"
        )

        return self._send_request_Stream(temp_context=self.to_openai_context(context))

    # ==========================================
    # Phase 2: 헬퍼 메서드 구현 (routes.py → stream.py)
    # ==========================================

    def _get_language_instruction(self, language: str) -> str:
        """
        언어 코드에 따른 응답 지침 반환
        
        Args:
            language: 언어 코드 (KOR, ENG, VI, JPN, CHN, UZB, MNG, IDN)
        
        Returns:
            str: 해당 언어에 맞는 응답 지침
        """
        instruction_map = {
            "KOR": "한국어로 정중하고 따뜻하게 답해주세요.",
            "ENG": "Please respond kindly in English.",
            "VI": "Vui lòng trả lời bằng tiếng Việt một cách nhẹ nhàng.",
            "JPN": "日本語で丁寧に温かく答えてください。",
            "CHN": "请用中文亲切地回答。",
            "UZB": "Iltimos, o'zbek tilida samimiy va hurmat bilan javob bering.",
            "MNG": "Монгол хэлээр эелдэг, дулаахан хариулна уу.",
            "IDN": "Tolong jawab dengan ramah dan hangat dalam bahasa Indonesia."
        }
        return instruction_map.get(language, instruction_map["KOR"])

    async def _condense_rag_context(self, user_question: str, raw_context: str) -> str:
        """
        긴 RAG 컨텍스트를 사용자 질문에 맞게 요약
        
        - 표/번호조항의 전체 맥락 포함 (최소 15줄)
        - 주석(주) 포함
        - 원문 구조 유지
        
        Args:
            user_question: 사용자 질문
            raw_context: 원본 RAG 컨텍스트
        
        Returns:
            str: 요약된 컨텍스트 (실패 시 원본 일부 반환)
        """
        self._dbg(f"[CONDENSE] 시작 - 원본 길이: {len(raw_context)}자, 질문: {user_question[:50]}...")
        
        def _sanitize_text(txt: str) -> str:
            """제어문자 제거 및 태그 충돌 방지"""
            if not isinstance(txt, str):
                txt = str(txt)
            # 간단 제어문자 필터링 (LF, TAB 제외)
            txt = ''.join(ch for ch in txt if ch in ('\n', '\t') or (ord(ch) >= 32 and ch != 127))
            # 태그 조기 종료 방지
            txt = txt.replace("</기억검색>", "[/기억검색]")
            # 과도한 길이 클램프
            max_len = 30000
            return txt[:max_len]

        sanitized_rag = _sanitize_text(raw_context)
        self._dbg(f"[CONDENSE] Sanitized 길이: {len(sanitized_rag)}자")

        condense_prompt = [
            {
                "role": "system",
                "content": (
                                    f"""
                당신은 긴 규정/세칙 문서 묶음에서 사용자 질문과 직접 관련된 부분을 "넓은 맥락"으로 추출·표시하는 어시스턴트입니다.
                규칙(넓은 맥락 포함):
                1) 원문 전체는 <기억검색> 태그 안에 있습니다.
                2) 사용자 질문과 직접 관련된 근거는 <반영>...</반영> 태그 안에 담되, 다음을 포함하세요.
                - 표/목록/번호 조항은 해당 항목의 머리글(제목/헤더)과 인접 행·항까지 함께 포함(최소 ±5~10줄 맥락).
                - "주)" 형태의 주석/비고가 붙은 경우 해당 주석 전부 포함.
                - 학점·과목·배분영역·트랙과 같은 숫자/항목은 표의 열 머리말과 같이 포함(헤더+행 세트).
                3) 사용자가 특정 번호(예: 1번, 2번)를 언급했지만 모호할 경우, 후보 번호 2~3개를 모두 포함하되 각 블록 앞에 [후보] 표기.
                4) 관련 근거가 충분치 않다고 판단되면, 상위 단락(조/항/표 제목) 단위까지 확장하여 최소 15줄 이상을 담고, 지나친 요약을 피하세요.
                5) 원문 구조(조/항/호/표 제목)는 유지하고 임의 재작성 금지. 반드시 원문을 거의 그대로 인용하세요.
                6) 원문 밖 추론/창작 금지.

                사용자 질문: {user_question}
                <기억검색>{sanitized_rag}</기억검색>
                """
                ),
            }
        ]
        
        self._dbg("[CONDENSE] 1차 요약 시도 중...")

        try:
            condensed = client.responses.create(
                model=self.model,
                input=condense_prompt,
                text={"format": {"type": "text"}},
            ).output_text.strip()
            
            self._dbg(f"[CONDENSE] 1차 결과 - 길이: {len(condensed)}자, 줄 수: {condensed.count(chr(10))}줄")
            
            # 결과가 지나치게 짧으면(줄 수<15 또는 길이<1000자) 넓은 맥락 재시도
            if (condensed.count("\n") < 15) or (len(condensed) < 1000):
                self._dbg("[CONDENSE] 1차 결과 너무 짧음 -> 2차 시도 (넓은 맥락)")
                broader_prompt = [
                    {
                        "role": "system",
                        "content": (
                                                    f"""
                        당신은 사용자 질문과 관련된 표/번호조항/주석의 전체 맥락을 넓게 포함해 추출합니다.
                        반드시 다음을 지키세요:
                        - <반영>...</반영> 안에 헤더(표 제목/열 머리말) + 관련 행/항 전부와 해당 주석(주)까지 포함.
                        - 최소 25줄 이상, 가능하면 관련 블록을 통째로 포함(불필요한 요약 금지).
                        - 모호하면 후보 블록 2~3개를 [후보]로 나누어 모두 포함.
                        원문: <기억검색>{sanitized_rag}</기억검색>
                        질문: {user_question}
                        """
                        ),
                    }
                ]
                try:
                    self._dbg("[CONDENSE] 2차 요약 시도 중...")
                    condensed2 = client.responses.create(
                        model=self.model,
                        input=broader_prompt,
                        text={"format": {"type": "text"}},
                    ).output_text.strip()
                    
                    self._dbg(f"[CONDENSE] 2차 결과 - 길이: {len(condensed2)}자, 줄 수: {condensed2.count(chr(10))}줄")
                    
                    # 더 길고 풍부하면 교체
                    if (condensed2.count("\n") >= condensed.count("\n")) and (len(condensed2) > len(condensed)):
                        self._dbg("[CONDENSE] 2차 결과가 더 풍부함 -> 교체")
                        condensed = condensed2
                    else:
                        self._dbg("[CONDENSE] 1차 결과 유지")
                except Exception as e2:
                    self._dbg(f"[CONDENSE] 2차 시도 실패: {e2}")
                    
            self._dbg(f"[CONDENSE] 최종 결과 - 길이: {len(condensed)}자")
            return condensed
            
        except Exception as e:
            # 요약 실패 시 원문을 짧게 잘라 사용
            self._dbg(f"[CONDENSE] 문서 요약 실패: {e}")
            fallback = sanitized_rag[:6000]
            self._dbg(f"[CONDENSE] Fallback 사용 - 길이: {len(fallback)}자")
            return fallback

    def _build_final_context(
        self,
        message: str,
        condensed_rag: Optional[str],
        func_results: List[FunctionCallMetadata],
    ) -> List[Dict[str, str]]:
        """최종 LLM 입력 컨텍스트를 구성합니다.

        사용자 질문, 요약된 기억검색 결과, 함수 호출 정보를 통합하여
        단일 시스템 메시지 형태로 정리한 뒤 기존 대화문맥에 추가합니다.

        Args:
            message: 현재 사용자 질문.
            condensed_rag: LLM으로 가공된 기억검색 요약 문자열. 없으면 None.
            func_results: 함수 호출 메타데이터 목록.

        Returns:
            OpenAI Responses API에 전달할 컨텍스트 리스트.
        """

        base_context = self.to_openai_context(self.context[:])
        has_rag = bool(condensed_rag and condensed_rag.strip())
        has_funcs = bool(func_results)

        sections: List[str] = []

        # 1) 사용자 쿼리 지침
        query_guidance = (
            f"이것은 사용자 쿼리입니다: {message}\n"
            "다음 정보를 [사용자쿼리지침],[일반지침],[기억검색지침],[웹검색지침] 등 서술된 서술과 지침에 따라 사용자가 원하는 대답에 맞게 통합해 전달하세요.\n"
            "- 함수호출 결과: 있으면 반영\n"
            "- 기억검색 결과: 있으면 반영 / 함수 호출 존재 자체는 언급 금지"
        )
        sections.append("[사용자쿼리지침]\n" + query_guidance)

        # 2) 일반 지침
        sections.append("[일반지침]\n" + self.instruction)

        # 3) 기억검색 지침 및 본문
        if has_rag:
            rag_guidance = (
                "기억검색 결과입니다. <반영> </반영> 태그 내부 내용을 보고 사용자의 원하는 쿼리에 맞게 대답하세요. "
                "<기억검색></기억검색> 태그는 참조용이며 태그 밖 임의 창작 금지"
            )
            sections.append("[기억검색지침]\n" + rag_guidance)
            sections.append("[기억검색]\n<기억검색>\n" + condensed_rag + "\n</기억검색>")

        web_status: Optional[str] = None

        if has_funcs:
            formatted_blocks_web: List[str] = []
            formatted_blocks_other: List[str] = []
            web_outputs: List[str] = []

            for meta in func_results:
                args_str: str
                try:
                    args_str = json.dumps(meta.arguments, ensure_ascii=False)
                except (TypeError, ValueError):
                    args_str = str(meta.arguments)

                out_text = meta.output if isinstance(meta.output, str) else str(meta.output)
                max_len = 4000
                if len(out_text) > max_len:
                    out_text = out_text[:max_len] + "...<truncated>"

                block = f"<function name='{meta.name}' args='{args_str}'>\n{out_text}\n</function>"

                if meta.name == "search_internet":
                    web_outputs.append(out_text)
                    formatted_blocks_web.append(block)
                else:
                    formatted_blocks_other.append(block)

            web_functions_block = "\n".join(formatted_blocks_web) if formatted_blocks_web else ""
            other_functions_block = "\n".join(formatted_blocks_other) if formatted_blocks_other else ""

            if not web_outputs:
                web_status = "not-run"
            else:
                def _is_error_or_empty(txt: str) -> bool:
                    t = (txt or "").strip()
                    if not t:
                        return True
                    err_keywords = [
                        "🚨",
                        "❌",
                        "오류",
                        "error",
                        "검색 결과를 찾을 수",
                        "no result",
                        "did_call=False",
                    ]
                    return any(k.lower() in t.lower() for k in err_keywords)

                all_bad = all(_is_error_or_empty(t) for t in web_outputs)
                web_status = "empty-or-error" if all_bad else "ok"

            web_guidance = (
                "다음은 인터넷 검색결과입니다. 공식 근거가 아니므로 참고용으로만 사용하세요. "
                "검색이 안되어 우회/문의 안내만 있을 경우, 무시하고 이 내용은'참조만' 하세요. 반드시 기억검색 근거를 우선 반영하세요. 참조란 안내 전화번호 사이트만을 반영하는것을 말합니다 "
            )
            sections.append("[웹검색지침]\n" + web_guidance)
            if web_functions_block:
                sections.append("[인터넷 검색결과]\n<인터넷검색>\n" + web_functions_block + "\n</인터넷검색>")

            func_guidance = (
                "다음은 함수(검색/메뉴 등) 호출 결과입니다. <함수결과> 태그 내부 내용은 참고용이며, 반드시 아래 기억검색(<기억검색>) 근거를 우선 답변에 반영하세요. "
                "'함수 호출'이라는 표현은 사용하지 말고, 거짓 정보 생성 금지."
            )
            sections.append("[함수결과지침]\n" + func_guidance)
            if other_functions_block:
                sections.append("[함수결과]\n<함수결과>\n" + other_functions_block + "\n</함수결과>")

            if web_status and web_status != "not-run":
                status_kr = {
                    "ok": "정상",
                    "empty-or-error": "결과없음/오류",
                    "not-run": "실행안함",
                }[web_status]
                sections.append("[웹검색상태]\n" + status_kr)

            if web_status in ("empty-or-error", "not-run"):
                if has_rag:
                    sections.append(
                        "[웹검색결과없음지침]\n인터넷 검색결과는 참고용입니다. 공식 규정은 아래 기억검색(<기억검색>) 근거를 반드시 우선 확인하세요. 검색이 되지 않거나 문의 안내만 있을 경우, 해당 내용은 참고만 하시고 반드시 아래 규정 근거를 답변에 반영하세요."
                    )
                else:
                    sections.append(
                        "[웹검색결과없음지침]\n웹검색 결과는 없었습니다. 관련 근거를 찾지 못했음을 한 문장으로 간단히 알리고, 필요한 추가 정보를 한 문장으로 요청하세요."
                    )

        if has_rag and has_funcs:
            extra_note = ""
            if web_status == "empty-or-error":
                extra_note = " 웹검색이 결과없음/오류여도 기억검색이 존재하면 '정보 없음'이라고 하지 말고 기억검색 근거로 답할 것."
            merge_instruction = (
                "위 기억검색 근거(<기억검색>)와 인터넷 검색결과(<인터넷검색>), 기타 함수결과(<함수결과>)를 대조하여 모순 없이 답하세요. "
                "핵심 답 먼저 제시하고, 필요한 근거만 축약 인용. 인터넷 검색결과는 참고용이며, 우회/문의 안내만 있을 경우 '참조만' 하고 -참조란 안내 전화번호 사이트만을 반영하는것을 말합니다   "
                "반드시 기억검색 근거를 우선 반영하세요. 근거가 없으면 그 사실을 명시." + extra_note
            )
            sections.append("[통합지침]\n" + merge_instruction)

        # 추가 정보가 없으면 원본 컨텍스트 사용
        if not (has_rag or has_funcs):
            self._last_web_status = web_status
            return base_context

        base_context.append({
            "role": "system",
            "content": "\n\n".join(sections),
        })

        self._last_web_status = web_status
        return base_context

    async def _analyze_and_execute_functions(
        self, 
        message: str
    ) -> List[FunctionCallMetadata]:
        """함수 호출 분석 및 실행
        
        1) FunctionCalling.analyze()로 필요한 함수 파악
        2) 각 함수 실행
        3) 학식 키워드 기반 fallback 호출(규칙 기반) 포함
        4) 결과를 FunctionCallMetadata 리스트로 직렬화하여 반환
        
        Args:
            message: 사용자 메시지
            
        Returns:
            함수 호출 메타데이터 목록
        """
        func_results: List[FunctionCallMetadata] = []
        
        # 1) 함수 분석 및 실행
        analyzed = self.func_calling.analyze(message, self.tools)
        
        for tool_call in analyzed:
            if getattr(tool_call, "type", None) != "function_call":
                continue
                
            func_name = tool_call.name
            call_id = getattr(tool_call, "call_id", "call_unknown")
            
            # 인자 파싱
            try:
                func_args = json.loads(tool_call.arguments)
            except (json.JSONDecodeError, TypeError) as e:
                self._dbg(f"[FUNCTION] 인자 파싱 실패: {func_name}, {e}")
                continue
                
            if not isinstance(func_args, dict):
                self._dbg(f"[FUNCTION] 잘못된 인자 형식: {func_name}")
                continue
            
            # 함수 레퍼런스 찾기
            func = self.available_functions.get(func_name)
            if not func:
                self._dbg(f"[FUNCTION] 미등록 함수: {func_name}")
                continue
            
            # 함수 실행
            try:
                # 안전 기본값 보강
                if func_name == "search_internet":
                    func_args.setdefault("chat_context", self.context[:])
                elif func_name == "get_halla_cafeteria_menu":
                    func_args.setdefault("date", "오늘")
                    # meal은 지정하지 않으면 전체 끼니 반환
                
                output = func(**func_args)
                
                # 메타데이터 생성
                func_results.append(FunctionCallMetadata(
                    name=func_name,
                    arguments=func_args,
                    output=str(output),
                    call_id=call_id,
                    is_fallback=False
                ))
                
            except Exception as exc:
                self._dbg(f"[FUNCTION] {func_name} 실행 실패: {exc}")
                # 실패해도 메타데이터는 기록 (에러 메시지 포함)
                func_results.append(FunctionCallMetadata(
                    name=func_name,
                    arguments=func_args,
                    output=f"❌ 실행 오류: {str(exc)}",
                    call_id=call_id,
                    is_fallback=False
                ))
        
        # 2) 학식 보강 Fallback
        lowered = message.lower()
        cafeteria_keywords = any(k in lowered for k in ["학식", "식단", "점심", "저녁", "메뉴", "조식", "석식", "아침", "오늘 메뉴", "밥 뭐"])
        already_called_cafeteria = any(meta.name == "get_halla_cafeteria_menu" for meta in func_results)
        
        if cafeteria_keywords and not already_called_cafeteria:
            try:
                self._dbg("[FUNCTION] Cafeteria fallback engaged")
                
                # 끼니 추출
                meal_pref = None
                if any(x in lowered for x in ["조식", "아침"]):
                    meal_pref = "조식"
                elif any(x in lowered for x in ["석식", "저녁"]):
                    meal_pref = "석식"
                elif "점심" in lowered or "중식" in lowered:
                    meal_pref = "중식"
                
                # 날짜 추출
                date_pref = "오늘"
                if "내일" in lowered:
                    date_pref = "내일"
                else:
                    import re
                    m = re.search(r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})", message)
                    if m:
                        date_pref = m.group(1)
                
                caf_args = {"date": date_pref, "meal": meal_pref}
                get_cafeteria_fn = self.available_functions.get("get_halla_cafeteria_menu")
                
                if not get_cafeteria_fn:
                    raise RuntimeError("get_halla_cafeteria_menu not registered")
                
                caf_out = get_cafeteria_fn(**caf_args)
                
                # Fallback 메타데이터 추가
                func_results.append(FunctionCallMetadata(
                    name="get_halla_cafeteria_menu",
                    arguments=caf_args,
                    output=str(caf_out),
                    call_id="cafeteria_auto",
                    is_fallback=True
                ))
                
            except Exception as e:
                self._dbg(f"[FUNCTION] 학식 fallback 실패: {e}")
        
        return func_results

    async def _stream_openai_response(
        self, 
        context: List[Dict[str, str]]
    ):
        """OpenAI Responses API 스트리밍 호출
        
        JSON Lines 형식으로 스트리밍 이벤트를 yield합니다.
        
        Args:
            context: OpenAI API에 전달할 컨텍스트
            
        Yields:
            Dict: 스트리밍 이벤트
                - {"type": "delta", "content": "..."}: 텍스트 청크
                - {"type": "completed", "text": "..."}: 완료된 전체 텍스트
        """
        completed_text = ""
        
        try:
            stream = client.responses.create(
                model=self.model,
                input=context,
                top_p=1,
                stream=True,
                text={"format": {"type": "text"}}
            )
            
            for event in stream:
                if event.type == "response.output_text.delta":
                    # 델타 이벤트 - 실시간 텍스트 청크
                    yield {
                        "type": "delta",
                        "content": event.delta
                    }
                    completed_text += event.delta
                    
                elif event.type == "response.output_item.done":
                    # 출력 아이템 완료 - 전체 텍스트 수집
                    item = event.item
                    if item.type == "message" and item.role == "assistant":
                        for part in item.content:
                            if getattr(part, "type", None) == "output_text":
                                completed_text = part.text
                                
                elif event.type == "response.failed":
                    # 실패 이벤트
                    yield {
                        "type": "error",
                        "message": "응답 생성 실패"
                    }
                    return
                    
            # 완료 이벤트
            yield {
                "type": "completed",
                "text": completed_text
            }
            
        except Exception as e:
            self._dbg(f"[STREAM] OpenAI 스트리밍 오류: {e}")
            yield {
                "type": "error",
                "message": f"스트리밍 중 에러 발생: {str(e)}"
            }

    async def stream_chat(
        self, 
        message: str, 
        language: str = "KOR"
    ) -> AsyncGenerator[str, None]:
        """챗봇 스트리밍 통합 메서드
        
        JSON Lines 형식으로 응답을 스트리밍합니다.
        
        처리 흐름:
        1. 사용자 메시지 추가 및 메타데이터 초기화
        2. 언어별 지침 추가
        3. RAG 컨텍스트 준비 및 요약
        4. 함수 호출 분석/실행
        5. 최종 컨텍스트 구성
        6. 스트리밍 응답 생성
        7. 메타데이터 전송
        8. 완료 신호
        9. 응답 저장
        
        Args:
            message: 사용자 메시지
            language: 응답 언어 (KOR, ENG, VI, JPN, CHN, UZB, MNG, IDN)
            
        Yields:
            JSON Lines 형식의 스트리밍 이벤트
        """
        self._dbg(f"[STREAM_CHAT] 시작 - 메시지: {message[:50]}..., 언어: {language}")
        
        # === 1단계: 초기화 ===
        self.add_user_message_in_context(message)
        metadata = ChatMetadata()
        self._dbg("[STREAM_CHAT] 1단계: 메시지 추가 완료")
        
        # === 2단계: 언어별 지침 추가 ===
        language_instruction = self._get_language_instruction(language)
        self.context[-1]["content"] += " " + language_instruction
        self._dbg(f"[STREAM_CHAT] 2단계: 언어 지침 추가 완료 - {language}")
        
        # === 3단계: RAG 컨텍스트 준비 ===
        self._dbg("[STREAM_CHAT] 3단계: RAG 검색 시작...")
        rag_result = self.rag_service.retrieve_context(message)
        condensed_rag = None
        
        if rag_result.merged_documents_text:
            self._dbg(f"[STREAM_CHAT] RAG 검색 완료 - 원본 길이: {len(rag_result.merged_documents_text)}자")
            
            # === RAG 검색 결과 상세 디버그 출력 ===
            self._dbg("=" * 80)
            self._dbg("[RAG 디버그] 검색 결과 상세 정보:")
            self._dbg(f"  - 규정 여부: {rag_result.is_regulation}")
            self._dbg(f"  - 판단 이유: {rag_result.gate_reason or 'N/A'}")
            self._dbg(f"  - 검색 소스: {rag_result.context_source}")
            self._dbg(f"  - 전체 문서 수: {len(rag_result.hits)}")
            self._dbg(f"  - MongoDB 문서: {rag_result.document_count}개")
            self._dbg(f"  - 프리뷰 문서: {rag_result.preview_count}개")
            self._dbg(f"  - 청크 ID 수: {len(rag_result.chunk_ids)}개")
            #검색문서 id 샘플 출력 (최대 5개) 5개 초과 시 생략표시
            if rag_result.chunk_ids:
                chunk_ids_str = ", ".join(rag_result.chunk_ids[:5])
                if len(rag_result.chunk_ids) > 5:
                    chunk_ids_str += f" ... (외 {len(rag_result.chunk_ids) - 5}개)"
                self._dbg(f"  - 청크 ID 샘플: [{chunk_ids_str}]")
            
            # 원본 컨텍스트 샘플 출력 (처음 500자)
            context_sample = rag_result.merged_documents_text[:500]
            if len(rag_result.merged_documents_text) > 500:
                context_sample += "..."
            self._dbg(f"  - 원본 컨텍스트 샘플:\n{context_sample}")
            self._dbg("=" * 80)
            
            condensed_rag = await self._condense_rag_context(
                message, rag_result.merged_documents_text
            )
            self._dbg(f"[STREAM_CHAT] RAG 요약 완료 - 요약 길이: {len(condensed_rag)}자")
            metadata.rag = RagMetadata(
                is_regulation=rag_result.is_regulation,
                gate_reason=rag_result.gate_reason or "",
                context_source=rag_result.context_source,
                hits_count=len(rag_result.hits),
                document_count=rag_result.document_count,
                preview_count=rag_result.preview_count,
                chunk_ids=list(rag_result.chunk_ids),
                source_documents=rag_result.source_documents,  # 출처 문서 정보 추가
                raw_context=rag_result.merged_documents_text,  # 원본 컨텍스트 추가
                condensed_context=condensed_rag,
            )
        else:
            self._dbg("[STREAM_CHAT] RAG 검색 결과 없음")
        
        # === 4단계: 함수 호출 분석/실행 ===
        self._dbg("[STREAM_CHAT] 4단계: 함수 호출 분석/실행 시작...")
        func_results = await self._analyze_and_execute_functions(message)
        metadata.functions = func_results
        self._dbg(f"[STREAM_CHAT] 함수 호출 완료 - {len(func_results)}개 함수 실행")
        
        # 웹검색 상태 설정
        web_search_used = any(meta.name == "search_internet" for meta in func_results)
        if web_search_used:
            # 웹검색 결과 오류 확인
            web_meta = next((m for m in func_results if m.name == "search_internet"), None)
            if web_meta and any(k in web_meta.output.lower() for k in ["오류", "error", "❌"]):
                metadata.web_search_status = "empty-or-error"
            else:
                metadata.web_search_status = "ok"
        else:
            metadata.web_search_status = "not-run"
        
        # === 5단계: 최종 컨텍스트 구성 ===
        final_context = self._build_final_context(
            message=message,
            condensed_rag=condensed_rag,
            func_results=func_results,
        )
        
        # === 6단계: 스트리밍 응답 생성 ===
        completed_text = ""
        async for chunk in self._stream_openai_response(final_context):
            if chunk["type"] == "delta":
                yield json.dumps(chunk, ensure_ascii=False) + "\n"
            elif chunk["type"] == "completed":
                completed_text = chunk["text"]
            elif chunk["type"] == "error":
                yield json.dumps(chunk, ensure_ascii=False) + "\n"
                return
        
        # === 7단계: 메타데이터 전송 ===
        self._dbg("[STREAM_CHAT] 7단계: 메타데이터 전송")
        yield json.dumps({
            "type": "metadata",
            "data": metadata.to_dict()
        }, ensure_ascii=False) + "\n"
        
        # === 8단계: 완료 신호 ===
        self._dbg("[STREAM_CHAT] 8단계: 완료 신호 전송")
        yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
        
        # === 9단계: 응답 저장 ===
        self.add_response_stream(completed_text)
        self._dbg(f"[STREAM_CHAT] 9단계: 응답 저장 완료 - 길이: {len(completed_text)}자")
        self._dbg("[STREAM_CHAT] 전체 처리 완료!")

'''
if __name__ == "__main__":
    #실행흐름
    단계	내용
#1️⃣	사용자 입력 받음 (user_input)
#2️⃣	→ add_user_message_in_context() 로 user 메시지를 문맥에 추가
#3️⃣	→ analyze() 로 함수 호출이 필요한지 판단
#4️⃣	→ 필요하면 함수 실행 + 결과를 temp_context에 추가
#5️⃣	→ chatbot._send_request_Stream(temp_context) 로 응답 받음
#6️⃣	✅ streamed_response 결과를 직접 add_response_stream()으로 수동 저장
    system_role = "당신은 친절하고 유능한 챗봇입니다."
    instruction = "당신은 사용자의 질문에 답변하는 역할을 합니다. 질문에 대한 답변을 제공하고, 필요한 경우 함수 호출을 통해 추가 정보를 검색할 수 있습니다. 사용자의 질문에 대해 정확하고 유용한 답변을 제공하세요."
    # ChatbotStream 인스턴스 생성
    chatbot = ChatbotStream(
        model.advanced,
        system_role=system_role,
        instruction=instruction,
        user="대기",
        assistant="memmo")
    func_calling=FunctionCalling(model.advanced)
    print("===== Chatbot Started =====")
    print("초기 context:", chatbot.context)
    print("사용자가 'exit'라고 입력하면 종료합니다.\n")
    
   # 출력: {}
    

    while True:
        try:
            user_input = input("User > ")

            if user_input.strip().lower() == "exit":
                print("Chatbot 종료.")
                break

            # 사용자 메시지 추가
            chatbot.add_user_message_in_context(user_input)

            # 1) 기억검색 후보 컨텍스트 준비
            rag_ctx = chatbot.get_rag_context(user_input)
            has_rag = rag_ctx is not None and len(rag_ctx.strip()) > 0

            # 2) 함수 호출 분석 및 실행
            analyzed = func_calling.analyze(user_input, tools)
            func_msgs = []  # function_call + function_call_output 메시지 누적
            func_outputs = []  # 함수 결과 문자열 누적

            for tool_call in analyzed:  # analyzed는 list of function_call objects
                if getattr(tool_call, "type", None) != "function_call":
                    continue

                func_name = tool_call.name
                func_args = json.loads(tool_call.arguments)
                call_id = tool_call.call_id

                func_to_call = func_calling.available_functions.get(func_name)
                if not func_to_call:
                    print(f"[오류] 등록되지 않은 함수: {func_name}")
                    continue

                try:
                    # 안전 기본값 보강: 분석기가 일부 인자를 생략해도 동작하도록
                    if func_name == "get_halla_cafeteria_menu":
                        func_args.setdefault("date", "오늘")
                        func_args.setdefault("meal", "중식")
                    func_response = (
                        func_to_call(chat_context=chatbot.context[:], **func_args)
                        if func_name == "search_internet"
                        else func_to_call(**func_args)
                    )

                    # function_call/ output 메시지 구성
                    func_msgs.extend([
                        {
                            "type": "function_call",
                            "call_id": call_id,
                            "name": func_name,
                            "arguments": tool_call.arguments,
                        },
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": str(func_response),
                        },
                    ])
                    func_outputs.append(str(func_response))
                except Exception as e:
                    print(f"[함수 실행 오류] {func_name}: {e}")

            has_funcs = len(func_outputs) > 0

            # 보강: 학식/식단 질의일 경우, 분석기가 호출을 안 했더라도 직접 함수 호출 시도
            lowered = user_input.lower()
            if ("학식" in lowered) or ("식단" in lowered) or ("점심" in lowered) or ("저녁" in lowered) or ("메뉴" in lowered) or ("조식" in lowered):
                if not has_funcs:
                    try:
                        # 기본값: 오늘/중식, 간단 규칙으로 끼니/날짜 추출
                        meal_pref = "중식"
                        if ("조식" in lowered) or ("아침" in lowered):
                            meal_pref = "조식"
                        elif ("석식" in lowered) or ("저녁" in lowered):
                            meal_pref = "석식"
                        # 날짜 키워드
                        date_pref = "오늘"
                        if "내일" in lowered:
                            date_pref = "내일"
                        else:
                            import re as _re
                            m = _re.search(r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})", user_input)
                            if m:
                                date_pref = m.group(1)
                        caf_args = {"date": date_pref, "meal": meal_pref}
                        from chatbotDirectory.functioncalling import get_halla_cafeteria_menu
                        caf_out = get_halla_cafeteria_menu(**caf_args)
                        # 메시지 형태로 삽입하여 모델이 근거로 활용
                        call_id = "cafeteria_auto"
                        func_msgs.extend([
                            {
                                "type": "function_call",
                                "call_id": call_id,
                                "name": "get_halla_cafeteria_menu",
                                "arguments": json.dumps(caf_args, ensure_ascii=False),
                            },
                            {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": str(caf_out),
                            },
                        ])
                        func_outputs.append(str(caf_out))
                        has_funcs = True
                    except Exception as e:
                        print(f"[보강 호출 실패] get_halla_cafeteria_menu: {e}")

            # 3) 최종 temp_context 구성
            temp_context = chatbot.to_openai_context(chatbot.context[:])

            # 전반 지침: 사용자 쿼리와 통합 지시
            temp_context.append({
                "role": "system",
                "content": (
                    f"이것은 사용자 쿼리입니다: {user_input}\n"
                    "다음 정보를 사용자가 원하는 대답에 맞게 통합해 전달하세요.\n"
                    "- 함수호출 결과: 있으면 반영\n- 기억검색 결과: 있으면 반영"
                ),
            })
            # 일반 지침 추가
            temp_context.append({"role": "system", "content": chatbot.instruction})

            if has_rag:
                # RAG 안내 + 근거 투입
                temp_context.append({"role": "system", "content": "검색결과입니다. 사용자의 원하는 쿼리에 맞게 대답하세요."})
                temp_context.append({"role": "system", "content": f"[검색결과]\n{rag_ctx}"})

            if has_funcs:
                # 함수 호출 결과 안내 및 메시지 삽입
                temp_context.append({"role": "system", "content": "함수호출결과입니다. 이걸 바탕으로 대답에 응하세요."})
                temp_context.extend(func_msgs)

            if has_rag and has_funcs:
                temp_context.append({
                    "role": "system",
                    "content": "아래 함수 호출 결과와 검색 결과를 모두 활용해, 두 문맥이 어떻게 도출되었는지 한 줄로 설명하고 사용자 질문에 답하세요.",
                })

            if not has_rag and not has_funcs:
                # 둘 다 없으면 일반 챗봇 스트림으로 응답
                print("RAG/함수호출 결과 없음 → 일반 챗봇 응답")
                streamed = chatbot.send_request_Stream()
                chatbot.add_response_stream(streamed)
                print("\n===== Chatbot Context Updated =====")
                print(chatbot.context)
                continue

            # 4) 스트리밍 요청
            streamed_response = chatbot._send_request_Stream(temp_context=temp_context)
            chatbot.add_response_stream(streamed_response)

            print("\n===== Chatbot Context Updated =====")
            print(chatbot.context)

        except KeyboardInterrupt:
            print("\n사용자 종료(Ctrl+C)")
            break
        except Exception as e:
            print(f"[루프 에러] {e}")
            continue

'''