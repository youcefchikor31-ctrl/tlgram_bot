import os
import logging
import threading
import asyncio
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
DOWNLOAD_DIR = "/tmp/videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass


def is_valid_url(text):
    return bool(re.match(r"^https?://\S+$", text.strip()))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👋 أهلاً {update.effective_user.first_name}!\n\n"
        "🎬 أرسل رابط أي فيديو وسأنزله لك!\n"
        "✅ YouTube • TikTok • Instagram • Twitter\n"
        "⚠️ الحد الأقصى: 50MB"
    )


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟢 البوت يعمل!")


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not is_valid_url(url):
        await update.message.reply_text("❌ أرسل رابطاً يبدأ بـ http://")
        return

    status = await update.message.reply_text("⏳ جاري التنزيل...")
    output = os.path.join(DOWNLOAD_DIR, "%(title).40s.%(ext)s")
    ydl_opts = {
        "outtmpl": output,
        "format": "best[filesize<45M]/best",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "retries": 3,
    }

    filepath = None
    try:
        loop = asyncio.get_running_loop()

        def do_dl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        filepath = await loop.run_in_executor(None, do_dl)

        if not os.path.exists(filepath):
            base = os.path.splitext(filepath)[0]
            for ext in [".mp4", ".mkv", ".webm"]:
                if os.path.exists(base + ext):
                    filepath = base + ext
                    break

        size_mb = os.path.getsize(filepath) / 1024 / 1024
        if size_mb > 50:
            await status.edit_text(f"⚠️ الفيديو كبير ({size_mb:.1f}MB) - الحد 50MB")
            return

        await status.edit_text("📤 جاري الإرسال...")
        with open(filepath, "rb") as f:
            await update.message.reply_video(
                video=f, caption="✅ تم! 🎬",
                supports_streaming=True,
                read_timeout=120, write_timeout=120
            )
        await status.delete()

    except Exception as e:
        err = str(e).lower()
        msg = ("🔒 الفيديو خاص" if "private" in err
               else "⛔ الفيديو غير متاح" if "unavailable" in err
               else "❌ فشل التنزيل! تأكد أن الرابط صحيح")
        await status.edit_text(msg)
        logger.error(e)
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN غير موجود!")

    threading.Thread(
        target=lambda: HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever(),
        daemon=True
    ).start()
    logger.info(f"Web server on port {PORT}")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    logger.info("البوت يعمل...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
