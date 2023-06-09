import os
from itertools import count
from typing import Union, Generator

import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


def fetch_hh_vacancies(
        token: str,
        professional_role_id: int,
        specialization_id: int,
        language: str,
        vacancy_count_per_page: int,
        area_id: int,
        period: int) -> Generator[tuple[dict, int], None, None]:
    """Create generator of vacancies from hh.ru"""
    page_content = {'pages': 0}
    for page in count():
        if page > page_content['pages'] or page == 200:
            break
        page_response = requests.get(
            url='https://api.hh.ru/vacancies',
            headers={
                'Authorization': f"Bearer {token}",
            },
            params={
                'period': period,
                'specialization': specialization_id,
                'area': area_id,
                'professional_role': professional_role_id,
                'per_page': vacancy_count_per_page,
                'page': page,
                'text': language,
            }
        )
        page_response.raise_for_status()
        page_content = page_response.json()

        for vacancy in page_content['items']:
            yield vacancy, page_content['found']


def fetch_sj_vacancies(
        language: str,
        catalogues_id: int,
        token: str,
        vacancy_count_per_page: int,
        town_id: int,
        period: int) -> Generator[tuple[dict, int], None, None]:
    """Create generator of vacancies from superjob.ru"""
    page_content = {'more': 'True'}
    for page in count():
        if not page_content['more'] or page == 50:
            break
        page_response = requests.get(
            url='https://api.superjob.ru/2.0/vacancies/',
            headers={
                'X-Api-App-Id': token,
            },
            params={
                'town': town_id,
                'catalogues': catalogues_id,
                'count': vacancy_count_per_page,
                'period': period,
                'page': page,
                'keyword': language,
            }
        )
        page_response.raise_for_status()
        page_content = page_response.json()

        for vacancy in page_content['objects']:
            yield vacancy, page_content['total']


def predict_salary(
        salary_from: Union[None, int],
        salary_to: Union[None, int]) -> Union[None, int]:
    """Return vacancy's approx salary."""
    if salary_from and salary_to:
        return int((salary_from + salary_to) / 2)
    elif salary_from:
        return int(salary_from * 1.2)
    elif salary_to:
        return int(salary_to * 0.8)
    return None


def predict_rub_salary_hh(vacancy: dict) -> Union[None, int]:
    """Return vacancy's approx salary in rubles for hh.ru."""
    salary = vacancy['salary']
    if salary and salary['currency'] == 'RUR':
        return predict_salary(salary['from'], salary['to'])
    return None


def predict_rub_salary_sj(vacancy: dict) -> Union[int, None]:
    """Return vacancy's approx salary in rubles for superjob.ru."""
    if vacancy['currency'] == 'rub':
        return predict_salary(vacancy['payment_from'], vacancy['payment_to'])
    return None


def get_hh_statistics(
        languages: list[str],
        token: str,
        professional_role_id: int,
        specialization_id: int,
        period: int,
        vacancy_count_per_page: int,
        area_id: int) -> str:
    """
    Get statictics of vacancies and average salary for programming
    language for hh.ru.
    """
    language_statistics = []
    for language in languages:
        vacancies_processed = 0
        salaries_sum = 0
        hh_vacancies = fetch_hh_vacancies(token=token, professional_role_id=professional_role_id,
                                          specialization_id=specialization_id, language=language,
                                          vacancy_count_per_page=vacancy_count_per_page, area_id=area_id, period=period)
        for vacancy, vacancy_count in hh_vacancies:
            if not vacancy:
                continue

            average_rub_salary = predict_rub_salary_hh(vacancy)
            if not average_rub_salary:
                continue

            vacancies_processed += 1
            salaries_sum += average_rub_salary
        language_statistics.append(
            [
                language,
                vacancy_count,
                vacancies_processed,
                int((salaries_sum / vacancies_processed) if vacancies_processed else 0)
            ]
        )
    return language_statistics


def get_sj_statistics(
        languages: list[str],
        catalogues_id: int,
        token: str,
        vacancy_count_per_page: int,
        town_id: int,
        period: int) -> str:
    """
    Get statictics of vacancies and average salary for programming
    language for superjob.ru.
    """
    language_statistics = []
    for language in languages:
        vacancies_processed = 0
        salaries_sum = 0
        sj_vacancies = fetch_sj_vacancies(language=language, catalogues_id=catalogues_id, token=token,
                                          vacancy_count_per_page=vacancy_count_per_page, town_id=town_id, period=period)
        for vacancy, vacancy_count in sj_vacancies:
            if not vacancy:
                continue

            average_rub_salary = predict_rub_salary_sj(vacancy)
            if not average_rub_salary:
                continue

            vacancies_processed += 1
            salaries_sum += average_rub_salary
        language_statistics.append(
            [
                language,
                vacancy_count,
                vacancies_processed,
                int((salaries_sum / vacancies_processed) if vacancies_processed else 0)
            ]
        )
    return language_statistics


def create_table(table_name: str, table_content: list) -> str:
    """Create terminal table."""
    table_header = [
        [
            'Язык программирования',
            'Вакансий найдено',
            'Вакансий обработано',
            'Средняя зарплата'
        ]
    ]
    table_header.extend(table_content)
    table = AsciiTable(table_header, table_name)
    return table.table


def main() -> None:
    """Print average salary tables for hh.ru and superjob.ru."""
    load_dotenv()
    hh_token = os.getenv('HH_TOKEN')
    hh_table_name = 'HeadHunter Moscow'

    sj_token = os.getenv('SJ_TOKEN')
    sj_table_name = 'SuperJob Moscow'

    vacancy_count_per_page = 10

    programming_languages = [
        'JavaScript', 'Python', 'Java', 'C#', 'PHP', 'C++',
        'C', 'Ruby', 'Go'
    ]

    hh_statistics = get_hh_statistics(
        languages=programming_languages,
        token=hh_token,
        professional_role_id=96,
        specialization_id=1,
        period=30,
        vacancy_count_per_page=vacancy_count_per_page,
        area_id=1
    )
    sj_statistics = get_sj_statistics(
        languages=programming_languages,
        catalogues_id=48,
        token=sj_token,
        vacancy_count_per_page=vacancy_count_per_page,
        town_id=4,
        period=7
    )

    terminal_tables = (create_table(hh_table_name, hh_statistics),
                       create_table(sj_table_name, sj_statistics))
    print(*terminal_tables, sep='\n')


if __name__ == '__main__':
    main()
