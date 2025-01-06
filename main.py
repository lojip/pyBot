import logging
import execjs
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json

# Вопросы и тесты
tasks = [
    {
        "description": "Напишите функцию, которая возвращает сумму двух чисел.",
        "function_name": "sum",
        "tests": [
            {"input": [1, 2], "expected": 3},
            {"input": [5, 5], "expected": 10},
            {"input": [-1, 1], "expected": 0}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает разность двух чисел.",
        "function_name": "subtract",
        "tests": [
            {"input": [3, 2], "expected": 1},
            {"input": [10, 5], "expected": 5},
            {"input": [1, -1], "expected": 2}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает произведение двух чисел.",
        "function_name": "multiply",
        "tests": [
            {"input": [3, 2], "expected": 6},
            {"input": [10, 5], "expected": 50},
            {"input": [1, -1], "expected": -1}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает частное двух чисел.",
        "function_name": "divide",
        "tests": [
            {"input": [6, 2], "expected": 3},
            {"input": [10, 5], "expected": 2},
            {"input": [1, -1], "expected": -1}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает квадрат числа.",
        "function_name": "square",
        "tests": [
            {"input": [2], "expected": 4},
            {"input": [5], "expected": 25},
            {"input": [-1], "expected": 1}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает факториал числа.",
        "function_name": "factorial",
        "tests": [
            {"input": [3], "expected": 6},
            {"input": [5], "expected": 120},
            {"input": [0], "expected": 1}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает true, если число четное, и false в противном случае.",
        "function_name": "isEven",
        "tests": [
            {"input": [2], "expected": True},
            {"input": [5], "expected": False},
            {"input": [0], "expected": True}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает длину строки.",
        "function_name": "stringLength",
        "tests": [
            {"input": ["hello"], "expected": 5},
            {"input": ["world"], "expected": 5},
            {"input": ["!"], "expected": 1}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает строку в верхнем регистре.",
        "function_name": "toUpperCase",
        "tests": [
            {"input": ["hello"], "expected": "HELLO"},
            {"input": ["world"], "expected": "WORLD"},
            {"input": ["!"], "expected": "!"}
        ]
    },
    {
        "description": "Напишите функцию, которая возвращает строку в нижнем регистре.",
        "function_name": "toLowerCase",
        "tests": [
            {"input": ["HELLO"], "expected": "hello"},
            {"input": ["WORLD"], "expected": "world"},
            {"input": ["!"], "expected": "!"}
        ]
    }
]

# Загрузка данных пользователей из файла
try:
    with open('user_data.json', 'r') as f:
        user_data = json.load(f)
except FileNotFoundError:
    user_data = {}

# Сохранение данных пользователей в файл
def save_user_data():
    with open('user_data.json', 'w') as f:
        json.dump(user_data, f)

# Проверка и инициализация данных пользователя
def ensure_user_data(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {"balance": 0, "completed_tasks": []}
    if "completed_tasks" not in user_data[str(user_id)]:
        user_data[str(user_id)]["completed_tasks"] = []

# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user_data(user.id)
    await update.message.reply_text(f'Привет, {user.first_name}! Твой текущий баланс: {user_data[str(user.id)]["balance"]} очков.')
    await show_tasks(update, context)

# Отображение списка задач
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user_data(user.id)
    keyboard = []
    for i, task in enumerate(tasks):
        status = "✅" if task["description"] in user_data[str(user.id)]["completed_tasks"] else "❌"
        keyboard.append([InlineKeyboardButton(f"Задача {i+1} {status}", callback_data=str(i))])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите задачу:', reply_markup=reply_markup)

# Обработка выбора задачи
async def select_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    task_index = int(query.data)
    task = tasks[task_index]
    context.user_data['current_task'] = task
    await query.answer()
    await query.edit_message_text(text=f"{task['description']}\nФункция должна называться: {task['function_name']}")

# Обработка присланного кода
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ensure_user_data(user.id)
    if 'current_task' not in context.user_data:
        await update.message.reply_text('Напиши /task чтобы получить задачу.')
        return

    task = context.user_data['current_task']
    user_code = update.message.text
    function_name = task["function_name"]
    
    try:
        js_context = execjs.compile(user_code)
        if not js_context.eval(f'typeof {function_name} === "function"'):
            await update.message.reply_text('Ошибка: Функция с указанным именем не найдена.')
            return
        
        passed_all_tests = True
        feedback = 'Результаты тестов:\n'
        
        for test in task["tests"]:
            input_data = test["input"]
            expected = test["expected"]
            try:
                result = js_context.call(function_name, *input_data)
                if result != expected:
                    passed_all_tests = False
                    feedback += f'❌ Тест не пройден для входных данных {input_data}: ожидалось {expected}, но получено {result}.\n'
                else:
                    feedback += f'✅ Тест пройден для входных данных {input_data}: ожидалось {expected}, и получено {result}.\n'
            except Exception as e:
                passed_all_tests = False
                error_message = str(e).split(':')[0]  # Извлечение основной сути ошибки
                feedback += f'❌ Ошибка при выполнении теста для входных данных {input_data}: {error_message}.\n'
        
        if passed_all_tests:
            if task["description"] not in user_data[str(user.id)]["completed_tasks"]:
                user_data[str(user.id)]["balance"] += 1
                user_data[str(user.id)]["completed_tasks"].append(task["description"])
                feedback += '\nВсе тесты пройдены! +1 очко.'
                save_user_data()  # Сохранение прогресса после успешного прохождения тестов
            else:
                feedback += '\nВсе тесты пройдены, но ты уже решал эту задачу.'
        else:
            feedback += '\nНекоторые тесты не пройдены. Попробуй снова.'
        
        await update.message.reply_text(feedback)
        await update.message.reply_text(f'Твой текущий баланс: {user_data[str(user.id)]["balance"]} очков.')
        await show_tasks(update, context)
    except execjs.ProgramError as e:
        # Обработка ошибок компиляции и выполнения JavaScript
        error_message = str(e).split('\n')[0]  # Извлечение основной сути ошибки
        await update.message.reply_text(f'Ошибка в коде: {error_message}')
    except Exception as e:
        error_message = str(e).split(':')[0]  # Извлечение основной сути ошибки
        await update.message.reply_text(f'Неизвестная ошибка: {error_message}')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Основная функция для запуска бота
def main() -> None:
    # Токен вашего бота
    token = '8049879839:AAEHvaiFcESu5137D7u2dMdCNsHoWoR5HwY'
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("task", show_tasks))
    application.add_handler(CallbackQueryHandler(select_task))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code))

    application.run_polling()

if __name__ == '__main__':
    main()
