import random
import time
import requests
import telegram
from bot_for_logging import setup_tg_logger
from utils import get_dict_for_quiz, check_answer
from redis_db import connect_to_redis
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from environs import Env

bd = connect_to_redis()


def start(update: Update, context: CallbackContext):
    reply_keyboard = [['Новый вопрос', 'Сдаться'], ['Узнать счет']]
    update.message.reply_text('Добро пожаловать в QUIZ игру от Devman',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))


def handle_new_question_request(update: Update, context: CallbackContext):
    quiz_dict = get_dict_for_quiz()
    question = random.choice(list(quiz_dict.keys()))
    answer = quiz_dict[question]
    hash_user_id = f'User_id:{update.message.from_user.id}'
    bd.hset(hash_user_id, mapping={
        'question': question,
        'answer': answer
    })
    update.message.reply_text(question)
    return 'ANSWERING'


def handle_solution_attempt(update: Update, context: CallbackContext):
    message = update.message.text.lower()
    user_id = update.effective_user.id
    if message == 'новый вопрос':
        handle_new_question_request(update, context)
    else:
        correct_answer = bd.hget(f'User_id:{user_id}', 'answer')
        if check_answer(message, correct_answer):
            update.message.reply_text('Правильно! Жмите новый вопрос')
        else:
            update.message.reply_text('Не верно, пробуйте новый вопрос!')


def handle_give_up(update: Update, context: CallbackContext):
    message = update.message.text.lower()
    user_id = update.effective_user.id
    if message == 'сдаться':
        give_up_answer = bd.hget(f'User_id:{user_id}', 'answer')
        update.message.reply_text(f'Правильный ответ: {give_up_answer}')
        handle_new_question_request(update, context)


def main():
    env = Env()
    env.read_env()
    Tg_bot_token = env.str("TELEGRAM_BOT_TOKEN")
    logger_bot_token = env.str("TG_LOG_TOKEN")
    logger_chat_id = env.str("TELEGRAM_CHAT_ID")
    logger_bot = telegram.Bot(token=logger_bot_token)
    logger = setup_tg_logger(logger_bot, logger_chat_id)
    updater = Updater(token=Tg_bot_token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^Новый вопрос$'), handle_new_question_request)],
        states={
            'ANSWERING': [
                MessageHandler(Filters.regex('^Сдаться$'), handle_give_up),
                MessageHandler(Filters.text & ~Filters.command, handle_solution_attempt)
            ]
        },
        fallbacks=[]
    ))

    while True:
        try:
            logger.info("Бот QUIZ Devman запущен...")
            updater.start_polling()
            updater.idle()
        except requests.exceptions.ReadTimeout:
            logger.warning('Повтор запроса')

            continue
        except requests.exceptions.ConnectionError:
            logger.error('Ошибка соединения, повторная попытка через 10 секунд')

            time.sleep(10)
        except telegram.error.TelegramError:
            logger.error('Ошибка Телеграмм, повторная попытка через 10 секунд')

            time.sleep(10)
        except telegram.error.NetworkError:
            logger.error('Ошибка подключения, повторная попытка через 10 сек')

            time.sleep(10)


if __name__ == '__main__':
    main()
