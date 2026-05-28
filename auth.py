from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from database import db

router = Router()


# ─── States ────────────────────────────────────────────────────────────────
# FSM = Finite State Machine: نظام لتتبع في أي "خطوة" يقف المستخدم الآن.
# هنا المستخدم الجديد ينتقل إلى حالة "انتظار الاسم" بعد /start

class RegistrationStates(StatesGroup):
    waiting_for_name = State()


# ─── /start ────────────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    نقطة الدخول للبوت.
    إذا كان المستخدم موجوداً نعرض حالته، وإذا كان جديداً نطلب اسمه.
    """
    user = await db.get_user(message.from_user.id)

    if user:
        if user["status"] == "approved":
            await message.answer(
                "مرحباً من جديد! ✅\n\n"
                "📤 *رفع ملف:* أرسل الملف → اكتب الكود\n"
                "📥 *تنزيل ملف:* /get كود\n"
                "📋 *عرض الكل:* /list\n"
                "🗑️ *حذف ملف:* /delete كود",
                parse_mode="Markdown"
            )
        elif user["status"] == "pending":
            await message.answer("⏳ طلبك لا يزال قيد المراجعة. سيتم إشعارك فور الموافقة.")
        elif user["status"] == "blocked":
            await message.answer("🚫 عذراً، تم حظرك من استخدام هذا البوت.")
        return

    # مستخدم جديد → نبدأ عملية التسجيل
    await message.answer(
        "مرحباً! 👋\n\n"
        "هذا البوت خاص ويتطلب موافقة المالك.\n"
        "الرجاء إرسال *اسمك الثلاثي* للمتابعة:",
        parse_mode="Markdown"
    )
    await state.set_state(RegistrationStates.waiting_for_name)


# ─── استقبال الاسم ─────────────────────────────────────────────────────────

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """
    يُنفَّذ فقط عندما يكون المستخدم في حالة 'waiting_for_name'.
    نتحقق من صحة الاسم، نحفظه كـ pending، ونُرسل إشعاراً للأدمنز.
    """
    full_name = message.text.strip() if message.text else ""

    # التحقق: لازم يكون الاسم جزأين على الأقل
    if len(full_name.split()) < 2:
        await message.answer("❗ الرجاء إدخال اسم كامل (جزأين على الأقل):")
        return

    # التحقق: هل الاسم مسجل مسبقاً؟
    existing = await db.get_user_by_name(full_name)
    if existing:
        await message.answer(
            "❗ هذا الاسم موجود مسبقاً في النظام.\n"
            "إذا كنت أنت صاحبه، تواصل مع المالك لحل المشكلة."
        )
        await state.clear()
        return

    # حفظ المستخدم بحالة pending
    await db.add_user(
        telegram_id=message.from_user.id,
        full_name=full_name,
        username=message.from_user.username
    )

    # بناء أزرار الموافقة والرفض
    approve_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ موافقة",
            callback_data=f"approve_{message.from_user.id}"
        ),
        InlineKeyboardButton(
            text="❌ رفض",
            callback_data=f"block_{message.from_user.id}"
        )
    ]])

    # إرسال إشعار لجميع الأدمنز
    admins = await db.get_admins()
    notification_text = (
        f"🔔 *طلب دخول جديد*\n\n"
        f"👤 الاسم: {full_name}\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"📛 يوزرنيم: @{message.from_user.username or 'بدون username'}"
    )

    for admin_id in admins:
        try:
            await message.bot.send_message(
                admin_id,
                notification_text,
                parse_mode="Markdown",
                reply_markup=approve_keyboard
            )
        except Exception:
            # الأدمن ربما حذف محادثته مع البوت → نتجاوز الخطأ
            pass

    await message.answer(
        "✅ تم إرسال طلبك!\n"
        "سيتم إشعارك فور مراجعته من قِبَل المالك."
    )
    await state.clear()


# ─── أزرار الموافقة والرفض ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("approve_"))
async def approve_user(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await db.approve_user(user_id)

    # إشعار المستخدم بالقبول
    try:
        await callback.bot.send_message(
            user_id,
            "🎉 *تهانينا! تم قبولك في البوت.*\n\n"
            "📤 *رفع ملف:* أرسل الملف → اكتب الكود\n"
            "📥 *تنزيل ملف:* /get كود\n"
            "📋 *عرض الكل:* /list",
            parse_mode="Markdown"
        )
    except Exception:
        pass

    # تحديث رسالة الأدمن لإزالة الأزرار
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ *تمت الموافقة*",
        parse_mode="Markdown",
        reply_markup=None
    )
    await callback.answer("تمت الموافقة ✅")


@router.callback_query(F.data.startswith("block_"))
async def block_user(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await db.block_user(user_id)

    try:
        await callback.bot.send_message(user_id, "❌ عذراً، تم رفض طلبك.")
    except Exception:
        pass

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ *تم الرفض*",
        parse_mode="Markdown",
        reply_markup=None
    )
    await callback.answer("تم الرفض ❌")
