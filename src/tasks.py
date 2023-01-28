import concurrent.futures
import datetime

from celery import Celery, schedules

import config
from db import (
    get_groups_collection,
    get_redis_connection,
    get_teachers_collection,
    get_timetables_collection,
)
from timetable_scraper import TimetableScraper2

app = Celery('tasks',
             broker=config.CELERY_BROKER_URL,
             backend=config.CELERY_BROKER_URL)
app.autodiscover_tasks()


@app.task
def update_group_collection() -> None:
    """Updates the groups collection in the database"""
    groups_db = get_groups_collection()
    for semester in range(1, 3):
        scraper = TimetableScraper2(semester=semester)
        groups = scraper.get_list_of(group=True)
        for value, name in groups:
            groups_db.update_one({
                'name': name,
                'semester': semester,
            }, {
                '$set': {
                    'value': value,
                    'last_updated': datetime.datetime.now()
                }
            },
                                 upsert=True)


@app.task
def update_teacher_collection() -> None:
    """Updates the teachers collection in the database"""

    teachers_db = get_teachers_collection()
    for semester in range(1, 3):
        scraper = TimetableScraper2(semester=semester)
        teachers = scraper.get_list_of(teacher=True)
        for value, name in teachers:
            teachers_db.update_one({
                'name': name,
                'semester': semester,
            }, {
                '$set': {
                    'value': value,
                    'last_updated': datetime.datetime.now()
                }
            },
                                   upsert=True)


@app.task
def update_timetables_collection() -> None:
    """Updates the timetables collection in the database"""
    scraper = TimetableScraper2(semester=2)
    timetables_db = get_timetables_collection()
    groups_db = get_groups_collection()
    groups = groups_db.find({})
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [(executor.submit(scraper.get_timetable_dict,
                                    group=(group['value'], group['name'])))
                   for group in groups]
        for future in concurrent.futures.as_completed(futures):
            item = future.result()
            timetable = item.pop('timetable')
            timetables_db.update_one({
                **item,
            }, {
                '$set': {
                    'timetable': timetable,
                    'last_updated': datetime.datetime.now()
                }
            }, True)

    teachers_db = get_teachers_collection()
    teachers = teachers_db.find({})
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [(executor.submit(scraper.get_timetable_dict,
                                    teacher=(teacher['value'],
                                             teacher['name'])))
                   for teacher in teachers]
        for future in concurrent.futures.as_completed(futures):
            item = future.result()
            timetable = item.pop('timetable')
            timetables_db.update_one({
                **item,
            }, {
                '$set': {
                    'timetable': timetable,
                    'last_updated': datetime.datetime.now()
                }
            }, True)


@app.task
def clear_redis_cache() -> None:
    """Clears the redis cache"""
    redis = get_redis_connection()
    redis.flushdb()


@app.on_after_configure.connect
def run_periodic_tasks(sender, *args, **kwargs):
    sender.add_periodic_task(schedules.crontab(hour='*/6'),
                             update_timetables_collection.s(),
                             name='update timetables collection')
    sender.add_periodic_task(schedules.crontab(hour='*/6'),
                             update_group_collection.s(),
                             name='update group collection')
    sender.add_periodic_task(schedules.crontab(hour='*/6'),
                             update_teacher_collection.s(),
                             name='update teacher collection')
    sender.add_periodic_task(schedules.crontab(hour='*/6'),
                             clear_redis_cache.s(),
                             name='clear redis cache')


if __name__ == '__main__':
    update_group_collection()
    update_teacher_collection()
    clear_redis_cache()
    update_timetables_collection()