from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from database import db
from middlewares.auth_check import IsAdmin

router = Router()


@router.message(Command("users"), IsAdmin())
async def list_users(message: Message):
    """
    /users — عرض جميع المستخدمين مع حالاتهم (للأدمنز فقط)
    """
    users = await db.get_all_users()

    if not users:
        await message.answer("لا يوجد مستخدمون مسجلون بعد.")
        return

    status_emoji = {"approved": "✅", "pending": "⏳", "blocked": "🚫"}
    lines = ["👥 *قائمة المستخدمين:*\n"]

    for user in users:
        emoji = status_emoji.get(user["status"], "❓")
        lines.append(
            f"{emoji} {user['full_name']}\n"
            f"    🆔 `{user['telegram_id']}`\n"
        )

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("pending"), IsAdmin())
async def pending_users(message: Message):
    """
    /pending — عرض الطلبات المعلقة مع أزرار موافقة/رفض
    """
    users = await db.get_pending_users()

    if not users:
        await message.answer("✅ لا توجد طلبات معلقة حالياً.")
        return

    for user in users:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ موافقة",
                callback_data=f"approve_{user['telegram_id']}"
            ),
            InlineKeyboardButton(
                text="❌ رفض",
                callback_data=f"block_{user['telegram_id']}"
            )
        ]])
        await message.answer(
            f"⏳ *طلب معلق*\n\n"
            f"👤 {user['full_name']}\n"
            f"🆔 `{user['telegram_id']}`",
            parse_mode="Markdown",
            reply_markup=keyboard
        )


@router.message(Command("addadmin"), IsAdmin())
async def add_admin(message: Message):
    """
    /addadmin telegram_id — إضافة أدمن جديد
    مثال: /addadmin 123456789
    """
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "❗ استخدام: /addadmin telegram_id\n"
            "للحصول على ID: اطلب من الشخص إرسال /start ثم أخبرك بـ ID."
        )
        return

    try:
        new_admin_id = int(parts[1].strip())
    except ValueError:
        await message.answer("❗ الـ ID يجب أن يكون رقماً صحيحاً.")
        return

    await db.add_admin(new_admin_id)

    # إشعار الأدمن الجديد إذا أمكن
    try:
        await message.bot.send_message(
            new_admin_id,
            "🎖️ تمت ترقيتك إلى أدمن في البوت."
        )
    except Exception:
        pass

    await message.answer(f"✅ تمت إضافة `{new_admin_id}` كأدمن.", parse_mode="Markdown")


@router.message(Command("removeadmin"), IsAdmin())
async def remove_admin(message: Message):
    """
    /removeadmin telegram_id — إزالة أدمن
    """
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer("❗ استخدام: /removeadmin telegram_id")
        return

    try:
        admin_id = int(parts[1].strip())
    except ValueError:
        await message.answer("❗ الـ ID يجب أن يكون رقماً.")
        return

    await db.remove_admin(admin_id)
    await message.answer(f"✅ تمت إزالة `{admin_id}` من الأدمنز.", parse_mode="Markdown")


@router.message(Command("stats"), IsAdmin())
async def stats(message: Message):
    """
    /stats — إحصائيات سريعة عن البوت
    """
    users = await db.get_all_users()
    files = await db.list_files()
    admins = await db.get_admins()

    approved = sum(1 for u in users if u["status"] == "approved")
    pending = sum(1 for u in users if u["status"] == "pending")
    blocked = sum(1 for u in users if u["status"] == "blocked")

    await message.answer(
        "📊 *إحصائيات البوت*\n\n"
        f"👥 إجمالي المستخدمين: {len(users)}\n"
        f"  ✅ معتمدون: {approved}\n"
        f"  ⏳ قيد الانتظار: {pending}\n"
        f"  🚫 محظورون: {blocked}\n\n"
        f"📁 إجمالي الملفات: {len(files)}\n"
        f"🎖️ الأدمنز: {len(admins)}",
        parse_mode="Markdown"
    )
