import re
import os
import json
import httpx
import tempfile
import subprocess
from pathlib import Path

TOKEN = "8863073767:AAHvRiufJzGOcOwdEYWjfvb1461jFemuUP8"
API = f"https://api.telegram.org/bot{TOKEN}"

IG_RE = re.compile(r"(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/[\w\-]+")

def get_url(text):
    m = IG_RE.search(text)
    if not m:
        return ""
    u = m.group(0)
    return u if u.startswith("http") else "https://" + u

def send(chat_id, text):
    httpx.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": text})

def edit(chat_id, msg_id, text):
    httpx.post(f"{API}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": text})

def send_video(chat_id, path):
    with open(path, "rb") as f:
        httpx.post(f"{API}/sendVideo", data={"chat_id": chat_id}, files={"video": f}, timeout=120)

def send_audio(chat_id, path):
    with open(path, "rb") as f:
        httpx.post(f"{API}/sendAudio", data={"chat_id": chat_id}, files={"audio": f}, timeout=120)

def send_doc(chat_id, path):
    with open(path, "rb") as f:
        httpx.post(f"{API}/sendDocument", data={"chat_id": chat_id}, files={"document": f}, timeout=120)

def dl(url, folder):
    out = os.path.join(folder, "file.%(ext)s")
    subprocess.run(["yt-dlp", "-o", out, "--no-playlist", "--max-filesize", "49m", url], timeout=120)
    files = list(Path(folder).glob("*"))
    if not files:
        return None, "doc"
    f = str(files[0])
    ext = Path(f).suffix.lower()
    if ext in [".mp3", ".m4a", ".aac"]:
        return f, "audio"
    elif ext in [".mp4", ".mov", ".mkv"]:
        return f, "video"
    return f, "doc"

def handle(update):
    msg = update.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "").strip()
    if not chat_id or not text:
        return
    if text == "/start":
        send(chat_id, "سلام! لینک اینستاگرام بفرست تا دانلود کنم 🎵")
        return
    url = get_url(text)
    if url:
        r = httpx.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": "دارم دانلود میکنم..."})
        msg_id = r.json().get("result", {}).get("message_id")
        with tempfile.TemporaryDirectory() as tmp:
            path, ftype = dl(url, tmp)
            if not path:
                edit(chat_id, msg_id, "دانلود نشد")
                return
            edit(chat_id, msg_id, "آپلود میشه...")
            if ftype == "video":
                send_video(chat_id, path)
            elif ftype == "audio":
                send_audio(chat_id, path)
            else:
                send_doc(chat_id, path)
    else:
        yt = "https://www.youtube.com/results?search_query=Kurdish+" + text.replace(" ", "+")
        send(chat_id, f"لینک اینستاگرام بفرست!\n\nیوتیوب: {yt}")

def main():
    offset = 0
    print("ربات روشنه!")
    while True:
        try:
            r = httpx.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=40)
            updates = r.json().get("result", [])
            for u in updates:
                offset = u["update_id"] + 1
                handle(u)
        except Exception as e:
            print(f"خطا: {e}")

if __name__ == "__main__":
    main()
    
