import logging


class TelegramLogsHandler(logging.Handler):

    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


def setup_tg_logger(tg_bot, chat_id):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    tg_handler = TelegramLogsHandler(tg_bot, chat_id)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    tg_handler.setFormatter(formatter)
    logger.addHandler(tg_handler)

    return logger
