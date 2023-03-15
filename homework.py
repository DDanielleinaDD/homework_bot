import os
import sys
import logging
from logging import StreamHandler, FileHandler
import requests
import telegram
import time
from http import HTTPStatus
from dotenv import load_dotenv


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG, handlers=[FileHandler('main.log', encoding='utf8'),
                                   StreamHandler(stream=sys.stdout)])
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия api ключей."""
    logging.info('Проверяем необходимые токены для работы приложения')
    return all(tokens)


def send_message(bot, message):
    """Бот отправляет сообщение о состояние д.з."""
    logging.info('Запущена функция отправки статуса д.з. в бот')
    try:
        logging.debug('Сообщение отправлено в бот')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as error:
        logging.error(error)


def get_api_answer(timestamp):
    """Направляем запрос о состоянии дз."""
    logging.info('Отправлен запрос к API Яндекс.Домашка')
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к API: {error}')
    if response.status_code != HTTPStatus.OK:
        logging.error(f'Запрос не удачный.'
                      f'Статус ошибки {response.status_code}')
        raise Exception(f'Ошибка запроса {response.status_code}')
    logging.info(f'Направлен запрос на {ENDPOINT}')
    homework = response.json()
    return homework


def check_response(response):
    """Проверка ответа API на документацию."""
    logging.info('Запущена проверка ответа от API')
    if not response:
        error_message = 'Нет ответа или он пуст!'
        logging.error(error_message)
        raise Exception(error_message)
    if not isinstance(response, dict):
        error_message = 'Ответ не соотвествует ожиданиям'
        logging.error(error_message)
        raise TypeError(error_message)
    if 'homeworks' not in response:
        error_message = 'Отсутсвует необходимый ключ в ответе'
        logging.error(error_message)
        raise Exception(error_message)
    if not isinstance(response.get('homeworks'), list):
        message = 'Формат ответа не соответствует.'
        logging.error(message)
        raise TypeError(message)
    logging.info('Получен корректный ответ API')
    return response['homeworks']


def parse_status(homework):
    """Получаем информацию о статусе работы."""
    logging.info('Извлекаем состояние д.з. из ответа API')
    if 'homework_name' not in homework:
        logging.warning('Название д.з. не найднено!')
    else:
        homework_name = homework.get('homework_name')

    if 'status' not in homework:
        logging.error('Статуса д.з. нет')
    else:
        status_of_homework = homework.get('status')
    if status_of_homework not in HOMEWORK_VERDICTS:
        message = 'Недокументированный статус д.з.'
        logging.error('Недокументированный статус домашней работы')
        raise KeyError(message)
    verdict = HOMEWORK_VERDICTS.get(status_of_homework)
    logging.info('получили информацию о статусе работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info('Запуск бота')
    if not check_tokens():
        logging.critical('Отсутствует необходимые'
                         'токены для работы приложения')
        sys.exit('Отсутствует необходимые'
                 'токены для работы приложения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    VERDICT_GENERAL = None
    while True:
        try:
            current_timestamp = int(time.time())
            response = get_api_answer(timestamp=current_timestamp)
            homework = check_response(response)
            for info in homework:
                message = parse_status(info)
                if message != VERDICT_GENERAL:
                    VERDICT_GENERAL = message
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
