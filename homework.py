import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from expection import MessageNotSendExpection
from settings import (ENDPOINT, HOMEWORK_STATUSES, RETRY_TIME, ONE_MONTH)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO)

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


def send_message(bot, message):
    """Отправляет сообщение."""
    logging.info(f'Новое сообщение {message} готово к отправке')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except MessageNotSendExpection:
        error = 'Ошибка при отправке сообщения'
        raise MessageNotSendExpection(error)
    else:
        logging.info(f'Новое сообщение {message} отправлено')


def get_api_answer(current_timestamp):
    """Запрос к ендпоинту."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.ConnectionError:
        error = (
            f'Error while request:'
            f'endpoint - {ENDPOINT}'
            f'headers - {HEADERS}'
            f'params - {params}'
        )
        raise requests.ConnectionError(error)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    error = f'code API {response.status_code} not equal {HTTPStatus.OK}'
    raise ValueError(error)


def check_response(response):
    """Возвращает список домашних работ."""
    if type(response) != dict:
        error = 'Тип ответа не словарь'
        raise TypeError(error)
    if 'homeworks' not in response:
        error = f'Отсутствует "homeworks" в:{response}'
        raise TypeError(error)
    homework = response['homeworks']
    if type(homework) != list:
        error = 'Тип ответа не список'
        raise TypeError(error)
    if not homework:
        error = 'Список работ пуст'
        raise NameError(error)
    logging.info('Status of homework update')
    return homework[0]


def parse_status(homework):
    """Статус домашней работы."""
    if 'homework_name' not in homework:
        error = f'hw not in API response - {homework}'
        raise KeyError(error)
    if 'status' not in homework:
        error = f'status not in API response - {homework}'
        raise KeyError(error)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        error = f'Status - {homework_status} of work not in s.l'
        f'{HOMEWORK_STATUSES}'
        raise KeyError(error)
    verdict = HOMEWORK_STATUSES.get(homework_status)
    logging.info('New status received')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка переменных окружения."""
    return all(
        [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, HEADERS]
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error = 'нет переменных или как-то так'
        logging.error(error, exc_info=True)
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    status = ''
    while True:
        try:
            current_timestamp = int(
                time.time() - ONE_MONTH
            )
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != status:
                send_message(bot, message)
                status = message
            logging.error(f'Ошибка при запросе к основному API: {error}')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
