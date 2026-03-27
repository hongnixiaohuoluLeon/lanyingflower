import requests
from bs4 import BeautifulSoup
import json
import os
import math

BASE_URL = "https://ofg-web-shop.com/?mode=grp&gid=2682518&page={}"
WEBHOOK = os.environ.get("WEBHOOK")
DATA_FILE = "data.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_total_pages():
    url = BASE_URL.format(1)
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.encoding = "euc-jp"

    soup = BeautifulSoup(res.text, "html.parser")

    pager_text = soup.select_one(".pager p")

    if not pager_text:
        return 1

    text = pager_text.get_text()

    # 👉 提取总商品数（例如 39）
    import re
    m = re.search(r'(\d+)', text)

    if not m:
        return 1

    total = int(m.group(1))

    per_page = 20
    pages = math.ceil(total / per_page)

    return pages


def get_products_from_page(page):
    url = BASE_URL.format(page)

    res = requests.get(url, headers=HEADERS, timeout=10)
    res.encoding = "euc-jp"

    soup = BeautifulSoup(res.text, "html.parser")

    items = soup.select("article.items dl")

    products = {}

    for item in items:
        link = item.select_one("dt a")
        title = item.select_one("dd.itemtitle")

        if link and title:
            href = link.get("href", "")
            name = title.get_text(separator=" ", strip=True)

            pid = href.split("pid=")[-1]
            products[pid] = name

    return products


def get_all_products():
    total_pages = get_total_pages()
    print(f"检测到 {total_pages} 页")

    all_products = {}

    for page in range(1, total_pages + 1):
        try:
            data = get_products_from_page(page)
            all_products.update(data)
        except Exception as e:
            print(f"第{page}页失败:", e)

    return all_products


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def send(msg):
    if not WEBHOOK:
        return
    requests.post(WEBHOOK, json={
        "msgtype": "text",
        "text": {"content": msg}
    })


def main():
    current = get_all_products()
    old = load_data()

    if old:
        new_ids = set(current.keys()) - set(old.keys())

        if new_ids:
            msg = "🆕 新增上架商品：\n\n"

            for pid in new_ids:
                name = current[pid]
                url = f"https://ofg-web-shop.com/?pid={pid}"

                msg += f"{name}\n{url}\n\n"

            send(msg)
            print("发现新品，已通知")

    save_data(current)


if __name__ == "__main__":
    main()
