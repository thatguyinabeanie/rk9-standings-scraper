from datetime import datetime, timezone
import json
import re
import argparse
import os

from bs4 import BeautifulSoup
import unicodedata
import requests

from standing import Standing
from player import Player


def remove_country(name):
    start = name.find(' [')
    stop = name.find(']')
    if stop - start == 4:
        return name[0:start]
    return name


# removing accents (for js calls)
def strip_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii


# points access for sorting function
def points(elem):
    return elem.points


def init_tournament(ident, name, start_date, end_date, rk9_id):
    return {
        "id": ident,
        "name": name,
        "date": {
            "start": start_date,
            "end": end_date
        },
        "decklists": 0,
        "players": {
            "juniors": 0,
            "seniors": 0,
            "masters": 0
        },
        "winners": {
            "juniors": None,
            "seniors": None,
            "masters": None
        },
        "tournamentStatus": "not-started",
        "roundNumbers": {
            "juniors": None,
            "seniors": None,
            "masters": None
        },
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "rk9link": rk9_id,
    }


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


def add_tournament_to_index(index_filename, tour_data):
    index_data = []

    try:
        with open(index_filename, 'r') as indexFile:
            index_data = json.load(indexFile)
    except OSError:
        pass

    for (i, tour) in enumerate(index_data):
        if tour['id'] == tour_data['id']:
            index_data[i] = tour_data
            break
    else:
        index_data.append(tour_data)

    with open(index_filename, 'w') as indexFile:
        json.dump(index_data, indexFile)


def main_worker(directory, link, output_dir):
    last_page_loaded = ""

    url = 'https://rk9.gg/tournament/' + link
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "lxml")

    page_title = soup.find('h3', {'class': 'mb-0'}).text
    title = page_title.split('\n')[0]
    date = page_title.split('\n')[1]
    dates = parse_rk9_date_range(date)

    rounds = []
    now = datetime.now()
    str_time = now.strftime("%Y/%m/%d - %H:%M:%S")
    print('starting at : ' + str_time)

    standings = [Standing(title, directory, 'juniors', 'Juniors', link, []),
                 Standing(title, directory, 'seniors', 'Seniors', link, []),
                 Standing(title, directory, 'masters', 'Masters', link, [])]

    tour_data = init_tournament(directory, title, dates[0], dates[1], link)

    for standing in standings:
        print(f'Standing : {standing.tournament_name} - in {standing.tournament_directory}/{standing.directory} for {standing.division_name} [{standing.level}/{standing.rounds_day1}/{standing.rounds_day2}]')

        os.makedirs(f'{output_dir}/{standing.tournament_directory}/{standing.directory}', exist_ok=True)

        winner = None
        # requesting RK9 pairings webpage
        url = 'https://rk9.gg/pairings/' + standing.url
        print("\t" + url)
        if last_page_loaded != url:
            last_page_loaded = url
            page = requests.get(url)
            # page content to BeautifulSoup
            soup = BeautifulSoup(page.content, "lxml")

        # finding out how many rounds on the page
        rounds_from_url = 0
        for ultag in soup.find_all('ul', {'class': 'nav nav-pills'}):
            for litag in ultag.find_all('li'):
                for aria in litag.find_all('a'):
                    sp = aria.text.split(" ")
                    if sp[0][0:-1].lower() == standing.division_name[0:len(sp[0][0:-1])].lower():
                        rounds_from_url = int(sp[len(sp) - 1])
                        standing.level = str(aria['aria-controls'])

        are_rounds_set = False
        standing.current_round = rounds_from_url

        rounds_data = soup.find_all("div", id=lambda value: value and value.startswith(standing.level + "R"))

        rounds.append(rounds_from_url)

        # scrapping standings if available, to compare results later
        standing_published_data = soup.find('div', attrs={'id': standing.level + "-standings"})
        published_standings = []
        if standing_published_data:
            standing_published = [y for y in [x.strip() for x in standing_published_data.text.split('\n')] if y]
            for line in standing_published:
                data = line.split(' ')
                player = ''
                for i in range(1, len(data)):
                    if i > 1:
                        player += ' '
                    player += data[i]
                published_standings.append(player.replace('  ', ' '))

        for iRounds in range(rounds_from_url):
            players_dictionary = {}
            for player in standing.players:
                counter = 0
                while f"{player.name}#{counter}" in players_dictionary:
                    counter += 1
                players_dictionary[f"{player.name}#{counter}"] = player

            tables = []
            round_data = rounds_data[iRounds]
            matches = round_data.find_all('div', attrs={'class': 'match'})
            still_playing = 0
            for match_data in matches:
                player1_name = ""
                player2_name = ""
                p1status = -1
                p2status = -1
                p1dropped = False
                p2dropped = False
                p1late = 0
                p2late = 0
                scores1 = []
                scores2 = []
                p1 = None
                p2 = None
                table = "0"

                table_data = match_data.find('div', attrs={'class': 'col-2'})
                if table_data:
                    table_data = table_data.find('span', attrs={'class': 'tablenumber'})
                    if table_data:
                        table = table_data.text

                player_data = match_data.find('div', attrs={'class': 'player1'})
                text_data = player_data.text.split('\n')
                name = player_data.find('span', attrs={'class': 'name'})
                if name:
                    score = text_data[3].strip().replace('(', '').replace(')', '')
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
                        if iRounds + 1 < rounds_from_url:
                            p1status = 0
                            if iRounds == 0:
                                p1late = -1

                player_data = match_data.find('div', attrs={'class': 'player2'})
                text_data = player_data.text.split('\n')
                name = player_data.find('span', attrs={'class': 'name'})
                if name:
                    score = text_data[3].strip().replace('(', '').replace(')', '')
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
                        if iRounds + 1 < rounds_from_url:
                            p2status = 0
                            if iRounds == 0:
                                p2late = -1

                result = []
                counter = 0
                while player1_name + '#' + str(counter) in players_dictionary:
                    result.append(players_dictionary[player1_name + '#' + str(counter)])
                    counter += 1

                if len(result) > 0:
                    for player in result:
                        if p1status == -1 and (
                                player.wins == scores1[0] and player.losses == scores1[1] and player.ties ==
                                scores1[2]):
                            p1 = player
                            still_playing += 1
                        elif p1status == 0 and (
                                player.wins == scores1[0] and player.losses + 1 == scores1[1] and player.ties ==
                                scores1[2]):
                            p1 = player
                        elif p1status == 1 and (
                                player.wins == scores1[0] and player.losses == scores1[1] and player.ties + 1 ==
                                scores1[2]):
                            p1 = player
                        elif p1status == 2 and (
                                player.wins + 1 == scores1[0] and player.losses == scores1[1] and player.ties ==
                                scores1[2]):
                            p1 = player

                        if p1dropped:
                            if p1 is None:
                                if player.wins == scores1[0] and player.losses == scores1[1] and player.ties == \
                                        scores1[2]:
                                    p1 = player
                            else:
                                p1.dropRound = iRounds + 1
                        if p1:
                            break

                result = []
                counter = 0
                while player2_name + '#' + str(counter) in players_dictionary:
                    result.append(players_dictionary[player2_name + '#' + str(counter)])
                    counter += 1

                if len(result) > 0:
                    for player in result:
                        if p2status == -1 and (
                                player.wins == scores2[0] and player.losses == scores2[1] and player.ties ==
                                scores2[2]):
                            p2 = player
                            still_playing += 1
                        elif p2status == 0 and (
                                player.wins == scores2[0] and player.losses + 1 == scores2[1] and player.ties ==
                                scores2[2]):
                            p2 = player
                        elif p2status == 1 and (
                                player.wins == scores2[0] and player.losses == scores2[1] and player.ties + 1 ==
                                scores2[2]):
                            p2 = player
                        elif p2status == 2 and (
                                player.wins + 1 == scores2[0] and player.losses == scores2[1] and player.ties ==
                                scores2[2]):
                            p2 = player

                        if p2dropped:
                            if p2 is None:
                                if player.wins == scores2[0] and player.losses == scores2[1] and player.ties == \
                                        scores2[2]:
                                    p2 = player
                            else:
                                p2.dropRound = iRounds + 1
                        if p2:
                            break

                if p1 is None:
                    if len(player1_name) > 0:
                        standing.player_id = standing.player_id + 1
                        p1 = Player(player1_name, standing.division_name, standing.player_id, p1late)
                        if p1.name in standing.dqed or (
                                len(published_standings) > 0 and p1.name not in published_standings):
                            p1.dqed = True
                        standing.players.append(p1)

                if p2 is None:
                    if len(player2_name) > 0:
                        standing.player_id = standing.player_id + 1
                        p2 = Player(player2_name, standing.division_name, standing.player_id, p2late)
                        if p2.name in standing.dqed or (
                                len(published_standings) > 0 and p2.name not in published_standings):
                            p2.dqed = True
                        standing.players.append(p2)

                if p1:
                    p1.add_match(p2, p1status, p1dropped, iRounds + 1 > standing.rounds_day1,
                                 iRounds + 1 > standing.rounds_day2, table)
                if p2:
                    p2.add_match(p1, p2status, p2dropped, iRounds + 1 > standing.rounds_day1,
                                 iRounds + 1 > standing.rounds_day2, table)

                if p1 is not None and p2 is not None:
                    tables.append({
                        'table': int(table),
                        'players': [
                            {
                                'name': p1.name,
                                'result': {-1: None, 0: 'L', 1: 'T', 2: 'W'}[p1status],
                                'record': {
                                    'wins': p1.wins,
                                    'losses': p1.losses,
                                    'ties': p1.ties
                                }
                            },
                            {
                                'name': p2.name,
                                'result': {-1: None, 0: 'L', 1: 'T', 2: 'W'}[p2status],
                                'record': {
                                    'wins': p2.wins,
                                    'losses': p2.losses,
                                    'ties': p2.ties
                                }
                            }
                        ]
                    })

            standing.tables.append({'tables': tables})

            if len(standing.hidden) > 0:
                for player in standing.players:
                    if player.name in standing.hidden:
                        standing.players.remove(player)

            nb_players = len(standing.players)

            for player in standing.players:
                if (len(player.matches) >= standing.rounds_day1) or standing.rounds_day1 > iRounds + 1:
                    player.update_win_percentage(standing.rounds_day1, standing.rounds_day2, iRounds + 1)
            for player in standing.players:
                if (len(player.matches) >= standing.rounds_day1) or standing.rounds_day1 > iRounds + 1:
                    player.update_opponent_win_percentage(standing.rounds_day1, standing.rounds_day2, iRounds + 1)
            for player in standing.players:
                if (len(player.matches) >= standing.rounds_day1) or standing.rounds_day1 > iRounds + 1:
                    player.update_oppopp_win_percentage(standing.rounds_day1, standing.rounds_day2, iRounds + 1)

            if iRounds + 1 <= standing.rounds_day2:
                standing.players.sort(key=lambda p: (
                    not p.dqed, p.points, p.late, round(p.OppWinPercentage * 100, 2),
                    round(p.OppOppWinPercentage * 100, 2)), reverse=True)
                placement = 1
                for player in standing.players:
                    if not player.dqed:
                        player.topPlacement = placement
                        placement = placement + 1
                    else:
                        player.topPlacement = 9999
            else:
                if iRounds + 1 > standing.rounds_day2:
                    for place in range(nb_players):
                        if len(standing.players[place].matches) == iRounds + 1:
                            if standing.players[place].matches[
                                    len(standing.players[place].matches) - 1].status == 2:  # if top win
                                stop = False
                                for above in range(place - 1, -1, -1):
                                    if not stop:
                                        if len(standing.players[place].matches) == len(
                                                standing.players[above].matches):
                                            if standing.players[above].matches[len(standing.players[
                                                    place].matches) - 1].status == 2:
                                                # if player above won, stop searching
                                                stop = True
                                            if standing.players[above].matches[len(standing.players[
                                                    place].matches) - 1].status == 0:
                                                # if player above won, stop searching
                                                temp_placement = standing.players[above].topPlacement
                                                standing.players[above].topPlacement = standing.players[
                                                    place].topPlacement
                                                standing.players[place].topPlacement = temp_placement
                                                standing.players.sort(key=lambda p: (
                                                    not p.dqed, nb_players - p.topPlacement - 1, p.points, p.late,
                                                    round(p.OppWinPercentage * 100, 2),
                                                    round(p.OppOppWinPercentage * 100, 2)), reverse=True)
                                                place = place - 1

            if standing.rounds_day1 == 999:
                are_rounds_set = True
                if 4 <= nb_players <= 8:
                    standing.rounds_day1 = 3
                    standing.rounds_day2 = 3
                    standing.rounds_cut = 0
                if 9 <= nb_players <= 12:
                    standing.rounds_day1 = 4
                    standing.rounds_day2 = 4
                    standing.rounds_cut = 2
                if 13 <= nb_players <= 20:
                    standing.rounds_day1 = 5
                    standing.rounds_day2 = 5
                    standing.rounds_cut = 2
                if 21 <= nb_players <= 32:
                    standing.rounds_day1 = 5
                    standing.rounds_day2 = 5
                    standing.rounds_cut = 3
                if 33 <= nb_players <= 64:
                    standing.rounds_day1 = 6
                    standing.rounds_day2 = 6
                    standing.rounds_cut = 3
                if 65 <= nb_players <= 128:
                    standing.rounds_day1 = 7
                    standing.rounds_day2 = 7
                    standing.rounds_cut = 3
                if 129 <= nb_players <= 226:
                    standing.rounds_day1 = 8
                    standing.rounds_day2 = 8
                    standing.rounds_cut = 3
                if 227 <= nb_players <= 799:
                    standing.rounds_day1 = 9
                    standing.rounds_day2 = 14
                    standing.rounds_cut = 3
                if nb_players >= 800:
                    standing.rounds_day1 = 9
                    standing.rounds_day2 = 15
                    standing.rounds_cut = 3

            if are_rounds_set is True and iRounds == 0:
                print(f'Standing : {standing.tournament_name} - in {standing.tournament_directory}/{standing.directory} for {standing.division_name} NbPlayers: {len(standing.players)} -> [{standing.level}/{standing.rounds_day1}/{standing.rounds_day2}]')
                with open(f"{output_dir}/{standing.tournament_directory}/{standing.directory}/players.json",
                          'w') as jsonPlayers:
                    json.dump({
                        'players': [{'id': str(player.id), 'name': player.name} for player in standing.players]
                    }, jsonPlayers, separators=(',', ':'), ensure_ascii=False)

            if iRounds + 1 == standing.rounds_day2 + standing.rounds_cut and still_playing == 0:
                winner = standing.players[0]

        with open(f"{output_dir}/{standing.tournament_directory}/{standing.directory}/tables.json",
                  'w') as tables_file:
            json.dump(standing.tables, tables_file, separators=(',', ':'), ensure_ascii=False)

        if len(standing.players) > 0:
            tour_data['lastUpdated'] = datetime.now(timezone.utc).isoformat()
            tour_data['roundNumbers'][standing.directory.lower()] = rounds_from_url
            tour_data['players'][standing.directory.lower()] = len(standing.players)
            if winner is not None:
                tour_data['winners'][standing.directory.lower()] = winner.name
            if winner is not None and standing.directory.lower() == 'masters':
                tour_data['tournamentStatus'] = "finished"
            else:
                tour_data['tournamentStatus'] = "running"

        add_tournament_to_index(f"{output_dir}/tournaments.json", tour_data)

        with open(f"{output_dir}/{standing.tournament_directory}/tournament.json", "w") as tournament_export:
            json.dump(tour_data, tournament_export, separators=(',', ':'), ensure_ascii=False)

        with open(f"{output_dir}/{standing.tournament_directory}/{standing.directory}/tables.csv", 'wb') as csvExport:
            for player in standing.players:
                if player:
                    player.to_csv(csvExport)

        with open(f"{output_dir}/{standing.tournament_directory}/{standing.directory}/standings.json", 'w') as json_export:
            json.dump(standing.players, json_export, default=lambda o: o.to_json(), separators=(',', ':'),
                      ensure_ascii=False)

        with open(f"{output_dir}/{standing.tournament_directory}/{standing.directory}/discrepancy.txt",
                  'w') as discrepancy_report:
            if len(published_standings) > 0:
                for player in standing.players:
                    if player and player.topPlacement - 1 < len(published_standings) and player.name != \
                            published_standings[player.topPlacement - 1]:
                        discrepancy_report.write(
                            f"{player.topPlacement} RK9: {published_standings[player.topPlacement - 1]} --- {player.name}\n")

    now = datetime.now()  # current date and time
    print('Ending at ' + now.strftime("%Y/%m/%d - %H:%M:%S") + " with no issues")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--id")
    parser.add_argument("--output-dir", help="output directory", default='.')

    args = parser.parse_args()

    """exemple: (Barcelona)
    id = '0000090'
    url = 'BA189xznzDvlCdfoQlBC'
    """
    os.makedirs(args.output_dir, exist_ok=True)
    main_worker(args.id, args.url, args.output_dir)
