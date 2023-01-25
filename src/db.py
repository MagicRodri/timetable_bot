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


def get_redis_connection() -> redis.Redis:
    return redis.Redis(host=config.REDIS_HOST,
                       port=config.REDIS_PORT,
                       password=config.REDIS_PASSWORD)


if __name__ == '__main__':
    users = get_users_collection()
    print(users.count_documents({}))
    r = get_redis_connection()
    r.set('test', 'test')
    print(r.exists('test'))