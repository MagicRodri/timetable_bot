import logging

from telegram.ext import ApplicationBuilder, CommandHandler

from bot import start
from config import TG_TOKEN


def main():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_date_format = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(format=log_format,
                        level=logging.INFO,
                        datefmt=log_date_format)

    app = ApplicationBuilder().token(TG_TOKEN).build()

    start_handler = CommandHandler(command='start', callback=start)

    app.add_handler(start_handler)

    app.run_polling()


if __name__ == '__main__':
    main()