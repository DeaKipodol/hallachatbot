import asyncio
import os
from openai import OpenAI
from fastapi import APIRouter, HTTPException 
from pydantic import BaseModel
from dotenv import load_dotenv  
from fastapi.responses import StreamingResponse
from ..chatbotDirectory import chatbot
from ..chatbotDirectory.functioncalling import tools, FunctionCalling
from ..chatbotDirectory.functioncalling import model
from ..chatbotDirectory.chatbot import ChatbotStream
import json


# UserRequest 클래스에 language 필드 추가
class UserRequest(BaseModel):
    message: str
    language: str = "KOR"  # 기본값은 한국어로 설정

func_calling = FunctionCalling(
    model=model.basic,
    available_functions={
        # 필요시 다른 함수도 여기에 추가
    }
)
router = APIRouter()

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 예시: 전역 또는 엔드포인트 내부에서 인스턴스 생성
chatbot = ChatbotStream(
    model=model.advanced,
    system_role="당신은 학교 생활, 학과 정보, 행사 등 사용자가 궁금한 점이 있으면 아는 범위 안에서 대답합니다. 단 절대 거짓내용을 말하지 않습니다. 아는 범위에서 말하고 부족한 부분은 인정하세요.당신은 실시간으로 검색하는 기능이있습니다. ",
    instruction="당신은 사용자의 질문에 답변하는 역할을 합니다.",
    user="한라대 대학생",
    assistant="memmo"
)

# 채팅
class Message(BaseModel):
    message: str

@router.post("/chat")
async def chat(message: Message):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "user", "content": message.message}
            ],
            temperature=0.5,
            max_tokens=512,
        )
        answer = response.choices[0].message.content
        return {"response": answer.strip()}
    except Exception as e:
        print(f"OpenAI API error: {e}")  
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/stream-chat")
async def stream_chat(user_input: UserRequest):
    # 1) 사용자 메시지를 원본 문맥에 추가
    chatbot.add_user_message_in_context(user_input.message)

    # 2) 언어 지침 추가
    instruction_map = {
        "KOR": "한국어로 정중하고 따뜻하게 답해주세요.",
        "ENG": "Please respond kindly in English.",
        "VI": "Vui lòng trả lời bằng tiếng Việt một cách nhẹ nhàng.",
        "JPN": "日本語で丁寧に温かく答えてください。",
        "CHN": "请用中文亲切地回答。",
    }
    instruction = instruction_map.get(user_input.language, instruction_map["KOR"])
    chatbot.context[-1]["content"] += " " + instruction

    # 3) RAG 컨텍스트 준비
    rag_ctx = chatbot.get_rag_context(user_input.message)
    has_rag = bool(rag_ctx and rag_ctx.strip())

    # 4) 함수 호출 분석 및 실행
    analyzed = func_calling.analyze(user_input.message, tools)
    func_msgs: list[dict] = []
    func_outputs: list[str] = []

    for tool_call in analyzed:
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
            # 안전 기본값 보강
            if func_name == "get_halla_cafeteria_menu":
                func_args.setdefault("date", "오늘")
                func_args.setdefault("meal", "중식")

            func_response = (
                func_to_call(chat_context=chatbot.context[:], **func_args)
                if func_name == "search_internet"
                else func_to_call(**func_args)
            )

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

    # 4-1) 학식/식단 질의 보강 호출
    lowered = user_input.message.lower()
    if ("학식" in lowered) or ("식단" in lowered) or ("점심" in lowered) or ("저녁" in lowered) or ("메뉴" in lowered) or ("조식" in lowered):
        if not has_funcs:
            try:
                meal_pref = "중식"
                if ("조식" in lowered) or ("아침" in lowered):
                    meal_pref = "조식"
                elif ("석식" in lowered) or ("저녁" in lowered):
                    meal_pref = "석식"
                date_pref = "오늘"
                if "내일" in lowered:
                    date_pref = "내일"
                else:
                    import re as _re
                    m = _re.search(r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})", user_input.message)
                    if m:
                        date_pref = m.group(1)
                caf_args = {"date": date_pref, "meal": meal_pref}
                from chatbotDirectory.functioncalling import get_halla_cafeteria_menu
                caf_out = get_halla_cafeteria_menu(**caf_args)
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

    # 5) 최종 스트리밍에 사용할 컨텍스트 구성
    base_context = chatbot.to_openai_context(chatbot.context[:])
    temp_context = base_context[:]

    temp_context.append({
        "role": "system",
        "content": (
            f"이것은 사용자 쿼리입니다: {user_input.message}\n"
            "다음 정보를 사용자가 원하는 대답에 맞게 통합해 전달하세요.\n"
            "- 함수호출 결과: 있으면 반영\n- 기억검색 결과: 있으면 반영/ 직접적으로 함수 호출 여부에 대해 사용자에게 언급하지 마세요."
        ),
    })
    temp_context.append({"role": "system", "content": chatbot.instruction})

    if has_rag:
        # 5-1) 기억검색 결과를 그대로 넣지 않고, 먼저 LLM으로 사용자 질문에 맞게 가공/요약
        def _sanitize_text(txt: str) -> str:
            # 제어문자 제거 및 태그 충돌 방지
            if not isinstance(txt, str):
                txt = str(txt)
            # 간단 제어문자 필터링 (LF, TAB 제외)
            txt = ''.join(ch for ch in txt if ch in ('\n', '\t') or (ord(ch) >= 32 and ch != 127))
            # 태그 조기 종료 방지
            txt = txt.replace("</기억검색>", "[/기억검색]")
            # 과도한 길이 클램프 (필요시 조정)
            max_len = 12000
            return txt[:max_len]

        sanitized_rag = _sanitize_text(rag_ctx)

        condense_prompt = [
            {"role": "system", "content": (
                "당신은 긴 문서 묶음을 사용자의 질문에 맞게 가공하는 어시스턴트입니다. "
                "아래 요구사항을 만족하세요: \n"
                "ㅇ원문내용의 특수문자를 지우고 그대로 출력\n"
                "사용자 질문에 근접한 내용을 <반영>...</반영> 태그안에 집어넣어 표시 "
                "- 모호하거나 불명확하면 '관련 근거 없음'이라고 표시\n"
                "최대한 원문 그대로 출력"
            )},
            {"role": "user", "content": f"사용자 질문: {user_input.message}"},
            {"role": "system", "content": "다음은 기억검색 원문입니다. <기억검색>...</기억검색> 내부만 참고하여 가공 결과를 생성하세요."},
            {"role": "system", "content": f"<기억검색>{sanitized_rag}</기억검색>"},
        ]

        # 디버그: condense_prompt와 rag_ctx 출력
        print("==== [DEBUG] condense_prompt ====")
        for item in condense_prompt:
            print(item)
        print("==== [DEBUG] rag_ctx ====")
        print(rag_ctx)

        try:
            condensed = client.responses.create(
                model=model.advanced,
                input=condense_prompt,
                text={"format": {"type": "text"}},
            ).output_text.strip()
            print("==== [DEBUG] condensed ====")
            print(condensed)
        except Exception as _e:
            # 요약 실패 시 원문을 짧게 잘라 사용
            print(f"[DEBUG] condense failed: {_e}")
            condensed = sanitized_rag[:3000]

        temp_context.append({
            "role": "system",
            "content": (
                "기억검색 결과입니다. <기억검색> </기억검색> 태그 내부 내용을 보고 사용자의 원하는 쿼리에 맞게 대답하세요."
            )
        })
        temp_context.append({
            "role": "system",
            "content": f"<기억검색>{condensed}</기억검색>"
        })

    if has_funcs:
        temp_context.append({"role": "system", "content": "인터넷 검색결과니다. <인터넷 검색> <인터넷검색> 태그 내부내용 바탕으로 대답에 응하세요./"
                             "<인터넷검색>{func_msgs}<인터넷검색> 단 기억검색결과가 주가 되어야합니다"})
       

    if has_rag and has_funcs:
        temp_context.append({
            "role": "system",
            "content": " 함수 호출 결과와 검색 결과를 모두 활용해, 두 문맥이 어떻게 도출되었는지 한 줄로 설명하고 사용자 질문에 답하세요. ",
        })

    # 둘 다 없으면 원본 컨텍스트만 사용해 일반 응답
    context_to_stream = temp_context if (has_rag or has_funcs) else base_context

    # 6) 스트리밍 응답 생성 및 최종 문맥 저장
    async def generate_with_tool():
        completed_text = ""
        try:
            stream = client.responses.create(
                model=chatbot.model,
                input=context_to_stream,
                top_p=1,
                stream=True,
                text={"format": {"type": "text"}},
            )

            loading = True
            for event in stream:
                match event.type:
                    case "response.created":
                        loading = True
                        yield "⏳ GPT가 응답을 준비 중입니다..."
                        await asyncio.sleep(0)
                    case "response.output_text.delta":
                        if loading:
                            yield "\n[� 응답 시작됨 ↓]"
                            loading = False
                        yield f"{event.delta}"
                        await asyncio.sleep(0)
                    case "response.in_progress":
                        yield "\n[🌀 응답 생성 중...]\n"
                    case "response.output_item.done":
                        item = event.item
                        if item.type == "message" and item.role == "assistant":
                            for part in item.content:
                                if getattr(part, "type", None) == "output_text":
                                    completed_text = part.text
                    case "response.completed":
                        yield "\n"
                    case "response.failed":
                        yield "❌ 응답 생성 실패"
                    case "error":
                        yield "⚠️ 스트리밍 중 에러 발생!"
                    case _:
                        yield f"\n[📬 기타 이벤트 감지: {event.type}]"
        except Exception as e:
            yield f"\nStream Error: {str(e)}"
        finally:
            if completed_text:
                chatbot.add_response_stream(completed_text)
            print(context_to_stream)

    return StreamingResponse(generate_with_tool(), media_type="text/plain")

