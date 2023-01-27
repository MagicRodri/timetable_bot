import logging
import time
from dataclasses import dataclass

from fake_useragent import UserAgent
from requests_html import HTML
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By


def get_user_agent():
    ua = UserAgent(verify_ssl=False)
    return ua.random


semesters = {
    1: "Осенний семестр {academic_year}",
    2: "Весенний семестр {academic_year}",
}

timetable_types_value = {
    "group": "1",
    "teacher": "2",
    "room": "3",
}

timetable_select_names = {
    "group": "student_group_id",
    "teacher": "teacher",
}


@dataclass
class TimetableScraper:
    """Scrapes the ISU timetable page for a given group and semester."""

    academic_year: str
    semester: int
    group: str = None
    teacher: str = None
    room: str = None
    endpoint: str = "https://isu.ugatu.su/api/new_schedule_api/"
    driver: WebDriver = None
    headless: bool = True

    def __post_init__(self):
        self.driver = self.get_driver()
        self.driver.get(self.endpoint)

    def get_driver(self) -> WebDriver:
        if self.driver is None:
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument(f'user-agent={get_user_agent()}')
            self.driver = webdriver.Chrome(options=options)
        return self.driver

    def close(self) -> None:
        self.driver.quit()

    def _submit_form(self) -> None:
        form = self.driver.find_element(By.TAG_NAME, "form")
        form.submit()

    def select_semester(self) -> None:
        semester_select = self.driver.find_element(By.NAME,
                                                   "schedule_semestr_id")
        semester_str = semesters[self.semester].format(
            academic_year=self.academic_year)
        for term in semester_select.find_elements(By.TAG_NAME, "option"):
            if term.text == semester_str:
                term.click()
                break

    def _get_select(self, timetable_type, select_name):
        filter_radio = self.driver.find_element(
            By.CSS_SELECTOR, f"input[value='{timetable_type}']")
        filter_radio.click()
        # self._submit_form()
        select = self.driver.find_element(By.CSS_SELECTOR,
                                          f"select[name='{select_name}']")
        return select

    def select_timetable_type(self) -> None:
        """Selects the timetable type (group, teacher)"""
        if self.group and self.teacher or self.group and self.room or self.teacher and self.room:
            raise ValueError(
                "Only one of group, teacher or room can be specified.")
        elif not self.group and not self.teacher and not self.room:
            raise ValueError(
                "One of group, teacher or room must be specified.")

        if self.group:
            timetable_value = timetable_types_value["group"]
            select_name = timetable_select_names["group"]
        elif self.teacher:
            timetable_value = timetable_types_value["teacher"]
            select_name = timetable_select_names["teacher"]

        select = self._get_select(timetable_value, select_name)
        for option in select.find_elements(By.TAG_NAME, "option"):
            if self.group and self.group.lower() in option.text.lower():
                option.click()
                break
            elif self.teacher and self.teacher.lower() in option.text.lower():
                option.click()
                break
        else:
            raise ValueError(
                f"Timetable for {self.group or self.teacher} not found.")

        # TODO: implement room selection

    def html_object(self) -> HTML:
        return HTML(html=self.driver.page_source)

    def _scrape_timetable(self, html: HTML) -> dict:
        timetable_table = html.find("table", first=True)
        if not timetable_table:
            raise ValueError("No timetable found.")

        table_header = timetable_table.find("thead", first=True)
        headers = []
        for td in table_header.find("td"):
            headers.append(td.text)
        # logging.info(f"Headers: {headers}")
        timetables_dict = {}
        table_body = timetable_table.find("tbody", first=True)
        day = None
        for row in table_body.find("tr"):
            cells = row.find("td")
            if cells[0].text != "" and cells[0].text not in timetables_dict:
                day = cells[0].text
                timetables_dict[day] = []
                # logging.info(f"Day: {day}")
            else:
                if day is not None:
                    timetable = {}
                    for header, cell in zip(headers[1:], cells[1:]):
                        timetable[header] = cell.text
                    timetables_dict[day].append(timetable)
        return timetables_dict

    def get_timetables_dict(self) -> dict:
        self.select_semester()
        self.select_timetable_type()
        # self._submit_form()
        html = self.html_object()
        return self._scrape_timetable(html)

    def get_list_of(self, *, group=False, teacher=False) -> list:
        if group and teacher:
            raise ValueError("Only one of group or teacher can be specified.")
        elif not group and not teacher:
            raise ValueError("One of group or teacher must be specified.")
        if group:
            timetable_value = timetable_types_value["group"]
            select_name = timetable_select_names["group"]
        elif teacher:
            timetable_value = timetable_types_value["teacher"]
            select_name = timetable_select_names["teacher"]
        self.select_semester()
        select = self._get_select(timetable_value, select_name)
        the_list = []
        for option in select.find_elements(By.TAG_NAME, "option"):
            the_list.append((option.get_attribute('value'), option.text))
        return the_list

    def scrape_all(self) -> list:
        data = []
        self.select_semester()
        timetable_value = timetable_types_value["group"]
        select_name = timetable_select_names["group"]
        for value in ['group', 'teacher']:
            timetable_value = timetable_types_value[value]
            select_name = timetable_select_names[value]
            select = self._get_select(timetable_value, select_name)
            options = select.find_elements(By.TAG_NAME, "option")
            i = 0
            while i < len(options):
                options[i].click()
                select = self._get_select(timetable_value, select_name)
                options = select.find_elements(By.TAG_NAME, "option")
                html = self.html_object()
                data.append({
                    value: options[i].text,
                    'timetable': self._scrape_timetable(html)
                })
                i += 1
        self.close()
        return data


if __name__ == "__main__":
    scraper = TimetableScraper(academic_year='2022/2023',
                               semester=2,
                               group='СУЛА-209С',
                               headless=True)
    # print(scraper.get_list_of(group=True))
    # print(scraper.get_timetables_dict())
    print(scraper.scrape_all())