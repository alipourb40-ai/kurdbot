"""
🎵 KurdBot Downloader
ربات تلگرام برای دانلود آهنگ و فیلم کردی از اینستاگرام

نصب:
    pip install python-telegram-bot yt-dlp instaloader

اجرا:
    python kurdbot_downloader.py
"""

import os
import re
import logging
import tempfile
import asyncio
import subprocess
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ─── تنظیمات ──────────────────────────────────────────────
TOKEN = "8863073767:AAHvRiufJzGOcOwdEYWjfvb1461jFemuUP8"

# اگه اینستاگرام لاگین میخواد (برای پست‌های خصوصی)
IG_USERNAME = ""   # اختیاری
IG_PASSWORD = ""   # اختیاری

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ─── تشخیص لینک ────────────────────────────────────────────

INSTAGRAM_PATTERN = re.compile(
    r"(https?://)?(www\.)?instagram\.com/(p|reel|tv|stories)/[\w\-]+"
)

def is_instagram_link(text: str) -> bool:
    return bool(INSTAGRAM_PATTERN.search(text))

def extract_url(text: str) -> str:
    match = INSTAGRAM_PATTERN.search(text)
    if match:
        url = match.group(0)
        if not url.startswith("http"):
            url = "https://" + url
        return url
    return ""

# ─── دانلود با yt-dlp ──────────────────────────────────────

async def download_instagram(url: str, output_dir: str) -> dict:
    """
    دانلود ویدیو یا تصویر از اینستاگرام با yt-dlp
    برمیگردونه: {"path": ..., "type": "video"/"audio"/"photo", "title": ...}
    """
    try:
        # ابتدا اطلاعات بگیر
        info_cmd = [
            "yt-dlp",
            "--print", "%(title)s|%(ext)s|%(_type)s",
            "--no-playlist",
            url
        ]
        if IG_USERNAME and IG_PASSWORD:
            info_cmd += ["--username", IG_USERNAME, "--password", IG_PASSWORD]

        proc = await asyncio.create_subprocess_exec(
            *info_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        info_line = stdout.decode().strip().split("\n")[0]
        parts = info_line.split("|")
        title = parts[0] if parts else "فایل کردی"

        # دانلود فایل
        out_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        dl_cmd = [
            "yt-dlp",
            "-o", out_template,
            "--no-playlist",
            "--max-filesize", "49m",   # حد تلگرام 50MB
            url
        ]
        if IG_USERNAME and IG_PASSWORD:
            dl_cmd += ["--username", IG_USERNAME, "--password", IG_PASSWORD]

        proc = await asyncio.create_subprocess_exec(
            *dl_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        # پیدا کردن فایل دانلود شده
        files = list(Path(output_dir).glob("*"))
        if not files:
            return {"error": "فایلی دانلود نشد. " + stderr.decode()[-200:]}

        file_path = str(files[0])
        ext = Path(file_path).suffix.lower()

        if ext in [".mp3", ".m4a", ".aac", ".ogg", ".opus"]:
            ftype = "audio"
        elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            ftype = "video"
        else:
            ftype = "photo"

        return {"path": file_path, "type": ftype, "title": title}

    except asyncio.TimeoutError:
        return {"error": "⏰ وقت دانلود تموم شد. لینک رو دوباره امتحان کن."}
    except FileNotFoundError:
        return {"error": "❌ yt-dlp نصب نیست.\nاجرا کن: pip install yt-dlp"}
    except Exception as e:
        return {"error": f"❌ خطا: {str(e)}"}

# ─── جستجوی بدون لینک ─────────────────────────────────────

SEARCH_SUGGESTIONS = {
    "music": {
        "hashtags": ["#kurdish_music", "#موسیقی_کردی", "#muzika_kurdi", "#dengbej"],
        "pages": ["kurdish.music.page", "kurdi_music_official", "sorani_music"],
    },
    "film": {
        "hashtags": ["#kurdish_film", "#فیلم_کردی", "#kurdish_series"],
        "pages": ["kurdsat_tv", "nrt_kurdish", "rudaw"],
    },
}

async def handle_search_query(update: Update, query: str):
    """وقتی کاربر اسم آهنگ/فیلم میده بدون لینک"""
    # جستجو در یوتیوب (از طریق yt-dlp)
    msg = await update.message.reply_text(f"🔍 دنبال *{query}* میگردم...", parse_mode="Markdown")

    try:
        search_cmd = [
            "yt-dlp",
            "--print", "%(webpage_url)s|%(title)s|%(duration_string)s",
            "--no-playlist",
            "--max-downloads", "5",
            f"ytsearch5:کردی {query}",
        ]
        proc = await asyncio.create_subprocess_exec(
            *search_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        lines = stdout.decode().strip().split("\n")

        if not lines or not lines[0]:
            raise ValueError("نتیجه‌ای پیدا نشد")

        results = []
        buttons = []
        for i, line in enumerate(lines[:5]):
            parts = line.split("|")
            if len(parts) >= 2:
                url = parts[0]
                title = parts[1][:40]
                duration = parts[2] if len(parts) > 2 else ""
                results.append({"url": url, "title": title, "duration": duration})
                buttons.append([
                    InlineKeyboardButton(
                        f"{i+1}. {title} ({duration})",
                        callback_data=f"dl_{url[:50]}"  # ذخیره URL کوتاه
                    )
                ])

        # ذخیره نتایج کامل در context
        context_data = {f"result_{i}": r["url"] for i, r in enumerate(results)}
        # (در پروژه واقعی از user_data استفاده کن)

        text = f"🎵 نتایج برای *{query}*:\nکدوم رو دانلود کنم؟"
        kb = InlineKeyboardMarkup(buttons + [[
            InlineKeyboardButton("❌ انصراف", callback_data="cancel")
        ]])
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=kb)

    except (asyncio.TimeoutError, ValueError, Exception):
        # اگه yt-dlp نداشت یا خطا داد، لینک‌های اینستاگرام بده
        ig_url = f"https://www.instagram.com/explore/search/?q={query.replace(' ', '+')}"
        yt_url = f"https://www.youtube.com/results?search_query=Kurdish+{query.replace(' ', '+')}"
        text = (
            f"🔍 نتیجه برای *{query}*:\n\n"
            f"📸 [جستجو در اینستاگرام]({ig_url})\n"
            f"▶️ [جستجو در یوتیوب]({yt_url})\n\n"
            "💡 لینک مستقیم پست رو بفرست تا برات دانلود کنم!"
        )
        await msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)

# ─── هندلرها ───────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "دوست"
    text = (
        f"سلام {name}! 👋\n\n"
        "🎵 *KurdBot* — ربات محتوای کردی\n\n"
        "چیکار میتونم بکنم:\n"
        "📎 *لینک اینستاگرام* بفرست → دانلود میکنم\n"
        "✏️ *اسم آهنگ/فیلم* بنویس → پیدا میکنم\n\n"
        "مثال:\n"
        "• `https://instagram.com/reel/ABC123`\n"
        "• `شیوان پرور`\n"
        "• `فیلم کردی عاشقانه`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # ─── حالت ۱: لینک اینستاگرام ───
    if is_instagram_link(text):
        url = extract_url(text)
        msg = await update.message.reply_text("⬇️ دارم دانلود میکنم... صبر کن 🎵")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await download_instagram(url, tmpdir)

            if "error" in result:
                await msg.edit_text(result["error"])
                return

            file_path = result["path"]
            ftype = result["type"]
            title = result.get("title", "محتوای کردی")
            caption = f"🎵 {title}\n\n@KurdContentBot"

            try:
                if ftype == "video":
                    await msg.edit_text("📤 داره آپلود میشه...")
                    with open(file_path, "rb") as f:
                        await update.message.reply_video(
                            f, caption=caption,
                            supports_streaming=True,
                        )
                elif ftype == "audio":
                    await msg.edit_text("📤 داره آپلود میشه...")
                    with open(file_path, "rb") as f:
                        await update.message.reply_audio(f, caption=caption, title=title)
                else:
                    await msg.edit_text("📤 داره آپلود میشه...")
                    with open(file_path, "rb") as f:
                        await update.message.reply_document(f, caption=caption)

                await msg.delete()

            except Exception as e:
                if "too large" in str(e).lower() or "413" in str(e):
                    await msg.edit_text(
                        "⚠️ فایل بیشتر از 50MB هست و تلگرام اجازه نمیده.\n"
                        f"لینک مستقیم: {url}"
                    )
                else:
                    await msg.edit_text(f"❌ خطا در آپلود: {str(e)[:100]}")

    # ─── حالت ۲: جستجو بدون لینک ───
    else:
        await handle_search_query(update, text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ لغو شد.")
        return

    if query.data.startswith("dl_"):
        url = query.data[3:]
        await query.edit_message_text(f"⬇️ دارم دانلود میکنم... صبر کن 🎵")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = await download_instagram(url, tmpdir)
            if "error" in result:
                await query.edit_message_text(result["error"])
                return

            file_path = result["path"]
            ftype = result["type"]
            title = result.get("title", "محتوای کردی")
            caption = f"🎵 {title}\n\n@KurdContentBot"

            try:
                if ftype == "video":
                    with open(file_path, "rb") as f:
                        await query.message.reply_video(f, caption=caption, supports_streaming=True)
                elif ftype == "audio":
                    with open(file_path, "rb") as f:
                        await query.message.reply_audio(f, caption=caption, title=title)
                else:
                    with open(file_path, "rb") as f:
                        await query.message.reply_document(f, caption=caption)

                await query.delete_message()

            except Exception as e:
                await query.edit_message_text(f"❌ خطا: {str(e)[:150]}")


# ─── اجرا ──────────────────────────────────────────────────

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🎵 KurdBot آماده‌ست!")
    print("📎 لینک اینستاگرام → دانلود خودکار")
    print("✏️  اسم → جستجو در یوتیوب")
    app.run_polling()


if __name__ == "__main__":
    main()
