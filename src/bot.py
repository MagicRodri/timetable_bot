import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import get_redis_connection, get_users_collection
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
users_db = get_users_collection()
r = get_redis_connection()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("User %s started the bot" % (update.effective_chat.id))
    start_message = _("""
    Hello! I'm a bot that can show you your timetable.
    To get started, enter your group name after the command /group.
    For example: /group СУЛА-308С 
    For more information, use the /help command.
    """)
    user_id = update.effective_chat.id
    if users_db.count_documents({'user_id': user_id}) == 0:
        users_db.insert_one({'user_id': user_id, 'semester': 2})
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
    users_db.update_one({'user_id': update.effective_chat.id},
                        {'$set': {
                            'semester': int(query.data)
                        }})
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=_('Semester changed'))


async def group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get group name from user and reply with timetable"""
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
    try:
        user = users_db.find_one({'user_id': update.effective_chat.id})
        scraper = TimetableScraper(academic_year=ACADEMIC_YEAR,
                                   headless=True,
                                   group=group,
                                   semester=user['semester'])
        # If day is specified, send only one day timetable
        if day:
            # Check if timetable is in cache
            key = f'{group.lower()}_{day.lower()}'
            if r.exists(key):
                message = r.get(key).decode('utf-8')
                logging.info("Got timetable %s from cache" % (key))
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=message)
                return
            timetable_dict = scraper.get_timetables_dict()
            message = compose_timetable(timetable_dict, day)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message)
            # Save timetable to cache
            r.set(key, message)
            logging.info("Saved timetable %s to cache" % (key))
            return
        # If day is not specified, send all days timetable
        key = f'{group.lower()}_all'
        if r.exists(key):
            messages = r.get(key).decode('utf-8').split('|||')
            logging.info("Got timetable %s from cache" % (key))
            for message in messages:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=message)
            return
        timetable_dict = scraper.get_timetables_dict()
        messages = compose_timetables(timetable_dict)
        for message in messages:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message)
        r.set(key, '|||'.join(messages))
        logging.info("Saved timetable %s to cache" % (key))
    except ValueError:
        logging.info("No timetable found for %s" % (group))
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(f'No timetable found for {group}. Try again'))
        return
    except Exception as e:
        logging.error(e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_('Something went wrong. Try again'))
        return


async def teacher_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_('Enter teacher name after command /teacher'))
        return
    day = None
    if len(context.args) == 1:
        teacher = context.args[0]
    elif len(context.args) >= 2:
        teacher = context.args[0]
        day = context.args[1]
        # TODO: better day parsing
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
    logging.info("Entered teacher: %s" % (teacher))
    user = users_db.find_one({'user_id': update.effective_chat.id})
    scraper = TimetableScraper(academic_year=ACADEMIC_YEAR,
                               headless=True,
                               teacher=teacher,
                               semester=user['semester'])
    try:
        # If day is specified, get timetable for this day
        if day:
            key = f'{teacher.lower()}_{day.lower()}'
            if r.exists(key):
                message = r.get(key).decode('utf-8')
                logging.info("Got timetable %s from cache" % (key))
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=message)
                return
            timetable_dict = scraper.get_timetables_dict()
            message = compose_timetable(timetable_dict, day)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message)
            r.set(key, message)
            logging.info("Saved timetable %s to cache" % (key))
            return
        # If day is not specified, get all timetables
        key = f'{teacher.lower()}_all'
        if r.exists(key):
            messages = r.get(key).decode('utf-8').split('|||')
            logging.info("Got timetable %s from cache" % (key))
            for message in messages:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=message)
            return
        messages = compose_timetables(timetable_dict)
        for message in messages:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message)
        r.set(key, '|||'.join(messages))
        logging.info("Saved timetable %s to cache" % (key))
    except ValueError:
        logging.info("No timetable found for %s" % (teacher))
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(f'No timetable found for {teacher}. Try again'))
        return
    except Exception as e:
        logging.error(e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_('Something went wrong. Try again'))
        return


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command_list = [
        '/start - Start the bot',
        '/help - Show this help message',
        '/semester - Choose semester',
        '/group <group> <day>- Get timetable per group',
        '/teacher <teacher> <day>- Get timetable per teacher',
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