import os
import re
import logging
import tempfile
import subprocess
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8863073767:AAHvRiufJzGOcOwdEYWjfvb1461jFemuUP8"
logging.basicConfig(level=logging.INFO)
IG_RE = re.compile(r"(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/[\w\-]+")

def get_url(text):
    m = IG_RE.search(text)
    if not m:
        return ""
    u = m.group(0)
    return u if u.startswith("http") else "https://" + u

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لینک اینستاگرام بفرست تا دانلود کنم")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url = get_url(text)
    if url:
        msg = await update.message.reply_text("دارم دانلود میکنم...")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                path, ftype = dl(url, tmp)
                if not path:
                    await msg.edit_text("دانلود نشد")
                    return
                await msg.edit_text("آپلود میشه...")
                with open(path, "rb") as f:
                    if ftype == "video":
                        await update.message.reply_video(f)
                    elif ftype == "audio":
                        await update.message.reply_audio(f)
                    else:
                        await update.message.reply_document(f)
                await msg.delete()
            except Exception as e:
                await msg.edit_text(str(e)[:200])
    else:
        yt = "https://www.youtube.com/results?search_query=Kurdish+" + text.replace(" ", "+")
        await update.message.reply_text("لینک پیدا نشد\n\nیوتیوب: " + yt)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("ربات روشنه!")
    app.run_polling()

if __name__ == "__main__":
    main()
            
