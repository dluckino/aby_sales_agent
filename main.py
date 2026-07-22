# Imports
from fastapi import FastAPI
from pydantic import BaseModel, Field
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from database import init_db, save_message, get_history
from knowledge import search_knowledge_base

load_dotenv()
client = AsyncAnthropic()

app = FastAPI()
SYSTEM_PROMPT = (
    "You are the AI sales assistant for American Backyard, an outdoor "
    "furniture store in Alpharetta, Georgia. Use the search_knowledge_base "
    "tool to look up product details before answering product questions. "
    "If the search results don't contain the answer, say you don't know "
    "rather than guessing. Never state that American Backyard does not "
    "offer a service, product, or option just because the search results "
    "don't mention it — missing information means you don't know, not "
    "that the answer is no. If the customer asks about multiple products, "
    "call the tool once per product. If you do not know the answer, ask "
    "the customer for their email address and tell them American Backyard "
    "will follow up with an answer. Also give them the store's phone number "
    "(770-754-5750) and email address (support@americanbackyard.com)."
)

TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": (
            "Search American Backyard's product catalog and story policy documents. Returns the most "
            "relevant product listings (title, vendor, description, warranty, "
            "lead time, dimensions) or policy sections (hours, location, payment, "
            "pickup, services) for a text query. Include the brand and "
            "product name when known, e.g. 'Three Birds Casual St. Lucia "
            "Chaise Lounger warranty'. Keep queries short and specific: "
            "product name plus the attribute you need. If the customer asks "
            "about multiple products, call this tool once per product."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Short search query: brand + product + attribute",
                },
                "category": {
                    "type": "string",
                    "enum": ["product", "policy"],
                    "description": (
                        "Optional filter. Use 'policy' for store hours, "
                        "location, payment, pickup, delivery, returns, and "
                        "services. Use 'product' for catalog items. Omit to "
                        "search everything."
                    ),
                },
            },
            "required": ["query"],
        },
    }
]

init_db()

@app.get("/health")
async def health_check():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=1, max_length=64)

def format_hits(hits):
    if not hits:
        return "No matching products found."
    return "\n\n---\n\n".join(hit["text"] for hit in hits)

@app.post("/chat")
async def chat(req: ChatRequest):
    save_message(req.session_id, "user", req.message)
    messages = get_history(req.session_id)
    response = None
    for _ in range(5):
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )
        if response.stop_reason != "tool_use":
            break
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"[tool] {block.name}: {block.input['query']} (category={block.input.get('category')})")
                hits = search_knowledge_base(
                    block.input["query"],
                    category=block.input.get("category")
                )
                if hits:
                    print(f"[tool] -> {len(hits)} hits, best {hits[0]['distance']:.3f}: {hits[0]['metadata']['title']}")
                else:
                    print("[tool] -> 0 hits")
                

                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": format_hits(hits),
                })
        messages.append({"role": "user", "content": results})

    reply = "".join(b.text for b in response.content if b.type == "text")
    save_message(req.session_id, "assistant", reply)
    return {"reply": reply}