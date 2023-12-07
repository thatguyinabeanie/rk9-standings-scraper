from datetime import datetime, timezone
import json
import re
import argparse
import os

from bs4 import BeautifulSoup
import requests

from player import Player
from event import Event


round_structures = [
    (3, 0, 0),
    (4, 0, 2),
    (5, 0, 2),
    (5, 0, 3),
    (6, 0, 3),
    (7, 0, 3),
    (8, 0, 3),
    (9, 5, 3),
    (9, 6, 3)
]


def get_round_count(players, tables):
    index = 0
    if players <= 8:
        pass
    elif players <= 12:
        index = 1
    elif players <= 20:
        index = 2
    elif players <= 32:
        index = 3
    elif players <= 64:
        index = 4
    elif players <= 128:
        index = 5
    elif players <= 226:
        index = 6
    elif players <= 799:
        index = 7
    elif players >= 800:
        index = 8

    if index == 0:
        if len(tables) > 3:
            index = 1
    if index == 1:
        if len(tables[4]) > 2:
            index = 2
    if index == 2:
        if len(tables[5]) > 2:
            index = 3
    if index == 3:
        if len(tables[5]) > 4:
            index = 4
    if index == 4:
        if len(tables[6]) > 4:
            index = 5
    if index == 5:
        if len(tables[7]) > 4:
            index = 6
    if index == 6:
        if len(tables[8]) > 4:
            index = 7
    if index == 7:
        if len(tables[15]) > 4:
            index = 8
    return index


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


def main_worker(directory, link, output_dir):
    url = 'https://rk9.gg/tournament/' + link
    print("Fetching: " + url)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "lxml")

    page_title = soup.find('h3', {'class': 'mb-0'}).text
    title = page_title.split('\n')[0]
    date = page_title.split('\n')[1]
    dates = parse_rk9_date_range(date)
    tour_data = Event(directory, title, dates[0], dates[1], link)
    published_standings = {
        'juniors': [],
        'seniors': [],
        'masters': [],
    }

    url = 'https://rk9.gg/pairings/' + tour_data.rk9_id
    print("Fetching: " + url)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "lxml")

    print('starting at : ' + datetime.now().strftime("%Y/%m/%d - %H:%M:%S"))

    for division_name in tour_data.divisions:
        division = tour_data.divisions[division_name]
        standing = division.standing
        tour_players = standing.players

        rounds_from_url = 0
        for ultag in soup.find_all('ul', {'class': 'nav nav-pills'}):
            for litag in ultag.find_all('li'):
                for aria in litag.find_all('a'):
                    sp = aria.text.split(" ")
                    if sp[0][0:-1].lower() == division_name[0:len(sp[0][0:-1])]:
                        rounds_from_url = int(sp[len(sp) - 1])
                        standing.level = str(aria['aria-controls'])

        rounds_data = soup.find_all("div", id=lambda value: value and value.startswith(standing.level + "R"))

        standing_published_data = soup.find('div', attrs={'id': standing.level + "-standings"})
        published_standings[division_name] = []
        if standing_published_data:
            standing_published = [y for y in [x.strip() for x in standing_published_data.text.split('\n')] if y]
            for line in standing_published:
                data = line.split(' ')
                player = ''
                for i in range(1, len(data)):
                    if i > 1:
                        player += ' '
                    player += data[i]
                published_standings[division_name].append(player.replace('  ', ' '))

        for iRounds in range(rounds_from_url):
            tables = []
            round_data = rounds_data[iRounds]
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
                scores1 = []
                scores2 = []
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
                                p1late = True

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
                                p2late = True

                table_players = []
                if len(player1_name) > 0:
                    standing.player_id = standing.player_id + 1
                    if iRounds == 0:
                        p1 = Player(player1_name, division_name, standing.player_id, p1late)
                        if (len(published_standings[division_name]) > 0 and
                                p1.name not in published_standings[division_name]):
                            p1.dqed = True
                        tour_players.append(p1)
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
                    standing.player_id = standing.player_id + 1
                    if iRounds == 0:
                        p2 = Player(player2_name, division_name, standing.player_id, p2late)
                        if (len(published_standings[division_name]) > 0 and
                                p2.name not in published_standings[division_name]):
                            p2.dqed = True
                        tour_players.append(p2)
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

            standing.tables.append(tables)

        standing_directory = f'{output_dir}/{tour_data.event_id}/{division_name}'
        os.makedirs(standing_directory, exist_ok=True)
        os.makedirs(f'{standing_directory}/players', exist_ok=True)

        with open(f"{standing_directory}/tables.json", 'w') as tables_file:
            json.dump(standing.tables, tables_file, separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/players.json",
                  'w') as jsonPlayers:
            json.dump({
                'players': [{'id': str(player.id), 'name': player.name} for player in tour_players]
            }, jsonPlayers, separators=(',', ':'), ensure_ascii=False)

        # This could/should be handled within the Division object
        nb_players_start = len(tour_players) - len([entry for entry in filter(lambda p: p.late, tour_players)])
        structure_index = get_round_count(nb_players_start, standing.tables)
        print(round_structures[structure_index], [len(round_tables) for round_tables in standing.tables])
        standing.rounds_day1 = round_structures[structure_index][0]
        standing.rounds_day2 = round_structures[structure_index][0] + round_structures[structure_index][1]
        standing.rounds_cut = round_structures[structure_index][2]
        print(f'{len(tour_players)}/{nb_players_start}/{standing.rounds_day1}/{standing.rounds_day2}')
        print(f'{tour_data.event_id}/{division_name}')

        teams = None
        try:
            with open(f"{standing_directory}/teams.json", 'r') as teams_file:
                teams = json.load(teams_file)
        except FileNotFoundError:
            # File is added by team scraping process (currently Flintstoned)
            pass

        winner = None

        post_swiss_players = None
        top_cut = None
        for (i, tables) in enumerate(standing.tables):
            current_round = i + 1
            players_dictionary = {}
            for player in tour_players:
                counter = 0
                while f"{player.name}#{counter}" in players_dictionary:
                    counter += 1
                players_dictionary[f"{player.name}#{counter}"] = player

            top_cut_round = None
            still_playing = 0
            for table in tables:
                players = []
                for player in table['players']:
                    result = []
                    counter = 0
                    while f"{player['name']}#{str(counter)}" in players_dictionary:
                        result.append(players_dictionary[f"{player['name']}#{str(counter)}"])
                        counter += 1

                    match = None
                    if len(result) > 0:
                        for candidate in result:
                            if player['result'] is None and (
                                    candidate.wins == player['record']['wins'] and
                                    candidate.losses == player['record']['losses'] and
                                    candidate.ties == player['record']['ties']):
                                match = candidate
                                still_playing += 1
                            elif player['result'] == 'L' and (
                                    candidate.wins == player['record']['wins'] and
                                    candidate.losses + 1 == player['record']['losses'] and
                                    candidate.ties == player['record']['ties']):
                                match = candidate
                            elif player['result'] == 'T' and (
                                    candidate.wins == player['record']['wins'] and
                                    candidate.losses == player['record']['losses'] and
                                    candidate.ties + 1 == player['record']['ties']):
                                match = candidate
                            elif player['result'] == 'W' and (
                                    candidate.wins + 1 == player['record']['wins'] and
                                    candidate.losses == player['record']['losses'] and
                                    candidate.ties == player['record']['ties']):
                                match = candidate

                            if match:
                                break
                    players.append((match, player['result'], player['dropped']))

                if len(players) == 1:
                    players[0][0].add_match(None, players[0][1], players[0][2], current_round > standing.rounds_day1,
                                            current_round > standing.rounds_day2, table['table'])
                elif len(players) == 2:
                    players[0][0].add_match(players[1][0], players[0][1], players[0][2],
                                            current_round > standing.rounds_day1,
                                            current_round > standing.rounds_day2, table['table'])
                    players[1][0].add_match(players[0][0], players[1][1], players[1][2],
                                            current_round > standing.rounds_day1,
                                            current_round > standing.rounds_day2, table['table'])

                # add match to top cut if relevant
                if current_round >= standing.rounds_day2:
                    if top_cut_round is None:
                        top_cut_round = []
                    try:
                        game_winner = [player['result'] for player in table['players']].index('W')
                    except ValueError:
                        game_winner = None
                    match = {
                        'players': [
                            player[0] for player in players
                        ],
                        'winner': game_winner
                    }
                    top_cut_round.append(match)

            for player in tour_players:
                if (len(player.matches) >= standing.rounds_day1) or standing.rounds_day1 > current_round:
                    player.update_win_percentage(standing.rounds_day1, standing.rounds_day2, current_round)
            for player in tour_players:
                if (len(player.matches) >= standing.rounds_day1) or standing.rounds_day1 > current_round:
                    player.update_opponent_win_percentage(standing.rounds_day1, standing.rounds_day2, current_round)
            for player in tour_players:
                if (len(player.matches) >= standing.rounds_day1) or standing.rounds_day1 > current_round:
                    player.update_oppopp_win_percentage(standing.rounds_day1, standing.rounds_day2, current_round)

            if current_round <= standing.rounds_day2:
                tour_players.sort(key=lambda p: (
                    not p.dqed, p.points, not p.late, round(p.opp_win_percentage * 100, 2),
                    round(p.oppopp_win_percentage * 100, 2)), reverse=True)
                placement = 1
                for player in tour_players:
                    if not player.dqed:
                        player.top_placement = placement
                        placement = placement + 1
                    else:
                        player.top_placement = 9999
            else:
                for place in range(len(tour_players)):
                    if len(tour_players[place].matches) == current_round:
                        if tour_players[place].matches[-1].status == 'W':  # if top win
                            stop = False
                            for above in range(place - 1, -1, -1):
                                if not stop:
                                    if len(tour_players[place].matches) == len(tour_players[above].matches):
                                        if tour_players[above].matches[-1].status == 'W':
                                            # if player above won, stop searching
                                            stop = True
                                        if tour_players[above].matches[-1].status == 'L':
                                            # if player above won, stop searching
                                            temp_placement = tour_players[above].top_placement
                                            tour_players[above].top_placement = tour_players[place].top_placement
                                            tour_players[place].top_placement = temp_placement
                                            tour_players.sort(key=lambda p: (
                                                not p.dqed, len(tour_players) - p.top_placement - 1, p.points,
                                                not p.late, round(p.opp_win_percentage * 100, 2),
                                                round(p.oppopp_win_percentage * 100, 2)), reverse=True)
                                            place = place - 1

            if current_round == standing.rounds_day2 and still_playing == 0:
                post_swiss_players = [player for player in tour_players]

            if current_round == standing.rounds_day2 + 1 and still_playing == 0:
                top_cut = [[]]
                for player in post_swiss_players:
                    try:
                        table = [match for match in top_cut_round if player in match['players']][0]
                        top_cut[0].append({
                            'players': [
                                {
                                    'name': player.name,
                                    'id': player.id
                                } for player in table['players']
                            ],
                            'winner': table['winner']
                        })
                        if len(top_cut[0]) == len(top_cut_round):
                            break
                    except IndexError:
                        pass

            if current_round >= standing.rounds_day2 + 2:
                last_round = top_cut[-1]
                this_round = []
                this_round_ids = []
                for table in last_round:
                    # grab winner ID
                    winner_id = table['players'][table['winner']]['id']
                    # check we don't have them in this_round
                    if winner_id in this_round_ids:
                        break
                    # find match they played in top_cut_round
                    table = [match for match in top_cut_round if winner_id in
                             [player.id for player in match['players']]
                             ][0]
                    # add match to this_round
                    this_round.append({
                        'players': [
                            {
                                'name': player.name,
                                'id': player.id
                            } for player in table['players']
                        ],
                        'winner': table['winner']
                    })
                    for playerId in [player.id for player in table['players']]:
                        this_round_ids.append(playerId)
                top_cut.append(this_round)

            if current_round >= standing.rounds_day2 + standing.rounds_cut and still_playing == 0:
                winner = tour_players[0]
                division.apply_points("International Championship" in tour_data.name)

        if len(tour_players) > 0:
            tour_data.tournament_status = "running"
            tour_data.divisions[division_name].round_number = rounds_from_url
            tour_data.divisions[division_name].player_count = len(tour_players)
            if winner is not None:
                tour_data.divisions[division_name].winner = winner.name

        tour_data.add_to_index(f"{output_dir}/tournaments.json")

        if top_cut is not None:
            with open(f"{standing_directory}/top-cut.json", 'w') as top_cut_export:
                json.dump(top_cut, top_cut_export, separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/tables.csv", 'wb') as csvExport:
            for player in tour_players:
                if player:
                    player.to_csv(csvExport)

        with open(f"{standing_directory}/standings.json", 'w') as json_export:
            json.dump(tour_players, json_export, default=lambda o: o.summary_json(teams), separators=(',', ':'),
                      ensure_ascii=False)

        for player in tour_players:
            with open(f'{standing_directory}/players/{player.id}.json', 'w') as json_export:
                json.dump(player, json_export, default=lambda o: o.to_json(tour_players, teams),
                          separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/discrepancy.txt", 'w') as discrepancy_report:
            if len(published_standings[division_name]) > 0:
                for player in tour_players:
                    if player and player.top_placement - 1 < len(published_standings[division_name]) \
                            and player.name != published_standings[division_name][player.top_placement - 1]:
                        discrepancy_report.write(
                            f"{player.top_placement} {player.name} RK9: {published_standings[division_name][player.top_placement - 1]}\n")

    tour_data.last_updated = datetime.now(timezone.utc).isoformat()

    winners = {
        'juniors': tour_data.divisions['juniors'].winner,
        'seniors': tour_data.divisions['seniors'].winner,
        'masters': tour_data.divisions['masters'].winner,
    }
    if winners['juniors'] is not None and winners['seniors'] is not None and winners['masters'] is not None:
        tour_data.tournament_status = "finished"

    with open(f"{output_dir}/{tour_data.event_id}/tournament.json", "w") as tournament_export:
        json.dump(tour_data.to_dict(), tournament_export, separators=(',', ':'), ensure_ascii=False)

    print('Ending at ' + datetime.now().strftime("%Y/%m/%d - %H:%M:%S") + " with no issues")


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
