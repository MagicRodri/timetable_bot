import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from timetable_scraper import TimetableScraper
from utils import compose_timetable, compose_timetables


def _(text: str):
    return text


ACADEMIC_YEAR = "2022/2023"
DAYS = {
    _("Понедельник"),
    _("Вторник"),
    _("Среда"),
    _("Четверг"),
    _("Пятница"),
    _("Суббота")
}
users_options = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("User %s started the bot" % (update.effective_chat.id))
    start_message = _("""
    Hello! I'm a bot that can show you your timetable.
    To get started, enter your group name after the command /group.
    For example: /group СУЛА-308С 
    For more information, use the /help command.
    """)
    if update.effective_chat.id not in users_options:
        users_options[update.effective_chat.id] = {
            'semester': 2,
        }
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=start_message)


async def semester_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Осенний семестр", callback_data=1),
        InlineKeyboardButton("Весенний семестр", callback_data=2)
    ]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Choose semester:",
                                   reply_markup=reply_markup)


async def semester_choice_callback(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logging.info("Selected semester: %s" % (query.data))
    users_options[update.effective_chat.id]['semester'] = int(query.data)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=_('Semester changed'))


async def group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_('Enter group name after command /group'))
        return
    day = None
    if len(context.args) == 1:
        group = context.args[0]
    elif len(context.args) == 2:
        group = context.args[0]
        day = context.args[1]
        if day not in DAYS:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_('Incorrect day name. Try again'))
            return
        logging.info("Entered day: %s" % (day))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=_('Too many arguments'))
        return

    logging.info("Entered group: %s" % (group))
    scraper = TimetableScraper(
        academic_year=ACADEMIC_YEAR,
        headless=True,
        group=group,
        semester=users_options[update.effective_chat.id]['semester'])
    try:
        timetable_dict = scraper.get_timetables_dict()
    except ValueError as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(f'No timetable found for {group}. Try again'))
        return
    if day:
        message = compose_timetable(timetable_dict, day)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message)
        return

    messages = compose_timetables(timetable_dict)
    for message in messages:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message)


async def teacher_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teacher = context.args[0]
    logging.info("Entered teacher: %s" % (teacher))


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_list = [
        '/start - Start the bot',
        '/help - Show this help message',
        '/semester - Choose semester',
        '/group <group> <day>- Enter group',
        '/teacher <teacher> <day>- Enter teacher',
    ]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=_('\n'.join(command_list)))


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.text.startswith('/'):
        logging.warning("Unknown command : %s" % (update.message.text))
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=
            _("Sorry, I didn't understand that command. Please refer to the /help command"
              ))
    else:
        logging.warning("Unknown message: %s" % (update.message.text))
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Sorry, I didn't understand that message."))