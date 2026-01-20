import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import time
import random
import os
import subprocess

# ================== KONFIGURACJA ==================

BASE_URL = (
    "https://www.vinted.pl/catalog"
    "?catalog[]=267"
    "&price_to=35.00"
    "&currency=PLN"
    "&size_ids[]=208"
    "&size_ids[]=209"
    "&status_ids[]=6"
    "&status_ids[]=1"
    "&status_ids[]=2"
    "&material_ids[]=44"
    "&color_ids[]=1"
    "&order=newest_first"
)

KNOWN_IDS_FILE = "bluza_z_kapturem.txt"

TELEGRAM_BOT_TOKEN = "8516081401:AAH3645bZPzQhCtWgFp1PtdM0tZFj4JQjXk"
TELEGRAM_CHAT_ID = "1233434142"

# ==================================================

session = requests.Session()
retry = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[403, 429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9",
}

# --------------------------------------------------

def random_delay(a=3.0, b=6.0):
    time.sleep(random.uniform(a, b))


def load_known_ids():
    if not os.path.exists(KNOWN_IDS_FILE):
        return set()
    with open(KNOWN_IDS_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_known_ids(ids_set):
    with open(KNOWN_IDS_FILE, "w", encoding="utf-8") as f:
        for _id in sorted(ids_set):
            f.write(f"{_id}\n")
    print(f"💾 Zapisano {len(ids_set)} ID do {KNOWN_IDS_FILE}")


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }
    requests.post(url, data=payload, timeout=15)


def git_commit_if_changed():
    subprocess.run(["git", "config", "user.name", "github-actions"], check=False)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=False)
    subprocess.run(["git", "add", KNOWN_IDS_FILE], check=False)

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True
    )

    if status.stdout.strip():
        subprocess.run(["git", "commit", "-m", "Update bluza_z_kapturem.txt"], check=False)
        subprocess.run(["git", "push"], check=False)
        print("📤 bluza_z_kapturem.txt zacommitowany")
    else:
        print("ℹ️ Brak zmian do commitu")

# --------------------------------------------------

def main():
    known_ids = load_known_ids()
    all_ids = set(known_ids)
    new_links = []

    page = 1
    stop_scanning = False

    print("➡️ Sprawdzanie nowych ogłoszeń...\n")

    while not stop_scanning:
        url = BASE_URL if page == 1 else f"{BASE_URL}&page={page}"
        random_delay(4, 8)

        r = session.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.find_all("div", class_="new-item-box__container")

        if not items:
            break

        for item in items:
            a = item.find("a", href=True)
            if not a:
                continue

            href = a["href"]
            if "/items/" not in href:
                continue

            try:
                item_id = href.split("/items/")[1].split("-")[0]
            except IndexError:
                continue

            if item_id in known_ids:
                stop_scanning = True
                break

            all_ids.add(item_id)
            
            # 🔍 POBIERANIE CENY (TYLKO CENA PRZEDMIOTU)
            price_tag = item.find("span", {"data-testid": "item-price"})
            if not price_tag:
                continue

            price_text = price_tag.get_text(strip=True)
            price_text = price_text.replace("zł", "").strip()

            # ✅ FILTR KOŃCÓWEK
            if price_text.endswith((",00", ",50", ",99")):
                full_link = href
                new_links.append(full_link)

        page += 1

    if new_links:
        message = "🆕 Nowe bluzy z kapturem:\n\n" + "\n\n".join(
            f"➜ {link}" for link in new_links
        )
        send_telegram(message)


    # 🔥 ZAWSZE zapisujemy bazę
    save_known_ids(all_ids)
    git_commit_if_changed()

    print(f"✅ Nowe ogłoszenia: {len(new_links)}")

# --------------------------------------------------

if __name__ == "__main__":
    main()




