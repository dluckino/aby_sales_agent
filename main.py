# Imports
from fastapi import FastAPI
from pydantic import BaseModel, Field
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from database import init_db, save_message, get_history

load_dotenv()
client = AsyncAnthropic()

app = FastAPI()

init_db()

@app.get("/health")
async def health_check():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=1, max_length=64)


@app.post("/chat")
async def chat(req: ChatRequest):
    save_message(req.session_id, "user", req.message)
    history = get_history(req.session_id)
    response = await client.messages.create(
        model = "claude-sonnet-4-6",
        max_tokens = 500,
        messages = history,
    )
    reply = response.content[0].text
    save_message(req.session_id, "assistant", reply)
    return {"reply": reply}