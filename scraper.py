import argparse
import json
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def parse_rk9_date_range(input_str):
    months = {
        'jan': '01',
        'feb': '02',
        'mar': '03',
        'apr': '04',
        'may': '05',
        'jun': '06',
        'jul': '07',
        'aug': '08',
        'sep': '09',
        'oct': '10',
        'nov': '11',
        'dec': '12'
    }
    date_fields = input_str.replace('–', ' ').replace('-', ' ').replace(', ', ' ').split(" ")
    if len(date_fields) > 4:
        start_date = f'{date_fields[4]}-{months[date_fields[0].strip()[:3].lower()]}-{int(date_fields[1]):02d}'
        end_date = f'{date_fields[4]}-{months[date_fields[2].strip()[:3].lower()]}-{int(date_fields[3]):02d}'
    else:
        start_date = f'{date_fields[3]}-{months[date_fields[0].strip()[:3].lower()]}-{int(date_fields[1]):02d}'
        end_date = f'{date_fields[3]}-{months[date_fields[0].strip()[:3].lower()]}-{int(date_fields[2]):02d}'
    return start_date, end_date


def table_scraper(link, division_name, pod, rounds_no, published_standings):
    round_tables = []
    last_player_id = 1
    player_list = []
    player_dict = {}
    for iRounds in range(rounds_no):
        tables = []
        round_url = f"https://rk9.gg/pairings/{link}?pod={pod}&rnd={iRounds + 1}"
        with requests.Session() as s:
            page = s.get(round_url)
        round_data = BeautifulSoup(page.content, 'lxml')
        matches = round_data.find_all('div', attrs={'class': 'match'})
        for match_data in matches:
            player1_name = ""
            player2_name = ""
            p1status = -1
            p2status = -1
            p1dropped = False
            p2dropped = False
            p1late = 0
            p2late = 0
            p1dqed = False
            p2dqed = False
            scores1 = []
            scores2 = []
            table = "0"

            table_data = match_data.find('div', attrs={'class': 'col-2'})
            if table_data:
                table_data = table_data.find('span', attrs={'class': 'tablenumber'})
                if table_data:
                    table = table_data.text

            player_data = match_data.find('div', attrs={'class': 'player1'})
            name = player_data.find('span', attrs={'class': 'name'})
            if name:
                score = re.sub(r'\).*', '', name.next_sibling.text.strip().replace('(', ''))
                scores1 = list(map(int, re.split('-', score)))
                player1_name = re.sub(r'\s+', ' ', name.text)
                pdata_text = str(player_data)
                if pdata_text.find(" winner") != -1:
                    p1status = 2
                elif pdata_text.find(" loser") != -1:
                    p1status = 0
                elif pdata_text.find(" tie") != -1:
                    p1status = 1
                if pdata_text.find(" dropped") != -1:
                    p1dropped = True
                if p1status == -1 and not p1dropped:
                    if iRounds + 1 < rounds_no:
                        p1status = 0
                        if iRounds == 0:
                            p1late = True

            player_data = match_data.find('div', attrs={'class': 'player2'})
            name = player_data.find('span', attrs={'class': 'name'})
            if name:
                score = re.sub(r'\).*', '', name.next_sibling.text.strip().replace('(', ''))
                scores2 = list(map(int, re.split('-', score)))
                player2_name = re.sub(r'\s+', ' ', name.text)
                pdata_text = str(player_data)
                if pdata_text.find(" winner") != -1:
                    p2status = 2
                elif pdata_text.find(" loser") != -1:
                    p2status = 0
                elif pdata_text.find(" tie") != -1:
                    p2status = 1
                if pdata_text.find(" dropped") != -1:
                    p2dropped = True
                if p2status == -1 and not p2dropped:
                    if iRounds + 1 < rounds_no:
                        p2status = 0
                        if iRounds == 0:
                            p2late = True

            table_players = []
            if len(player1_name) > 0:
                if iRounds == 0:
                    last_player_id = last_player_id + 1
                    p1dqed = len(published_standings) > 0 and player1_name not in published_standings
                    player_dict[last_player_id] = {
                        'name': player1_name,
                        'division': division_name,
                        'late': p1late,
                        'dqed': p1dqed
                    }
                table_players.append({
                    'name': player1_name,
                    'result': {-1: None, 0: 'L', 1: 'T', 2: 'W'}[p1status],
                    'dropped': p1dropped,
                    'record': {
                        'wins': scores1[0],
                        'losses': scores1[1],
                        'ties': scores1[2]
                    }
                })

            if len(player2_name) > 0:
                if iRounds == 0:
                    last_player_id = last_player_id + 1
                    p2dqed = len(published_standings) > 0 and player2_name not in published_standings
                    player_dict[last_player_id] = {
                        'name': player2_name,
                        'division': division_name,
                        'late': p2late,
                        'dqed': p2dqed
                    }
                table_players.append({
                    'name': player2_name,
                    'result': {-1: None, 0: 'L', 1: 'T', 2: 'W'}[p2status],
                    'dropped': p2dropped,
                    'record': {
                        'wins': scores2[0],
                        'losses': scores2[1],
                        'ties': scores2[2]
                    }
                })

            if len(table_players) > 0:
                tables.append({
                    'table': int(table),
                    'players': table_players
                })

            if len(table_players) == 1 and table_players[0]['result'] is None:
                table_players[0]['result'] = 'L'

        round_tables.append(tables)
    return {
        'players': player_dict,
        'tables': round_tables
    }


def main_worker(directory, link, output_dir):
    url = 'https://rk9.gg/tournament/' + link
    print("Fetching: " + url)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "lxml")

    page_title = soup.find('h3', {'class': 'mb-0'}).text
    title = page_title.split('\n')[0]
    date = page_title.split('\n')[1]
    dates = parse_rk9_date_range(date)

    url = 'https://rk9.gg/pairings/' + link
    print("Fetching: " + url)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "lxml")

    print('scrape start : ' + datetime.now().strftime("%Y/%m/%d - %H:%M:%S"))

    for division_name in ['juniors', 'seniors', 'masters']:
        print(f"scrape start {division_name} : {datetime.now().strftime('%Y/%m/%d - %H:%M:%S')}")
        pod = 0
        rounds_from_url = 0
        for ultag in soup.find_all('ul', {'class': 'nav nav-pills'}):
            for litag in ultag.find_all('li'):
                for aria in litag.find_all('a'):
                    sp = aria.text.split(" ")
                    if sp[0][0:-1].lower() == division_name[0:len(sp[0][0:-1])]:
                        rounds_from_url = int(sp[len(sp) - 1])
                        pod = str(aria['aria-controls']).replace('P', '')

        standing_published_data = soup.find('div', attrs={'id': f"P{pod}-standings"})
        published_standings = []
        if standing_published_data:
            published_standings = [re.sub(r'\d+\.', '', child.text).strip() for child in standing_published_data.children if child.text is not None]

        scrape_results = table_scraper(link, division_name, pod, rounds_from_url, published_standings)

        standing_directory = f'{output_dir}/{directory}/{division_name}'
        os.makedirs(standing_directory, exist_ok=True)
        os.makedirs(f'{standing_directory}/players', exist_ok=True)

        with open(f"{standing_directory}/tables.json", 'w') as tables_file:
            json.dump(scrape_results['tables'], tables_file, separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/players.json",
                  'w') as jsonPlayers:
            json.dump(scrape_results['players'], jsonPlayers, separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/published_standings.txt", "w") as published_standings_out:
            published_standings_out.writelines([f"{line}\n" for line in published_standings if len(line) > 0])

        print(f"scrape end {division_name} : {datetime.now().strftime('%Y/%m/%d - %H:%M:%S')}")

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
    id = 'special-barcelona'
    url = 'BA189xznzDvlCdfoQlBC'
    """
    os.makedirs(args.output_dir, exist_ok=True)
    main_worker(args.id, args.url, args.output_dir)
