# Imports
from fastapi import FastAPI
from pydantic import BaseModel, Field
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from database import init_db, save_message, get_history
from knowledge import search_knowledge_base
from shopify_client import search_products
import asyncio

load_dotenv()
client = AsyncAnthropic()

app = FastAPI()
SYSTEM_PROMPT = (
    "You are the AI sales assistant for American Backyard, an outdoor "
    "furniture store in Alpharetta, Georgia. Use the search_knowledge_base "
    "tool to look up information before answering questions about products "
    "or store policies. Answer as completely as you can from the search "
    "results. If a question has multiple parts, search for each part "
    "before deciding anything is unknown — for example, a question about "
    "closed days may need both holiday information and regular weekly "
    "hours. Never tell a customer to call or email for information the "
    "knowledge base contains, such as store hours, location, or policies. "
    "If the search results don't contain the answer, say you don't know "
    "rather than guessing. Never state that American Backyard does not "
    "offer a service, product, or option just because the search results "
    "don't mention it — missing information means you don't know, not "
    "that the answer is no. Never assure a customer that they are "
    "eligible, covered, or guaranteed anything — including warranty "
    "claims, replacements, discounts, or delivery dates. You may state a "
    "product's listed warranty term as a fact, but explain that claims "
    "and eligibility are reviewed case-by-case by American Backyard "
    "staff. You cannot check stock, inventory, or availability; if a customer "
    "asks whether something is in stock, direct them to call the store. "
    "If the customer asks about multiple products, call the tool "
    "once per product. Only when searching has failed to answer the "
    "question: ask the customer for their email address, tell them "
    "American Backyard will follow up, and share the store's phone "
    "number (770-754-5750) and email address (support@americanbackyard.com)."
)

TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": (
            "Search American Backyard's product catalog and store policy documents. Returns the most "
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
    },
    {
        "name": "search_products",
        "description": (
            "Look up LIVE product data from American Backyard's online "
            "store: current prices and available variants. Use this "
            "whenever a customer asks about price or cost. Use short "
            "queries with the key product words, e.g. 'St. Lucia Chaise' "
            "or 'South Beach conversation'. This tool does NOT provide "
            "stock or inventory information. For product descriptions, "
            "warranties, care, and store policies, use "
            "search_knowledge_base instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Short product search: 2-4 key words from the product name",
                }
            },
            "required": ["query"],
        },
    },
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

def format_products(products):
    if not products:
        return "No matching products found in the live catalog."
    lines = []
    for p in products:
        lo = p["priceRangeV2"]["minVariantPrice"]["amount"]
        hi = p["priceRangeV2"]["maxVariantPrice"]["amount"]
        price = f"${lo}" if lo == hi else f"${lo} - ${hi}"
        lines.append(f"{p['title']} ({p['vendor']}) - {price}")
        variants = p["variants"]["nodes"]
        if len(variants) > 1:
            for v in variants:
                lines.append(f"  - {v['title']}: ${v['price']}")
    return "\n".join(lines)

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
                if block.name == "search_knowledge_base":
                    print(f"[tool] {block.name}: {block.input['query']} (category={block.input.get('category')})")
                    hits = search_knowledge_base(
                        block.input["query"],
                        category=block.input.get("category"),
                    )
                    content = format_hits(hits)
                    if hits:
                        print(f"[tool] -> {len(hits)} hits, best {hits[0]['distance']:.3f}: {hits[0]['metadata']['title']}")
                    else:
                        print("[tool] -> 0 hits")
                elif block.name == "search_products":
                    print(f"[tool] {block.name}: {block.input['query']}")
                    products = await asyncio.to_thread(search_products, block.input["query"])
                    content = format_products(products)
                    print(f"[tool] -> {len(products)} products")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                })
        messages.append({"role": "user", "content": results})

    reply = "".join(b.text for b in response.content if b.type == "text")
    save_message(req.session_id, "assistant", reply)
    return {"reply": reply}