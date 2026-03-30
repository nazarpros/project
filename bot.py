import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, request

from database import (
    get_player, add_exp, can_search_dragon, search_dragon, update_dragon_search_time,
    add_dragon, get_player_dragons, get_current_dragon, set_current_dragon,
    start_raid, raid_attack, get_raid_info, get_max_dragons, DRAGONS, update_player
)

# Берем токен из переменных окружения Render
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ TOKEN не найден! Добавь переменную окружения TOKEN в Render")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

user_temp_data = {}

# Создаём приложение Telegram
app = Application.builder().token(TOKEN).build()

# Создаём Flask приложение
flask_app = Flask(__name__)

# ============ ВСЕ ОБРАБОТЧИКИ ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player = get_player(user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("⚔️ Рейд", callback_data="raid")],
        [InlineKeyboardButton("🐉 Найти Дракона", callback_data="search_dragon")],
        [InlineKeyboardButton("🏠 Конюшня", callback_data="stable")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🐉 *Добро пожаловать в игру, {user.first_name}!*\n\n"
        "Ты — начинающий наездник драконов. Исследуй мир, находи драконов и сражайся с охотниками!\n\n"
        f"📊 *Твой уровень:* {player[2]}\n"
        f"✨ *Опыт:* {player[3]}/{player[2] * 100}\n"
        f"💰 *Золото:* {player[4]}",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    player = get_player(user.id, user.username)
    
    current_dragon = get_current_dragon(user.id)
    dragons = get_player_dragons(user.id)
    
    dragon_text = "❌ Нет дракона" if not current_dragon else f"🐉 {current_dragon[2]} ({current_dragon[3]})"
    stable_count = f"{len(dragons)}/{get_max_dragons(player[2])}"
    
    text = (
        f"👤 *Профиль игрока*\n\n"
        f"📛 *Имя:* {user.first_name}\n"
        f"🌟 *Уровень:* {player[2]}\n"
        f"✨ *Опыт:* {player[3]}/{player[2] * 100}\n"
        f"💰 *Золото:* {player[4]}\n"
        f"🐉 *Активный дракон:* {dragon_text}\n"
        f"🏠 *Конюшня:* {stable_count}\n"
        f"🎯 *Следующий уровень:* {player[2] * 100 - player[3]} опыта"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def raid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    current_dragon = get_current_dragon(user.id)
    
    if not current_dragon:
        text = "❌ *У тебя нет активного дракона!*\n\nСначала найди дракона и выбери его в конюшне."
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    raid_enemies = get_raid_info(user.id)
    
    if raid_enemies == 0:
        enemies = start_raid(user.id, current_dragon)
        text = (
            f"⚔️ *Начался рейд!*\n\n"
            f"Твой дракон {current_dragon[2]} атакует корабль охотников!\n"
            f"👥 *Врагов на корабле:* {enemies}\n\n"
            f"Нажми кнопку, чтобы атаковать!"
        )
    else:
        text = (
            f"⚔️ *Рейд продолжается!*\n\n"
            f"Твой дракон {current_dragon[2]} сражается!\n"
            f"👥 *Осталось врагов:* {raid_enemies}\n\n"
            f"Нажми кнопку, чтобы продолжить атаку!"
        )
    
    keyboard = [
        [InlineKeyboardButton("⚔️ Атаковать!", callback_data="raid_attack")],
        [InlineKeyboardButton("🔙 Выход из рейда", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def raid_attack_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    current_dragon = get_current_dragon(user.id)
    
    if not current_dragon:
        await query.edit_message_text("❌ У тебя нет дракона!", reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")
        ]]))
        return
    
    victory, reward_gold, reward_exp = raid_attack(user.id)
    
    if victory:
        add_exp(user.id, reward_exp)
        player = get_player(user.id, user.username)
        new_gold = player[4] + reward_gold
        update_player(user.id, gold=new_gold)
        
        text = (
            f"🎉 *ПОБЕДА!*\n\n"
            f"Твой дракон {current_dragon[2]} уничтожил всех охотников!\n"
            f"💰 *Награда:* {reward_gold} золота\n"
            f"✨ *Опыт:* +{reward_exp}\n\n"
            f"Охотники больше не побеспокоят эти воды..."
        )
        keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        enemies_left = reward_exp
        text = (
            f"⚔️ *Атака!*\n\n"
            f"{current_dragon[2]} наносит удар!\n"
            f"👥 *Осталось врагов:* {enemies_left}\n\n"
            f"Продолжай сражение!"
        )
        keyboard = [[InlineKeyboardButton("⚔️ Следующая атака", callback_data="raid_attack")],
                    [InlineKeyboardButton("🔙 Выход", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def search_dragon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    player = get_player(user.id, user.username)
    
    can_search, wait_minutes = can_search_dragon(user.id)
    
    if not can_search:
        text = f"⏰ *Ты устал после поисков!*\n\nОтдохни {wait_minutes} минут и попробуй снова."
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    found, dragon_name, dragon_data = search_dragon(user.id, player[2])
    
    if not found:
        text = "🔍 *Ты обыскал окрестности, но никого не нашел...*\n\nПопробуй снова через 3 часа!"
        update_dragon_search_time(user.id)
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    update_dragon_search_time(user.id)
    
    user_temp_data[user.id] = {
        "dragon_name": dragon_name,
        "dragon_data": dragon_data
    }
    
    dragon_gifs = dragon_data.get("gifs", {})
    found_gif = dragon_gifs.get("found")
    if found_gif:
        await query.message.reply_animation(found_gif, caption=f"✨ *Ты нашел дикого {dragon_name}!*", parse_mode="Markdown")
    
    text = (
        f"🐉 *{dragon_name}* ({dragon_data['type']})\n"
        f"❤️ *Здоровье:* {dragon_data['health']}\n"
        f"⚔️ *Атака:* {dragon_data['attack']}\n\n"
        f"Дракон выглядит голодным... Что ты предложишь ему?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🐟 Рыба", callback_data="feed_fish")],
        [InlineKeyboardButton("🪨 Камень", callback_data="feed_stone")],
        [InlineKeyboardButton("🐍 Угорь", callback_data="feed_eel")],
        [InlineKeyboardButton("🐔 Курица", callback_data="feed_chicken")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def feed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    food_map = {
        "feed_fish": "рыба",
        "feed_stone": "камень",
        "feed_eel": "угорь",
        "feed_chicken": "курица"
    }
    
    food = food_map.get(query.data)
    
    if user.id not in user_temp_data:
        await query.edit_message_text("Ошибка! Начни поиск дракона заново.")
        return
    
    dragon_name = user_temp_data[user.id]["dragon_name"]
    dragon_data = user_temp_data[user.id]["dragon_data"]
    dragon_gifs = dragon_data.get("gifs", {})
    
    if food in dragon_data["favorite_foods"]:
        feed_gif = dragon_gifs.get("feed")
        if feed_gif:
            await query.message.reply_animation(feed_gif, caption=f"😍 *{dragon_name} с удовольствием съел {food}!*", parse_mode="Markdown")
        
        text = f"Дракон подходит к тебе и позволяет себя приручить!\n\nТы хочешь приручить {dragon_name}?"
        keyboard = [
            [InlineKeyboardButton("✅ Приручить!", callback_data="tame_yes")],
            [InlineKeyboardButton("❌ Отпустить", callback_data="tame_no")]
        ]
    else:
        disgust_gif = dragon_gifs.get("disgust")
        if disgust_gif:
            await query.message.reply_animation(disgust_gif, caption=f"😕 *{dragon_name} попробовал {food}, но ему не понравилось...*", parse_mode="Markdown")
        
        text = f"Дракон улетает. Может быть, в следующий раз повезет больше!"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        del user_temp_data[user.id]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def tame_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "tame_yes":
        if user.id not in user_temp_data:
            await query.edit_message_text("Ошибка! Начни поиск заново.")
            return
        
        dragon_name = user_temp_data[user.id]["dragon_name"]
        dragon_data = user_temp_data[user.id]["dragon_data"]
        dragon_gifs = dragon_data.get("gifs", {})
        
        tame_gif = dragon_gifs.get("tame") or dragon_gifs.get("feed")
        if tame_gif:
            await query.message.reply_animation(tame_gif, caption=f"🎉 *Ты приручил {dragon_name}!*", parse_mode="Markdown")
        
        dragon_id = add_dragon(user.id, dragon_name, dragon_data)
        
        if dragon_id is None:
            text = "❌ *Этот дракон уже принадлежит другому наезднику!*\n\nНочная Фурия может быть только у одного игрока."
            keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
            del user_temp_data[user.id]
            return
        
        dragons = get_player_dragons(user.id)
        player = get_player(user.id, user.username)
        max_dragons = get_max_dragons(player[2])
        
        if len(dragons) == 1:
            set_current_dragon(user.id, dragon_id)
            current_text = " и назначен активным!"
        else:
            current_text = "!"
        
        text = (
            f"🎉 *Поздравляю!*\n\n"
            f"Ты приручил {dragon_name} ({dragon_data['type']}){current_text}\n\n"
            f"❤️ *Здоровье:* {dragon_data['health']}\n"
            f"⚔️ *Атака:* {dragon_data['attack']}\n"
            f"🍽️ *Любимая еда:* {', '.join(dragon_data['favorite_foods'])}"
        )
        
        add_exp(user.id, 20)
        text += f"\n\n✨ *+20 опыта за приручение!*"
        
        del user_temp_data[user.id]
    else:
        text = "🍃 *Ты отпустил дракона на свободу...*\n\nМожет быть, в другой раз судьба будет благосклоннее."
        del user_temp_data[user.id]
    
    keyboard = [[InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def stable_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    dragons = get_player_dragons(user.id)
    player = get_player(user.id, user.username)
    current = get_current_dragon(user.id)
    
    if not dragons:
        text = "🏠 *Твоя конюшня пуста...*\n\nНайди и приручи своего первого дракона!"
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        return
    
    max_dragons = get_max_dragons(player[2])
    text = f"🏠 *Твоя конюшня* ({len(dragons)}/{max_dragons})\n\n"
    
    keyboard = []
    
    for dragon in dragons:
        is_current = "⭐ " if current and current[0] == dragon[0] else "   "
        text += f"{is_current}🐉 *{dragon[2]}* ({dragon[3]})\n"
        text += f"   ❤️ {dragon[5]} | ⚔️ {dragon[6]} | 🍽️ {dragon[4]}\n\n"
        
        if not (current and current[0] == dragon[0]):
            keyboard.append([InlineKeyboardButton(f"Выбрать {dragon[2]}", callback_data=f"select_dragon_{dragon[0]}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)

async def select_dragon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    dragon_id = int(query.data.split("_")[2])
    
    set_current_dragon(user.id, dragon_id)
    
    await query.edit_message_text("✅ *Дракон выбран активным!*\n\nОн готов к приключениям!")
    
    await stable_callback(update, context)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    player = get_player(user.id, user.username)
    
    keyboard = [
        [InlineKeyboardButton("👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton("⚔️ Рейд", callback_data="raid")],
        [InlineKeyboardButton("🐉 Найти Дракона", callback_data="search_dragon")],
        [InlineKeyboardButton("🏠 Конюшня", callback_data="stable")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"🐉 *Главное меню*\n\n"
        f"🌟 Уровень: {player[2]}\n"
        f"💰 Золото: {player[4]}",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ============ НАСТРОЙКА ХЕНДЛЕРОВ ============

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(profile_callback, pattern="^profile$"))
app.add_handler(CallbackQueryHandler(raid_callback, pattern="^raid$"))
app.add_handler(CallbackQueryHandler(raid_attack_callback, pattern="^raid_attack$"))
app.add_handler(CallbackQueryHandler(search_dragon_callback, pattern="^search_dragon$"))
app.add_handler(CallbackQueryHandler(feed_callback, pattern="^feed_"))
app.add_handler(CallbackQueryHandler(tame_callback, pattern="^tame_"))
app.add_handler(CallbackQueryHandler(stable_callback, pattern="^stable$"))
app.add_handler(CallbackQueryHandler(select_dragon_callback, pattern="^select_dragon_"))
app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))

# ============ FLASK WEBHOOK ============

@flask_app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        try:
            update = Update.de_json(request.get_json(force=True), app.bot)
            app.process_update(update)
            return 'ok', 200
        except Exception as e:
            logging.error(f"Ошибка обработки update: {e}")
            return 'error', 500
    return 'Bot is running', 200

# ============ ЗАПУСК ============

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/"
    
    # Устанавливаем вебхук
    app.bot.set_webhook(webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")
    
    # Запускаем Flask
    flask_app.run(host='0.0.0.0', port=port)
