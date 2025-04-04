from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime
from pathlib import Path

# doom phrases to trigger the "YEAH" state
TRIGGER_PHRASES = [
    "markets in turmoil",
    "market in turmoil",
    "turmoil in market"
]

# bonus doom for flavor
RELATED_PHRASES = [
    "markets in chaos",
    "dow plunges",
    "recession fears",
    "stocks tumble",
    "sell-off",
    "bloodbath",
    "panic selling"
]

CNBC_URL = "https://www.cnbc.com"
DATA_FILE = Path("data.json")
HTML_FILE = Path("site/index.html")

app = Flask(__name__)

def scrape_cnbc():
    try:
        resp = requests.get(CNBC_URL, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("a")

        matched_main = None
        related_matches = []

        for a in articles:
            title = a.get_text(strip=True).lower()
            href = a.get("href", "#")

            if any(p in title for p in TRIGGER_PHRASES) and not matched_main:
                matched_main = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "url": href
                }

            elif any(p in title for p in RELATED_PHRASES):
                related_matches.append({
                    "title": a.get_text(strip=True),
                    "url": href
                })

        if matched_main:
            DATA_FILE.write_text(json.dumps(matched_main))
            update_html(found=True, timestamp=matched_main["timestamp"], url=matched_main["url"], related=related_matches)
        else:
            # fallback to known panic event
            update_html(
                found=False,
                timestamp="February 24, 2020",
                url="https://www.cnbc.com/2020/02/24/stock-market-today-live.html",
                related=related_matches
            )

    except Exception as e:
        print("scrape error:", e)

def update_html(found, timestamp, url=None, related=[]):
    if found:
        answer = f"<span style='color:darkred;font-weight:bold;'>YEAH</span>, it happened. CNBC posted it on {timestamp}."
        proof = f"<a href='{url}' target='_blank'>here's the link</a>"
    else:
        answer = f"<strong>No</strong>, CNBC last mentioned it on {timestamp}."
        proof = f"<a href='{url}' target='_blank'>{url}</a>"

    related_html = ""
    if related:
        related_html = "<h2>Related Panic Headlines</h2><ul>"
        for match in related:
            related_html += f"<li><a href='{match['url']}' target='_blank'>{match['title']}</a></li>"
        related_html += "</ul>"

    html = f"""<!DOCTYPE html>
<html>
  <head>
    <title>Are Markets in Turmoil?</title>
    <style>
      body {{
        font-family: system-ui, sans-serif;
        max-width: 700px;
        margin: 4em auto;
        padding: 1em;
        line-height: 1.6;
        color: #111;
      }}
      h1 {{
        font-size: 2.4em;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5em;
      }}
      .answer {{
        font-size: 1.5em;
        margin-bottom: 1em;
        text-align: center;
      }}
      .proof {{
        font-size: 1.1em;
        text-align: center;
        margin-bottom: 2em;
      }}
      h2 {{
        margin-top: 2em;
        border-top: 1px solid #ccc;
        padding-top: 1em;
      }}
      ul {{
        padding-left: 1.2em;
      }}
      li {{
        margin-bottom: 0.6em;
      }}
      a {{
        color: #0645AD;
        text-decoration: none;
      }}
      a:hover {{
        text-decoration: underline;
      }}
    </style>
  </head>
  <body>
    <h1>Are Markets in Turmoil?</h1>
    <div class="answer">{answer}</div>
    <div class="proof">Here’s the proof: {proof}</div>
    {related_html}
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
