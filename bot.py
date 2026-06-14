import os
import logging
import yt_dlp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode
import re
import asyncio

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DOWNLOAD_DIR = "/tmp/videos"
MAX_FILE_SIZE_MB = 50

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def is_valid_url(text: str) -> bool:
    pattern = re.compile(r"^https?://\S+$", re.IGNORECASE)
    return bool(pattern.match(text.strip()))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome = (
        f"👋 أهلاً {user.first_name}!\n\n"
        "🎬 *بوت تنزيل الفيديو*\n\n"
        "أرسل لي رابط أي فيديو وسأنزله لك!\n\n"
        "✅ *المواقع المدعومة:*\n"
        "• YouTube • Instagram • TikTok\n"
        "• Twitter/X • Facebook • وأكثر!\n\n"
        "⚠️ الحد الأقصى: 50MB"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🟢 البوت يعمل!")


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text("❌ أرسل رابطاً صحيحاً يبدأ بـ http://")
        return

    status_msg = await update.message.reply_text("⏳ جاري التنزيل...")

    output_template = os.path.join(DOWNLOAD_DIR, "%(title).50s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "format": "best[filesize<45M]/best",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "socket_timeout": 30,
        "retries": 3,
    }

    downloaded_file = None

    try:
        loop = asyncio.get_event_loop()

        def do_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename

        downloaded_file = await loop.run_in_executor(None, do_download)

        # البحث عن الملف إذا تغير الامتداد
        if not os.path.exists(downloaded_file):
            base = os.path.splitext(downloaded_file)[0]
            for ext in [".mp4", ".mkv", ".webm", ".avi"]:
                if os.path.exists(base + ext):
                    downloaded_file = base + ext
                    break

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise FileNotFoundError("لم يوجد الملف")

        file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)

        if file_size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"⚠️ الفيديو كبير جداً ({file_size_mb:.1f}MB)\nالحد: {MAX_FILE_SIZE_MB}MB"
            )
            return

        await status_msg.edit_text("📤 جاري الإرسال...")

        with open(downloaded_file, "rb") as vf:
            await update.message.reply_video(
                video=vf,
                supports_streaming=True,
                caption="✅ تم التنزيل! 🎬",
                read_timeout=120,
                write_timeout=120,
            )

        await status_msg.delete()

    except Exception as e:
        err = str(e).lower()
        if "private" in err:
            msg = "🔒 الفيديو خاص"
        elif "unavailable" in err:
            msg = "⛔ الفيديو غير متاح"
        else:
            msg = "❌ فشل التنزيل! تأكد أن الرابط صحيح والفيديو عام"
        await status_msg.edit_text(msg)
        logger.error(f"Error: {e}")

    finally:
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN غير موجود!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    logger.info("البوت يعمل...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
