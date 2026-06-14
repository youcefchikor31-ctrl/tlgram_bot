import os
import logging
import threading
import re
from http.server import HTTPServer, BaseHTTPRequestHandler

import yt_dlp
import telebot

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 10000))
DOWNLOAD_DIR = "/tmp/videos"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass


def is_valid_url(text):
    return bool(re.match(r"^https?://\S+$", text.strip()))


@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message,
        f"👋 أهلاً {message.from_user.first_name}!\n\n"
        "🎬 أرسل رابط أي فيديو وسأنزله لك!\n\n"
        "✅ YouTube • TikTok • Instagram • Twitter • Facebook\n\n"
        "⚠️ الحد الأقصى: 50MB"
    )


@bot.message_handler(commands=["ping"])
def ping(message):
    bot.reply_to(message, "🟢 البوت يعمل!")


@bot.message_handler(func=lambda m: True, content_types=["text"])
def download_video(message):
    url = message.text.strip()

    if not is_valid_url(url):
        bot.reply_to(message, "❌ أرسل رابطاً يبدأ بـ http://")
        return

    status = bot.reply_to(message, "⏳ جاري التنزيل...")

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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

        # البحث عن الملف إذا تغير الامتداد
        if not os.path.exists(filepath):
            base = os.path.splitext(filepath)[0]
            for ext in [".mp4", ".mkv", ".webm", ".avi"]:
                if os.path.exists(base + ext):
                    filepath = base + ext
                    break

        if not filepath or not os.path.exists(filepath):
            bot.edit_message_text("❌ لم يتم العثور على الملف", message.chat.id, status.message_id)
            return

        size_mb = os.path.getsize(filepath) / 1024 / 1024
        if size_mb > 50:
            bot.edit_message_text(
                f"⚠️ الفيديو كبير جداً ({size_mb:.1f}MB)\nالحد الأقصى: 50MB",
                message.chat.id, status.message_id
            )
            return

        bot.edit_message_text("📤 جاري الإرسال...", message.chat.id, status.message_id)
        with open(filepath, "rb") as f:
            bot.send_video(message.chat.id, f, caption="✅ تم التنزيل! 🎬",
                          supports_streaming=True, timeout=120)
        bot.delete_message(message.chat.id, status.message_id)

    except Exception as e:
        err = str(e).lower()
        msg = ("🔒 الفيديو خاص" if "private" in err
               else "⛔ الفيديو غير متاح" if "unavailable" in err
               else "❌ فشل التنزيل! تأكد أن الرابط صحيح والفيديو عام")
        try:
            bot.edit_message_text(msg, message.chat.id, status.message_id)
        except Exception:
            bot.reply_to(message, msg)
        logger.error(e)
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN غير موجود!")

    # Web server لـ Render
    threading.Thread(
        target=lambda: HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever(),
        daemon=True
    ).start()
    logger.info(f"Web server on port {PORT}")
    logger.info("البوت يعمل...")

    bot.infinity_polling(timeout=60, long_polling_timeout=30)


if __name__ == "__main__":
    main()
