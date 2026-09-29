import datetime
import threading
import os
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ─────────────── ВЕБ-СЕРВЕР ДЛЯ RENDER ───────────────
web_app = Flask(__name__)

@web_app.route('/')
def health():
    return "OK", 200
# ─────────────────────────────────────────────────────

# ─────────────── НАСТРОЙКИ ───────────────
# Токен берётся из переменной окружения Render.
# Локально (на своём ПК) можно вписать напрямую для теста.
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "СЮДА_ВСТАВЬ_СВОЙ_ТОКЕН_ДЛЯ_ЛОКАЛЬНОГО_ТЕСТА")

DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

BTN_TODAY = "📅 На сегодня"
BTN_TOMORROW = "📅 На завтра"
BTN_WEEK = "🗓 На неделю"

# ─────────────── РАСПИСАНИЕ ───────────────
# Формат: (время, предмет, преподаватель)
# 0 — Пн, 1 — Вт, 2 — Ср, 3 — Чт, 4 — Пт, 5 — Сб, 6 — Вс

SCHEDULE_PLUS = {
    0: [  # Понедельник
        ("10:15-11:50", "Современные теории массовой коммуникации", "Бушев"),
        ("12:10-13:45", "Организация и продюсирование телепроизводства и телевещания", "Горобий"),
        ("14:00-15:35", "Теория и практика производства телевизионных программ", "Горобий"),
    ],
    1: [],  # Вторник
    2: [],  # Среда
    3: [],  # Четверг
    4: [  # Пятница
        ("14:00-15:35", "Методика интервью", "Петренко"),
        ("15:55-17:30", "СМИ и PR технологии", "Петренко"),
        ("17:45-19:20", "Психолингвистические особенности создания и восприятия журналистских текстов", "Петренко"),
    ],
    5: [  # Суббота
        ("15:55-17:30", "История отечественного телевидения", "Казанцева"),
    ],
    6: [],  # Воскресенье
}

SCHEDULE_MINUS = {
    0: [],  # Понедельник
    1: [],  # Вторник
    2: [],  # Среда
    3: [],  # Четверг
    4: [],  # Пятница
    5: [  # Суббота
        ("12:10-13:45", "Профессиональная этика тележурналиста", "Иванова"),
        ("14:00-15:35", "Современные медиасистемы", "Казанцева"),
    ],
    6: [],  # Воскресенье
}
# ──────────────────────────────────────────


def get_week_type(date):
    """Определяет тип недели ('+' или '-') относительно 1 сентября.
    
    1 сентября — всегда '-' неделя, дальше чередуются.
    """
    if date.month >= 9:
        semester_start = datetime.date(date.year, 9, 1)
    else:
        semester_start = datetime.date(date.year - 1, 9, 1)
    
    start_monday = semester_start - datetime.timedelta(days=semester_start.weekday())
    current_monday = date - datetime.timedelta(days=date.weekday())
    weeks_passed = (current_monday - start_monday).days // 7
    
    return "-" if weeks_passed % 2 == 0 else "+"


def format_schedule(day_index, week_type, date):
    """Формирует сообщение с расписанием на конкретный день."""
    day_name = DAYS[day_index]
    schedule = SCHEDULE_PLUS if week_type == "+" else SCHEDULE_MINUS
    classes = schedule.get(day_index, [])
    
    week_label = "чётная (+)" if week_type == "+" else "нечётная (−)"
    header = f"📅 {day_name}, {date.strftime('%d.%m.%Y')}\n"
    header += f"Неделя: {week_label}\n\n"
    
    if not classes:
        return header + "Пар нет! 🎉"
    
    result = header
    for i, (time, subject, teacher) in enumerate(classes, 1):
        result += f"{i}. 🕐 {time}\n"
        result += f"   📚 {subject}\n"
        result += f"   👤 {teacher}\n\n"
    
    return result.strip()


def get_keyboard():
    """Создаёт клавиатуру с кнопками."""
    keyboard = [
        [KeyboardButton(BTN_TODAY), KeyboardButton(BTN_TOMORROW)],
        [KeyboardButton(BTN_WEEK)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот группы 14-М. 📺\n\n"
        "Выбери нужный пункт на кнопках ниже 👇",
        reply_markup=get_keyboard()
    )


async def send_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    week_type = get_week_type(now.date())
    text = format_schedule(now.weekday(), week_type, now)
    await update.message.reply_text(text, reply_markup=get_keyboard())


async def send_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date = datetime.datetime.now() + datetime.timedelta(days=1)
    week_type = get_week_type(date.date())
    text = format_schedule(date.weekday(), week_type, date)
    await update.message.reply_text(text, reply_markup=get_keyboard())


async def send_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now()
    week_type = get_week_type(now.date())
    
    monday = now - datetime.timedelta(days=now.weekday())
    week_label = "чётная (+)" if week_type == "+" else "нечётная (−)"
    
    parts = [f"🗓 Расписание на неделю ({week_label})\n"]
    schedule = SCHEDULE_PLUS if week_type == "+" else SCHEDULE_MINUS
    
    for i in range(7):
        day_name = DAYS[i]
        date = monday + datetime.timedelta(days=i)
        classes = schedule.get(i, [])
        
        parts.append(f"━━━ {day_name} ({date.strftime('%d.%m')}) ━━━")
        if not classes:
            parts.append("— пар нет —\n")
        else:
            for time, subject, teacher in classes:
                parts.append(f"🕐 {time} — {subject} ({teacher})")
            parts.append("")
    
    full_text = "\n".join(parts)
    if len(full_text) <= 4096:
        await update.message.reply_text(full_text, reply_markup=get_keyboard())
    else:
        chunk = ""
        for line in parts:
            if len(chunk) + len(line) + 1 > 4000:
                await update.message.reply_text(chunk)
                chunk = ""
            chunk += line + "\n"
        if chunk:
            await update.message.reply_text(chunk)
        await update.message.reply_text("Готово 👆", reply_markup=get_keyboard())


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки клавиатуры."""
    text = update.message.text
    if text == BTN_TODAY:
        await send_today(update, context)
    elif text == BTN_TOMORROW:
        await send_tomorrow(update, context)
    elif text == BTN_WEEK:
        await send_week(update, context)
    else:
        await update.message.reply_text(
            "Не понял команду 🤔 Используй кнопки ниже.",
            reply_markup=get_keyboard()
        )


def run_bot():
    """Запускает Telegram-бота в отдельном потоке."""
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("today", send_today))
    bot_app.add_handler(CommandHandler("tomorrow", send_tomorrow))
    bot_app.add_handler(CommandHandler("week", send_week))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button))
    
    print("Бот запущен...")
    bot_app.run_polling()


if __name__ == '__main__':
    # Запускаем бота в фоновом потоке
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Запускаем веб-сервер для Render
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)