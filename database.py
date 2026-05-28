from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from typing import Optional

# إنشاء اتصال واحد مشترك مع Supabase (Singleton pattern)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class Database:
    """
    كل العمليات مع قاعدة البيانات مجمّعة هنا.
    يسهّل هذا الأسلوب تغيير قاعدة البيانات مستقبلاً دون تعديل باقي الكود.
    """

    # ─── إدارة المستخدمين ───────────────────────────────────────────

    async def get_user(self, telegram_id: int) -> Optional[dict]:
        """جلب مستخدم عن طريق Telegram ID"""
        result = supabase.table("users") \
            .select("*") \
            .eq("telegram_id", telegram_id) \
            .execute()
        return result.data[0] if result.data else None

    async def get_user_by_name(self, full_name: str) -> Optional[dict]:
        """التحقق إذا كان الاسم مسجلاً مسبقاً (حساسية حروف إيقاف)"""
        result = supabase.table("users") \
            .select("*") \
            .ilike("full_name", full_name) \
            .execute()
        return result.data[0] if result.data else None

    async def add_user(self, telegram_id: int, full_name: str, username: str = None):
        """إضافة مستخدم جديد بحالة 'pending' (قيد المراجعة)"""
        supabase.table("users").insert({
            "telegram_id": telegram_id,
            "full_name": full_name,
            "username": username,
            "status": "pending"
        }).execute()

    async def approve_user(self, telegram_id: int):
        """الموافقة على مستخدم"""
        supabase.table("users") \
            .update({"status": "approved"}) \
            .eq("telegram_id", telegram_id) \
            .execute()

    async def block_user(self, telegram_id: int):
        """حظر مستخدم"""
        supabase.table("users") \
            .update({"status": "blocked"}) \
            .eq("telegram_id", telegram_id) \
            .execute()

    async def get_all_users(self) -> list:
        result = supabase.table("users").select("*").execute()
        return result.data

    async def get_pending_users(self) -> list:
        result = supabase.table("users") \
            .select("*") \
            .eq("status", "pending") \
            .execute()
        return result.data

    # ─── إدارة الملفات ──────────────────────────────────────────────

    async def save_file(self, code: str, file_id: str, file_type: str,
                        file_name: str, uploaded_by: int):
        """حفظ الكود المرتبط بـ file_id في تيليجرام"""
        supabase.table("files").insert({
            "code": code.lower().strip(),
            "file_id": file_id,
            "file_type": file_type,
            "file_name": file_name,
            "uploaded_by": uploaded_by
        }).execute()

    async def get_file(self, code: str) -> Optional[dict]:
        result = supabase.table("files") \
            .select("*") \
            .eq("code", code.lower().strip()) \
            .execute()
        return result.data[0] if result.data else None

    async def delete_file(self, code: str):
        supabase.table("files") \
            .delete() \
            .eq("code", code.lower().strip()) \
            .execute()

    async def list_files(self) -> list:
        result = supabase.table("files") \
            .select("*") \
            .order("created_at", desc=True) \
            .execute()
        return result.data

    # ─── إدارة الأدمنز ──────────────────────────────────────────────

    async def get_admins(self) -> list[int]:
        result = supabase.table("admins").select("telegram_id").execute()
        return [r["telegram_id"] for r in result.data]

    async def add_admin(self, telegram_id: int):
        supabase.table("admins") \
            .upsert({"telegram_id": telegram_id}) \
            .execute()

    async def remove_admin(self, telegram_id: int):
        supabase.table("admins") \
            .delete() \
            .eq("telegram_id", telegram_id) \
            .execute()


# نسخة واحدة مشتركة عبر كل الملفات
db = Database()
