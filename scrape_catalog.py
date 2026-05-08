import httpx
from bs4 import BeautifulSoup
import json

async def scrape_shl_catalog():
    url = "https://www.shl.com/solutions/products/product-catalog/"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
    
    products = []
    # Adapt selector based on actual page structure
    for item in soup.select(".product-item"):
        name = item.select_one(".product-name").text.strip()
        url = item.select_one("a")["href"]
        test_type = item.select_one(".test-type").text.strip() if item.select_one(".test-type") else "Unknown"
        products.append({"name": name, "url": url, "test_type": test_type})
    
    with open("catalog.json", "w") as f:
        json.dump(products, f, indent=2)
    return products
