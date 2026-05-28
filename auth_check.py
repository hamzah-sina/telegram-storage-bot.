from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.filters import Filter
from typing import Callable, Dict, Any, Awaitable
from database import db


class AuthCheckMiddleware(BaseMiddleware):
    """
    فلتر المصادقة: يتحقق من كل رسالة واردة قبل أن تصل للـ handler.

    المنطق:
    - /start مسموح لأي أحد (لأنه بداية التسجيل)
    - باقي الأوامر تتطلب مستخدماً معتمداً
    """

    EXEMPT_COMMANDS = ["/start"]

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # السماح بأوامر التسجيل بدون فحص
        if event.text and any(event.text.startswith(cmd) for cmd in self.EXEMPT_COMMANDS):
            return await handler(event, data)

        user = await db.get_user(event.from_user.id)

        if not user:
            await event.answer("❗ أنت غير مسجل. اكتب /start للبدء.")
            return

        if user["status"] == "pending":
            await event.answer("⏳ طلبك قيد المراجعة. سيتم إشعارك عند الموافقة.")
            return

        if user["status"] == "blocked":
            await event.answer("🚫 تم حظرك من استخدام هذا البوت.")
            return

        # إضافة بيانات المستخدم إلى الـ context ليستخدمها الـ handler
        data["user"] = user
        return await handler(event, data)


class IsAdmin(Filter):
    """
    فلتر مخصص للأوامر الإدارية.
    يُستخدم كـ decorator: @router.message(Command("users"), IsAdmin())
    """

    async def __call__(self, message: Message) -> bool:
        admins = await db.get_admins()
        return message.from_user.id in admins
