import os
from openai import OpenAI
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv  

router = APIRouter()

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


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
