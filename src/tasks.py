import config
from db import get_groups_collection, get_redis_connection, get_teachers_collection
from timetable_scraper import TimetableScraper


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


def clear_redis_cache() -> None:
    """Clears the redis cache"""
    redis = get_redis_connection()
    redis.flushdb()


if __name__ == '__main__':
    # update_group_collection()
    # update_teacher_collection()
    clear_redis_cache()