import logging
import requests
from telegram.ext import Application, MessageHandler, filters
from telegram.ext import CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)
logger = logging.getLogger(__name__)

token = ''


async def start(update, context):
    user = update.effective_user
    await update.message.reply_html(
        rf'Привет {user.mention_html()}! Я бот для взаимодействия с сайтом keepthescore.com.'
        ' Напиши мне /help, и я выведу список доступных команд!')


async def help_command(update, context):
    await update.message.reply_text("Доступные команды: /token <token доски>; ")


async def token_command(update, context):
    token = update.message.text.split()[1]
    response = requests.get(f'https://keepthescore.com/api/{token}/board/')
    if response:
        await update.message.reply_text(f"Ответ сервера: {response.status_code}")


async def echo(update, context):
    await update.message.reply_text(f'это не похоже на команду')


def main():
    application = Application.builder().token('7812730029:AAGXD3aUt-OWdrXa7298BRPoFpqXP-xBaNE').build()
    text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, echo)  # UPD

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("token", token_command))

    application.add_handler(text_handler)
    application.run_polling()


# Запускаем функцию main() в случае запуска скрипта.
if __name__ == '__main__':
    main()
