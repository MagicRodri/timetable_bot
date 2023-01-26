import config
from db import get_groups_collection, get_teachers_collection
from timetable_scraper import TimetableScraper

groups_db = get_groups_collection()
teachers_db = get_teachers_collection()


def update_group_collection() -> None:
    """Updates the groups collection in the database"""

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


if __name__ == '__main__':
    update_group_collection()
    update_teacher_collection()