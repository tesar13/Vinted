import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import time
import random
import os
import subprocess
import re

# ================== KONFIGURACJA ==================

BASE_URL = (
    "https://www.vinted.pl/catalog"
    "?catalog[]=76"
    "&brand_ids[]=57542" #Farah
    "&brand_ids[]=17" #Esprit
    "&brand_ids[]=259" #Wrangler
    "&brand_ids[]=2319" #The North Face
    "&brand_ids[]=14" #Adidas
    "&brand_ids[]=1845" #Tom Tailor
    "&brand_ids[]=407" #Lee Cooper
    "&brand_ids[]=2287" #Next
    "&brand_ids[]=53" #Nike
    "&brand_ids[]=63" #Lee
    "&brand_ids[]=10" #Levi's
    "&size_ids[]=208"
    "&price_to=30.00"
    "&currency=PLN"
    "&status_ids[]=6"
    "&status_ids[]=1"
    "&order=newest_first"
)

# zmień na True jeśli chcesz żeby skrypt pobierał tylko ogłoszenia z Polski
TYLKO_PL = True # ⬅️⬅️⬅️⬅️⬅️
# zmień na True jeśli chcesz żeby skrypt pobierał tylko ogłoszenia z Polski

KNOWN_IDS_FILE = "koszulki_do_30.txt" # ⬅️⬅ do zmiany

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
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
        print("📤 koszulki_do_30.txt zacommitowany")
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

        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Błąd sieci na stronie {page}: {e}")
            print("↻ Pomijam stronę i idę dalej")
            page += 1
            random_delay(6, 10)
            continue

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
            price_tag = item.select_one('p[data-testid$="--price-text"]')
            if not price_tag:
                continue
            
            raw_price = price_tag.get_text(" ", strip=True)
            
            match = re.search(r"\d+,\d{2}", raw_price)
            if not match:
                continue
            
            price_value = match.group()
            
            if not TYLKO_PL or price_value.endswith((",00", ",50", ",99")):
                clean_href = href.split("?")[0]
                full_link = clean_href
                new_links.append(full_link)

        page += 1

    if new_links:
        message = "🆕 Nowe koszulki:\n\n" + "\n\n".join(
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

















