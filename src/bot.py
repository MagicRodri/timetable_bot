import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import config
from db import (
    get_groups_collection,
    get_redis_connection,
    get_teachers_collection,
    get_users_collection,
)
from timetable_scraper import TimetableScraper
from utils import compose_timetable, update_user


def _(text: str):
    return text


ACADEMIC_YEAR = config.ACADEMIC_YEAR
DAYS = {
    _("Monday"): "Понедельник",
    _("Tuesday"): "Вторник",
    _("Wednesday"): "Среда",
    _("Thursday"): "Четверг",
    _("Friday"): "Пятница",
    _("Saturday"): "Суббота",
}
users_db = get_users_collection()
groups_db = get_groups_collection()
teachers_db = get_teachers_collection()
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
                                   text=_("Choose semester:"),
                                   reply_markup=reply_markup)


async def semester_choice_callback(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.message.text == _("Choose semester:"):
        await query.answer()
        logging.info("Selected semester: %s" % (query.data))
        users_db.update_one({'user_id': update.effective_chat.id},
                            {'$set': {
                                'semester': int(query.data)
                            }})
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=_('Semester changed'))
    return


async def group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get group name from user and reply with timetable"""
    if len(context.args) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_('Enter group name after command /group'))
        return
    if len(context.args) == 1:
        group = context.args[0]
        result = groups_db.find({'$text': {'$search': group}})
        count = len(list(result.clone()))
        if count == 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_('Group not found. Try again'))
            return
        elif count > 1:
            keyboad = []
            for group in result:
                keyboad.append([
                    InlineKeyboardButton(group['name'],
                                         callback_data=group['name'])
                ])
            reply_markup = InlineKeyboardMarkup(keyboad)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=_('Choose group:'),
                                           reply_markup=reply_markup)
            return
        group = result[0]['name']
        update_user(update.effective_chat.id, group)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=_('Group successfully set to %s' %
                                              (group)))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=_('Too many arguments'))


async def group_input_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.message.text == _("Choose group:"):
        await query.answer()
        group = query.data
        update_user(update.effective_chat.id, group)
        logging.info("Entered group: %s" % (group))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=_('Group successfully set to %s' %
                                              (group)))


async def teacher_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_('Enter teacher name after command /teacher'))
        return
    else:
        teacher = ' '.join(context.args)
        result = teachers_db.find({'$text': {'$search': teacher}})
        count = len(list(result.clone()))
        if count == 0:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_('No teacher found. Try again'))
            return
        elif count > 1:
            keyboad = []
            for teacher in result:
                keyboad.append([
                    InlineKeyboardButton(teacher['name'],
                                         callback_data=teacher['name'])
                ])
            reply_markup = InlineKeyboardMarkup(keyboad)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=_('Choose teacher:'),
                                           reply_markup=reply_markup)
        teacher = result[0]['name']
        update_user(update.effective_chat.id, teacher=teacher)
        logging.info("Entered teacher: %s" % (teacher))
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_('Teacher successfully set to %s' % (teacher)))
        return


async def teacher_input_callback(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.message.text == _('Choose teacher:'):
        await query.answer()
        teacher = query.data
        update_user(update.effective_chat.id, teacher=teacher)
        logging.info("Entered teacher: %s" % (teacher))
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_('Teacher successfully set to %s' % (teacher)))


async def day_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboad = []
    for en_day, ru_day in DAYS.items():
        keyboad.append([InlineKeyboardButton(en_day, callback_data=ru_day)])
    reply_markup = InlineKeyboardMarkup(keyboad)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=_('Choose day:'),
                                   reply_markup=reply_markup)


async def day_input_callback(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.message.text == _('Choose day:'):
        await query.answer()
        day = query.data
        logging.info("Entered day: %s" % (day))
        try:
            user = users_db.find_one({'user_id': update.effective_chat.id})
            user.pop('_id')
            user.pop('user_id')
            semester = user.pop('semester')
            k, value = list(user.items())[0]
            key = f'{"".join(value.lower().split())}_{semester}_{day.lower()}'
            if r.exists(key):
                message = r.get(key).decode('utf-8')
                logging.info("Got timetable %s from cache" % (key))
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=message)
                return
            scraper = TimetableScraper(academic_year=ACADEMIC_YEAR,
                                       headless=True,
                                       semester=semester,
                                       **user)
            timetable_dict = scraper.get_timetables_dict()
            message = compose_timetable(timetable_dict, day)
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message)
            r.set(key, message)
            logging.info("Saved timetable %s to cache" % (key))
            return

        except IndexError:
            logging.info("No group or teacher found")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=
                _('No group or teacher found. Refer to /help to set group or teacher'
                  ))
            return
        except ValueError:
            logging.info("No timetable found for %s" % (value))
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_(f'No timetable found for {value}. Try again'))
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
        '/group <group> - Enter group',
        '/teacher <teacher> - Enter teacher\'s name',
        '/day - Get timetable for a day',
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