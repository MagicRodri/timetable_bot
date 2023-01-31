import pymongo
import redis

import config


def get_db() -> pymongo.database.Database:
    client = pymongo.MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB_NAME]
    return db


def get_users_collection() -> pymongo.collection.Collection:
    db = get_db()
    return db.users


def get_groups_collection() -> pymongo.collection.Collection:
    db = get_db()
    groups = db.groups
    if 'name_text' not in groups.index_information():
        groups.create_index([('name', 'text')],
                            unique=False,
                            default_language='russian')
    return groups


def get_teachers_collection() -> pymongo.collection.Collection:
    db = get_db()
    teachers = db.teachers
    if 'name_text' not in teachers.index_information():
        teachers.create_index([('name', 'text')],
                              unique=False,
                              default_language='russian')
    return teachers


def get_timetables_collection() -> pymongo.collection.Collection:
    db = get_db()
    return db.timetables


def get_redis_connection() -> redis.Redis:
    return redis.Redis(host=config.REDIS_HOST,
                       port=config.REDIS_PORT,
                       password=config.REDIS_PASSWORD)


if __name__ == '__main__':
    users = get_users_collection()
    print(users.count_documents({}))
    # r = get_redis_connection()
    # r.set('test', 'test')
    # print(r.exists('test'))
    # groups_db = get_groups_collection()
    # result = groups_db.find({'$text': {'$search': 'СУЛА-308С'}})
    # for i in result:
    #     print(i)
    # timetables_db = get_timetables_collection()
    # timetable_doc = timetables_db.find_one({"group": "СУЛА-308С"})
    # print(timetable_doc)
