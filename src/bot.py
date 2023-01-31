import datetime
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import MessageLimit
from telegram.ext import ContextTypes
from translate import Translator

import config
from db import (
    get_groups_collection,
    get_redis_connection,
    get_teachers_collection,
    get_timetables_collection,
    get_users_collection,
)
from utils import (
    get_timetable,
    send_message_by_chunks,
    update_user,
    get_ongoing_week
)

translator = Translator(to_lang="en")


def _(text):
    return translator.translate(text)


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
timetables_db = get_timetables_collection()
r = get_redis_connection()


def insert_or_update_user(update: Update):
    user_id = update.effective_chat.id
    user = users_db.find_one({'user_id': user_id})
    username = update.effective_chat.username
    users_db.update_one({
        'user_id': user_id,
    }, {'$set': {
        'username': username,
        'semester': user['semester'],
    }},
                        upsert=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("User %s started the bot" % (update.effective_chat.id))
    start_message = _("""
    Hello! I'm a bot that can show you your timetable.
    To get started, enter your group name after the command /group.
    For example /group СУЛА-308С 
    For more information, use the /help command.
    """)
    user_id = update.effective_chat.id
    username = update.effective_chat.username
    if users_db.count_documents({'user_id': user_id}) == 0:
        users_db.insert_one({
            'user_id': user_id,
            'username': username,
            'semester': 2
        })
    await context.bot.send_message(chat_id=user_id, text=start_message)


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
    insert_or_update_user(update)
    query = update.callback_query
    if query.message.text == _("Choose semester:"):
        await query.answer()
        logging.info("Selected semester: %s" % (query.data))
        users_db.update_one({'user_id': update.effective_chat.id},
                            {'$set': {
                                'semester': int(query.data)
                            }})
        await query.edit_message_text(text=_("Semester successfully set "))
    return


async def group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get group name from user and reply with timetable"""
    insert_or_update_user(update)
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
        await query.edit_message_text(text=_('Group successfully set to %s' %
                                             (group)))


async def teacher_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    insert_or_update_user(update)
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
        await query.message.edit_text(text=_('Teacher successfully set to %s' %
                                             (teacher)))


async def day_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    insert_or_update_user(update)
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
            message = get_timetable(timetables_db=timetables_db,redis_cache=r,user=user, day=day)
            if len(message) > MessageLimit.MAX_TEXT_LENGTH:
                await query.edit_message_text(text=_('Loading...'))
                await send_message_by_chunks(context.bot,
                                             update.effective_chat.id, message)
            else:
                await query.edit_message_text(text=message)
            return

        except IndexError:
            logging.info("No group or teacher found")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=
                _('You must set group or teacher before choosing day. Refer to /help'
                  ))
            return
        except ValueError:
            logging.info("No timetable found for %s" % (value))
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_(f"I didn't find any timetable for {value}. Try again"))
            return
        except Exception as e:
            logging.error(e)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_('Something went wrong. Try again'))
            return

async def send_daily_timetable(context: ContextTypes.DEFAULT_TYPE):
    day = DAYS[datetime.datetime.today().strftime('%A')]
    week_message = get_ongoing_week()
    users = users_db.find({'$or': [{'group': {'$exists': True}},{"teacher": {'$exists': True}}]})
    for user in users:
        user_id = user['user_id']
        message = get_timetable(timetables_db=timetables_db,redis_cache=r,user=user, day=day)
        message = f"{week_message}\nРасписание дня\n{message}"
        if len(message) > MessageLimit.MAX_TEXT_LENGTH:
            await send_message_by_chunks(context.bot, user_id, message)
        else:
            await context.bot.send_message(chat_id=user_id, text=message)

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Translate the bot's messages to the user's language.
    """
    language_keyboad = [
        [InlineKeyboardButton(_("English"), callback_data="en")],
        [InlineKeyboardButton(_("Russian"), callback_data="ru")],
        [InlineKeyboardButton(_("French"), callback_data="fr")],
    ]
    language_keyboad_markup = InlineKeyboardMarkup(language_keyboad)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=_("Choose your language:"),
        reply_markup=language_keyboad_markup,
    )


async def language_choice_callback(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the user's choice of language.
    """
    global translator
    query = update.callback_query
    if query.message.text == _("Choose your language:"):
        await query.answer()
        language = query.data
        if len(language) != 2:
            return
        translator = Translator(to_lang=language)
        logging.info("Language set to: %s" % (language))
        await query.message.edit_text(text=_("Language set "))


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    insert_or_update_user(update)
    command_list = [
        '/start - Start the bot',
        '/semester - Choose semester',
        '/group - Enter group name after command e.g. /group СУЛА-2',
        '/teacher - Enter teacher\'s name after command e.g. /teacher Иванов',
        '/day - Get timetable for a day',
        '/language - Choose language. For a smooth experience, choose English',
        '/help - Show this message',
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