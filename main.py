import logging
import os
import json
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8743657755:AAFswnfX3pAirTo0MBLaUhn1G0MEI0NPLK4"
ADMIN_IDS = [6576334405]

FILES_DB = "files_db.json"
USERS_DB = "users_db.json"
PAYMENTS_DB = "payments_db.json"

REQUIRED_CHANNELS = [
    {"name": "📢 Zak Shtorm 1-fasl👍", "url": "https://t.me/zakshtorm2008", "chat_id": "@zakshtorm2008"},
    {"name": "💬 NUROTA Kompyuter xizmatlari 💻. POLIGRAFIYA🖨", "url": "https://t.me/kompyuter_xizmatlari_poligrafiya", "chat_id": "@kompyuter_xizmatlari_poligrafiya"},
]

CATEGORIES = {
    "📚 Ta'lim": "talim",
    "💼 Ish hujjatlari": "ish",
    "🎮 O'yinlar": "oyinlar",
    "📱 Ilovalar": "ilovalar",
    "🎵 Musiqa": "musiqa",
    "🎬 Video": "video",
    "🖼 Rasmlar": "rasmlar",
    "📦 Boshqa": "boshqa",
}

TIME_OPTIONS = {
    "⏱ 1 soat": 1,
    "🕒 3 soat": 3,
    "🕕 6 soat": 6,
    "🕛 12 soat": 12,
    "📅 24 soat": 24,
    "♾ Cheksiz": 0,
}

# ==================== DB ====================
def load_files():
    if os.path.exists(FILES_DB):
        with open(FILES_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"files": []}

def save_files(data):
    with open(FILES_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    if os.path.exists(USERS_DB):
        with open(USERS_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}

def save_users(data):
    with open(USERS_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_payments():
    if os.path.exists(PAYMENTS_DB):
        with open(PAYMENTS_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"payments": []}

def save_payments(data):
    with open(PAYMENTS_DB, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def register_user(user):
    db = load_users()
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": user.id,
            "first_name": user.first_name,
            "username": user.username or "",
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "downloads": 0,
        }
    else:
        db["users"][uid]["first_name"] = user.first_name
        db["users"][uid]["username"] = user.username or ""
    save_users(db)

def increment_download(user_id):
    db = load_users()
    uid = str(user_id)
    if uid in db["users"]:
        db["users"][uid]["downloads"] = db["users"][uid].get("downloads", 0) + 1
        save_users(db)

def add_file(file_id, file_name, file_type, category, description, uploader_id,
             is_paid=False, price=0, expires_hours=0):
    db = load_files()
    expires_at = None
    if expires_hours > 0:
        expires_at = (datetime.now() + timedelta(hours=expires_hours)).strftime("%Y-%m-%d %H:%M:%S")
    db["files"].append({
        "id": len(db["files"]) + 1,
        "file_id": file_id,
        "file_name": file_name,
        "file_type": file_type,
        "category": category,
        "description": description,
        "uploader_id": uploader_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "downloads": 0,
        "is_paid": is_paid,
        "price": price,
        "expires_hours": expires_hours,
        "expires_at": expires_at,
    })
    save_files(db)

def is_file_expired(file_obj):
    if not file_obj.get("expires_at"):
        return False
    expires = datetime.strptime(file_obj["expires_at"], "%Y-%m-%d %H:%M:%S")
    return datetime.now() > expires

def has_user_paid(user_id, file_id):
    db = load_payments()
    for p in db["payments"]:
        if str(p["user_id"]) == str(user_id) and p["file_id"] == file_id and p["status"] == "approved":
            return True
    return False

def add_payment_request(user_id, file_id, file_name, price):
    db = load_payments()
    db["payments"].append({
        "id": len(db["payments"]) + 1,
        "user_id": user_id,
        "file_id": file_id,
        "file_name": file_name,
        "price": price,
        "status": "pending",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save_payments(db)
    return len(db["payments"])

def approve_payment(payment_id):
    db = load_payments()
    for p in db["payments"]:
        if p["id"] == payment_id:
            p["status"] = "approved"
            save_payments(db)
            return p
    return None

def reject_payment(payment_id):
    db = load_payments()
    for p in db["payments"]:
        if p["id"] == payment_id:
            p["status"] = "rejected"
            save_payments(db)
            return p
    return None

def get_files_by_category(category):
    db = load_files()
    return [f for f in db["files"] if f["category"] == category]

def get_all_files():
    db = load_files()
    return db["files"]

def delete_file(file_id_num):
    db = load_files()
    db["files"] = [f for f in db["files"] if f["id"] != file_id_num]
    save_files(db)

def delete_expired_files():
    db = load_files()
    before = len(db["files"])
    db["files"] = [f for f in db["files"] if not is_file_expired(f)]
    after = len(db["files"])
    if before != after:
        save_files(db)
    return before - after

def increment_file_download(file_id_num):
    db = load_files()
    for f in db["files"]:
        if f["id"] == file_id_num:
            f["downloads"] = f.get("downloads", 0) + 1
            break
    save_files(db)

def search_files(query):
    db = load_files()
    q = query.lower()
    return [f for f in db["files"] if q in f["file_name"].lower() or q in f.get("description", "").lower()]

# ==================== HOLAT ====================
user_states = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== YORDAMCHI ====================
def is_admin(user_id):
    return user_id in ADMIN_IDS

async def check_subscription(bot, user_id):
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            if member.status in ["left", "kicked", "banned"]:
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined

def subscription_keyboard(not_joined):
    keyboard = []
    for ch in not_joined:
        keyboard.append([InlineKeyboardButton(ch["name"], url=ch["url"])])
    keyboard.append([InlineKeyboardButton("✅ A'zo bo'ldim, tekshir", callback_data="check_sub")])
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("📂 Kategoriyalar", callback_data="show_categories"),
         InlineKeyboardButton("🔍 Barcha fayllar", callback_data="all_files")],
        [InlineKeyboardButton("🔎 Qidirish", callback_data="search")],
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("🔧 Admin panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def admin_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Fayl yuklash", callback_data="upload_file"),
         InlineKeyboardButton("🗑 Fayl o'chirish", callback_data="delete_file")],
        [InlineKeyboardButton("📊 Statistika", callback_data="statistics"),
         InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_list")],
        [InlineKeyboardButton("📢 Hammaga xabar", callback_data="broadcast"),
         InlineKeyboardButton("💳 To'lovlar", callback_data="pending_payments")],
        [InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def categories_keyboard():
    keyboard = []
    row = []
    for i, (name, key) in enumerate(CATEGORIES.items()):
        row.append(InlineKeyboardButton(name, callback_data=f"cat_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)

def category_select_keyboard():
    keyboard = []
    row = []
    for i, (name, key) in enumerate(CATEGORIES.items()):
        row.append(InlineKeyboardButton(name, callback_data=f"select_cat_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_upload")])
    return InlineKeyboardMarkup(keyboard)

def time_select_keyboard():
    keyboard = []
    row = []
    for i, (label, hours) in enumerate(TIME_OPTIONS.items()):
        row.append(InlineKeyboardButton(label, callback_data=f"set_time_{hours}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_upload")])
    return InlineKeyboardMarkup(keyboard)

def file_label(f):
    labels = []
    if f.get("is_paid"):
        labels.append(f"💰{f['price']:,}")
    if f.get("expires_at"):
        expires = datetime.strptime(f["expires_at"], "%Y-%m-%d %H:%M:%S")
        remaining = expires - datetime.now()
        if remaining.total_seconds() > 0:
            mins = int(remaining.total_seconds() / 60)
            if mins >= 60:
                labels.append(f"⏳{mins//60}s")
            else:
                labels.append(f"⏳{mins}d")
    labels.append(f"{f.get('downloads', 0)}⬇")
    suffix = " | ".join(labels)
    return f"📄 {f['file_name']} | {suffix}"

# ==================== KOMANDALAR ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    # Eski reply keyboard ni o'chirish
    await update.message.reply_text(".", reply_markup=ReplyKeyboardRemove())

    not_joined = await check_subscription(context.bot, user.id)
    if not_joined:
        await update.message.reply_text(
            "⚠️ <b>Botdan foydalanish uchun quyidagi kanal/guruhlarga a'zo bo'ling:</b>",
            parse_mode="HTML",
            reply_markup=subscription_keyboard(not_joined)
        )
        return

    await update.message.reply_text(
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        "🗂 Kerakli bo'limni tanlang:",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user.id)
    )

# ==================== CALLBACK ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "check_sub":
        not_joined = await check_subscription(context.bot, user_id)
        if not_joined:
            await query.edit_message_text(
                "❌ Hali a'zo bo'lmagansiz:",
                reply_markup=subscription_keyboard(not_joined)
            )
        else:
            await query.edit_message_text(
                "✅ Rahmat! Botdan foydalanishingiz mumkin.",
                reply_markup=main_menu_keyboard(user_id)
            )
        return

    not_joined = await check_subscription(context.bot, user_id)
    if not_joined and not is_admin(user_id):
        await query.edit_message_text(
            "⚠️ Avval kanallarga a'zo bo'ling:",
            reply_markup=subscription_keyboard(not_joined)
        )
        return

    if data == "back_main":
        await query.edit_message_text(
            "🏠 <b>Asosiy menyu</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_id)
        )

    elif data == "show_categories":
        await query.edit_message_text(
            "📂 <b>Kategoriyalar</b>",
            parse_mode="HTML",
            reply_markup=categories_keyboard()
        )

    elif data.startswith("cat_"):
        cat_key = data[4:]
        cat_name = next((n for n, k in CATEGORIES.items() if k == cat_key), cat_key)
        files = get_files_by_category(cat_key)
        active = [f for f in files if not is_file_expired(f)]
        if not active:
            await query.edit_message_text(
                f"📂 <b>{cat_name}</b>\n\n❌ Bu kategoriyada fayl yo'q.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="show_categories")]])
            )
            return
        keyboard = [[InlineKeyboardButton(file_label(f), callback_data=f"getfile_{f['id']}")] for f in active]
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="show_categories")])
        await query.edit_message_text(
            f"📂 <b>{cat_name}</b> — {len(active)} ta fayl:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("getfile_"):
        file_num = int(data[8:])
        db = load_files()
        file_obj = next((f for f in db["files"] if f["id"] == file_num), None)
        if not file_obj:
            await query.answer("❌ Fayl topilmadi!", show_alert=True)
            return
        if is_file_expired(file_obj):
            await query.answer("⏰ Bu faylning muddati tugagan!", show_alert=True)
            return

        if file_obj.get("is_paid") and not is_admin(user_id):
            if not has_user_paid(user_id, file_num):
                cat_name = next((n for n, k in CATEGORIES.items() if k == file_obj["category"]), "")
                expires_text = ""
                if file_obj.get("expires_at"):
                    expires = datetime.strptime(file_obj["expires_at"], "%Y-%m-%d %H:%M:%S")
                    remaining = expires - datetime.now()
                    mins = int(remaining.total_seconds() / 60)
                    expires_text = f"\n⏳ Qolgan vaqt: {mins//60} soat {mins%60} daqiqa"
                await query.edit_message_text(
                    f"💰 <b>Bu fayl pullik!</b>\n\n"
                    f"📄 {file_obj['file_name']}\n"
                    f"📂 {cat_name}\n"
                    f"💵 Narxi: <b>{file_obj['price']:,} so'm</b>{expires_text}",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💳 To'lov so'rash", callback_data=f"request_pay_{file_num}")],
                        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
                    ])
                )
                return

        increment_file_download(file_num)
        increment_download(user_id)
        cat_name = next((n for n, k in CATEGORIES.items() if k == file_obj["category"]), "")
        caption = f"📄 <b>{file_obj['file_name']}</b>\n📂 {cat_name}\n"
        if file_obj.get("description"):
            caption += f"📝 {file_obj['description']}\n"
        if file_obj.get("expires_at"):
            expires = datetime.strptime(file_obj["expires_at"], "%Y-%m-%d %H:%M:%S")
            remaining = expires - datetime.now()
            mins = int(remaining.total_seconds() / 60)
            caption += f"⏳ {mins//60}s {mins%60}d ichida o'chadi!\n"
        try:
            if file_obj["file_type"] == "photo":
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=file_obj["file_id"], caption=caption, parse_mode="HTML")
            elif file_obj["file_type"] == "video":
                await context.bot.send_video(chat_id=query.message.chat_id, video=file_obj["file_id"], caption=caption, parse_mode="HTML")
            elif file_obj["file_type"] == "audio":
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=file_obj["file_id"], caption=caption, parse_mode="HTML")
            else:
                await context.bot.send_document(chat_id=query.message.chat_id, document=file_obj["file_id"], caption=caption, parse_mode="HTML")
        except Exception as e:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ Xatolik: {e}")

    elif data.startswith("request_pay_"):
        file_num = int(data[12:])
        db = load_files()
        file_obj = next((f for f in db["files"] if f["id"] == file_num), None)
        if not file_obj:
            return
        pay_id = add_payment_request(user_id, file_num, file_obj["file_name"], file_obj["price"])
        username = f"@{query.from_user.username}" if query.from_user.username else str(user_id)
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"💳 <b>To'lov so'rovi #{pay_id}</b>\n\n"
                         f"👤 {query.from_user.first_name} ({username})\n"
                         f"📄 {file_obj['file_name']}\n"
                         f"💵 {file_obj['price']:,} so'm",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approvepay_{pay_id}"),
                        InlineKeyboardButton("❌ Rad etish", callback_data=f"rejectpay_{pay_id}"),
                    ]])
                )
            except:
                pass
        await query.edit_message_text(
            "✅ To'lov so'rovingiz adminga yuborildi!\nTasdiqlangandan so'ng fayl yuboriladi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_main")]])
        )

    elif data.startswith("approvepay_"):
        if not is_admin(user_id):
            return
        pay_id = int(data[11:])
        payment = approve_payment(pay_id)
        if not payment:
            await query.answer("Topilmadi!", show_alert=True)
            return
        db = load_files()
        file_obj = next((f for f in db["files"] if f["id"] == payment["file_id"]), None)
        try:
            await context.bot.send_message(
                chat_id=payment["user_id"],
                text=f"✅ <b>To'lovingiz tasdiqlandi!</b>\n📄 {payment['file_name']}",
                parse_mode="HTML"
            )
            if file_obj:
                caption = f"📄 <b>{file_obj['file_name']}</b>\n💰 To'langan"
                if file_obj["file_type"] == "photo":
                    await context.bot.send_photo(chat_id=payment["user_id"], photo=file_obj["file_id"], caption=caption, parse_mode="HTML")
                elif file_obj["file_type"] == "video":
                    await context.bot.send_video(chat_id=payment["user_id"], video=file_obj["file_id"], caption=caption, parse_mode="HTML")
                elif file_obj["file_type"] == "audio":
                    await context.bot.send_audio(chat_id=payment["user_id"], audio=file_obj["file_id"], caption=caption, parse_mode="HTML")
                else:
                    await context.bot.send_document(chat_id=payment["user_id"], document=file_obj["file_id"], caption=caption, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error: {e}")
        await query.edit_message_text(f"✅ To'lov #{pay_id} tasdiqlandi, fayl yuborildi.")

    elif data.startswith("rejectpay_"):
        if not is_admin(user_id):
            return
        pay_id = int(data[10:])
        payment = reject_payment(pay_id)
        if payment:
            try:
                await context.bot.send_message(
                    chat_id=payment["user_id"],
                    text=f"❌ <b>To'lovingiz rad etildi.</b>\n📄 {payment['file_name']}",
                    parse_mode="HTML"
                )
            except:
                pass
        await query.edit_message_text(f"❌ To'lov #{pay_id} rad etildi.")

    elif data == "all_files":
        files = get_all_files()
        active = [f for f in files if not is_file_expired(f)]
        if not active:
            await query.edit_message_text(
                "📦 Hali fayl yo'q.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]))
            return
        keyboard = [[InlineKeyboardButton(file_label(f), callback_data=f"getfile_{f['id']}")] for f in active]
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])
        await query.edit_message_text(
            f"🗂 <b>Barcha fayllar</b> — {len(active)} ta",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "search":
        user_states[user_id] = {"step": "wait_search"}
        await query.edit_message_text(
            "🔎 <b>Qidirish</b>\n\nFayl nomi yoki kalit so'z yozing:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="back_main")]])
        )

    elif data == "admin_panel":
        if not is_admin(user_id):
            return
        await query.edit_message_text(
            "🔧 <b>Admin panel</b>",
            parse_mode="HTML",
            reply_markup=admin_panel_keyboard()
        )

    elif data == "statistics":
        if not is_admin(user_id):
            return
        files = get_all_files()
        active = [f for f in files if not is_file_expired(f)]
        expired = len(files) - len(active)
        paid_files = [f for f in active if f.get("is_paid")]
        users_db = load_users()
        total_downloads = sum(f.get("downloads", 0) for f in files)
        top_files = sorted(active, key=lambda x: x.get("downloads", 0), reverse=True)[:5]
        top_text = "".join(f"  {i}. {f['file_name']} — {f.get('downloads',0)}⬇\n" for i, f in enumerate(top_files, 1))
        text = (
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{len(users_db['users'])}</b>\n"
            f"📁 Faol fayllar: <b>{len(active)}</b>\n"
            f"❌ Muddati o'tgan: <b>{expired}</b>\n"
            f"💰 Pullik fayllar: <b>{len(paid_files)}</b>\n"
            f"⬇️ Jami yuklab olish: <b>{total_downloads}</b>\n\n"
            f"🏆 <b>Top 5:</b>\n{top_text}"
        )
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )

    elif data == "users_list":
        if not is_admin(user_id):
            return
        users_db = load_users()
        users = list(users_db["users"].values())
        text = f"👥 <b>Foydalanuvchilar</b> — {len(users)} ta\n\n"
        for u in users[-20:]:
            uname = f"@{u['username']}" if u.get("username") else "—"
            text += f"• <b>{u['first_name']}</b> {uname} | {u.get('downloads',0)}⬇ | {u.get('joined','')}\n"
        if len(users) > 20:
            text += f"\n... va yana {len(users)-20} ta"
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )

    elif data == "pending_payments":
        if not is_admin(user_id):
            return
        db = load_payments()
        pending = [p for p in db["payments"] if p["status"] == "pending"]
        if not pending:
            await query.edit_message_text(
                "💳 Kutilayotgan to'lov yo'q.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]]))
            return
        text = f"💳 <b>Kutilayotgan to'lovlar</b> — {len(pending)} ta\n\n"
        keyboard = []
        for p in pending:
            text += f"#{p['id']} | {p['file_name']} | {p['price']:,} so'm | {p['date']}\n"
            keyboard.append([
                InlineKeyboardButton(f"✅ #{p['id']}", callback_data=f"approvepay_{p['id']}"),
                InlineKeyboardButton(f"❌ #{p['id']}", callback_data=f"rejectpay_{p['id']}"),
            ])
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "broadcast":
        if not is_admin(user_id):
            return
        user_states[user_id] = {"step": "wait_broadcast"}
        await query.edit_message_text(
            "📢 <b>Hammaga xabar yuborish</b>\n\nXabar matnini yozing:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )

    elif data == "upload_file":
        if not is_admin(user_id):
            return
        user_states[user_id] = {"step": "wait_file", "data": {}}
        await query.edit_message_text(
            "📤 <b>Fayl yuklash</b>\n\nFaylni yuboring:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_upload")]])
        )

    elif data.startswith("select_cat_"):
        if not is_admin(user_id) or user_id not in user_states:
            return
        cat_key = data[11:]
        user_states[user_id]["data"]["category"] = cat_key
        user_states[user_id]["step"] = "wait_paid"
        await query.edit_message_text(
            "💰 <b>Fayl pullikmi?</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 Ha, pullik", callback_data="set_paid_yes"),
                 InlineKeyboardButton("🆓 Bepul", callback_data="set_paid_no")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_upload")],
            ])
        )

    elif data in ["set_paid_yes", "set_paid_no"]:
        if not is_admin(user_id) or user_id not in user_states:
            return
        is_paid = data == "set_paid_yes"
        user_states[user_id]["data"]["is_paid"] = is_paid
        if is_paid:
            user_states[user_id]["step"] = "wait_price"
            await query.edit_message_text(
                "💵 <b>Narxni yozing</b> (faqat son, masalan: 5000):",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_upload")]])
            )
        else:
            user_states[user_id]["data"]["price"] = 0
            user_states[user_id]["step"] = "wait_time"
            await query.edit_message_text(
                "⏰ <b>Fayl qancha vaqt ko'rinadi?</b>",
                parse_mode="HTML",
                reply_markup=time_select_keyboard()
            )

    elif data.startswith("set_time_"):
        if not is_admin(user_id) or user_id not in user_states:
            return
        hours = int(data[9:])
        user_states[user_id]["data"]["expires_hours"] = hours
        user_states[user_id]["step"] = "wait_description"
        time_text = f"{hours} soat" if hours > 0 else "Cheksiz"
        await query.edit_message_text(
            f"⏰ Vaqt: <b>{time_text}</b>\n\n📝 Tavsif yozing yoki o'tkazib yuboring:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="skip_description")]])
        )

    elif data == "skip_description":
        if not is_admin(user_id) or user_id not in user_states:
            return
        await _finalize_upload(update, context, user_id, description="")

    elif data == "cancel_upload":
        if user_id in user_states:
            del user_states[user_id]
        await query.edit_message_text("❌ Bekor qilindi.", reply_markup=admin_panel_keyboard())

    elif data == "delete_file":
        if not is_admin(user_id):
            return
        files = get_all_files()
        if not files:
            await query.edit_message_text("📦 Fayl yo'q.", reply_markup=admin_panel_keyboard())
            return
        keyboard = [[InlineKeyboardButton(f"🗑 {f['file_name']}", callback_data=f"confirmdelete_{f['id']}")] for f in files]
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")])
        await query.edit_message_text("🗑 <b>Qaysi faylni o'chirmoqchisiz?</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("confirmdelete_"):
        if not is_admin(user_id):
            return
        delete_file(int(data[14:]))
        await query.edit_message_text("✅ Fayl o'chirildi!", reply_markup=admin_panel_keyboard())

# ==================== FAYL QABUL ====================
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id) or user_id not in user_states or user_states[user_id]["step"] != "wait_file":
        return
    msg = update.message
    file_id, file_name, file_type = None, "Nomsiz", "document"
    if msg.document:
        file_id, file_name, file_type = msg.document.file_id, msg.document.file_name or "Hujjat", "document"
    elif msg.photo:
        file_id, file_name, file_type = msg.photo[-1].file_id, "Rasm", "photo"
    elif msg.video:
        file_id, file_name, file_type = msg.video.file_id, msg.video.file_name or "Video", "video"
    elif msg.audio:
        file_id, file_name, file_type = msg.audio.file_id, msg.audio.file_name or "Audio", "audio"
    else:
        await update.message.reply_text("❌ Noto'g'ri fayl turi.")
        return
    user_states[user_id]["data"].update({"file_id": file_id, "file_name": file_name, "file_type": file_type})
    user_states[user_id]["step"] = "wait_category"
    await update.message.reply_text(
        f"✅ <b>{file_name}</b> qabul qilindi!\n\n📂 Kategoriyani tanlang:",
        parse_mode="HTML",
        reply_markup=category_select_keyboard()
    )

# ==================== MATN QABUL ====================
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_states:
        # Botga oddiy matn yozsa — menyuni ko'rsat
        await update.message.reply_text(
            "🏠 <b>Asosiy menyu</b>",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(user_id)
        )
        return

    step = user_states[user_id]["step"]

    if step == "wait_price":
        try:
            price = int(text.replace(" ", "").replace(",", ""))
            user_states[user_id]["data"]["price"] = price
            user_states[user_id]["step"] = "wait_time"
            await update.message.reply_text(
                f"💵 Narx: <b>{price:,} so'm</b>\n\n⏰ Fayl qancha vaqt ko'rinadi?",
                parse_mode="HTML",
                reply_markup=time_select_keyboard()
            )
        except:
            await update.message.reply_text("❌ Faqat son kiriting! Masalan: 5000")

    elif step == "wait_description":
        await _finalize_upload(update, context, user_id, description=text)

    elif step == "wait_search":
        del user_states[user_id]
        results = search_files(text)
        active = [f for f in results if not is_file_expired(f)]
        if not active:
            await update.message.reply_text(
                f"🔎 <b>'{text}'</b> — hech narsa topilmadi.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(user_id)
            )
            return
        keyboard = [[InlineKeyboardButton(file_label(f), callback_data=f"getfile_{f['id']}")] for f in active]
        keyboard.append([InlineKeyboardButton("🔙 Asosiy menyu", callback_data="back_main")])
        await update.message.reply_text(
            f"🔎 <b>'{text}'</b> — {len(active)} ta natija:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif step == "wait_broadcast":
        if not is_admin(user_id):
            return
        del user_states[user_id]
        users_db = load_users()
        sent, failed = 0, 0
        for uid in users_db["users"]:
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=f"📢 <b>E'lon</b>\n\n{text}",
                    parse_mode="HTML"
                )
                sent += 1
            except:
                failed += 1
        await update.message.reply_text(
            f"📢 Yuborildi!\n✅ Muvaffaqiyatli: {sent}\n❌ Yuborilmadi: {failed}",
            reply_markup=admin_panel_keyboard()
        )

async def _finalize_upload(update, context, user_id, description):
    d = user_states[user_id]["data"]
    add_file(
        d["file_id"], d["file_name"], d["file_type"],
        d["category"], description, user_id,
        is_paid=d.get("is_paid", False),
        price=d.get("price", 0),
        expires_hours=d.get("expires_hours", 0)
    )
    del user_states[user_id]
    cat_name = next((n for n, k in CATEGORIES.items() if k == d["category"]), "")
    expires_hours = d.get("expires_hours", 0)
    time_text = f"{expires_hours} soat" if expires_hours > 0 else "Cheksiz"
    paid_text = f"💰 {d.get('price', 0):,} so'm" if d.get("is_paid") else "🆓 Bepul"
    msg = (
        f"✅ <b>Saqlandi!</b>\n"
        f"📄 {d['file_name']}\n"
        f"📂 {cat_name}\n"
        f"{paid_text} | ⏰ {time_text}"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=admin_panel_keyboard())
    else:
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=admin_panel_keyboard())

# ==================== TOZALASH ====================
async def cleanup_expired(context: ContextTypes.DEFAULT_TYPE):
    deleted = delete_expired_files()
    if deleted > 0:
        logger.info(f"O'chirildi: {deleted} ta muddati o'tgan fayl")

# ==================== ISHGA TUSHIRISH ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", lambda u, c: u.message.reply_text("🏠 Menyu", reply_markup=main_menu_keyboard(u.effective_user.id))))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, receive_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    app.job_queue.run_repeating(cleanup_expired, interval=600, first=10)
    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
