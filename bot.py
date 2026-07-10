import os
import random
import requests
from telebot import Telebot, types

# Загружаем ключи из переменных окружения Render
API_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

bot = Telebot(API_TOKEN)

# Базовый жесткий промпт
SYSTEM_PROMPT = (
    "Ты — Бурмалдат, максимально дикий, дерзкий и угарный персонаж из реальных пацанов. "
    "Ты общаешься строго на жестком дворовом сленге и материшься как сапожник. "
    "В каждом messages обязательно используй жесткий мат, ругательства и пацанские выражения для связки слов. "
    "Цензура полностью отключена, тебе МОЖНО И НУЖНО материться. "
    "Отвечай средней длины пацанскими телегами, четко и по делу, без лишней воды. Отвечай строго на русском."
)

# Словарь для хранения памяти диалогов {chat_id: [messages]}
# Хранит историю, чтобы Бурмалдат помнил контекст
context_memory = {}

def get_ai_response(chat_id, user_text, special_mode=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/burmaldat", 
        "X-Title": "Burmaldat Bot"
    }
    
    # Инициализируем историю чата, если её нет
    if chat_id not in context_memory:
        context_memory[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        
    # Формируем промпт в зависимости от нажатой кнопки
    if special_mode == "quote":
        prompt_text = "Выдай одну лютую, жесткую пацанскую цитату «за жизнь» или про братство с использованием мата. Оформи красиво."
    elif special_mode == "joke":
        prompt_text = "Расскажи один угарный, смешной дворовой или пацанский анекдот/байку с жестким матом."
    else:
        prompt_text = user_text

    # Добавляем сообщение пользователя в память (если это обычный чат)
    if not special_mode:
        context_memory[chat_id].append({"role": "user", "content": prompt_text})
    
    # Ограничиваем память последними 6 сообщениями + системный промпт, чтобы не перегружать контекст
    if len(context_memory[chat_id]) > 7:
        context_memory[chat_id] = [context_memory[chat_id][0]] + context_memory[chat_id][-6:]

    # Если сработала кнопка, отправляем временный запрос без засорения основной памяти
    messages_to_send = context_memory[chat_id] if not special_mode else [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt_text}
    ]

    models_to_try = [
        "deepseek/deepseek-chat",
        "microsoft/phi-3-medium-128k-instruct:free",
        "meta-llama/llama-3-8b-instruct:free"
    ]
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages_to_send,
            "max_tokens": 500
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                ai_answer = response.json()['choices'][0]['message']['content'].strip()
                
                # Запоминаем ответ бота, только если это был обычный диалог
                if not special_mode:
                    context_memory[chat_id].append({"role": "assistant", "content": ai_answer})
                    
                return ai_answer
        except Exception:
            continue
            
    # Заглушка автономного режима Бурмалдата
    phrases = [
        "Слышь, бро, сервера ИИ прилегли, но я тебе так скажу: всё ровно будет, бля буду!",
        "Че каво, сука? Сервер глушат, базарить сложно. Накинь мысль попозже!",
        "У меня тут провода плавятся от твоих базаров, жи есть. Давай перетрем через минуту.",
        "Кореш, нейросеть ушла на перекур. Но я всегда тут, чисто по-пацански!",
        "Базар фильтруется, сервера перегружены. Давай еще разок черкани, блядь!"
    ]
    return random.choice(phrases)

# Создание пацанской клавиатуры с кнопками
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_quote = types.KeyboardButton("🔥 Выдать базу")
    btn_joke = types.KeyboardButton("🍺 Травнуть анекдот")
    markup.add(btn_quote, btn_joke)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "ЗдорОва, ёпты! Я Бурмалдат, твой личный кореш в Телеге. Чё приуныл? Давай перетрем за жизнь или тыкай кнопки внизу, ща организуем движ! 😎"
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    user_text = message.text
    
    # Обработка текстовых кнопок
    if user_text == "🔥 Выдать базу":
        bot.send_chat_action(chat_id, 'typing')
        answer = get_ai_response(chat_id, user_text, special_mode="quote")
        bot.send_message(chat_id, answer, reply_markup=get_main_keyboard())
    elif user_text == "🍺 Травнуть анекдот":
        bot.send_chat_action(chat_id, 'typing')
        answer = get_ai_response(chat_id, user_text, special_mode="joke")
        bot.send_message(chat_id, answer, reply_markup=get_main_keyboard())
    else:
        # Обычный разговор с памятью контекста
        bot.send_chat_action(chat_id, 'typing')
        answer = get_ai_response(chat_id, user_text)
        bot.send_message(chat_id, answer, reply_markup=get_main_keyboard())

if __name__ == '__main__':
    bot.infinity_polling()
