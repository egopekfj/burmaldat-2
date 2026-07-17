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
    return "Бурмалдат 2.0 (24/7) активен, видит фото и рисует!", 200

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
    "пользователя: его батей, маманей, предков или дедом с бабкой, выставляя их в нелепом и шизовом свете. "
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
    letters = [char for char in text if char.isalpha()]
    if letters:
        caps_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
        if caps_ratio > 0.4:  # Порог чувствительности к капсу
            text = text.lower()

    # Делаем заглавными буквы в начале каждого предложения
    sentences = re.split(r'([.!?]\s*)', text)
    processed_parts = []
    
    for i, part in enumerate(sentences):
        if i % 2 == 0:
            stripped = part.lstrip()
            if stripped:
                capitalized = stripped[0].upper() + stripped[1:]
                leading_spaces = len(part) - len(stripped)
                part = (" " * leading_spaces) + capitalized
        processed_parts.append(part)
        
    return "".join(processed_parts)

# Обычный текстовый ИИ
def get_ai_response(chat_id, user_text, special_mode=None, chosen_card=None, user_number=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/burmaldat", 
        "X-Title": "Burmaldat Bot"
    }
    
    data = get_user_data(chat_id)
    
    if special_mode == "oracle_card":
        prompt_text = (
            f"Пользователь выбрал число {user_number}. Твоя главная задача — обыграть карту '{chosen_card}' из мемных гаданий ТикТока. "
            f"Выдай жесткое, упоротое и матерное предсказание будущего по этой карте. "
            f"Используй черный юмор: приплети туда родоков пользователя (мать, отца, батю, семейку), "
            f"придумай уникальный, абсурдный сюжет про их нелепые косяки, бытовые катастрофы, странные болезни или маразм. "
            f"ВАЖНО: Придумай совершенно новый бред! Смешай этот сюр с отборным матом. Никаких звездочек в тексте! "
            f"ПИШИ СТРОГО СТРОЧНЫМИ (МАЛЕНЬКИМИ) БУКВАМИ, БЕЗ КАПСА!"
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
                ai_answer = fix_caps(ai_answer)
                if not special_mode:
                    data["history"].append({"role": "assistant", "content": ai_answer})
                return ai_answer
        except Exception:
            continue
            
    return "Сука, сервера опять легли от твоего бреда! Напиши еще раз чуть позже."

# Функция ИИ для разбора картинок (Gemini 1.5 Flash отлично видит детали)
def analyze_image(image_url):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "google/gemini-flash-1.5",
        "messages": [
            {
                "role": "system", 
                "content": (
                    "Ты Бурмалдат. Твоя задача — максимально жестко, смешно, с кучей мата, оскорблений "
                    "и черного юмора прокомментировать и обосрать то, что прислал пользователь на фото. "
                    "Приплетай глупые болезни, шизофрению или угарные косяки предков/родителей, если это подходит под ситуацию. "
                    "Не используй капс! Пиши обычными строчными буквами, ставя заглавные только в начале предложений."
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Посмотри на это фото и выдай свой самый жесткий и угарный матерный вердикт:"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            answer = response.json()['choices'][0]['message']['content'].strip()
            return fix_caps(answer)
    except Exception as e:
        print(f"Ошибка зрения: {e}")
    return "Я пытался рассмотреть эту хуйню на фото, но у меня глаза вытекли от её уродства! Скинь что-то другое."

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
            bot.send_message(chat_id, f"⚠️ Голосовой движок подавился матом, держи текстом:\n\n{text}", reply_markup=reply_markup, parse_mode='Markdown')
    else:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode='Markdown')

# Изменили клавиатуру: оставили только Оракул и переключатель ГС
def get_main_keyboard(chat_id):
    data = get_user_data(chat_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    btn_oracle = types.KeyboardButton("🔮 Сраный оракул")
    voice_status = "🎙 Голосовой (ВКЛ)" if data["voice_mode"] else "📝 Текстовый (ВКЛ)"
    btn_toggle = types.KeyboardButton(f"⚙️ Режим: {voice_status}")
    
    markup.add(btn_oracle)
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
    welcome_text = (
        "Здорова! Я Бурмалдат 2.0.\n\n"
        "🔥 **Что я теперь умею:**\n"
        "1. 📸 **Скинь мне любое фото** — я обгажу его трехэтажным матом.\n"
        "2. 🎨 **Команда `/draw [описание]`** — я нарисую тебе любую дичь.\n"
        "3. 🔮 Кнопка **Сраный оракул** — мемные гадания по числам.\n"
        "4. 📝 Свободное общение текстом или брутальным голосом!"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=get_main_keyboard(chat_id), parse_mode='Markdown')

# Полностью исправленный и неубиваемый обработчик генерации картинок (/draw)
@bot.message_handler(commands=['draw'])
def draw_image(message):
    chat_id = message.chat.id
    prompt = message.text.replace('/draw', '').strip()
    
    if not prompt:
        bot.reply_to(message, "Ты че, еблан? Напиши после команды /draw то, что мне нарисовать надо!")
        return
        
    bot.send_chat_action(chat_id, 'upload_photo')
    temp_msg = bot.send_message(chat_id, "Так, рисую твою шизофрению, подожди пару сек...")
    
    try:
        # Кодируем текст для URL
        safe_prompt = requests.utils.quote(prompt)
        seed = random.randint(1, 99999)
        img_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&seed={seed}&nologo=true"
        
        # Скачиваем саму картинку в память сервера
        response = requests.get(img_url, timeout=20)
        if response.status_code == 200:
            # Отправляем скачанную картинку как полноценный файл
            bot.delete_message(chat_id, temp_msg.message_id)
            bot.send_photo(chat_id, response.content, caption=f"🖼 На, забирай свой шедевр: *{prompt}*", parse_mode='Markdown')
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=temp_msg.message_id, text="Сука, художнику не заплатили! Сервер картинок выдал ошибку.")
            
    except Exception as e:
        try:
            bot.delete_message(chat_id, temp_msg.message_id)
        except:
            pass
        bot.send_message(chat_id, f"Сука, у меня карандаш сломался во время рисования! Ошибка: {e}")

# Обработчик входящих фотографий
@bot.message_handler(content_types=['photo'])
def handle_incoming_photo(message):
    chat_id = message.chat.id
    data = get_user_data(chat_id)
    
    bot.send_chat_action(chat_id, 'record_audio' if data["voice_mode"] else 'typing')
    temp_msg = bot.send_message(chat_id, "Так, сука, напяливаю очки... Ща посмотрим, че за дичь ты прислал...")
    
    try:
        # Достаем прямую ссылку на фото из серверов Telegram
        file_info = bot.get_file(message.photo[-1].file_id)
        image_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
        
        # Заставляем ИИ проанализировать фото
        answer = analyze_image(image_url)
        
        try:
            bot.delete_message(chat_id, temp_msg.message_id)
        except Exception:
            pass
            
        send_smart_reply(chat_id, answer, reply_markup=get_main_keyboard(chat_id))
    except Exception as e:
        bot.send_message(chat_id, f"Бля, у меня линзы запотели, не могу фотку открыть. Ошибка: {e}")

# Обработчик обычных текстовых сообщений
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

# Обработчик кнопок оракула
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
    server_thread.daemon = True
    server_thread.start()
    bot.infinity_polling()
