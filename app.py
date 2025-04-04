from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime
from pathlib import Path

# exact match phrases that trigger the "YEAH" state
TRIGGER_PHRASES = [
    "markets in turmoil",
    "market in turmoil",
    "turmoil in market"
]

# doom scoring keywords
DOOM_WORDS = [
    "plunge", "panic", "fear", "tumble", "collapse", "chaos", "turmoil", "bloodbath",
    "jitters", "uncertain", "recession", "crash", "sell-off", "volatility", "dive",
    "free fall", "shock", "bears", "inflation", "yield", "downgrade", "slump",
    "defaults", "bank run", "liquidity crisis"
]

CNBC_URL = "https://www.cnbc.com"
DATA_FILE = Path("data.json")
HTML_FILE = Path("site/index.html")

app = Flask(__name__)

def score_headline(text):
    score = 0
    lower_text = text.lower()

    for word in DOOM_WORDS:
        if word in lower_text:
            score += 1

    if any(word in lower_text for word in ["now", "today"]):
        score += 1
    if len(text.split()) <= 6:
        score += 1
    if text.isupper():
        score += 1

    return score

def scrape_cnbc():
    try:
        resp = requests.get(CNBC_URL, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.find_all("a")

        matched_main = None
        ranked_headlines = []
        now = datetime.utcnow().isoformat() + "Z"
        latest_title = "N/A"

        for a in articles:
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            title_lower = title.lower()
            href = a.get("href", "#")

            if not latest_title:
                latest_title = title

            if any(p in title_lower for p in TRIGGER_PHRASES) and not matched_main:
                matched_main = {
                    "timestamp": now,
                    "url": href
                }

            score = score_headline(title)
            if score > 0:
                ranked_headlines.append({
                    "title": title,
                    "url": href,
                    "score": score
                })

        ranked_headlines.sort(key=lambda x: x["score"], reverse=True)
        top_5 = ranked_headlines[:5]

        if matched_main:
            DATA_FILE.write_text(json.dumps(matched_main))
            update_html(
                found=True,
                timestamp=matched_main["timestamp"],
                url=matched_main["url"],
                panic_headlines=top_5,
                last_scraped=now,
                last_seen_title=latest_title
            )
        else:
            update_html(
                found=False,
                timestamp="February 24, 2020",
                url="https://www.cnbc.com/2020/02/24/stock-market-today-live.html",
                panic_headlines=top_5,
                last_scraped=now,
                last_seen_title=latest_title
            )

    except Exception as e:
        print("scrape error:", e)

def update_html(found, timestamp, url=None, panic_headlines=[], last_scraped=None, last_seen_title=None):
    if found:
        answer = f"<span style='color:darkred;font-weight:bold;'>YEAH</span>, it happened. CNBC posted it on {timestamp}."
        proof = f"<a href='{url}' target='_blank'>here's the link</a>"
    else:
        answer = f"<strong>No</strong>, CNBC last mentioned it on {timestamp}."
        proof = f"<a href='{url}' target='_blank'>{url}</a>"

    panic_html = ""
    if panic_headlines:
        panic_html = "<h2>Top 5 Panic Headlines Right Now</h2><ul>"
        for h in panic_headlines:
            panic_html += f"<li><a href='{h['url']}' target='_blank'>{h['title']}</a> <small>(score: {h['score']})</small></li>"
        panic_html += "</ul>"

    debug_html = f"""
      <div class="footer">
        <hr>
        <p><strong>Last scrape:</strong> {last_scraped}</p>
        <p><strong>Most recent headline:</strong> {last_seen_title}</p>
      </div>
    """

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
      small {{
        color: #888;
        font-size: 0.9em;
      }}
      .footer {{
        margin-top: 3em;
        font-size: 0.9em;
        color: #555;
        text-align: center;
      }}
    </style>
  </head>
  <body>
    <h1>Are Markets in Turmoil?</h1>
    <div class="answer">{answer}</div>
    <div class="proof">Here’s the proof: {proof}</div>
    {panic_html}
    {debug_html}
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
