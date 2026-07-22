import os
import json
import functools 
from functools import lru_cache
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
STORE_DOMAIN = os.getenv("SHOPIFY_STORE_DOMAIN")
API_URL = f"https://{STORE_DOMAIN}/admin/api/2026-07/graphql.json"
TOKEN_URL = f"https://{STORE_DOMAIN}/admin/oauth/access_token"



@lru_cache(maxsize=1)
def get_access_token():
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def run_query(query, variables=None):
    resp = requests.post(
        API_URL,
        json={"query": query, "variables": variables or {}},
        headers={
            "X-Shopify-Access-Token": get_access_token(),
            "Content-Type": "application/json",
        },
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]

PRODUCTS_QUERY = """
query Products($cursor: String) {
  products(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id title handle vendor productType tags descriptionHtml }
  }
}
"""

def fetch_all_products():
    products = []
    cursor = None
    while True:
        result = run_query(PRODUCTS_QUERY, {"cursor": cursor})
        products_block = result["products"]
        products.extend(products_block["nodes"])
        page_info = products_block["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    return products

PRODUCT_SEARCH_QUERY = """
query ProductSearch($q: String!) {
  products(first: 5, query: $q) {
    nodes {
      title
      handle
      vendor
      priceRangeV2 {
        minVariantPrice { amount currencyCode }
        maxVariantPrice { amount }
      }
      variants(first: 20) {
        nodes { title price }
      }
    }
  }
}
"""

def search_products(q):
    result = run_query(PRODUCT_SEARCH_QUERY, {"q": q})
    return result["products"]["nodes"]


if __name__ == "__main__":
    shop = run_query("{ shop { name} }")
    print("Connected to:", shop["shop"]["name"])

    products = fetch_all_products()
    print(f"Fetched {len(products)} products:")
    print("First product:", products[0]["title"] if products else "No products found")

    os.makedirs("data", exist_ok=True)
    with open("data/products.json", "w") as f:
        json.dump(products, f, indent=2)
    print("Saved products to data/products.json")
