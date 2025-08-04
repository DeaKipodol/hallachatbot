import math
# 상대 임포트 대신 절대 임포트 사용
from common import model, makeup_response, client
from functioncalling import FunctionCalling, tools
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
          - assistant 이름
        """
        self.context = [{"role": "system","content": system_role}]
               
        self.current_field = "main"
        
        self.model = model
        self.instruction=instruction

        self.max_token_size = 16 * 1024 #최대 토큰이상을 쓰면 오류가발생 따라서 토큰 용량관리가 필요.
        self.available_token_rate = 0.9#최대토큰의 90%만 쓰겠다.
    
        self.username=kwargs["user"]
        self.assistantname=kwargs["assistant"]

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
    def _send_request_Stream(self):
        
        completed_text = ""
        stream = client.responses.create(
        model=self.model,
        input=self.context,  
        stream=True,
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

if __name__ == "__main__":
    '''실행흐름
    단계	내용
1️⃣	사용자 입력 받음 (user_input)
2️⃣	→ add_user_message_in_context() 로 user 메시지를 문맥에 추가
3️⃣	→ analyze() 로 함수 호출이 필요한지 판단
4️⃣	→ 필요하면 함수 실행 + 결과를 temp_context에 추가
5️⃣	→ chatbot._send_request_Stream(temp_context) 로 응답 받음
6️⃣	✅ streamed_response 결과를 직접 add_response_stream()으로 수동 저장'''
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
        user_input = input("User > ")
        if user_input.strip().lower() == "exit":
            print("Chatbot 종료.")
            

        # 사용자 메시지를 문맥에 추가
        chatbot.add_user_message_in_context(user_input)

        # 사용자 입력 분석 (함수 호출 여부 확인)
        analyzed = func_calling.analyze(user_input, tools)

        temp_context = chatbot.to_openai_context(chatbot.context[:])

        for tool_call in analyzed:  # analyzed는 list of function_call dicts
            if tool_call.type != "function_call":
                continue
            
            func_name = tool_call.name
            func_args = json.loads(tool_call.arguments)
            call_id = tool_call.call_id

            func_to_call = func_calling.available_functions.get(func_name)
            if not func_to_call:
                print(f"[오류] 등록되지 않은 함수: {func_name}")
                continue


            try:
               
                function_call_msg = {
                    "type": "function_call",  # 고정
                    "call_id": call_id,  # 딕셔너리 내에 있거나 key가 다를 수 있으니 주의
                    "name": func_name,
                    "arguments": tool_call.arguments  # dict -> JSON string
                }
                print(f"함수 호출 메시지: {function_call_msg}")
                if func_name == "search_internet":
                    # context는 이미 run 메서드의 매개변수로 받고 있음
                    func_response = func_to_call(chat_context=chatbot.context[:], **func_args)
                else:
                    func_response=func_to_call(**func_args)
                

                temp_context.extend([
                    function_call_msg,
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": str(func_response)
                }
            ])
              #  print("함수 실행후 임시문맥:{}".format(temp_context))

            except Exception as e:
                print(f"[함수 실행 오류] {func_name}: {e}")

        # 함수 결과 포함 응답 요청
        streamed_response = chatbot._send_request_Stream()
        temp_context = None
        chatbot.add_response_stream(streamed_response)
        print(chatbot.context)

    # === 분기 처리 끝 ===