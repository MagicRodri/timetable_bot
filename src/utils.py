from typing import List


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
