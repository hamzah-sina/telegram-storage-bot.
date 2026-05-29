import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import auth, files, admin
from rate_limit import RateLimitMiddleware
from middlewares.auth_check import

# ─── إعداد اللوجز ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ─── دالة التهيئة الأولى ────────────────────────────────────────────────────

async def setup_owner():
    """
    عند أول تشغيل، نضيف OWNER_ID تلقائياً كأدمن
    حتى لا تحتاج لإدخاله يدوياً في قاعدة البيانات.
    """
    if OWNER_ID:
        admins = await db.get_admins()
        if OWNER_ID not in admins:
            await db.add_admin(OWNER_ID)
            logger.info(f"✅ تمت إضافة المالك {OWNER_ID} كأدمن.")


# ─── الدالة الرئيسية ────────────────────────────────────────────────────────

async def main():
    # إنشاء Bot و Dispatcher
    # MemoryStorage: يحفظ حالات FSM في الذاكرة (كافي للبوتات الصغيرة)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # تهيئة المالك
    await setup_owner()

    # ─── تسجيل الـ Middlewares ───────────────────────────────────────────
    # ترتيب الـ Middlewares مهم: يُنفَّذ من الأول للأخير
    # 1. RateLimit: يوقف الطلبات الكثيرة قبل أي معالجة
    # 2. AuthCheck: يتحقق من هوية المستخدم
    dp.message.middleware(RateLimitMiddleware(rate_limit=10, period=60))
    dp.message.middleware(AuthCheckMiddleware())

    # ─── تسجيل الـ Routers ───────────────────────────────────────────────
    # الترتيب مهم أيضاً: auth أولاً لأنه يتعامل مع /start
    dp.include_router(auth.router)
    dp.include_router(files.router)
    dp.include_router(admin.router)

    # ─── تشغيل البوت ────────────────────────────────────────────────────
    logger.info("🤖 البوت يعمل...")
    try:
        await dp.start_polling(
            bot,
            # نحدد نوع الأحداث التي نتعامل معها لتقليل الضغط على تيليجرام
            allowed_updates=dp.resolve_used_update_types()
        )
    finally:
        await bot.session.close()
        logger.info("🔴 البوت توقف.")


if __name__ == "__main__":
    asyncio.run(main())
