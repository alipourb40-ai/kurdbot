"""
🎵 ربات کردی - نسخه سازگار
"""
import os
import re
import logging
import tempfile
import subprocess
from pathlib import Path
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

TOKEN = "8863073767:AAHvRiufJzGOcOwdEYWjfvb1461jFemuUP8"

logging.basicConfig(level=logging.INFO)

INSTAGRAM_RE = re.compile(r"(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/[\w\-]+")

def get_url(text):
    m = INSTAGRAM_RE.search(text)
    if m:
        u = m.group(0)
        return u if u.startswith("http") else "https://" + u
    return ""

def download(url, folder):
    try:
        out = os.path.join(folder, "%(title)s.%(ext)s")
        r = subprocess.run(
            ["yt-dlp", "-o", out, "--no-playlist", "--max-filesize", "49m", url],
            capture_output=True, timeout=120
        )
        files = list(Path(folder).glob("*"))
        if not files:
            return None, "❌ دانلود نشد: " + r.stderr.decode()[-200:]
        f = str(files[0])
        ext = Path(f).suffix.lower()
        if ext in [".mp3", ".m4a", ".aac", ".ogg"]:
            t = "audio"
        elif ext in [".mp4", ".mov", ".mkv", ".webm"]:
            t = "video"
        else:
            t = "doc"
        return f, t
    except subprocess.TimeoutExpired:
        return None, "⏰ وقت تموم شد"
    except Exception as e:
        return None, f"❌ {e}"

def start(update, context):
    name = update.effective_user.first_name or "دوست"
    update.message.reply_text(
        f"سلام {name}! 👋\n\n"
        "🎵 ربات محتوای کردی\n\n"
        "📎 لینک اینستاگرام بفرست → دانلود\n"
        "✏️ اسم آهنگ بنویس → جستجو"
    )

def handle(update, context):
    text = update.message.text.strip()
    url = get_url(text)

    if url:
        msg = update.message.reply_text("⬇️ دارم دانلود میکنم...")
        with tempfile.TemporaryDirectory() as tmp:
            path, ftype = download(url, tmp)
            if not path:
                msg.edit_text(ftype)
                return
            msg.edit_text("📤 آپلود میشه...")
            try:
                with open(path, "rb") as f:
                    if ftype == "video":
                        update.message.reply_video(f, caption="🎵 محتوای کردی")
                    elif ftype == "audio":
                        update.message.reply_audio(f, caption="🎵 محتوای کردی")
                    else:
                        update.message.reply_document(f, caption="🎵 محتوای کردی")
                msg.delete()
            except Exception as e:
                msg.edit_text(f"❌ {str(e)[:150]}")
    else:
        yt = f"https://www.youtube.com/results?search_query=Kurdish+{text.replace(' ','+')}"
        ig = f"https://www.instagram.com/explore/search/?q={text.replace(' ','+')}"
        update.message.reply_text(
            f"🔍 *{text}*\n\n▶️ [یوتیوب]({yt})\n📸 [اینستاگرام]({ig})\n\n"
            "💡 لینک پست رو بفرست تا دانلود کنم!",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))
    print("🎵 ربات روشنه!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
