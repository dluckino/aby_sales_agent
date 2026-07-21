import json
from bs4 import BeautifulSoup
from knowledge import collection

def html_to_text(html):
    soup = BeautifulSoup(html or "", "html.parser")
    lines = []
    for block in soup.find_all(["p", "li"]):
        text = block.get_text(" ", strip=True)
        if text:
            lines.append(text)
    return "\n".join(lines)

def build_chunk_text(product):
    header = f"{product['title']}\nVendor: {product['vendor']} | Type: {product['productType']} | Tags: {', '.join(product['tags'])}"
    body = html_to_text(product["descriptionHtml"])
    return f"{header}\n\n{body}"

if __name__ == "__main__":
    with open("data/products.json") as f:
        products = json.load(f)

    ids = []
    documents = []
    metadatas = []
    for product in products:
        ids.append(product["handle"])
        documents.append(build_chunk_text(product))
        metadatas.append({
            "title": product["title"],
            "vendor": product["vendor"],
            "product_type": product["productType"],
            "handle": product["handle"],
            "source": "product",
        })

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Ingested {len(products)} products")
    print(f"Collection now holds {collection.count()} chunks")