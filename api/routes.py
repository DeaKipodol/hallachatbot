from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ai.chatbot import ChatbotStream, model

class UserRequest(BaseModel):
    message: str
    language: str = "KOR"


router = APIRouter()

# ChatbotStream 인스턴스 생성
chatbot = ChatbotStream(
    model=model.advanced,
    system_role="""당신은 학교 생활, 학과 정보, 행사 등 사용자가 궁금한 점이 있으면 아는 범위 안에서 대답합니다. 단 절대 거짓내용을 말하지 않습니다. 아는 범위에서 말하고 부족한 부분은 인정하세요.
    당신은 실시간으로 검색하는 기능이있습니다.
    당신은 한라대 공지사항을 탐색할 수 있습니다.
    당신은 한라대 학식메뉴를 탐색할 수 있습니다.
    당신은 한라대 학사일정을 탐색할 수 있습니다.""",
    instruction="당신은 사용자의 질문에 답변하는 역할을 합니다.",
    user="한라대 대학생",
    assistant="memmo"
)


@router.post("/chat")
async def chat_endpoint(user_input: UserRequest):
    """
    채팅 엔드포인트 - ChatbotStream.stream_chat()에 모든 로직 위임
    """
    stream_generator = chatbot.stream_chat(
        message=user_input.message,
        language=user_input.language
    )
    
    return StreamingResponse(
        stream_generator,
        media_type="application/x-ndjson"
    )
