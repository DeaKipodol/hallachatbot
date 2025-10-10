import math
import os
import sys
from pathlib import Path

# 실행 방식과 무관하게 패키지 루트를 인지시키기 위한 부트스트랩
# (예: `python chatbotDirectory/chatbot.py`로 직접 실행하는 경우 대비)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT)) 
# 상대 임포트 대신 절대 임포트 사용
from .common import model, client
from .functioncalling import FunctionCalling, tools
from .rag import RagService
import json

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
        result = self.rag_service.build_context(user_question)
        self._last_rag_result = result
        return result.context_text

    @property
    def last_rag_result(self):
        """최근 RAG 검색 결과를 노출합니다 (없으면 None)."""
        return self._last_rag_result or self.rag_service.last_result
    def get_response_from_db_only(self, user_question: str):
        self._dbg("get_response_from_db_only: start")
        rag_result = self.rag_service.build_context(user_question)
        rag_context = rag_result.context_text
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
 


