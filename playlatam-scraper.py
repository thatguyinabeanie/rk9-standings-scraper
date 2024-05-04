import argparse
import json
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


# TODO: how does playlatam deal with events over multiple days?
def parse_playlatam_date_range(input_str):
    months = {
        'enero': '01',
        'febrero': '02',
        'marzo': '03',
        'abril': '04',
        'mayo': '05',
        'junio': '06',
        'julio': '07',
        'agosto': '08',
        'septiembre': '09',
        'octubre': '10',
        'noviembre': '11',
        'diciembre': '12'
    }
    date_fields = input_str.lower().replace('–', ' ').replace('-', ' ').replace(', ', ' ').split(" ")
    date = f'{date_fields[3]}-{months[date_fields[2]]}-{date_fields[0]}'
    return date, date


def table_scraper(tour_id, division_name, pod, rounds_no, published_standings):
    round_tables = []
    last_player_id = 1
    player_dict = {}
    for iRounds in range(rounds_no):
        current_round = iRounds + 1

        round_url = f"https://pairings.playlatam.net/refresh-pairings/{tour_id}/{pod}/{current_round}"
        with requests.Session() as s:
            page = s.get(round_url)
        round_data = BeautifulSoup(page.content, 'lxml')
        round_players = round_data.find('table', {'id': 'matches'}).find_all('tr')[1:]
        max_tables = 0
        tables_dict = {}
        for row in round_players:
            row_data = row.find_all('td')
            table_number = 0 if row_data[0].string == 'Bye' else int(row.find('td').string)
            max_tables = max(max_tables, table_number)

            if table_number not in tables_dict:
                tables_dict[table_number] = {'table': table_number, 'players': []}

            player_data = row_data[1].find('span')
            player_name = player_data.contents[1].strip()

            player_result = None
            try:
                if 'tie' in row['class']:
                    player_result = 'T'
            except KeyError:
                pass
            try:
                if 'win' in row_data[1]['class']:
                    player_result = 'W'
            except KeyError:
                pass
            try:
                if 'win' in row_data[3]['class']:
                    player_result = 'L'
            except KeyError:
                pass

            player_dropped = False
            try:
                if 'drop' in player_data['class']:
                    player_dropped = True
            except KeyError:
                pass

            record_match = re.match('\((\d+)/(\d+)/(\d+)\)', row_data[1].contents[-1])
            player_record = {
                'wins': int(record_match.group(1)),
                'losses': int(record_match.group(2)),
                'ties': int(record_match.group(3))
            }

            tables_dict[table_number]['players'].append({
                'name': player_name,
                'result': player_result,
                'dropped': player_dropped,
                'record': player_record
            })

            if current_round == 1:
                last_player_id = last_player_id + 1
                player_dict[last_player_id] = {
                    'name': player_name,
                    'division': division_name,
                    'late': False,
                    'dqed': False
                }

        tables_list = []
        for current_table in range(max_tables + 1):
            if current_table in tables_dict:
                tables_list.append(tables_dict[current_table])
        round_tables.append(tables_list)

    return {
        'players': player_dict,
        'tables': round_tables
    }


def rename_divs(name):
    if name.startswith('Junior'):
        return 'juniors'
    if name.startswith('Senior'):
        return 'seniors'
    return 'masters'


def main_worker(directory, link, output_dir):
    url = f"https://pairings.playlatam.net/matches/{link}"
    print("Fetching: " + url)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "lxml")

    tour_info = soup.find('ul', {'class': 'collection'}).find_all('li', {'class': 'collection-item'})
    title = tour_info[0].contents[2].strip()
    dates = parse_playlatam_date_range(tour_info[3].contents[2].strip())
    print(title, dates)

    print('scrape start : ' + datetime.now().strftime("%Y/%m/%d - %H:%M:%S"))
    pod_selector = soup.find('div', {'id': 'pod-selector'}).find('select').find_all('option')
    divisions = [{'name': rename_divs(item.text), 'pod': item['value']} for item in pod_selector]

    # yes we are sniffing through a script for the internal tour ID
    # i am going insane
    script = [tag for tag in soup.find('body').contents if tag.name == 'script'][0]
    tour_id = re.search('refresh-rounds/(\d+)', script.string).group(1)

    for division in divisions:
        print(f"scrape start {division['name']} : {datetime.now().strftime('%Y/%m/%d - %H:%M:%S')}")
        rounds_url = f"https://pairings.playlatam.net/refresh-rounds/{tour_id}/{division['pod']}"
        rounds_page = requests.get(rounds_url)
        rounds_soup = BeautifulSoup(rounds_page.content, "lxml")
        rounds = max([tag['value'] for tag in rounds_soup.find_all('option')])
        print(rounds)

        published_standings = []

        scrape_results = table_scraper(tour_id, division['name'], division['pod'], int(rounds), published_standings)

        standing_directory = f'{output_dir}/{directory}/{division["name"]}'
        os.makedirs(standing_directory, exist_ok=True)
        os.makedirs(f'{standing_directory}/players', exist_ok=True)

        with open(f"{standing_directory}/tables.json", 'w') as tables_file:
            json.dump(scrape_results['tables'], tables_file, separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/players.json",
                  'w') as jsonPlayers:
            json.dump(scrape_results['players'], jsonPlayers, separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/published_standings.txt", "w") as published_standings_out:
            published_standings_out.writelines([f"{line}\n" for line in published_standings if len(line) > 0])

        print(f"scrape end {division['name']} : {datetime.now().strftime('%Y/%m/%d - %H:%M:%S')}")

    with open(f"{output_dir}/{directory}/tournament.json", "w") as tournament_export:
        json.dump({
            'id': directory,
            'name': title,
            'date': {
                'start': dates[0],
                'end': dates[1]
            },
            'rk9link': link
        }, tournament_export, separators=(',', ':'), ensure_ascii=False)

    print('scrape end : ' + datetime.now().strftime("%Y/%m/%d - %H:%M:%S"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--id")
    parser.add_argument("--output-dir", help="output directory", default='.')

    args = parser.parse_args()

    """exemple: (Barcelona)
    id = 'special-buenos-aires'
    url = 'BsAs24-VG'
    """
    os.makedirs(args.output_dir, exist_ok=True)
    main_worker(args.id, args.url, args.output_dir)
