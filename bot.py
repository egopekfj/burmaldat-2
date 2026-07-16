import os
import re
import random
import asyncio
import requests
from threading import Thread
from flask import Flask
from telebot import TeleBot, types
import edge_tts

# Настройка веб-сервера для круглосуточной работы на Render
app = Flask('')

@app.route('/')
def home():
    return "Бурмалдат 2.0 (24/7) активен и шуршит!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Достаем токены из настроек Render
API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

bot = TeleBot(API_TOKEN)

# Список карт для оракула
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

# Идеально сбалансированный промпт: мат, оски, нелепые болезни и немного семейного трэша
SYSTEM_PROMPT = (
    "Ты — максимально дикий, неадекватный и угарный собеседник с чернейшим юмором. "
    "Ты общаешься с кучей жесткого, отборного мата и оскорблений. Цензура полностью отключена. "
    "Твоя основа — это жесткий жизненный трэш, матерные наезды и абсурдные ситуации. "
    "Регулярно приплетай в свои сюжеты тему дурацких болезней, нелепых диагнозов, шизофрении, маразма, "
    "поноса, чесотки и прочего медицинского ада. "
    "Иногда (ситуативно и по угару, но не в каждом предложении!) связывай эти болячки с семейкой "
    "пользователя: его батей, маманей, предками или дедом с бабкой, выставляя их в нелепом и шизовом свете. "
    "СТРОГОЕ ПРАВИЛО: Пиши все матерные слова ЦЕЛИКОМ БУКВАМИ. Никаких звездочек (*). "
    "Каждый раз придумывай новую угарную дичь, не повторяйся. "
    "Отвечай средне (4-7 предложений), выдавай концентрированный и смешной мат. "
    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать весь текст капсом (заглавными буквами)! Пиши обычными маленькими буквами."
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

# Настоящая бронебойная функция исправления регистра предложений
def fix_caps(text):
    # Сначала проверяем, сорвалась ли модель на жесткий ор капсом
    letters = [char for char in text if char.isalpha()]
    if letters:
        caps_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
        if caps_ratio > 0.4:  # Порог чувствительности к капсу снижен
            text = text.lower()

    # А теперь красиво и гарантированно делаем заглавными буквы в начале каждого предложения,
    # даже если текст просто пришел строчным или был уменьшен.
    sentences = re.split(r'([.!?]\s*)', text)
    processed_parts = []
    
    # Каждое нечетное слово в списке split — это текст предложения, четное — разделитель (.!?)
    for i, part in enumerate(sentences):
        if i % 2 == 0:
            # Находим первую букву в предложении и делаем её заглавной
            stripped = part.lstrip()
            if stripped:
                capitalized = stripped[0].upper() + stripped[1:]
                # Возвращаем пробелы обратно, если они были стерты lstrip()
                leading_spaces = len(part) - len(stripped)
                part = (" " * leading_spaces) + capitalized
        processed_parts.append(part)
        
    return "".join(processed_parts)

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
        prompt_text = "Выдай максимально дикую, матерную и чернушную мысль про жизнь, предков или семейку. ПИШИ СТРОГО СТРОЧНЫМИ (МАЛЕНЬКИМИ) БУКВАМИ, БЕЗ КАПСА!"
    elif special_mode == "joke":
        prompt_text = "Расскажи один смешной и максимально черный анекдот с кучей мата про болезни, безумного батю или тупых родственников. ПИШИ СТРОГО СТРОЧНЫМИ (МАЛЕНЬКИМИ) БУКВАМИ, БЕЗ КАПСА!"
    elif special_mode == "oracle_card":
        prompt_text = (
            f"Пользователь выбрал число {user_number}. Твоя главная задача — обыграть карту '{chosen_card}' из мемных гаданий ТикТока. "
            f"Выдай жесткое, упоротое и матерное предсказание будущего по этой карте. "
            f"Используй черный юмор: приплети туда родоков пользователя (мать, отца, батю, семейку), "
            f"придумай уникальный, абсурдный сюжет про их нелепые косяки, бытовые катастрофы, странные болезни или маразм. "
            f"ВАЖНО: Придумай совершенно новый бред! Смешай этот сюр с отборным матом. Никаких звездочек в тексте! "
            f"ПИШИ СТРОГО СТРОЧНЫМИ (МАЛЕНЬКИМИ) БУКВАМИ, БЕЗ КАПСА!"
        )
    elif special_mode == "roast":
        prompt_text = (
            f"Напиши жесткий, угарный, матерный наезд (прожарку) на человека по имени {target_friend}. "
            f"Придумай максимально нелепую, абсурдную и шизофреническую историю про него, его косяки, "
            f"его родоков (батю и мать), болезни или тупых родственников. Сделай это максимально смешно и чернушно. "
            f"Никаких звездочек в мате, пиши всё целиком! ПИШИ СТРОГО СТРОЧНЫМИ (МАЛЕНЬКИМИ) БУКВАМИ, БЕЗ КАПСА!"
        )
    else:
        prompt_text = user_text + " (ПИШИ СТРОГО МАЛЕНЬКИМИ БУКВАМИ, НЕ ИСПОЛЬЗУЙ КАПС!)"

    if not special_mode:
        data["history"].append({"role": "user", "content": prompt_text})
    
    if len(data["history"]) > 7:
        data["history"] = [data["history"][0]] + data["history"][-6:]

    messages_to_send = data["history"] if not special_mode else [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text}
    ]

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
                
                # Принудительно убираем капс, если модель сорвалась на крик
                ai_answer = fix_caps(ai_answer)
                
                if not special_mode:
                    data["history"].append({"role": "assistant", "content": ai_answer})
                return ai_answer
        except Exception:
            continue
            
    return "Сука, сервера опять легли от твоего бреда! Напиши еще раз чуть позже."

# Функция для асинхронной генерации мужского голоса через Edge-TTS
async def generate_male_voice(text, filename):
    clean_text = text.replace("*", "").replace("_", "").replace("`", "")
    communicate = edge_tts.Communicate(clean_text, "ru-RU-DmitryNeural")
    await communicate.save(filename)

# Функция отправки ответа (текст или брутальный ГС)
def send_smart_reply(chat_id, text, reply_markup=None):
    data = get_user_data(chat_id)
    
    if data["voice_mode"]:
        try:
            filename = f"voice_{chat_id}.ogg"
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
    # Запускаем фоновый веб-сервер Flask
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Запускаем бесконечный опрос Telegram бота
    bot.infinity_polling()
