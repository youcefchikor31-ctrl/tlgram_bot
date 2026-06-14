# 🤖 بوت تلغرام لتنزيل الفيديوهات

بوت مجاني ودائم لتنزيل الفيديوهات من أكثر من 1000 موقع

---

## 🚀 خطوات النشر المجاني على Render

### الخطوة 1: إنشاء بوت تلغرام
1. افتح تلغرام وابحث عن `@BotFather`
2. أرسل الأمر `/newbot`
3. أدخل اسماً للبوت (مثلاً: `My Video Bot`)
4. أدخل username ينتهي بـ `bot` (مثلاً: `myvideodownloader_bot`)
5. **احتفظ بالتوكن** الذي سيعطيك إياه BotFather

### الخطوة 2: رفع الكود على GitHub
1. افتح [github.com](https://github.com) وأنشئ حساباً مجانياً
2. اضغط **New Repository**
3. اسم المستودع: `telegram-video-bot`
4. اختر **Public** ثم اضغط **Create repository**
5. ارفع ملفات المشروع الثلاثة:
   - `bot.py`
   - `requirements.txt`
   - `render.yaml`

### الخطوة 3: النشر على Render
1. افتح [render.com](https://render.com) وأنشئ حساباً مجانياً
2. اضغط **New +** ثم اختر **Blueprint**
3. اربط حساب GitHub واختر مستودعك
4. Render سيكتشف `render.yaml` تلقائياً
5. في قسم **Environment Variables** أضف:
   - Key: `BOT_TOKEN`
   - Value: التوكن الذي أخذته من BotFather
6. اضغط **Apply** وانتظر 2-3 دقائق

### ✅ البوت جاهز!
ابحث عن بوتك في تلغرام وأرسل `/start`

---

## 📱 كيفية الاستخدام
1. افتح البوت في تلغرام
2. أرسل أي رابط فيديو
3. انتظر قليلاً وسيصلك الفيديو!

## 🌐 المواقع المدعومة
- YouTube, Instagram, TikTok
- Twitter/X, Facebook, Reddit
- Vimeo, Dailymotion
- وأكثر من 1000 موقع آخر!

## ⚠️ ملاحظات
- الحد الأقصى للفيديو: **50MB** (قيد تلغرام للبوتات المجانية)
- الخطة المجانية على Render: الخدمة تعمل باستمرار
