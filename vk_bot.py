import requests
import time
import telegram
import random
import vk_api as vk
from environs import Env

from utils import get_dict_for_quiz, check_answer
from redis_db import connect_to_redis
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from bot_for_logging import setup_tg_logger

db = connect_to_redis()


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


def handle_new_question_request(event, vk_api):
    quiz_dict = get_dict_for_quiz()
    question = random.choice(list(quiz_dict.keys()))
    answer = quiz_dict[question]
    hash_user_id = f'User_id:{event.user_id}'
    db.hset(hash_user_id, mapping={
        'question': question,
        'answer': answer
    })
    vk_api.messages.send(
        user_id=event.user_id,
        message=question,
        random_id=get_random_id()
    )


def handle_solution_attempt(event, vk_api):
    message = event.text.lower()
    user_id = event.user_id
    if message == 'Новый вопрос':
        handle_new_question_request(event, vk_api)
    else:
        correct_answer = db.hget(f'User_id:{user_id}', 'answer')
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


def handle_give_up(event, vk_api):
    user_id = event.user_id
    give_up_answer = db.hget(f'User_id:{user_id}', 'answer')
    vk_api.messages.send(
        user_id=user_id,
        message=f'Правильный ответ: {give_up_answer}',
        random_id=get_random_id()
    )
    handle_new_question_request(event, vk_api)


def main():
    env = Env()
    env.read_env()
    logger_bot_token = env.str("TG_LOG_TOKEN")
    logger_chat_id = env.str("TELEGRAM_CHAT_ID")
    logger_bot = telegram.Bot(token=logger_bot_token)
    logger = setup_tg_logger(logger_bot, logger_chat_id)
    vk_session = vk.VkApi(token=env.str("VK_GROUP_API_KEY"))
    while True:
        try:
            vk_api = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)
            logger.info('QUIZ бот VK запущен!')
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    if event.text == 'Начать':
                        handle_vk_event_start(event, vk_api)
                    elif event.text == 'Новый вопрос':
                        handle_new_question_request(event, vk_api)
                    elif event.text == 'Сдаться':
                        handle_give_up(event, vk_api)
                    else:
                        handle_solution_attempt(event, vk_api)
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
