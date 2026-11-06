"""Envoie data/telegram.html sur Telegram (bot inli). Ne fait rien si les secrets ne sont pas configurés."""
import json, os, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
token, chats = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
if not token or not chats:
    print("Secrets TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID absents : message non envoyé.")
    sys.exit(0)
chat = [c.strip() for c in chats.split(",") if c.strip()][0]
data = {"chat_id": chat, "text": (ROOT / "data/telegram.html").read_text(), "parse_mode": "HTML",
        "disable_web_page_preview": "true",
        "reply_markup": json.dumps({"inline_keyboard": [[{"text": "Ouvrir le tableau de bord",
                                                          "url": "https://paulleriic.github.io/ai-bubble-tracker/"}]]})}
r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=30)
if not r.ok:
    sys.exit(f"Telegram a refusé l'envoi (HTTP {r.status_code}) : {r.text[:300]}")
print("Message envoyé")
