from typing import List

from db import get_users_collection


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