from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime
from pathlib import Path

PHRASE = "the"  # use "markets in turmoil" for prod
CNBC_URL = "https://www.cnbc.com"
DATA_FILE = Path("data.json")
HTML_FILE = Path("site/index.html")

app = Flask(__name__)

def scrape_cnbc():
    try:
        resp = requests.get(CNBC_URL, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("a")

        for a in articles:
            title = a.get_text(strip=True).lower()
            if PHRASE in title:
                url = a['href']
                timestamp = datetime.utcnow().isoformat() + "Z"
                DATA_FILE.write_text(json.dumps({"last_seen": timestamp, "last_url": url}))
                update_html(found=True, timestamp=timestamp, url=url)
                return

        # not found — use fallback
        update_html(
            found=False,
            timestamp="February 24, 2020",
            url="https://www.cnbc.com/2020/02/24/stock-market-today-live.html"
        )

    except Exception as e:
        print("scrape error:", e)

def update_html(found, timestamp, url=None):
    if found:
        msg = f"YEAH, it happened. CNBC posted it on {timestamp} — <a href='{url}'>here's the link</a>."
    else:
        msg = f"No, CNBC last mentioned it on {timestamp}. Here's the proof: <a href='{url}'>{url}</a>"

    html = f"""<!DOCTYPE html>
<html>
  <head><title>Are Markets in Turmoil?</title></head>
  <body>
    <h1>{msg}</h1>
  </body>
</html>"""
    HTML_FILE.write_text(html)

@app.route('/')
def home():
    return HTML_FILE.read_text()

# run once at boot
scrape_cnbc()

# run every 15 min
sched = BackgroundScheduler()
sched.add_job(scrape_cnbc, 'interval', minutes=15)
sched.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
