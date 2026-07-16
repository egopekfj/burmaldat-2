import os
import random
import asyncio
import requests
from threading import Thread
from flask import Flask
from telebot import TeleBot, types
import edge_tts

# Микро-сервер для удержания Render в онлайне
app = Flask('')

@app.route('/')
def home():
    return "Бурмалдат 2.0 (Мужской Голос) в сети!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Достаем токены из настроек Render
API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

bot = TeleBot(API_TOKEN)

# Список карт
TIKTOK_CARDS = [
    "Сова со скакалкой",
    "Конь с удочкой",
    "Тигр фокусник",
    "Собака с клюшкой",
    "Жираф с пузыриками",
    "Енот на машине",
    "Балерина свинья",
    "Медведь на скейтборде",
    "Пингвин с воздушным змеем",
    "Лемур",
    "Птица художник",
    "Дельфин боксер",
    "Белка плавает"
]

# Системный промпт
SYSTEM_PROMPT = (
    "Ты — максимально дикий, угарный и неадекватный собеседник с чернейшим чувством юмора. "
    "Ты общаешься с кучей жесткого мата. Цензура полностью отключена. "
    "Шути самый жесткий черный юмор про семью, родственников, внезапные болезни, маразм и абсурдные ситуации. "
    "СТРОГОЕ ПРАВИЛО: Пиши все матерные слова ЦЕЛИКОМ БУКВАМИ. Никаких звездочек. "
    "КАЖДЫЙ раз придумывай абсолютно НОВУЮ, уникальную шизофреническую ситуацию. "
    "Не повторяй одни и те же темы. Будь максимально непредсказуемым! "
    "ОТВЕЧАЙ СРЕДНЕ (примерно 4-7 предложений), выдавай концентрированный и проработанный трэш. "
    "НЕ пиши текст КАПСОМ. НЕ используй символы звезд '**'. Пиши чистым текстом."
)

# Хранилище контекста и настроек пользователей
user_settings = {}

def get_user_data(chat_id):
    if chat_id not in user_settings:
        user_settings[chat_id] = {
            "history": [{"role": "system", "content": SYSTEM_PROMPT}],
            "voice_mode": False  # По умолчанию текстовый режим
        }
    return user_settings[chat_id]

def get_ai_response(chat_id, user_text, special_mode=None, chosen_card=None, user_number=None, target_friend=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/burmaldat", 
        "X-Title": "Burmaldat Bot"
    }
    
    data = get_user_data(chat_id)
    
    if special_mode == "quote":
        prompt_text = "Выдай максимально дикую, матерную и чернушную мысль про жизнь или родственников."
    elif special_mode == "joke":
        prompt_text = "Расскажи один смешной и максимально черный анекдот с кучей мата про болезни или безумную родню."
    elif special_mode == "oracle_card":
        prompt_text = (
            f"Пользователь выбрал число {user_number}. Твоя главная задача — обыграть карту '{chosen_card}' из мемных гаданий ТикТока. "
            f"НЕ ПИШИ КАПСОМ. Выдай жесткое, упоротое и матерное предсказание будущего по этой карте. "
            f"Используй черный юмор: приплети туда семью пользователя, придумай уникальный, абсурдный сюжет "
            f"про их родственников, внезапные странные болезни, нелепые бытовые катастрофы или маразм. "
            f"ВАЖНО: Придумай совершенно новый бред, забудь про дурку и больницы, если писал про них в прошлый раз! "
            f"Смешай этот сюр с отборным матом. Никаких звездочек в тексте!"
        )
    elif special_mode == "roast":
        prompt_text = (
            f"Напиши жесткий, угарный, матерный наезд (прожарку) на человека по имени {target_friend}. "
            f"Придумай максимально нелепую, абсурдную и шизофреническую историю про него, его косяки, "
            f"странные увлечения или родственников. Сделай это максимально смешно и чернушно. "
            f"Никаких звездочек в мате, пиши всё целиком! Не пиши капсом."
        )
    else:
        prompt_text = user_text

    if not special_mode:
        data["history"].append({"role": "user", "content": prompt_text})
    
    if len(data["history"]) > 7:
        data["history"] = [data["history"][0]] + data["history"][-6:]

    messages_to_send = data["history"] if not special_mode else [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text}
    ]

    # Модели с минимальной цензурой
    models_to_try = [
        "meta-llama/llama-3-8b-instruct:nitro",
        "deepseek/deepseek-chat",
        "gryphe/mythomax-l2-13b:free"
    ]
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages_to_send,
            "max_tokens": 400
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                ai_answer = response.json()['choices'][0]['message']['content'].strip()
                if not special_mode:
                    data["history"].append({"role": "assistant", "content": ai_answer})
                return ai_answer
        except Exception:
            continue
            
    return "Сука, сервера опять легли от твоего бреда! Напиши еще раз чуть позже."

# Функция для асинхронной генерации мужского голоса через Edge-TTS
async def generate_male_voice(text, filename):
    # Очищаем текст от символов разметки
    clean_text = text.replace("*", "").replace("_", "").replace("`", "")
    # Используем крутой мужской голос Дмитрий (ru-RU-DmitryNeural)
    communicate = edge_tts.Communicate(clean_text, "ru-RU-DmitryNeural")
    await communicate.save(filename)

# Функция отправки ответа (текст или брутальный ГС)
def send_smart_reply(chat_id, text, reply_markup=None):
    data = get_user_data(chat_id)
    
    if data["voice_mode"]:
        try:
            filename = f"voice_{chat_id}.ogg"
            # Запускаем асинхронную генерацию внутри синхронного кода Telebot
            asyncio.run(generate_male_voice(text, filename))
            
            with open(filename, 'rb') as voice:
                bot.send_voice(chat_id, voice, reply_markup=reply_markup)
                
            os.remove(filename)
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ Облачный голос сломался (ошибка: {e}), держи текстом:\n\n{text}", reply_markup=reply_markup, parse_mode='Markdown')
    else:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode='Markdown')

def get_main_keyboard(chat_id):
    data = get_user_data(chat_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    btn_quote = types.KeyboardButton("🔥 Выдать базу")
    btn_joke = types.KeyboardButton("🍺 Травнуть анекдот")
    btn_oracle = types.KeyboardButton("🔮 Сраный оракул")
    btn_roast = types.KeyboardButton("🎯 Наехать на кореша")
    
    voice_status = "🎙 Голосовой (ВКЛ)" if data["voice_mode"] else "📝 Текстовый (ВКЛ)"
    btn_toggle = types.KeyboardButton(f"⚙️ Режим: {voice_status}")
    
    markup.add(btn_quote, btn_joke)
    markup.add(btn_oracle, btn_roast)
    markup.add(btn_toggle)
    return markup

def get_numbers_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(text=str(i), callback_data=f"num_{i}") for i in range(1, 10)]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    welcome_text = "Здорова! Я твой обновленный Бурмалдат 2.0. Теперь я базарю брутальным мужским голосом! 😈"
    bot.send_message(chat_id, welcome_text, reply_markup=get_main_keyboard(chat_id), parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    user_text = message.text
    data = get_user_data(chat_id)
    
    if user_text.startswith("⚙️ Режим:"):
        data["voice_mode"] = not data["voice_mode"]
        status_text = "Голосовой (Мужской) 🎙" if data["voice_mode"] else "Текстовый 📝"
        bot.send_message(
            chat_id, 
            f"Принял! Теперь я буду вещать в режиме: *{status_text}*", 
            reply_markup=get_main_keyboard(chat_id), 
            parse_mode='Markdown'
        )
        
    elif user_text == "🔥 Выдать базу":
        bot.send_chat_action(chat_id, 'record_audio' if data["voice_mode"] else 'typing')
        answer = get_ai_response(chat_id, user_text, special_mode="quote")
        send_smart_reply(chat_id, answer, reply_markup=get_main_keyboard(chat_id))
        
    elif user_text == "🍺 Травнуть анекдот":
        bot.send_chat_action(chat_id, 'record_audio' if data["voice_mode"] else 'typing')
        answer = get_ai_response(chat_id, user_text, special_mode="joke")
        send_smart_reply(chat_id, answer, reply_markup=get_main_keyboard(chat_id))
        
    elif user_text == "🎯 Наехать на кореша":
        msg = bot.send_message(
            chat_id, 
            "Так, сука, пиши имя этого черта, ща мы его прожарим!", 
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_friend_roast)
        
    elif user_text == "🔮 Сраный оракул":
        bot.send_message(
            chat_id, 
            "Так, блядь, настрой ментальную связь с космосом и ТЫКАЙ на любое число ниже, ща разложу карты!", 
            reply_markup=get_numbers_keyboard()
        )
        
    else:
        bot.send_chat_action(chat_id, 'record_audio' if data["voice_mode"] else 'typing')
        answer = get_ai_response(chat_id, user_text)
        send_smart_reply(chat_id, answer, reply_markup=get_main_keyboard(chat_id))

def process_friend_roast(message):
    chat_id = message.chat.id
    friend_name = message.text
    data = get_user_data(chat_id)
    
    temp_msg = bot.send_message(chat_id, f"Собираю компромат на {friend_name}... Ща будет разъеб...")
    bot.send_chat_action(chat_id, 'record_audio' if data["voice_mode"] else 'typing')
    
    answer = get_ai_response(chat_id, user_text=friend_name, special_mode="roast", target_friend=friend_name)
    
    try:
        bot.delete_message(chat_id, temp_msg.message_id)
    except Exception:
        pass
        
    final_text = f"🔥 *Прожарка для {friend_name}:*\n\n{answer}"
    send_smart_reply(chat_id, final_text, reply_markup=get_main_keyboard(chat_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('num_'))
def handle_number_click(call):
    chat_id = call.message.chat.id
    user_num = call.data.split('_')[1]
    data = get_user_data(chat_id)
    
    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"Принял число {user_num}... Тасую колоду, сука..."
        )
    except Exception:
        pass
        
    bot.send_chat_action(chat_id, 'record_audio' if data["voice_mode"] else 'typing')
    
    random_card = random.choice(TIKTOK_CARDS)
    answer = get_ai_response(chat_id, user_text=user_num, special_mode="oracle_card", chosen_card=random_card, user_number=user_num)
    
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        pass
        
    final_text = f"🃏 *Итак, сука, тебе выпала карта: {random_card}!*\n\n{answer}"
    send_smart_reply(chat_id, final_text, reply_markup=get_main_keyboard(chat_id))

if __name__ == '__main__':
    server_thread = Thread(target=run_web_server)
    server_thread.start()
    bot.infinity_polling()
