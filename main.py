import os
from dataclasses import dataclass, field
from typing import Dict, List, Set

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, ApplicationBuilder, CallbackQueryHandler,
                          CommandHandler, ContextTypes)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set. Define it in your .env file.")

app = FastAPI(title="Volvo XC40 Quiz Bot")


@dataclass
class UserState:
    score: int = 0
    pending_questions: List[int] = field(default_factory=list)
    incorrect_questions: Set[int] = field(default_factory=set)
    milestones_sent: Set[int] = field(default_factory=set)
    started: bool = False
    awaiting_intro_ack: bool = False


QUESTIONS = [
    {
        "prompt": "Какой объём двигателя у твоего Volvo XC40?",
        "options": ["1 л", "2 л", "3 л", "4 л"],
        "correct": 1,
    },
    {
        "prompt": "Сколько лошадиных сил у двигателя в твоем XC40?",
        "options": ["90", "190", "290", "390"],
        "correct": 1,
    },
    {
        "prompt": "Какой тип привода у твоего автомобиля?",
        "options": ["Передний", "Задний", "Полный", "Не знаю"],
        "correct": 2,
    },
    {
        "prompt": "Разгон 0–100 км/ч у твоей машинки составляет:",
        "options": ["4,0 с", "8,5 с", "14 с", "20.5 с"],
        "correct": 1,
    },
    {
        "prompt": "Какой средний расход топлива?",
        "options": ["4,2 л/100 км", "6,9 л/100 км", "14,8 л/100 км", "24,8 л/100 км"],
        "correct": 1,
    },
    {
        "prompt": "Какой тип двигателя?",
        "options": ["Дизель", "Гибрид", "Бензиновый", "Электрический"],
        "correct": 2,
    },
    {
        "prompt": "Какой тип коробки передач используется?",
        "options": ["Робот", "Механика", "Вариатор", "Автомат"],
        "correct": 3,
    },
    {
        "prompt": "Какой клиренс (дорожный просвет) у XC40?",
        "options": ["140 мм", "201 мм", "240 мм", "320 мм"],
        "correct": 1,
    },
    {
        "prompt": "Какой минимальный бензин надо заливать:",
        "options": ["86", "92", "95", "Дизель"],
        "correct": 2,
    },
    {
        "prompt": "Какая страна является «родиной» бренда Volvo?",
        "options": ["Швеция", "Дания", "Норвегия", "Швейцария"],
        "correct": 0,
    },
    {
        "prompt": "Кузов?",
        "options": ["Седан", "Купе", "Внедорожник", "Пикап"],
        "correct": 2,
    },
    {
        "prompt": "Вольво считается каким классом?",
        "options": ["Эконом", "Комфорт", "Комфорт+", "Премиум"],
        "correct": 3,
    },
    {
        "prompt": "Какое важнейшее изобретение было создано инженером Volvo в 1959 году?",
        "options": ["ABS", "Трёхточечный ремень безопасности", "Подушка безопасности", "Зона программируемой деформации"],
        "correct": 1,
    },
    {
        "prompt": "Автомобиль какого бренда первым в мире получил максимальный рейтинг безопасности по EuroNCAP?",
        "options": ["Mercedes-Benz", "Volvo", "Toyota", "BMW"],
        "correct": 1,
    },
    {
        "prompt": "Что означает, когда водитель моргает дальним на перекрёстке?",
        "options": ["Хочет проехать первым", "Даёт вам дорогу", "Предупреждает о пробке", "Показывает, что он зол"],
        "correct": 1,
    },
    {
        "prompt": "Если сзади едет машина и несколько раз моргает дальним светом — это чаще всего:",
        "options": ["Водитель скучает", "Просьба уступить полосу", "Просьба о помощи", "Обратный отсчёт"],
        "correct": 1,
    },
    {
        "prompt": "Как Volvo относится к максимальной скорости автомобилей?",
        "options": ["Ограничивает её на уровне 180 км/ч для безопасности", "Никак не ограничивает", "Даёт регулировку в настройках", "Ограничивает её на уровне 250 км/ч"],
        "correct": 0,
    },
    {
        "prompt": "Что делает система Pilot Assist?",
        "options": ["Полностью автономно ведёт машину", "Удерживает скорость и дистанцию + помогает удерживать полосу", "Управляет движением по пересечённой местности", "Помогает парковаться"],
        "correct": 1,
    },
    {
        "prompt": "Что делает система Auto Hold?",
        "options": ["Удерживает машину на месте при остановке", "Повышает мощность двигателя", "Включает автодоводчики дверей", "Удерживает скорость на трассе"],
        "correct": 0,
    },
    {
        "prompt": "Какой факт о Volvo НЕ является правдой?",
        "options": ["Компания делает собственные манекены для краш-тестов детей", "Volvo первой сделала встроенные детские сиденья", "Volvo изобрела подогрев сидений", "Volvo первой в мире поставила кондиционер"],
        "correct": 3,
    },
    {
        "prompt": "Что считается самым частым отвлекающим фактором для водителей?",
        "options": ["Радио", "Телефон", "Открытое окно", "Солнцезащитные очки"],
        "correct": 1,
    },
    {
        "prompt": "Какой тип усилителя руля установлен?",
        "options": ["Гидравлический", "Никакой", "Электрический", "Вакуумный"],
        "correct": 2,
    },
    {
        "prompt": "Где находится рычаг открывания капота?",
        "options": ["Под рулевой колонкой", "Под передним пассажиром", "Там где ручник", "На мультимедия экране"],
        "correct": 0,
    },
    {
        "prompt": "Какова длина XC40?",
        "options": ["4 м", "4.4 м", "5 м", "6 м"],
        "correct": 1,
    },
    {
        "prompt": "Что означает, когда водитель после обгона кратко мигает аварийкой?",
        "options": ["Просит проехать первым", "Благодарит за то, что его пропустили", "Просит уступить дорогу", "Сообщает об аварии"],
        "correct": 1,
    },
    {
        "prompt": "Что обычно означает короткое мигание дальним светом встречной машины?",
        "options": ["Ты ему понравилась - хочет номерок", "Сообщает о том, что у тебя с машиной что-то не так", "Впереди стоит ДПС/камера", "Он хочет тебя ослепить"],
        "correct": 2,
    },
]

SAFETY_TIPS = [
    "Всегда держи дистанцию — она спасает больше, чем тормоза.",
    "Не спеши — безопасность всегда важнее скорости.",
    "Чистые зеркала = залог безопасных маневров",
    "Если сомневаешься — не делай манёвр.",
    "Смотри на три шага вперёд, а не только перед капотом.",
    "Помни от дедовском важном правиле трех Д - дай дорогу дураку.",
    "Плавный разгон, плавный тормоз — и машина, и дети скажут спасибо.",
    "Уставший водитель — как телефон на 5%: вроде работает, но риски большие.",
    "Всегда думай за двоих — за себя и за того, кто рядом.",
    "Не забывай: лучший водитель — спокойный водитель.",
]

PARKING_TIPS = [
    "Паркуйся так, чтобы выезжать было проще, чем заезжать.",
    "Если сомневаешься — используй камеры и зеркала одновременно.",
    "Медленно — значит правильно. Быстро — значит дорого.",
    "Не бойся перепарковаться — это сила, а не слабость.",
    "Чем ближе к бордюру — тем меньше шанс, что кто-то обдерёт.",
    "Всегда сначала смотри заднюю камеру, потом в зеркала.",
    "Парковка задом почти всегда проще, чем носом.",
    "Ставь машину чуть правее — дверям будет легче открываться.",
    "Если рядом дорогая машина — оставь себе больше пространства.",
    "Главное правило парковки: не спешить. Вообще.",
]

INSPIRATION = [
    "Ты управляешь машиной уверенно — и с каждым километром всё лучше.",
    "Никто не рождается водителем. Все становятся. И ты — уже стала.",
    "Спокойствие — твоя суперспособность за рулём.",
    "Твоя машина доверяет тебе. Доверяй и ты себе.",
    "Ты управляешь XC40, а не страх управляет тобой.",
    "Главная сила — в плавности и уверенности. У тебя это есть.",
    "Каждая поездка делает тебя ещё более опытной.",
    "Ты — отличный водитель. Машина это чувствует.",
    "Дорога любит тех, кто не спешит и не нервничает.",
    "Ты — за рулём. А значит, всё под контролем.",
]

user_states: Dict[int, UserState] = {}
telegram_app: Application


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    state = user_states.setdefault(chat_id, UserState())
    state.started = True
    state.awaiting_intro_ack = True
    intro_text = (
        "Привет! Я твой тайный санта и я знаю, что у тебя недавно появилась машинка. "
        "Я подготовил для тебя интересные вопросы. 1 правильный ответ дает тебе 1 балл. "
        "После 5 набранных баллов ты получишь топ советов по безопасности для водителя. "
        "После 10 набранных баллов ты получишь топ лайфхаков по парковке. "
        "После 15 набранных баллов ты получишь топ вдохновляющих фраз для уверенности на дороге и главный приз."
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=intro_text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Поехали", callback_data="intro")]]
        ),
    )


async def handle_intro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    chat_id = query.message.chat_id
    state = user_states.setdefault(chat_id, UserState())
    if state.score >= 15:
        return
    state.awaiting_intro_ack = False
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "Автомобильный квест: “Мой новый друг”.\n\n"
            "Внимание! Не бойся ошибиться, при ошибке бот покажет верный ответ, а ты постарайся его запомнить, "
            "ведь возможно получишь этот вопрос повторно, чтобы добрать необходимые 15 баллов."
        ),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Поехали", callback_data="start_quiz")]]
        ),
    )


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    chat_id = query.message.chat_id
    state = user_states.setdefault(chat_id, UserState())
    if state.score >= 15:
        return
    if not state.pending_questions:
        state.pending_questions = list(range(len(QUESTIONS)))
    await send_next_question(chat_id, state, context)


def build_question_markup(question_index: int) -> InlineKeyboardMarkup:
    buttons = []
    letters = ["A", "B", "C", "D"]
    for idx, letter in enumerate(letters):
        buttons.append(
            [InlineKeyboardButton(text=letter, callback_data=f"q:{question_index}:{idx}")]
        )
    return InlineKeyboardMarkup(buttons)


async def send_next_question(chat_id: int, state: UserState, context: ContextTypes.DEFAULT_TYPE) -> None:
    if state.score >= 15:
        return
    if not state.pending_questions and state.score < 15:
        if state.incorrect_questions:
            state.pending_questions = list(state.incorrect_questions)
        else:
            return
    if not state.pending_questions:
        return
    q_index = state.pending_questions.pop(0)
    question = QUESTIONS[q_index]
    question_text = f"Вопрос {q_index + 1}/{len(QUESTIONS)}\n{question['prompt']}\n\n"
    letters = ["A", "B", "C", "D"]
    for idx, option in enumerate(question["options"]):
        question_text += f"{letters[idx]}) {option}\n"
    await context.bot.send_message(
        chat_id=chat_id,
        text=question_text,
        reply_markup=build_question_markup(q_index),
    )


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    data_parts = query.data.split(":")
    if len(data_parts) != 3 or data_parts[0] != "q":
        return
    await query.answer()
    chat_id = query.message.chat_id
    q_index = int(data_parts[1])
    chosen = int(data_parts[2])
    state = user_states.setdefault(chat_id, UserState())

    question = QUESTIONS[q_index]
    correct = question["correct"]
    letters = ["A", "B", "C", "D"]
    if chosen == correct:
        state.score += 1
        state.incorrect_questions.discard(q_index)
        feedback = (
            f"Верно! Ты набрала {state.score} баллов."
        )
    else:
        state.incorrect_questions.add(q_index)
        feedback = (
            f"Упс, правильный ответ: {letters[correct]}) {question['options'][correct]}. "
            f"Твой счёт: {state.score}."
        )
    await context.bot.send_message(chat_id=chat_id, text=feedback)

    await send_milestone_if_needed(chat_id, state, context)

    if state.score >= 15:
        await send_inspiration(chat_id, context)
        return

    await send_next_question(chat_id, state, context)


async def send_milestone_if_needed(chat_id: int, state: UserState, context: ContextTypes.DEFAULT_TYPE) -> None:
    if state.score >= 5 and 5 not in state.milestones_sent:
        tips = "\n\n".join(f"• {tip}" for tip in SAFETY_TIPS)
        await context.bot.send_message(chat_id=chat_id, text=f"Советы по безопасности\n{tips}")
        state.milestones_sent.add(5)
    if state.score >= 10 and 10 not in state.milestones_sent:
        tips = "\n\n".join(f"• {tip}" for tip in PARKING_TIPS)
        await context.bot.send_message(chat_id=chat_id, text=f"🅿️ Лайфхаки по парковке\n{tips}")
        state.milestones_sent.add(10)


async def send_inspiration(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = "\n\n".join(f"• {text}" for text in INSPIRATION)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🌟 Вдохновляющие фразы для уверенности на дороге\n"
            f"{lines}\n\nТы собрала 15 баллов — квест завершён!"
        ),
    )


def create_bot_application() -> Application:
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_intro, pattern="^intro$"))
    application.add_handler(CallbackQueryHandler(start_quiz, pattern="^start_quiz$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^q:"))
    return application


telegram_app = create_bot_application()


@app.on_event("startup")
async def on_startup() -> None:
    await telegram_app.initialize()
    await telegram_app.start()
    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(url=WEBHOOK_URL)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return JSONResponse({"ok": True})


@app.get("/")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
