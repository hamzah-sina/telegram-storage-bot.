from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db

router = Router()

# ─── States ────────────────────────────────────────────────────────────────

class UploadStates(StatesGroup):
    """
    حالة انتظار الكود بعد إرسال الملف.
    المستخدم يُرسل الملف → ينتقل إلى هذه الحالة → يكتب الكود → يُحفظ.
    """
    waiting_for_code = State()


# تخزين مؤقت في الذاكرة: user_id → بيانات الملف
# هذا يسمح لنا بربط الملف بالكود في رسالتين منفصلتين
pending_uploads: dict = {}


# ─── استقبال الملفات ────────────────────────────────────────────────────────

@router.message(F.photo | F.video | F.document | F.audio | F.voice | F.video_note)
async def receive_file(message: Message, state: FSMContext):
    """
    يُفعَّل عند إرسال أي نوع من الملفات.
    نستخرج الـ file_id من تيليجرام ونخزنه مؤقتاً بانتظار الكود.
    """

    # استخراج نوع الملف ومعرفه
    if message.photo:
        # تيليجرام يرسل الصور بأحجام متعددة → نأخذ الأعلى جودة [-1]
        file_id = message.photo[-1].file_id
        file_type, file_name = "photo", "صورة"

    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = message.video.file_name or "فيديو"

    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name or "ملف"

    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
        file_name = message.audio.file_name or "ملف صوتي"

    elif message.voice:
        file_id = message.voice.file_id
        file_type, file_name = "voice", "رسالة صوتية"

    elif message.video_note:
        file_id = message.video_note.file_id
        file_type, file_name = "video_note", "رسالة مرئية"

    # حفظ مؤقت في الذاكرة مرتبط بـ user_id
    pending_uploads[message.from_user.id] = {
        "file_id": file_id,
        "file_type": file_type,
        "file_name": file_name
    }

    await message.answer(
        f"📎 استلمت: *{file_name}*\n\n"
        f"الآن اكتب الكود الذي تريد ربطه بهذا الملف:\n"
        f"_(مثال: myphoto أو doc2024 أو 1234)_",
        parse_mode="Markdown"
    )
    await state.set_state(UploadStates.waiting_for_code)


# ─── استقبال الكود وحفظ الملف ──────────────────────────────────────────────

@router.message(UploadStates.waiting_for_code)
async def assign_code(message: Message, state: FSMContext):
    """
    يُفعَّل فقط عندما يكون المستخدم في حالة انتظار الكود.
    نتحقق من الكود ونحفظ الملف في قاعدة البيانات.
    """
    if not message.text:
        await message.answer("❗ الرجاء إرسال كود نصي:")
        return

    # تنظيف الكود: حروف صغيرة، لا مسافات
    code = message.text.strip().lower().replace(" ", "_")

    # التحقق من الطول
    if len(code) < 2:
        await message.answer("❗ الكود قصير جداً. اكتب على الأقل حرفين:")
        return

    if len(code) > 50:
        await message.answer("❗ الكود طويل جداً. 50 حرفاً كحد أقصى:")
        return

    # التحقق إذا كان الكود مستخدماً مسبقاً
    existing = await db.get_file(code)
    if existing:
        await message.answer(
            f"❗ الكود `{code}` مستخدم مسبقاً.\n"
            f"اختر كوداً مختلفاً:",
            parse_mode="Markdown"
        )
        return

    # استرجاع الملف المؤقت
    file_data = pending_uploads.get(message.from_user.id)
    if not file_data:
        await message.answer("❗ انتهت صلاحية الملف. أرسله مرة أخرى.")
        await state.clear()
        return

    # حفظ في قاعدة البيانات
    await db.save_file(
        code=code,
        file_id=file_data["file_id"],
        file_type=file_data["file_type"],
        file_name=file_data["file_name"],
        uploaded_by=message.from_user.id
    )

    # حذف من الذاكرة المؤقتة
    del pending_uploads[message.from_user.id]
    await state.clear()

    await message.answer(
        f"✅ *تم الحفظ بنجاح!*\n\n"
        f"🔑 الكود: `{code}`\n"
        f"📎 النوع: {file_data['file_name']}\n\n"
        f"لاسترجاعه في أي وقت: /get {code}",
        parse_mode="Markdown"
    )


# ─── استرجاع ملف ──────────────────────────────────────────────────────────

@router.message(Command("get"))
async def get_file(message: Message):
    """
    /get كود
    البوت يبحث عن الكود ويُرسل الملف المرتبط به مباشرة.
    """
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("❗ استخدام: /get كود\nمثال: /get myphoto")
        return

    code = parts[1].strip().lower()
    file_data = await db.get_file(code)

    if not file_data:
        await message.answer(
            f"❌ لم أجد ملفاً بالكود: `{code}`",
            parse_mode="Markdown"
        )
        return

    # إرسال الملف حسب نوعه
    try:
        caption = f"🔑 `{code}` — {file_data['file_name']}"

        if file_data["file_type"] == "photo":
            await message.answer_photo(file_data["file_id"], caption=caption, parse_mode="Markdown")
        elif file_data["file_type"] == "video":
            await message.answer_video(file_data["file_id"], caption=caption, parse_mode="Markdown")
        elif file_data["file_type"] == "document":
            await message.answer_document(file_data["file_id"], caption=caption, parse_mode="Markdown")
        elif file_data["file_type"] == "audio":
            await message.answer_audio(file_data["file_id"], caption=caption, parse_mode="Markdown")
        elif file_data["file_type"] == "voice":
            await message.answer_voice(file_data["file_id"])
        elif file_data["file_type"] == "video_note":
            await message.answer_video_note(file_data["file_id"])

    except Exception as e:
        # هذا يحدث نادراً إذا انتهت صلاحية الـ file_id في تيليجرام
        await message.answer(
            "❌ حدث خطأ عند إرسال الملف.\n"
            "ربما انتهت صلاحية الملف في تيليجرام. أعد رفعه."
        )


# ─── حذف ملف ──────────────────────────────────────────────────────────────

@router.message(Command("delete"))
async def delete_file(message: Message):
    """
    /delete كود
    يحذف الملف من قاعدة البيانات (الملف نفسه يبقى في سيرفرات تيليجرام).
    """
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("❗ استخدام: /delete كود\nمثال: /delete myphoto")
        return

    code = parts[1].strip().lower()
    file_data = await db.get_file(code)

    if not file_data:
        await message.answer(f"❌ لم أجد ملفاً بالكود: `{code}`", parse_mode="Markdown")
        return

    await db.delete_file(code)
    await message.answer(f"🗑️ تم حذف الملف بالكود: `{code}`", parse_mode="Markdown")


# ─── عرض جميع الملفات ──────────────────────────────────────────────────────

@router.message(Command("list"))
async def list_files(message: Message):
    """
    /list
    يعرض قائمة بجميع الملفات المحفوظة مع أكوادها.
    """
    files = await db.list_files()

    if not files:
        await message.answer("📭 لا توجد ملفات محفوظة حتى الآن.")
        return

    # نحدد رمزاً مناسباً لكل نوع ملف
    type_emojis = {
        "photo": "🖼️",
        "video": "🎬",
        "document": "📄",
        "audio": "🎵",
        "voice": "🎤",
        "video_note": "📹"
    }

    lines = ["📁 *الملفات المحفوظة:*\n"]
    for f in files:
        emoji = type_emojis.get(f["file_type"], "📎")
        lines.append(f"{emoji} `{f['code']}` — {f['file_name']}")

    # إذا كانت القائمة طويلة جداً نقسّمها لرسائل متعددة
    text = "\n".join(lines)
    if len(text) > 4000:
        chunks = [lines[i:i+50] for i in range(0, len(lines), 50)]
        for chunk in chunks:
            await message.answer("\n".join(chunk), parse_mode="Markdown")
    else:
        await message.answer(text, parse_mode="Markdown")
