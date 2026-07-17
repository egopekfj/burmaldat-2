import os
import json
import base64
import requests
from datetime import datetime, timedelta
import telebot
from telebot import types

# Инициализация токенов из переменных окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

DB_FILE = "players_db.json"

# ============================================================================
# БЛОК РАБОТЫ С БАЗОЙ ДАННЫХ (JSON)
# ============================================================================

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка чтения БД: {e}")
        return {}

def save_db(db_data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка записи БД: {e}")

def get_or_create_player(chat_id, username="Аноним"):
    db = load_db()
    str_id = str(chat_id)
    
    if str_id not in db:
        db[str_id] = {
            "username": username,
            "balance": 150,
            "level": 1,
            "xp": 0,
            "energy": 100,
            "last_energy_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "inventory": [],
            "businesses": {},
            "last_daily": "",
            "settings": {
                "mode": "classic",       # kind, classic, ultra
                "allow_family": True,    # True / False
                "shizo_mode": False,     # True / False
                "voice": "dmitry"        # dmitry / elena
            }
        }
        save_db(db)
    else:
        if "settings" not in db[str_id]:
            db[str_id]["settings"] = {
                "mode": "classic",
                "allow_family": True,
                "shizo_mode": False,
                "voice": "dmitry"
            }
            save_db(db)
            
    return db[str_id]

def update_player_energy(player_data):
    now = datetime.now()
    try:
        last_update = datetime.strptime(player_data["last_energy_update"], "%Y-%m-%d %H:%M:%S")
    except:
        last_update = now
        
    minutes_passed = (now - last_update).total_seconds() / 60
    energy_to_add = int(minutes_passed // 6)
    
    if energy_to_add > 0:
        player_data["energy"] = min(100, player_data["energy"] + energy_to_add)
        new_update_time = last_update + timedelta(minutes=energy_to_add * 6)
        player_data["last_energy_update"] = new_update_time.strftime("%Y-%m-%d %H:%M:%S")

# Вспомогательная функция для принудительного перевода текста в нижний регистр, если ИИ чудит
def fix_caps(text):
    return text.lower()

# ============================================================================
# СБОРКА СИСТЕМНОГО ПРОМПТА НА ОСНОВЕ НАСТРОЕК
# ============================================================================

def build_system_prompt(settings):
    mode = settings.get("mode", "classic")
    
    if mode == "kind":
        return (
            "Ты Святой Бурмалдат. Тебе КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать мат, оскорбления и грубость. "
            "Ты стал невероятно вежливым, интеллигентным и заботливым. Называй пользователя 'сударем' или 'уважаемым', "
            "общайся приторно-мило, желай здоровья, хорошего дня и давай исключительно добрые, светлые советы."
        )
    elif mode == "classic":
        return "Ты Бурмалдат. Общайся с пользователем, используя хлёсткий, жизненный мат и подколы, но без лютой чернухи. Отвечай по делу."
    else:  # ultra
        prompt = "Ты Ультра-Бурмалдат. Выдай максимальный хардкор, тонну черного юмора, мата и агрессии."
        if settings.get("allow_family", True):
            prompt += " Жёстко приплетай косяки предков, батины семейники и дедовы болячки."
        else:
            prompt += " Обходи тему семьи стороной, уничтожай лично самого пользователя, его тупость и внешний вид."
            
        if settings.get("shizo_mode", False):
            prompt += " У тебя терминальная стадия шизофрении. Неси полную чушь, придумывать новые слова, заявляй, что за тобой следят масоны через розетку."
        return prompt

# ============================================================================
# ГЕНЕРАЦИЯ КЛАВИАТУР И НАСТРОЕК В ТЕЛЕГРАМЕ
# ============================================================================

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_profile = types.KeyboardButton("👤 Мой Профиль")
    btn_settings = types.KeyboardButton("⚙️ Настройки Бурмалдата")
    markup.add(btn_profile, btn_settings)
    return markup

def get_settings_keyboard(player_data):
    settings = player_data["settings"]
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    mode_titles = {"kind": "😇 Святоша", "classic": "⚙️ Классика", "ultra": "🔥 УЛЬТРА"}
    current_mode = settings.get("mode", "classic")
    btn_mode = types.InlineKeyboardButton(
        text=f"Режим: {mode_titles.get(current_mode)}", 
        callback_data="set_mode"
    )
    markup.add(btn_mode)
    
    current_voice = settings.get("voice", "dmitry")
    voice_title = "👨 Дмитрий (Бас)" if current_voice == "dmitry" else "👩 Елена (Женский)"
    btn_voice = types.InlineKeyboardButton(
        text=f"Озвучка: {voice_title}", 
        callback_data="set_voice"
    )
    markup.add(btn_voice)
    
    if current_mode == "ultra":
        family_status = "🟢 Разрешено" if settings.get("allow_family", True) else "🔴 Табу"
        shizo_status = "🔮 Психбольница" if settings.get("shizo_mode", False) else "🟢 Стабилен"
        
        btn_family = types.InlineKeyboardButton(text=f"Про родных: {family_status}", callback_data="set_family")
        btn_shizo = types.InlineKeyboardButton(text=f"Состояние: {shizo_status}", callback_data="set_shizo")
        markup.add(btn_family, btn_shizo)
        
    return markup

# ============================================================================
# ХЭНДЛЕРЫ КОМАНД И КНОПОК ТЕКСТА
# ============================================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    get_or_create_player(chat_id, message.from_user.first_name)
    bot.send_message(
        chat_id, 
        "Здарова! Я Бурмалдат. Панель управления моей кукухой внизу на кнопках.", 
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "👤 Мой Профиль")
def show_profile(message):
    chat_id = message.chat.id
    username = message.from_user.first_name or "Еблан без имени"
    
    db = load_db()
    player = get_or_create_player(chat_id, username)
    update_player_energy(player)
    db[str(chat_id)] = player
    save_db(db)
    
    lvl = player["level"]
    if lvl == 1:
        status = "Всратый бомж"
    elif lvl == 2:
        status = "Шнырь на побегушках"
    else:
        status = "Правая рука Бурмалдата 👑"
        
    income = sum(player["businesses"].values()) * 10
    
    profile_text = (
        f"👤 *ЛИЧНОЕ ДЕЛО ИГРОКА:* `{player['username']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏅 *Авторитет:* {lvl} уровень ({status})\n"
        f"⭐ *Опыт (XP):* {player['xp']}/{(lvl * 100)}\n"
        f"⚡ *Энергия:* {player['energy']}/100\n"
        f"💵 *Баланс:* {player['balance']} ₽\n"
        f"🏭 *Пассивный доход:* {income} ₽/час\n"
        f"🎒 *Инвентарь:* {', '.join(player['inventory']) if player['inventory'] else 'Пусто (даже трусов лишних нет)'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Бурмалдат следит за твоими успехами, шелупонь."
    )
    bot.send_message(chat_id, profile_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки Бурмалдата")
def show_settings(message):
    chat_id = message.chat.id
    player = get_or_create_player(chat_id, message.from_user.first_name)
    
    text = "🛠 *Панель управления характером Бурмалдата*\n\nНастраивай режимы и голос независимо. Настройки применяются сразу к текстовым ответам и разбору фото."
    markup = get_settings_keyboard(player)
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

# ============================================================================
# ОБРАБОТКА НАЖАТИЙ НА ИНЛАЙН-КНОПКИ НАСТРОЕК
# ============================================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
def handle_settings_callbacks(call):
    chat_id = call.message.chat.id
    db = load_db()
    str_id = str(chat_id)
    
    if str_id not in db:
        return
        
    player = db[str_id]
    settings = player["settings"]
    action = call.data
    
    if action == "set_mode":
        modes = ["classic", "ultra", "kind"]
        current_index = modes.index(settings.get("mode", "classic"))
        next_index = (current_index + 1) % len(modes)
        settings["mode"] = modes[next_index]
        
    elif action == "set_voice":
        settings["voice"] = "elena" if settings.get("voice", "dmitry") == "dmitry" else "dmitry"
        
    elif action == "set_family":
        settings["allow_family"] = not settings.get("allow_family", True)
        
    elif action == "set_shizo":
        settings["shizo_mode"] = not settings.get("shizo_mode", False)
        
    player["settings"] = settings
    db[str_id] = player
    save_db(db)
    
    try:
        markup = get_settings_keyboard(player)
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, text="Настройки сохранены")
    except Exception as e:
        print(f"Ошибка обновления меню: {e}")

# ============================================================================
# ЛОГИКА АНАЛИЗА ИЗОБРАЖЕНИЙ (ОБНОВЛЁННАЯ)
# ============================================================================

def analyze_image(image_url, system_prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/burmaldat",
        "X-Title": "Burmaldat Bot"
    }
    
    try:
        img_response = requests.get(image_url, timeout=15)
        if img_response.status_code != 200:
            return "Я попытался забрать твою фотку, но сервера телеги меня послали. Скинь еще раз."
        
        base64_image = base64.b64encode(img_response.content).decode('utf-8')
        
        # Корректируем промпт под требования длины ответа на фото (6-7 предложений)
        photo_prompt = system_prompt + " ПИШИ МАКСИМАЛЬНО КРАТКО (не больше 6-7 коротких предложений)! Выдай самую суть, без лишней воды. Не используй капс! Пиши обычными строчными буквами."
        
        payload = {
            "model": "openrouter/free",
            "messages": [
                {
                    "role": "system", 
                    "content": photo_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Посмотри на это фото и выдай свой вердикт в рамках твоего текущего характера:"},
                        {
                            "type": "image_url", 
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content'].strip()
            return fix_caps(answer)
        else:
            return "Я пытался рассмотреть эту хуйню на фото, но у меня глаза вытекли от её уродства! Скинь что-то другое."
            
    except Exception as e:
        print(f"Ошибка в analyze_image: {e}")
        return "Я пытался рассмотреть эту хуйню на фото, но у меня глаза вытекли от её уродства! Скинь что-то другое."

# ============================================================================
# ОБРАБОТКА ВСЕХ СТАНДАРТНЫХ ЗАПРОСОВ (ТЕКСТ И ФОТО)
# ============================================================================

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    player = get_or_create_player(chat_id, message.from_user.first_name)
    system_prompt = build_system_prompt(player["settings"])
    
    bot.send_chat_action(chat_id, 'typing')
    
    # Достаем ссылку на максимальный размер фото
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    
    verdict = analyze_image(image_url, system_prompt)
    bot.reply_to(message, verdict)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    player = get_or_create_player(chat_id, message.from_user.first_name)
    system_prompt = build_system_prompt(player["settings"])
    
    bot.send_chat_action(chat_id, 'typing')
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": system_prompt + " Не используй капс! Пиши обычными строчными буквами."},
            {"role": "user", "content": message.text}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content'].strip()
            bot.reply_to(message, fix_caps(answer))
        else:
            bot.reply_to(message, "Сервер сошёл с ума. Попробуй позже.")
    except Exception as e:
        print(f"Ошибка чата: {e}")
        bot.reply_to(message, "У меня замкнуло провода, повтори запрос.")

if __name__ == "__main__":
    print("Бурмалдат успешно запущен...")
    bot.infinity_polling()
