import os
import re
import logging
import tempfile
import asyncio
import subprocess
from pathlib import Path
from telegram import Update
ApplicationBuilder ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8863073767:AAHvRiufJzGOcOwdEYWjfvb1461jFemuUP8"
logging.basicConfig(level=logging.INFO)

IG_RE = re.compile(r"(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/[\w\-]+")

def get_url(text):
    m = IG_RE.search(text)
    if not m:
        return ""
    u = m.group(0)
    return u if u.startswith("http") else "https://" + u

def download(url, folder):
    try:
        out = os.path.join(folder, "file.%(ext)s")
        r = subprocess.run(
            ["yt-dlp", "-o", out, "--no-playlist", "--max-filesize", "49m", url],
            capture_output=True, timeout=120
        )
        files = list(Path(folder).glob("*"))
        if not files:
            return None, "❌ دانلود نشد"
        f = str(files[0])
        ext = Path(f).suffix.lower()
        if ext in [".mp3", ".m4a", ".aac", ".ogg"]:
            t = "audio"
        elif ext in [".mp4", ".mov", ".mkv", ".webm"]:
            t = "video"
        else:
            t = "doc"
        return f, t
    except Exception as e:
        return None, f"❌ {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"سلام! 👋\n\n🎵 ربات محتوای کردی\n\n"
        "📎 لینک اینستاگرام بفرست → دانلود\n"
        "✏️ اسم آهنگ بنویس → جستجو"
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    url = get_url(text)
    if url:
        msg = await update.message.reply_text("⬇️ دارم دانلود میکنم...")
        with tempfile.TemporaryDirectory() as tmp:
            path, ftype = await asyncio.to_thread(download, url, tmp)
            if not path:
                await msg.edit_text(ftype)
                return
            await msg.edit_text("📤 آپلود میشه...")
            try:
                with open(path, "rb") as f:
                    if ftype == "video":
                        await update.message.reply_video(f, caption="🎵 محتوای کردی")
                    elif ftype == "audio":
                        await update.message.reply_audio(f, caption="🎵 محتوای کردی")
                    else:
                        await update.message.reply_document(f, caption="🎵 محتوای کردی")
                await msg.delete()
            except Exception as e:
                await msg.edit_text(f"❌ {str(e)[:150]}")
    else:
        yt = f"https://www.youtube.com/results?search_query=Kurdish+{text.replace(' ','+')}"
        ig = f"https://www.instagram.com/explore/search/?q={text.replace(' ','+')}"
        await update.message.reply_text(
            f"🔍 *{text}*\n\n▶️ [یوتیوب]({yt})\n📸 [اینستاگرام]({ig})\n\n"
            "💡 لینک پست رو بفرست تا دانلود کنم!",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("🎵 ربات روشنه!")
    app.run_polling()

if __name__ == "__main__":
    main()
    
