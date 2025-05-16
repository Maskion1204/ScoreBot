import json
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler,
                          MessageHandler, filters)
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# КОНСТАНТЫ
BASE_URL = "https://keepthescore.com/api"
HEADERS = {
    'Content-Type': 'application/json',
    'accept': '*/*'
}

# States для ConversationHandler
(ENTER_TOKEN, MAIN_MENU, ENTER_PLAYER_NAME, SELECT_PLAYER_RENAME, ENTER_NEW_PLAYER_NAME, SELECT_PLAYER_DELETE,
 CONFIRM_DELETE, ENTER_SCORE_CHANGE, SELECT_PLAYER_SCORE, ENTER_BOARD_RENAME) = range(10)

BOT_TOKEN = "7616109982:AAFChljlV3PLVhrthr9vts-3EGbNsHYO1MA"  # ТОКЕН БОТА

# Глобальный словарь для хранения данных пользователя
user_data = {}


def make_api_request(method, endpoint, token, payload=None):
    """Универсальная функция для выполнения API-запросов."""
    url = f"{BASE_URL}/{token}/{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, headers=HEADERS)
        elif method == 'POST':
            response = requests.post(url, data=json.dumps(payload), headers=HEADERS)
        elif method == 'PUT':
            response = requests.put(url, data=json.dumps(payload), headers=HEADERS)
        elif method == 'PATCH':
            response = requests.patch(url, data=json.dumps(payload), headers=HEADERS)
        elif method == 'DELETE':
            response = requests.delete(url, headers=HEADERS)
        else:
            raise ValueError(f"Неизвестный HTTP метод: {method}")

        response.raise_for_status()
        return response.json() if response.text else {}
    except requests.exceptions.RequestException as e:
        print(f"Ошибка API: {e}")
        return None


def get_board_data(token):
    """Получение данных доски по токену."""
    return make_api_request('GET', 'board', token)


def get_players(board_data):
    """Получение списка игроков из данных доски."""
    if board_data and 'players' in board_data and isinstance(board_data['players'], list):
        return board_data['players']
    return None


def print_players(players):
    """Форматированный вывод списка игроков."""
    if not players:
        return "Нет данных об игроках"

    result = "Список игроков:\n"
    for player in players:
        result += f"Имя: {player['name']} Очки: {player['score']}\n"
    return result


def find_player_by_input(players, input_str):
    """Поиск игрока по имени или ID."""
    return [
        player for player in players
        if player['name'] == input_str or str(player['id']) == input_str
    ]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с ботом."""
    await update.message.reply_text("Привет! Я бот для управления досками на keepthescore.com.\n"
                                      "Пожалуйста, введите токен вашей доски:")
    return ENTER_TOKEN


async def enter_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает и сохраняет токен доски."""
    token = update.message.text.strip()
    if not token:
        await update.message.reply_text("Ошибка: Токен не может быть пустым. Попробуйте еще раз /start")
        return ENTER_TOKEN

    user_data[update.message.chat_id] = {'token': token}
    await show_main_menu(update, context)
    return MAIN_MENU


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает главное меню."""
    keyboard = [
        [InlineKeyboardButton("Список игроков", callback_data="list_players"),
         InlineKeyboardButton("Добавить игрока", callback_data="add_player")],
        [InlineKeyboardButton("Редактировать игрока", callback_data="edit_player"),
         InlineKeyboardButton("Редактировать очки", callback_data="edit_scores")],
        [InlineKeyboardButton("Переименовать доску", callback_data="board_rename"),
         InlineKeyboardButton("Сбросить очки", callback_data="reset_all")],
        [InlineKeyboardButton("Удалить игрока", callback_data="delete_player")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("Что вы хотите сделать?", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Что вы хотите сделать?", reply_markup=reply_markup)


async def list_players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выводит список игроков."""
    logger.info("Вызвана функция list_players") # Логируем
    chat_id = update.callback_query.message.chat_id
    token = user_data[chat_id]['token']
    board_data = get_board_data(token)
    if board_data:
        players = get_players(board_data)
        if players:
            player_list = print_players(players)
            await update.callback_query.edit_message_text(text=player_list, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Главное меню", callback_data="main_menu")]]))
            await update.callback_query.answer()  # Добавляем answer()
            logger.info("Успешно выведен список игроков и предложена кнопка 'Главное меню'") # Логируем
        else:
            await update.callback_query.answer("Не удалось получить список игроков")
            logger.warning("Не удалось получить список игроков из board_data") # Логируем
    else:
        await update.callback_query.answer("Не удалось получить данные доски")
        logger.error("Не удалось получить board_data") # Логируем
    return MAIN_MENU


async def add_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает имя нового игрока."""
    await update.callback_query.edit_message_text("Введите имя нового игрока (или 'отмена' для отмены):")
    return ENTER_PLAYER_NAME


async def enter_player_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Добавляет нового игрока."""
    chat_id = update.message.chat_id
    token = user_data[chat_id]['token']
    name = update.message.text.strip()

    if not name or name.lower() == 'отмена':
        await update.message.reply_text("Добавление игрока отменено.")
        await show_main_menu(update, context)
        return MAIN_MENU

    response = make_api_request('POST', 'player', token, {"name": name})
    if response:
        await update.message.reply_text("Игрок успешно создан!")
    else:
        await update.message.reply_text("Не удалось добавить игрока. Попробуйте позже.")
    await show_main_menu(update, context)
    return MAIN_MENU


async def edit_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор игрока для переименования."""
    logger.info("Вызвана функция edit_player") # Log
    chat_id = update.callback_query.message.chat_id
    token = user_data[chat_id]['token']

    board_data = get_board_data(token)
    if not board_data:
        await update.callback_query.answer("Не удалось получить данные доски")
        await show_main_menu(update, context)
        return MAIN_MENU

    players = get_players(board_data)
    if not players:
        await update.callback_query.answer("Не удалось получить список игроков")
        await show_main_menu(update, context)
        return MAIN_MENU

    keyboard = []
    for player in players:
        keyboard.append([InlineKeyboardButton(player['name'], callback_data=f"select_player_rename_{player['id']}")])
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="main_menu")]) # Кнопка Отмена

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Выберите игрока для переименования:", reply_markup=reply_markup)
    await update.callback_query.answer() # Add answer
    return SELECT_PLAYER_RENAME


async def select_player_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает новое имя игрока."""
    logger.info("Вызвана функция select_player_rename") # Log
    player_id = update.callback_query.data.split('_')[-1]
    context.user_data['player_id'] = player_id
    await update.callback_query.edit_message_text("Введите новое имя игрока (или 'отмена' для отмены):")
    await update.callback_query.answer() # Add answer
    return ENTER_NEW_PLAYER_NAME


async def enter_new_player_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Переименовывает игрока."""
    chat_id = update.message.chat_id
    token = user_data[chat_id]['token']
    new_name = update.message.text.strip()
    player_id = context.user_data['player_id']

    if not new_name or new_name.lower() == 'отмена':
        await update.message.reply_text("Переименование игрока отменено.")
        await show_main_menu(update, context)
        return MAIN_MENU

    response = make_api_request('PATCH', f'player/{player_id}', token, {"name": new_name})
    if response:
        await update.message.reply_text("Имя игрока успешно изменено!")
    else:
        await update.message.reply_text("Не удалось изменить имя игрока. Попробуйте позже.")

    await show_main_menu(update, context)
    return MAIN_MENU


async def delete_player(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор игрока для удаления."""
    logger.info("Вызвана функция delete_player")  # Log
    chat_id = update.callback_query.message.chat_id
    token = user_data[chat_id]['token']

    board_data = get_board_data(token)
    if not board_data:
        await update.callback_query.answer("Не удалось получить данные доски")
        await show_main_menu(update, context)
        return MAIN_MENU

    players = get_players(board_data)
    if not players:
        await update.callback_query.answer("Не удалось получить список игроков")
        await show_main_menu(update, context)
        return MAIN_MENU

    keyboard = []
    for player in players:
        keyboard.append([InlineKeyboardButton(player['name'], callback_data=f"confirm_delete_{player['id']}")])
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Выберите игрока для удаления:", reply_markup=reply_markup)
    await update.callback_query.answer() # Важно!
    return SELECT_PLAYER_DELETE


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждает удаление игрока."""
    logger.info("Вызвана функция confirm_delete")  # Log
    player_id = update.callback_query.data.split('_')[-1]
    context.user_data['player_id'] = player_id

    keyboard = [
        [InlineKeyboardButton("Удалить", callback_data=f"delete_player_confirmed"),
         InlineKeyboardButton("Отмена", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Вы уверены, что хотите удалить этого игрока?",
                                                  reply_markup=reply_markup)
    await update.callback_query.answer()  # Важно!
    return CONFIRM_DELETE


async def delete_player_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаляет игрока."""
    chat_id = update.callback_query.message.chat_id
    token = user_data[chat_id]['token']
    player_id = context.user_data['player_id']

    response = make_api_request('DELETE', f'player/{player_id}', token)
    if response:
        await update.callback_query.answer("Игрок успешно удален!")
    else:
        await update.callback_query.answer("Не удалось удалить игрока")

    await show_main_menu(update, context)
    return MAIN_MENU


async def edit_scores(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор игрока для редактирования очков."""
    logger.info("Вызвана функция edit_scores") # Log
    chat_id = update.callback_query.message.chat_id
    token = user_data[chat_id]['token']

    board_data = get_board_data(token)
    if not board_data:
        await update.callback_query.answer("Не удалось получить данные доски")
        await show_main_menu(update, context)
        return MAIN_MENU

    players = get_players(board_data)
    if not players:
        await update.callback_query.answer("Не удалось получить список игроков")
        await show_main_menu(update, context)
        return MAIN_MENU

    keyboard = []
    for player in players:
        keyboard.append([InlineKeyboardButton(player['name'], callback_data=f"select_score_edit_{player['id']}")])
    keyboard.append([InlineKeyboardButton("Отмена", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Выберите игрока, чтобы изменить очки:",
                                                  reply_markup=reply_markup)
    await update.callback_query.answer()  # Важно!
    return SELECT_PLAYER_SCORE


async def select_score_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает изменение очков."""
    logger.info("Вызвана функция select_score_edit") # Log
    player_id = update.callback_query.data.split('_')[-1]
    context.user_data['player_id'] = player_id
    await update.callback_query.edit_message_text("Введите изменение очков (например, +5 или -3, или "
                                                  "'отмена' для отмены):")
    await update.callback_query.answer()  # Важно!
    return ENTER_SCORE_CHANGE


async def enter_score_change(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Изменяет очки игрока."""
    chat_id = update.message.chat_id
    token = user_data[chat_id]['token']
    score_input = update.message.text.strip()
    player_id = context.user_data['player_id']

    if not score_input or score_input.lower() == 'отмена':
        await update.message.reply_text("Изменение очков отменено.")
        await show_main_menu(update, context)
        return MAIN_MENU

    if not score_input.lstrip('-+').isdigit():
        await update.message.reply_text("Очки должны быть целым числом. Используйте + для добавления, - для вычитания.")
        return ENTER_SCORE_CHANGE

    response = make_api_request('POST', 'score', token, {
        "player_id": player_id,
        "score": int(score_input)
    })
    if response:
        await update.message.reply_text("Очки успешно изменены!")
    else:
        await update.message.reply_text("Не удалось изменить очки. Попробуйте позже.")

    await show_main_menu(update, context)
    return MAIN_MENU


async def board_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает новое название доски."""
    chat_id = update.callback_query.message.chat_id
    token = user_data[chat_id]['token']

    board_data = get_board_data(token)
    if not board_data or 'board' not in board_data:
        await update.callback_query.answer("Не удалось получить данные доски")
        await show_main_menu(update, context)
        return MAIN_MENU

    current_title = board_data['board']['appearance']['title']
    await update.callback_query.edit_message_text(f"Текущее название доски: {current_title}\nВведите новое название "
                                                  f"(или 'отмена' для отмены):")
    return ENTER_BOARD_RENAME


async def enter_board_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Переименовывает доску."""
    chat_id = update.message.chat_id
    token = user_data[chat_id]['token']
    new_title = update.message.text.strip()

    if not new_title or new_title.lower() == 'отмена':
        await update.message.reply_text("Переименование доски отменено.")
        await show_main_menu(update, context)
        return MAIN_MENU

    board_data = get_board_data(token)
    if not board_data or 'board' not in board_data:
        await update.message.reply_text("Не удалось получить данные доски.")
        await show_main_menu(update, context)
        return MAIN_MENU

    appearance = board_data['board']['appearance']
    payload = {
        "theme": appearance['theme'],
        "layout": appearance['layout'],
        "sorting": appearance['sorting'],
        "score_format": appearance['score_format'],
        "title": new_title,
        "goal_value": appearance['goal_value']
    }

    response = make_api_request('PUT', 'board', token, payload)
    if response:
        await update.message.reply_text("Название доски успешно изменено!")
    else:
        await update.message.reply_text("Не удалось изменить название доски. Попробуйте позже.")

    await show_main_menu(update, context)
    return MAIN_MENU


async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сбрасывает все очки."""
    logger.info("Вызвана функция reset_all")
    chat_id = update.callback_query.message.chat_id
    token = user_data[chat_id]['token']

    keyboard = [
        [InlineKeyboardButton("Сбросить все очки", callback_data="confirm_reset"),
         InlineKeyboardButton("Отмена", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Вы уверены, что хотите сбросить все очки?",
                                                  reply_markup=reply_markup)
    await update.callback_query.answer()
    return CONFIRM_DELETE


async def confirm_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выполняет сброс очков."""
    logger.info("Вызвана функция confirm_reset")
    chat_id = update.callback_query.message.chat_id
    token = user_data[chat_id]['token']

    response = make_api_request('POST', 'board/reset-scores', token)
    if response:
        await update.callback_query.answer("Все очки успешно обнулены!")  # Отправляем подтверждение
    else:
        await update.callback_query.answer("Не удалось сбросить очки")  # Отправляем подтверждение даже при ошибке

    await show_main_menu(update, context)
    return MAIN_MENU


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возвращает в главное меню."""
    logger.info("Вызвана функция main_menu") # Логируем
    await show_main_menu(update, context)
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущую операцию."""
    await update.message.reply_text("Действие отменено.")
    await show_main_menu(update, context)
    return MAIN_MENU


def main() -> None:
    """Запуск бота."""
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ENTER_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_token)],
            MAIN_MENU: [CallbackQueryHandler(list_players, pattern="^list_players$"),
                        CallbackQueryHandler(add_player, pattern="^add_player$"),
                        CallbackQueryHandler(edit_player, pattern="^edit_player$"),
                        CallbackQueryHandler(delete_player, pattern="^delete_player$"),
                        CallbackQueryHandler(edit_scores, pattern="^edit_scores$"),
                        CallbackQueryHandler(board_rename, pattern="^board_rename$"),
                        CallbackQueryHandler(reset_all, pattern="^reset_all$"),
                        CallbackQueryHandler(main_menu, pattern="^main_menu$")],  # main menu доступен в главном меню
            ENTER_PLAYER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_player_name)],
            SELECT_PLAYER_RENAME: [CallbackQueryHandler(select_player_rename, pattern="^select_player_rename_"),
                                   CallbackQueryHandler(main_menu, pattern="^main_menu$")],  # обработка "Отмена"
            ENTER_NEW_PLAYER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_new_player_name)],
            SELECT_PLAYER_DELETE: [CallbackQueryHandler(delete_player, pattern="^delete_player$"),
                                   CallbackQueryHandler(confirm_delete, pattern="^confirm_delete_"),
                                   CallbackQueryHandler(main_menu, pattern="^main_menu$")],  #
            CONFIRM_DELETE: [CallbackQueryHandler(delete_player_confirmed, pattern="^delete_player_confirmed$"),
                             CallbackQueryHandler(confirm_reset, pattern="^confirm_reset$"),
                             CallbackQueryHandler(main_menu, pattern="^main_menu$")],  # обработка "Отмена"
            SELECT_PLAYER_SCORE: [CallbackQueryHandler(select_score_edit, pattern="^select_score_edit_"),
                                  CallbackQueryHandler(main_menu, pattern="^main_menu$")],  # обработка "Отмена"
            ENTER_SCORE_CHANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_score_change)],
            ENTER_BOARD_RENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_board_rename)],

        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    print("Бот запущен!")
    application.run_polling()


if __name__ == '__main__':
    main()
