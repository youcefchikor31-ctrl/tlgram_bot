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


def get_direct_url(url):
    """احصل على رابط التنزيل المباشر بدون تنزيل"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best[ext=mp4]/best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get("title", "الفيديو")
        duration = info.get("duration", 0)
        filesize = info.get("filesize") or info.get("filesize_approx") or 0
        direct_url = info.get("url", "")
        # للفيديوهات التي فيها formats متعددة
        if not direct_url and info.get("formats"):
            formats = info["formats"]
            # اختر أفضل mp4
            mp4 = [f for f in formats if f.get("ext") == "mp4" and f.get("url")]
            if mp4:
                direct_url = mp4[-1]["url"]
            else:
                direct_url = formats[-1].get("url", "")
        return title, duration, filesize, direct_url


@bot.message_handler(commands=["start", "help"])
def start(message):
    bot.reply_to(message,
        f"👋 أهلاً {message.from_user.first_name}!\n\n"
        "🎬 أرسل رابط أي فيديو وسأنزله لك!\n\n"
        "✅ YouTube • TikTok • Instagram • Twitter • Facebook\n\n"
        "📦 إذا كان الفيديو أقل من 50MB سيصلك مباشرة\n"
        "🔗 إذا كان أكبر ستحصل على رابط تنزيل مباشر"
    )


@bot.message_handler(commands=["ping"])
def ping(message):
    bot.reply_to(message, "🟢 البوت يعمل!")


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_url(message):
    url = message.text.strip()

    if not is_valid_url(url):
        bot.reply_to(message, "❌ أرسل رابطاً يبدأ بـ http://")
        return

    status = bot.reply_to(message, "⏳ جاري تحليل الرابط...")

    try:
        # أولاً: احصل على معلومات الفيديو
        bot.edit_message_text("🔍 جاري فحص حجم الفيديو...", message.chat.id, status.message_id)
        title, duration, filesize, direct_url = get_direct_url(url)

        filesize_mb = filesize / 1024 / 1024 if filesize else 0
        mins = int(duration // 60) if duration else 0
        secs = int(duration % 60) if duration else 0

        # إذا الحجم معروف وأكبر من 45MB — أرسل رابط مباشرة بدون تنزيل
        if filesize_mb > 45:
            bot.edit_message_text(
                f"📁 *{title}*\n"
                f"⏱ المدة: {mins}:{secs:02d}\n"
                f"📦 الحجم: {filesize_mb:.1f}MB\n\n"
                f"⚠️ الفيديو كبير، إليك رابط التنزيل المباشر:\n\n"
                f"🔗 [اضغط هنا للتنزيل]({direct_url})\n\n"
                f"_الرابط صالح لفترة محدودة_",
                message.chat.id, status.message_id,
                parse_mode="Markdown"
            )
            return

        # إذا الحجم صغير أو مجهول — حاول التنزيل
        bot.edit_message_text("⬇️ جاري التنزيل...", message.chat.id, status.message_id)

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
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

        if not os.path.exists(filepath):
            base = os.path.splitext(filepath)[0]
            for ext in [".mp4", ".mkv", ".webm", ".avi"]:
                if os.path.exists(base + ext):
                    filepath = base + ext
                    break

        if not filepath or not os.path.exists(filepath):
            raise FileNotFoundError("الملف لم يوجد")

        actual_size_mb = os.path.getsize(filepath) / 1024 / 1024

        # إذا بعد التنزيل اتضح أنه كبير — أرسل الرابط
        if actual_size_mb > 50:
            os.remove(filepath)
            bot.edit_message_text(
                f"📁 *{title}*\n"
                f"📦 الحجم: {actual_size_mb:.1f}MB\n\n"
                f"⚠️ الفيديو كبير جداً للإرسال المباشر\n"
                f"🔗 [اضغط هنا للتنزيل]({direct_url})\n\n"
                f"_الرابط صالح لفترة محدودة_",
                message.chat.id, status.message_id,
                parse_mode="Markdown"
            )
            return

        # إرسال الفيديو مباشرة
        bot.edit_message_text("📤 جاري الإرسال...", message.chat.id, status.message_id)
        with open(filepath, "rb") as f:
            bot.send_video(
                message.chat.id, f,
                caption=f"✅ *{title}*",
                supports_streaming=True,
                timeout=120,
                parse_mode="Markdown"
            )
        bot.delete_message(message.chat.id, status.message_id)

    except Exception as e:
        err = str(e).lower()
        msg = ("🔒 الفيديو خاص" if "private" in err
               else "⛔ الفيديو غير متاح" if "unavailable" in err
               else f"❌ فشل التنزيل!\nتأكد أن الرابط صحيح والفيديو عام")
        try:
            bot.edit_message_text(msg, message.chat.id, status.message_id)
        except Exception:
            bot.reply_to(message, msg)
        logger.error(e)
    finally:
        if 'filepath' in dir() and filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN غير موجود!")

    threading.Thread(
        target=lambda: HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever(),
        daemon=True
    ).start()
    logger.info(f"Web server on port {PORT}")
    logger.info("البوت يعمل...")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)


if __name__ == "__main__":
    main()
