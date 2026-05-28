from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from collections import defaultdict
import time


class RateLimitMiddleware(BaseMiddleware):
    """
    حماية ضد الإغراق (Flood Protection).

    كيف يعمل: لكل مستخدم نحفظ قائمة بأوقات طلباته الأخيرة.
    إذا تجاوز العدد المسموح به خلال الفترة المحددة → نوقف الطلب.

    rate_limit: أقصى عدد رسائل مسموح بها
    period: خلال كم ثانية (افتراضياً 60 ثانية)
    """

    def __init__(self, rate_limit: int = 10, period: int = 60):
        self.rate_limit = rate_limit
        self.period = period
        # defaultdict يوفر قائمة فارغة تلقائياً لكل مستخدم جديد
        self.user_requests: Dict[int, list] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        now = time.time()

        # حذف الطلبات القديمة التي خرجت من النافذة الزمنية
        self.user_requests[user_id] = [
            t for t in self.user_requests[user_id]
            if now - t < self.period
        ]

        # فحص التجاوز
        if len(self.user_requests[user_id]) >= self.rate_limit:
            await event.answer("⚠️ أرسلت طلبات كثيرة جداً. انتظر دقيقة ثم حاول مجدداً.")
            return  # لا نكمل تنفيذ الأمر

        # تسجيل الطلب الحالي
        self.user_requests[user_id].append(now)

        # تمرير الطلب للـ handler التالي
        return await handler(event, data)
