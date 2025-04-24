import requests
import time
import telegram
import redis
import random
import vk_api as vk
from environs import Env

from utils import get_question_answer_for_quiz, check_answer

from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from bot_for_logging import setup_tg_logger


def handle_vk_event_start(event, vk_api):
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('Узнать счет', color=VkKeyboardColor.SECONDARY)
    vk_api.messages.send(
        user_id=event.user_id,
        message='Добро пожаловать в QUIZ игру от Devman',
        keyboard=keyboard.get_keyboard(),
        random_id=get_random_id()
    )


def handle_new_question_request(event, vk_api, db, quiz_game: dict):
    question = random.choice(list(quiz_game.keys()))
    answer = quiz_game[question]
    hash_user_id = f'VK_user_id:{event.user_id}'
    db.hset(hash_user_id, mapping={
        'question': question,
        'answer': answer
    })
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=get_random_id()
    )


def handle_solution_attempt(event, vk_api, db):
    message = event.text.lower()
    user_id = event.user_id
    if message == 'Новый вопрос':
        handle_new_question_request(event, vk_api)
    else:
        correct_answer = db.hget(f'VK_user_id:{user_id}', 'answer')
        if check_answer(message, correct_answer):
            vk_api.messages.send(
                user_id=user_id,
                message='Правильно! Жмите новый вопрос',
                random_id=get_random_id()
            )
        else:
            vk_api.messages.send(
                user_id=user_id,
                message='Не правильно, пробуйте снова!',
                random_id=get_random_id()
            )


def handle_give_up(event, vk_api, db):
    user_id = event.user_id
    give_up_answer = db.hget(f'VK_user_id:{user_id}', 'answer')
    vk_api.messages.send(
        user_id=user_id,
        message=f'Правильный ответ: {give_up_answer}',
        random_id=get_random_id()
    )
    handle_new_question_request(event, vk_api, db)


def main():
    env = Env()
    env.read_env()
    logger_bot_token = env.str("TG_LOG_TOKEN")
    logger_chat_id = env.str("TELEGRAM_CHAT_ID")
    db = redis.Redis(
        host=env.str("REDIS_HOST"),
        port=env.int("REDIS_PORT"),
        decode_responses=True,
        username=env.str("REDIS_USERNAME", "default"),
        password=env.str("REDIS_PASSWORD"),
    )
    quiz_game = get_question_answer_for_quiz()
    logger_bot = telegram.Bot(token=logger_bot_token)
    logger = setup_tg_logger(logger_bot, logger_chat_id)
    vk_session = vk.VkApi(token=env.str("VK_GROUP_API_KEY"))
    while True:
        try:
            vk_api = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)
            logger.info('QUIZ бот VK запущен!')
            for event in longpoll.listen():
                if not event.type == VkEventType.MESSAGE_NEW:
                    continue
                if not event.to_me:
                    continue

                if event.text == 'Начать':
                    handle_vk_event_start(event, vk_api)
                    continue

                if event.text == 'Новый вопрос':
                    handle_new_question_request(event, vk_api, db, quiz_game)
                    continue

                if event.text == 'Сдаться':
                    handle_give_up(event, vk_api, db)
                    continue

                handle_solution_attempt(event, vk_api, db)

        except requests.exceptions.ReadTimeout:
            logger.warning('Повтор запроса')
            continue
        except requests.exceptions.ConnectionError:
            logger.error('Ошибка соединения, повторная попытка через 10 секунд')
            time.sleep(10)

        except vk.exceptions.ApiError:
            logger.error('Ошибка API VK !')


if __name__ == '__main__':
    main()
