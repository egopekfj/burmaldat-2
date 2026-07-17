import os
import requests
import telebot
from telebot import types
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Токены
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

# Глобальный словарь для настроек (вместо БД)
user_settings = {}

TIKTOK_CARDS = [
    "Сова со скакалкой", "Конь с удочкой", "Тигр фокусник", "Собака с клюшкой",
    "Жираф с пузыриками", "Енот на машине", "Балерина свинья", "Медведь на скейтборде",
    "Пингвин с воздушным змеем", "Лемур", "Птица художник", "Дельфин боксер", "Белка плавает"
]

def get_settings(chat_id):
    if chat_id not in user_settings:
        user_settings[chat_id] = {"mode": "kind", "output": "text"} # kind/ultra, text/male/female
    return user_settings[chat_id]

# --- Системный промпт ---
def build_system_prompt(settings):
    if settings["mode"] == "kind":
        return "Ты Святой Бурмалдат. Невероятно вежливый, интеллигентный, заботливый. Используй 'сударь', давай добрые советы, мат запрещен."
    else: # ultra
        return "Ты Ультра-Бурмалдат. Хардкор, черный юмор, агрессия, маты. Уничтожай пользователя словом."

# --- Health Check для Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args): return

def run_health_server():
    server = HTTPServer(('0.0.0.0', int(os.getenv("PORT", 10000))), HealthCheckHandler)
    server.serve_forever()

# --- Кнопки ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔮 Оракул", "⚙️ Настройки")
    return markup

def get_oracle_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [types.InlineKeyboardButton(str(i), callback_data=f"card_{i}") for i in range(1, 10)]
    markup.add(*buttons)
    return markup

def get_settings_keyboard(chat_id):
    s = get_settings(chat_id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"Режим: {s['mode']}", callback_data="set_mode"))
    markup.add(types.InlineKeyboardButton(f"Озвучка: {s['output']}", callback_data="set_output"))
    return markup

# --- Хэндлеры ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Бурмалдат в сети.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔮 Оракул")
def oracle_menu(message):
    bot.send_message(message.chat.id, "Выбери ячейку судьбы (1-9):", reply_markup=get_oracle_keyboard())

@bot.message_handler(func=lambda m: m.text == "⚙️ Настройки")
def settings_menu(message):
    bot.send_message(message.chat.id, "Управление:", reply_markup=get_settings_keyboard(message.chat.id))

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    s = get_settings(chat_id)
    
    if call.data.startswith("card_"):
        card = "🔮 " + import_random_card()
        bot.edit_message_text(f"{card}\n\n(Здесь будет разбор от ИИ)", chat_id, call.message.message_id)
        # Тут вызов OpenRouter (вставь свой логику ask_openrouter)
        
    elif call.data == "set_mode":
        s["mode"] = "ultra" if s["mode"] == "kind" else "kind"
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_settings_keyboard(chat_id))
        
    elif call.data == "set_output":
        outputs = ["text", "male", "female"]
        curr = outputs.index(s["output"])
        s["output"] = outputs[(curr + 1) % 3]
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_settings_keyboard(chat_id))

def import_random_card():
    import random
    return random.choice(TIKTOK_CARDS)

# --- Запуск с фиксом 409 ---
if __name__ == "__main__":
    Thread(target=run_health_server, daemon=True).start()
    while True:
        try:
            bot.delete_webhook()
            bot.infinity_polling(skip_pending=True)
            break
        except Exception as e:
            if "409" in str(e) or "Conflict" in str(e):
                time.sleep(10)
            else:
                time.sleep(5)
