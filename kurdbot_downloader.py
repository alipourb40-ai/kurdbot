"""
🎵 KurdBot Downloader - ربات تلگرام محتوای کردی
"""

import os
import re
import logging
import tempfile
import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = "8863073767:AAHvRiufJzGOcOwdEYWjfvb1461jFemuUP8"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

INSTAGRAM_PATTERN = re.compile(
    r"(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/[\w\-]+"
)

def is_instagram_link(text):
    return bool(INSTAGRAM_PATTERN.search(text))

def extract_url(text):
    match = INSTAGRAM_PATTERN.search(text)
    if match:
        url = match.group(0)
        if not url.startswith("http"):
            url = "https://" + url
        return url
    return ""

async def download_content(url, output_dir):
    try:
        out_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        dl_cmd = [
            "yt-dlp",
            "-o", out_template,
            "--no-playlist",
            "--max-filesize", "49m",
            url
        ]
        proc = await asyncio.create_subprocess_exec(
            *dl_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        files = list(Path(output_dir).glob("*"))
        if not files:
            return {"error": "❌ فایلی دانلود نشد.\n" + stderr.decode()[-200:]}

        file_path = str(files[0])
        ext = Path(file_path).suffix.lower()

        if ext in [".mp3", ".m4a", ".aac", ".ogg", ".opus"]:
            ftype = "audio"
        elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            ftype = "video"
        else:
            ftype = "photo"

        return {"path": file_path, "type": ftype}

    except asyncio.TimeoutError:
        return {"error": "⏰ وقت دانلود تموم شد."}
    except FileNotFoundError:
        return {"error": "❌ yt-dlp پیدا نشد."}
    except Exception as e:
        return {"error": f"❌ خطا: {str(e)}"}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "دوست"
    await update.message.reply_text(
        f"سلام {name}! 👋\n\n"
        "🎵 به ربات محتوای کردی خوش اومدی!\n\n"
        "📎 لینک اینستاگرام بفرست → دانلود میکنم\n"
        "✏️ اسم آهنگ یا فیلم بنویس → پیدا میکنم"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if is_instagram_link(text):
        url = extract_url(text)
        msg = await update.message.reply_text("⬇️ دارم دانلود میکنم... صبر کن 🎵")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await download_content(url, tmpdir)

            if "error" in result:
                await msg.edit_text(result["error"])
                return

            file_path = result["path"]
            ftype = result["type"]
            caption = "🎵 محتوای کردی"

            try:
                await msg.edit_text("📤 داره آپلود میشه...")
                if ftype == "video":
                    with open(file_path, "rb") as f:
                        await update.message.reply_video(f, caption=caption, supports_streaming=True)
                elif ftype == "audio":
                    with open(file_path, "rb") as f:
                        await update.message.reply_audio(f, caption=caption)
                else:
                    with open(file_path, "rb") as f:
                        await update.message.reply_document(f, caption=caption)
                await msg.delete()
            except Exception as e:
                await msg.edit_text(f"❌ خطا در آپلود: {str(e)[:150]}")
    else:
        yt_url = f"https://www.youtube.com/results?search_query=Kurdish+{text.replace(' ', '+')}"
        ig_url = f"https://www.instagram.com/explore/search/?q={text.replace(' ', '+')}"
        await update.message.reply_text(
            f"🔍 نتیجه برای: *{text}*\n\n"
            f"▶️ [یوتیوب]({yt_url})\n"
            f"📸 [اینستاگرام]({ig_url})\n\n"
            "💡 لینک مستقیم پست رو بفرست تا دانلود کنم!",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🎵 ربات روشنه!")
    app.run_polling()


if __name__ == "__main__":
    main()
        
