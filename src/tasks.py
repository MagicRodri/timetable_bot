from celery import Celery, schedules

import config
from db import get_groups_collection, get_redis_connection, get_teachers_collection
from timetable_scraper import TimetableScraper

app = Celery('tasks',
             broker=config.CELERY_BROKER_URL,
             backend=config.CELERY_BROKER_URL)
app.autodiscover_tasks()


@app.task
def update_group_collection() -> None:
    """Updates the groups collection in the database"""
    groups_db = get_groups_collection()
    for semester in range(1, 3):
        scraper = TimetableScraper(semester=semester,
                                   academic_year=config.ACADEMIC_YEAR)
        groups = scraper.get_list_of(group=True)
        for value, name in groups:
            groups_db.update_one({
                'name': name,
                'semester': semester,
            }, {'$set': {
                'value': value
            }},
                                 upsert=True)


@app.task
def update_teacher_collection() -> None:
    """Updates the teachers collection in the database"""

    teachers_db = get_teachers_collection()
    for semester in range(1, 3):
        scraper = TimetableScraper(semester=semester,
                                   academic_year=config.ACADEMIC_YEAR)
        teachers = scraper.get_list_of(teacher=True)
        for value, name in teachers:
            teachers_db.update_one({
                'name': name,
                'semester': semester,
            }, {'$set': {
                'value': value
            }},
                                   upsert=True)


@app.task
def clear_redis_cache() -> None:
    """Clears the redis cache"""
    redis = get_redis_connection()
    redis.flushdb()


@app.task
def add(x, y):
    return x + y


@app.on_after_configure.connect
def run_periodic_tasks(sender, *args, **kwargs):
    sender.add_periodic_task(schedules.crontab(minute='*/1'),
                             add.s(2, 2),
                             name='add every 1')
    # sender.add_periodic_task(schedules.crontab(hour='*/2'),
    #                          update_group_collection.s(),
    #                          name='update group collection')
    # sender.add_periodic_task(schedules.crontab(hour='*/2'),
    #                          update_teacher_collection.s(),
    #                          name='update teacher collection')
    # sender.add_periodic_task(schedules.crontab(hour='*/2'),
    #                          clear_redis_cache.s(),
    #                          name='clear redis cache')


if __name__ == '__main__':
    update_group_collection()
    update_teacher_collection()
    clear_redis_cache()