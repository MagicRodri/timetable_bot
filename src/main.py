import logging

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot import (
    day_input,
    day_input_callback,
    group_input,
    group_input_callback,
    help,
    language,
    language_choice_callback,
    semester_choice,
    semester_choice_callback,
    start,
    teacher_input,
    teacher_input_callback,
    unknown,
)
from config import DEBUG, TG_TOKEN


def main():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_date_format = '%Y-%m-%d %H:%M:%S'
    level = logging.INFO
    log_file = 'bot.log' if not DEBUG else None
    logging.basicConfig(format=log_format,
                        level=level,
                        datefmt=log_date_format,
                        filename=log_file)

    app = ApplicationBuilder().token(TG_TOKEN).build()

    start_handler = CommandHandler(command='start', callback=start)
    semester_handler = CommandHandler(command='semester',
                                      callback=semester_choice)
    semester_callback_handler = CallbackQueryHandler(
        callback=semester_choice_callback)
    group_input_handler = CommandHandler(command='group', callback=group_input)
    group_input_callback_handler = CallbackQueryHandler(
        callback=group_input_callback)
    teacher_input_handler = CommandHandler(command='teacher',
                                           callback=teacher_input)
    teacher_input_callback_handler = CallbackQueryHandler(
        callback=teacher_input_callback)
    day_input_handler = CommandHandler(command='day', callback=day_input)
    day_input_callback_handler = CallbackQueryHandler(
        callback=day_input_callback)
    language_handler = CommandHandler(command='language', callback=language)
    language_callback_handler = CallbackQueryHandler(
        callback=language_choice_callback)
    help_handler = CommandHandler(command='help', callback=help)
    unknown_handler = MessageHandler(filters=filters.COMMAND | filters.TEXT,
                                     callback=unknown)

    app.add_handler(start_handler)
    app.add_handler(semester_handler)
    app.add_handler(semester_callback_handler, group=2)
    app.add_handler(group_input_handler)
    app.add_handler(group_input_callback_handler, group=1)
    app.add_handler(teacher_input_handler)
    app.add_handler(teacher_input_callback_handler, group=0)
    app.add_handler(day_input_handler)
    app.add_handler(day_input_callback_handler, group=3)
    app.add_handler(language_handler)
    app.add_handler(language_callback_handler, group=4)
    app.add_handler(help_handler)
    app.add_handler(unknown_handler)

    app.run_polling()


if __name__ == '__main__':
    main()