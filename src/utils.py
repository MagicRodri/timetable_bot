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
