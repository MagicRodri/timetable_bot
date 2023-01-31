from typing import List
import pymongo
import datetime
import logging
import redis
from db import (
    get_groups_collection,
    get_teachers_collection,
    get_timetables_collection,
    get_users_collection,
)
from timetable_scraper import TimetableScraper2

def get_ongoing_week() -> str:
    """Returns the number of the ongoing week"""
    return TimetableScraper2(semester=2).scrape_ongoing_week()

def compose_timetable(timetable_dict: dict, day: str) -> str:
    message = [day]
    for timetable_cell in timetable_dict[day]:
        if len(timetable_cell) <= 2:
            # Skip if there is no lesson
            continue
        for key, value in timetable_cell.items():
            message.append(f"\t{key}: {value}")
        message.append("\n")
    if len(message) == 1:
        return f"{day}: Нет пар "
    return "\n".join(message)

def compose_timetables(timetable_dict: dict) -> List[str]:
    messages = []
    for day in timetable_dict:
        messages.append(compose_timetable(timetable_dict, day))
    return messages

def get_timetable(timetables_db:pymongo.collection.Collection,redis_cache:redis.Redis,user,day:str) ->str:
    user.pop('_id')
    user.pop('user_id')
    user.pop('username')
    semester = user.pop('semester')
    k, value = list(user.items())[
        0]  # can raise IndexError if user has no group or teacher
    key = f'{"".join(value.lower().split())}_{semester}_{day.lower()}'
    if redis_cache.exists(key):
        message = redis_cache.get(key).decode('utf-8')
        logging.info("Got timetable %s from cache" % (key))
        return message
    else:
        timetable_doc = timetables_db.find_one({k: value})
        last_updated = timetable_doc['last_updated']
        message = compose_timetable(timetable_doc['timetable'], day)
        if datetime.datetime.now() - last_updated > datetime.timedelta(
                hours=6):
            logging.info("Timetable is outdated, scraping new one")
            timetable_dict = scrape_new_timetable((k, value),
                                                    semester=semester)
            message = compose_timetable(timetable_dict['timetable'], day)
        redis_cache.set(key, message)
        logging.info("Saved timetable %s to cache" % (key))
        return message


def update_user(user_id: int, group: str = None, teacher: str = None) -> None:
    """Updates the user's group or teacher"""
    users_db = get_users_collection()
    user = users_db.find_one({'user_id': user_id})
    user_semester = user.get('semester')
    if group and teacher:
        raise ValueError("You can't set both group and teacher")
    if not group and not teacher:
        raise ValueError("You must set either group or teacher")
    if group:
        field = {'group': group}
    elif teacher:
        field = {'teacher': teacher}

    users_db.replace_one({'user_id': user_id}, {
        'user_id': user_id,
        'semester': user_semester,
        **field
    },
                         upsert=True)


async def send_message(bot, chat_id, message):
    """Sends a message"""
    await bot.send_message(chat_id=chat_id, text=message)


async def send_message_by_chunks(bot, chat_id, message, chunk_size=4096):
    """Sends a message by chunks if it's too long"""
    for i in range(0, len(message), chunk_size):
        await bot.send_message(chat_id=chat_id, text=message[i:i + chunk_size])


def scrape_new_timetable(query: tuple, semester: int) -> dict:
    """Scrapes a new timetable"""
    scraper = TimetableScraper2(semester=semester)
    if query[0] == 'group':
        groups_db = get_groups_collection()
        group = groups_db.find_one({'name': query[1], 'semester': semester})
        return scraper.get_timetable_dict(group=(group['value'],
                                                 group['name']))
    elif query[0] == 'teacher':
        teachers_db = get_teachers_collection()
        teacher = teachers_db.find_one({
            'name': query[1],
            'semester': semester
        })
        return scraper.get_timetable_dict(teacher=(teacher['value'],
                                                   teacher['name']))
