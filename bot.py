import os
import asyncio
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

# --- إعداد السجل ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- التوكن من متغير البيئة ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DOWNLOAD_DIR = "/tmp/videos"
MAX_FILE_SIZE_MB = 50  # حد تلغرام للبوتات المجانية

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def is_valid_url(text: str) -> bool:
    pattern = re.compile(
        r"^(https?://)"
        r"([\w.-]+)"
        r"(/[\w./?=%&_#-]*)?"
        r"$",
        re.IGNORECASE,
    )
    return bool(pattern.match(text.strip()))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome = (
        f"👋 أهلاً {user.first_name}!\n\n"
        "🎬 *بوت تنزيل الفيديو*\n\n"
        "فقط أرسل لي رابط أي فيديو وسأقوم بتنزيله لك!\n\n"
        "✅ *المواقع المدعومة:*\n"
        "• YouTube\n"
        "• Instagram\n"
        "• TikTok\n"
        "• Twitter / X\n"
        "• Facebook\n"
        "• وأكثر من 1000 موقع آخر!\n\n"
        "📌 *كيف تستخدمني:*\n"
        "فقط أرسل الرابط مباشرة في المحادثة\n\n"
        "⚠️ الحد الأقصى لحجم الفيديو: 50MB"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📖 *تعليمات الاستخدام:*\n\n"
        "1️⃣ انسخ رابط الفيديو من أي موقع\n"
        "2️⃣ أرسله هنا مباشرة\n"
        "3️⃣ انتظر قليلاً وسيصلك الفيديو 🎉\n\n"
        "🔧 *الأوامر المتاحة:*\n"
        "/start - بدء البوت\n"
        "/help - عرض المساعدة\n"
        "/ping - التحقق من أن البوت يعمل"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🟢 البوت يعمل بشكل مثالي!")


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()

    if not is_valid_url(url):
        await update.message.reply_text(
            "❌ الرابط غير صحيح!\n\nتأكد من إرسال رابط كامل يبدأ بـ http:// أو https://"
        )
        return

    status_msg = await update.message.reply_text(
        "⏳ جاري تحليل الرابط...\nانتظر قليلاً"
    )

    output_path = os.path.join(DOWNLOAD_DIR, "%(title).50s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestvideo[ext=mp4][filesize<45M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<45M]/best[filesize<45M]/best",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "socket_timeout": 30,
        "retries": 3,
    }

    downloaded_file = None

    try:
        await status_msg.edit_text("⬇️ جاري التنزيل... 0%")

        loop = asyncio.get_event_loop()

        def do_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        downloaded_file = await loop.run_in_executor(None, do_download)

        # أحياناً الامتداد يتغير بعد المعالجة
        if not os.path.exists(downloaded_file):
            base = os.path.splitext(downloaded_file)[0]
            for ext in [".mp4", ".mkv", ".webm", ".avi", ".mov"]:
                if os.path.exists(base + ext):
                    downloaded_file = base + ext
                    break

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise FileNotFoundError("لم يتم العثور على الملف المنزّل")

        file_size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)

        if file_size_mb > MAX_FILE_SIZE_MB:
            await status_msg.edit_text(
                f"⚠️ حجم الفيديو كبير جداً ({file_size_mb:.1f}MB)\n"
                f"الحد المسموح هو {MAX_FILE_SIZE_MB}MB\n\n"
                "💡 حاول مع فيديو أقصر أو بجودة أقل"
            )
            return

        await status_msg.edit_text("📤 جاري الإرسال إليك...")

        with open(downloaded_file, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                supports_streaming=True,
                caption="✅ تم التنزيل بنجاح! 🎬",
                read_timeout=120,
                write_timeout=120,
                connect_timeout=30,
            )

        await status_msg.delete()

    except yt_dlp.utils.DownloadError as e:
        error_str = str(e).lower()
        if "private" in error_str:
            msg = "🔒 هذا الفيديو خاص ولا يمكن تنزيله"
        elif "unavailable" in error_str or "not available" in error_str:
            msg = "⛔ هذا الفيديو غير متاح أو محذوف"
        elif "geo" in error_str or "country" in error_str:
            msg = "🌍 هذا الفيديو غير متاح في منطقتك"
        elif "copyright" in error_str:
            msg = "©️ هذا الفيديو محمي بحقوق النشر"
        else:
            msg = f"❌ فشل التنزيل!\n\nتأكد أن الرابط صحيح وأن الفيديو متاح للعموم"
        await status_msg.edit_text(msg)
        logger.error(f"Download error: {e}")

    except Exception as e:
        await status_msg.edit_text(
            "❌ حدث خطأ غير متوقع!\n\nحاول مرة أخرى أو جرب رابطاً مختلفاً"
        )
        logger.error(f"Unexpected error: {e}", exc_info=True)

    finally:
        # حذف الملف المؤقت لتوفير المساحة
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN غير موجود! أضفه في متغيرات البيئة")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    logger.info("🤖 البوت يعمل الآن...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
