import os
import datetime
from dotenv import load_dotenv
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import db
from translations import t, set_user_lang, get_user_lang, get_available_languages

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# ============ TUGMALAR MENUSI ============
def main_menu(user_id=None):
    if user_id:
        play_btn = t(user_id, "play")
        rating_btn = t(user_id, "rating")
        profile_btn = t(user_id, "profile")
        coins_btn = t(user_id, "coins")
        shop_btn = t(user_id, "shop")
        bonus_btn = t(user_id, "bonus")
        tournaments_btn = t(user_id, "tournaments")
        lang_btn = t(user_id, "language")
        lang = get_user_lang(user_id)
    else:
        play_btn = "🎮 O'ynash"
        rating_btn = "🏆 Reyting"
        profile_btn = "📊 Profil"
        coins_btn = "🪙 Tangalar"
        shop_btn = "🛒 Do'kon"
        bonus_btn = "🎁 Bonus"
        tournaments_btn = "🏆 Turnirlar"
        lang_btn = "🌐 Til"
        lang = "uz"

    web_app_url = f"{WEBAPP_URL}?lang={lang}"

    keyboard = [
        [KeyboardButton(play_btn, web_app=WebAppInfo(url=web_app_url))],
        [KeyboardButton(rating_btn), KeyboardButton(profile_btn)],
        [KeyboardButton(coins_btn), KeyboardButton(shop_btn)],
        [KeyboardButton(bonus_btn), KeyboardButton(tournaments_btn)],
        [KeyboardButton(lang_btn)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============ START ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    if not db.user_exists(user_id):
        db.add_user(user_id, username or '', first_name)

    await update.message.reply_text(
        t(user_id, "start", name=first_name),
        reply_markup=main_menu(user_id)
    )

# ============ TUGMALARGA JAVOB ============
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    if not db.user_exists(user_id):
        db.add_user(user_id, username or '', first_name)

    rating_btn = t(user_id, "rating")
    profile_btn = t(user_id, "profile")
    coins_btn = t(user_id, "coins")
    shop_btn = t(user_id, "shop")
    bonus_btn = t(user_id, "bonus")
    tournaments_btn = t(user_id, "tournaments")
    lang_btn = t(user_id, "language")

    if text == rating_btn:
        top_players = db.get_top_players(10)
        if not top_players:
            await update.message.reply_text(t(user_id, "rating_empty"), reply_markup=main_menu(user_id))
            return
        msg = t(user_id, "top10")
        medals = ["🥇", "🥈", "🥉"]
        for i, p in enumerate(top_players):
            name = p['first_name'] or f"@{p['username']}" or "Anonim"
            medal = medals[i] if i < 3 else f"{i+1}."
            msg += f"{medal} {name}\n"
            msg += f"   ⭐ {p['total_score']} {t(user_id, 'rating_score')} | 🪙 {p['coins']} {t(user_id, 'rating_coins')}\n"
            if p['best_time'] > 0:
                mins, secs = p['best_time'] // 60, p['best_time'] % 60
                msg += f"   ⏱ {mins}:{secs:02d}\n"
            msg += "\n"
        await update.message.reply_text(msg, reply_markup=main_menu(user_id))

    elif text == profile_btn:
        user_stats = db.get_user_stats(user_id)
        coins_balance = db.get_user_coins(user_id)
        msg = t(user_id, "profile_title", name=first_name)
        msg += f"{t(user_id, 'profile_id')}: {user_id}\n"
        msg += f"🪙 {t(user_id, 'rating_coins')}: {coins_balance}\n\n"
        msg += f"{t(user_id, 'profile_stats')}:\n"
        msg += f"{t(user_id, 'profile_games')}: {user_stats['total_games']}\n"
        msg += f"{t(user_id, 'profile_wins')}: {user_stats['total_wins']}\n"
        msg += f"{t(user_id, 'profile_score')}: {user_stats['total_score']}\n"
        if user_stats['total_games'] > 0:
            winrate = (user_stats['total_wins'] / user_stats['total_games'] * 100)
            msg += f"{t(user_id, 'profile_winrate')}: {winrate:.1f}%\n"
        if user_stats['best_time'] > 0:
            mins, secs = user_stats['best_time'] // 60, user_stats['best_time'] % 60
            msg += f"{t(user_id, 'profile_time')}: {mins}:{secs:02d}\n"
        msg += f"\n{t(user_id, 'profile_today')}:\n"
        msg += f"{t(user_id, 'profile_games')}: {user_stats['today_games']}\n"
        msg += f"{t(user_id, 'profile_wins')}: {user_stats['today_wins']}\n"
        msg += f"\n{t(user_id, 'profile_friends')}: {user_stats['referal_count']}\n"
        await update.message.reply_text(msg, reply_markup=main_menu(user_id))

    elif text == coins_btn:
        coins_balance = db.get_user_coins(user_id)
        history = db.get_coin_history(user_id, 5)
        msg = t(user_id, "coins_balance", name=first_name, coins=coins_balance)
        if history:
            msg += t(user_id, "coins_history")
            for h in history:
                sign = "+" if h['amount'] > 0 else ""
                msg += f"  {sign}{h['amount']} - {h['description']}\n"
        await update.message.reply_text(msg, reply_markup=main_menu(user_id))

    elif text == shop_btn:
        packages = db.get_coin_packages()
        msg = t(user_id, "shop_title")
        for pkg in packages:
            msg += t(user_id, "shop_item", name=pkg['name'], coins=pkg['coins'], price=pkg['price'])
        msg += t(user_id, "shop_note")
        await update.message.reply_text(msg, reply_markup=main_menu(user_id))

    elif text == bonus_btn:
        if db.can_claim_bonus(user_id):
            db.claim_bonus(user_id, 100)
            coins_balance = db.get_user_coins(user_id)
            await update.message.reply_text(
                t(user_id, "bonus_claimed", name=first_name, coins=coins_balance),
                reply_markup=main_menu(user_id)
            )
        else:
            await update.message.reply_text(t(user_id, "bonus_wait"), reply_markup=main_menu(user_id))

    elif text == tournaments_btn:
        tournaments_list = db.get_active_tournaments()
        if not tournaments_list:
            keyboard = [[
                InlineKeyboardButton(t(user_id, "quick_tournament"), callback_data='create_quick'),
                InlineKeyboardButton(t(user_id, "daily_tournament"), callback_data='create_daily'),
            ]]
            await update.message.reply_text(t(user_id, "tournaments_empty"), reply_markup=InlineKeyboardMarkup(keyboard))
            return
        msg = t(user_id, "tournaments_title")
        keyboard = []
        for tour in tournaments_list:
            end_date = datetime.datetime.fromisoformat(tour['end_date'])
            remaining = end_date - datetime.datetime.now()
            hours_left = max(0, int(remaining.total_seconds() // 3600))
            mins_left = max(0, int((remaining.total_seconds() % 3600) // 60))
            msg += f"📌 {tour['name']}\n"
            msg += f"   {t(user_id, 'tournament_entry')}: {tour['entry_fee']} 🪙\n"
            msg += f"   {t(user_id, 'tournament_prize')}: {tour['prize_pool']} 🪙\n"
            msg += f"   {t(user_id, 'tournament_end')}: {hours_left}s {mins_left}daq\n\n"
            keyboard.append([
                InlineKeyboardButton(t(user_id, "join"), callback_data=f"join_tournament_{tour['id']}"),
                InlineKeyboardButton(t(user_id, "leaderboard"), callback_data=f"tournament_lb_{tour['id']}")
            ])
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    elif text == lang_btn:
        languages = get_available_languages()
        keyboard = []
        row = []
        for i, (code, name) in enumerate(languages.items()):
            row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        await update.message.reply_text(t(user_id, "lang_select"), reply_markup=InlineKeyboardMarkup(keyboard))

# ============ GURUH TURNIRI ============
async def freetournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    if not db.user_exists(user_id):
        db.add_user(user_id, username or '', first_name)

    tournament_id = db.create_group_tournament(chat_id, user_id, f"🏆 {first_name} turniri", "medium", 10, 0)
    db.join_group_tournament(tournament_id, user_id, first_name, username or '')

    web_app_url = f"{WEBAPP_URL}?lang={get_user_lang(user_id)}&tournament={tournament_id}"
    is_group = chat_id != user_id
    forward_text = "\n📤 Guruhga forward qiling!" if not is_group else ""

    keyboard = [
        [InlineKeyboardButton("✅ Qatnashish", callback_data=f"gjoin_{tournament_id}"),
         InlineKeyboardButton("🎮 O'ynash", url=web_app_url)]
    ]

    await update.message.reply_text(
        f"🏆 **GURUH TURNIRI**\n\n"
        f"👤 Yaratuvchi: {first_name}\n"
        f"📊 Qiyinlik: O'rta\n"
        f"👥 Ishtirokchilar: 1/10\n"
        f"🆔 ID: `{tournament_id}`\n\n"
        f"Quyidagi tugmalarni bosing:{forward_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============ GURUH BUYRUQLARI ============
async def handle_group_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    if not db.user_exists(user_id):
        db.add_user(user_id, username or '', first_name)

    if text.startswith('/join_'):
        tid = int(text.replace('/join_', ''))
        result = db.join_group_tournament(tid, user_id, first_name, username or '')
        tournament = db.get_group_tournament(tid)
        count = db.count_group_tournament_players(tid)

        if result == 'success':
            await update.message.reply_text(
                f"✅ {first_name} turnirga qo'shildi!\n"
                f"Ishtirokchilar: {count}/{tournament['max_players'] if tournament else 10}"
            )
        elif result == 'already':
            await update.message.reply_text("❌ Allaqachon qo'shilgansiz!")
        else:
            await update.message.reply_text("❌ Xatolik! Turnir topilmadi.")

    elif text.startswith('/play_'):
        tid = int(text.replace('/play_', ''))
        web_app_url = f"{WEBAPP_URL}?lang={get_user_lang(user_id)}&tournament={tid}"
        await context.bot.send_message(
            chat_id=user_id,
            text="🎮 O'yin ochish uchun tugmani bosing:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎮 O'ynash", web_app=WebAppInfo(url=web_app_url))
            ]])
        )

# ============ BUYRUQLAR ============
async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_menu(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_menu(update, context)

async def coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_menu(update, context)

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_menu(update, context)

async def daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_menu(update, context)

async def tournaments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_menu(update, context)

async def mytournaments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    if not db.user_exists(user_id):
        db.add_user(user_id, username or '', first_name)
    my_tours = db.get_user_tournaments(user_id)
    if not my_tours:
        await update.message.reply_text(t(user_id, "no_tournaments"), reply_markup=main_menu(user_id))
        return
    msg = t(user_id, "my_tournaments")
    for tour in my_tours[:5]:
        emoji = "🟢" if tour['status'] == 'active' else "🔴"
        msg += f"{emoji} {tour['name']} - ⭐{tour['score']}\n"
    await update.message.reply_text(msg, reply_markup=main_menu(user_id))

async def share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    text = f"🎮 Sudoku!\n👉 @{bot_username}"
    keyboard = [[InlineKeyboardButton("📱 Share", url=f"https://t.me/share/url?url=https://t.me/{bot_username}")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ADMIN_IDS = [7948136406]
    if user_id in ADMIN_IDS:
        await update.message.reply_text(t(user_id, "admin", url=f"{WEBAPP_URL}/admin"))
    else:
        await update.message.reply_text(t(user_id, "no_access"))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(t(user_id, "help"), reply_markup=main_menu(user_id))

# ============ CALLBACK ============
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    if not db.user_exists(user_id):
        db.add_user(user_id, username or '', first_name)

    if data.startswith('lang_'):
        lang = data.split('_')[1]
        set_user_lang(user_id, lang)
        lang_names = {'uz': "🇺🇿 O'zbekcha", 'ru': "🇷🇺 Русский", 'en': "🇬🇧 English",
                      'zh': "🇨🇳 中文", 'ja': "🇯🇵 日本語", 'ko': "🇰🇷 한국어", 'hi': "🇮🇳 हिन्दी"}
        await query.edit_message_text(f"✅ {t(user_id, 'lang_changed')}: {lang_names.get(lang, lang)}")
        await context.bot.send_message(
            chat_id=user_id,
            text=t(user_id, "start", name=first_name),
            reply_markup=main_menu(user_id)
        )

    elif data == 'buy_coins':
        packages = db.get_coin_packages()
        text = t(user_id, "shop_title")
        keyboard = []
        for pkg in packages:
            keyboard.append([InlineKeyboardButton(
                f"{pkg['name']} - {pkg['coins']} 🪙 ({pkg['price']:,} so'm)",
                callback_data=f"buy_package_{pkg['id']}"
            )])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith('buy_package_'):
        package_id = int(data.split('_')[2])
        packages = db.get_coin_packages()
        pkg = next((p for p in packages if p['id'] == package_id), None)
        if pkg:
            await query.edit_message_text(f"💳 {pkg['name']}\n💰 {pkg['coins']} 🪙\n💵 {pkg['price']:,} so'm\n\n👤 @YourUsername")

    elif data == 'daily_bonus':
        if db.can_claim_bonus(user_id):
            db.claim_bonus(user_id, 100)
            coins_balance = db.get_user_coins(user_id)
            await query.edit_message_text(t(user_id, "bonus_claimed", name=first_name, coins=coins_balance))
        else:
            await query.edit_message_text(t(user_id, "bonus_wait"))

    elif data == 'watch_ad':
        db.record_ad_view(user_id)
        coins_balance = db.get_user_coins(user_id)
        await query.edit_message_text(f"📺 +5 🪙\n💰 {coins_balance}")

    elif data == 'create_quick':
        tournament_id = db.create_tournament("⚡ Quick", "quick", "medium", 1, 25, 0)
        db.join_tournament(tournament_id, user_id)
        await query.edit_message_text("⚡ Tezkor turnir!\nKirish: 25 🪙\n1 soat")

    elif data == 'create_daily':
        tournament_id = db.create_tournament("📅 Daily", "daily", "hard", 24, 100, 0)
        db.join_tournament(tournament_id, user_id)
        await query.edit_message_text("📅 Kunlik turnir!\nKirish: 100 🪙\n24 soat")

    elif data.startswith('join_tournament_'):
        tournament_id = int(data.split('_')[2])
        result = db.join_tournament(tournament_id, user_id)
        messages = {
            'success': t(user_id, "joined"),
            'already': t(user_id, "already_joined"),
            'no_coins': t(user_id, "no_coins"),
            'not_found': t(user_id, "not_found")
        }
        await query.edit_message_text(messages.get(result, "Xatolik!"))

    elif data.startswith('tournament_lb_'):
        tournament_id = int(data.split('_')[2])
        lb = db.get_tournament_leaderboard(tournament_id, 10)
        tournament = db.get_tournament(tournament_id)
        text = f"📊 {tournament['name']}:\n\n"
        if not lb:
            text += "Ishtirokchilar yo'q!"
        else:
            medals = ["🥇", "🥈", "🥉"]
            for i, player in enumerate(lb):
                medal = medals[i] if i < 3 else f"{i+1}."
                name = player['first_name'] or f"@{player['username']}" or "Anonim"
                text += f"{medal} {name} - ⭐{player['score']}\n"
        await query.edit_message_text(text)

# ============ MAIN ============
def main():
    print("🤖 Bot ishga tushmoqda...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rating", rating))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("coins", coins))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("bonus", daily_bonus))
    app.add_handler(CommandHandler("tournaments", tournaments))
    app.add_handler(CommandHandler("mytournaments", mytournaments))
    app.add_handler(CommandHandler("share", share))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("freetournament", freetournament))

    # Guruh buyruqlari (/join_ID, /play_ID)
    app.add_handler(MessageHandler(filters.Regex(r'^/(join_|play_)\d+'), handle_group_commands))

    # Tugmalar
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.add_handler(CallbackQueryHandler(callback_handler))

    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == '__main__':
    main()