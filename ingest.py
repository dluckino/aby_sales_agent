import json
from bs4 import BeautifulSoup
from knowledge import collection
from pathlib import Path

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

def split_markdown_sections(text):
    doc_title = ""
    sections = []
    current_title = None
    current_lines = []
    for line in text.splitlines():
        if line.startswith("# ") and not line.startswith("## "):
            doc_title = line[2:].strip()
        elif line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return doc_title, sections

def load_policy_chunks():
    ids, documents, metadatas = [], [], []
    for path in sorted(Path("knowledge").glob("*.md")):
        doc_title, sections = split_markdown_sections(path.read_text())
        for section_title, body in sections:
            if not body:
                print(f"[skip] empty section: {path.name} - {section_title}")
                continue
            slug = section_title.lower().replace(" ", "-")
            ids.append(f"policy-{path.stem}-{slug}")
            documents.append(f"{doc_title} - {section_title}\n\n{body}")
            metadatas.append({
                "title": f"{doc_title} - {section_title}",
                "source": "policy",
                "doc": path.name,
            })
    return ids, documents, metadatas

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

    p_ids, p_docs, p_metas = load_policy_chunks()
    if p_ids:
        collection.upsert(ids=p_ids, documents=p_docs, metadatas=p_metas)
    print(f"Ingested {len(p_ids)} policy sections")
    print(f"Collection now holds {collection.count()} chunks")