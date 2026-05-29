import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, OWNER_ID
from database import db
import auth, files, admin
from rate_limit import RateLimitMiddleware
from auth_check import AuthCheckMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


async def setup_owner():
    if OWNER_ID:
        admins = await db.get_admins()
        if OWNER_ID not in admins:
            await db.add_admin(OWNER_ID)
            logger.info(f"✅ تمت إضافة المالك {OWNER_ID} كأدمن.")


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    await setup_owner()

    dp.message.middleware(RateLimitMiddleware(rate_limit=10, period=60))
    dp.message.middleware(AuthCheckMiddleware())

    dp.include_router(auth.router)
    dp.include_router(files.router)
    dp.include_router(admin.router)

    logger.info("🤖 البوت يعمل...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    finally:
        await bot.session.close()
        logger.info("🔴 البوت توقف.")


if __name__ == "__main__":
    asyncio.run(main())