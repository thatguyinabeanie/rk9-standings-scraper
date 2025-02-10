from datetime import datetime, timezone
import json
import argparse
import os

from player import Player
from event import Event


def get_last_round(matches):
    result = []
    player_count = len(matches) * 2
    for match in matches:
        flip = False
        for player in match:
            if flip:
                result.append((player_count*2 - player - 1, player))
            else:
                result.append((player, player_count*2 - player - 1))
            flip = not flip
    return result


# returns a list of the higher ranked player in each match of the first round
# used to determine bracket seeding
def single_elim_order(players):
    matches = [(0, 1)]
    while len(matches) * 2 < players:
        matches = get_last_round(matches)
    return [min(match[0], match[1]) for match in matches]


def main_worker(directory, output_dir, input_dir, season):
    with open(f"{input_dir}/{directory}/tournament.json", "r") as tournament_export:
        raw_tour = json.load(tournament_export)
        try:
            tour_data = Event(raw_tour['id'], raw_tour['name'], raw_tour['date']['start'], raw_tour['date']['end'],
                              'rk9', raw_tour['rk9link'], int(season))
        except KeyError:
            tour_data = Event(raw_tour['id'], raw_tour['name'], raw_tour['date']['start'], raw_tour['date']['end'],
                              'playlatam', raw_tour['playlatamlink'], int(season))

    for division_name in tour_data.divisions:
        standing_directory = f'{output_dir}/{tour_data.event_id}/{division_name}'
        standing_directory_in = f'{input_dir}/{tour_data.event_id}/{division_name}'
        os.makedirs(standing_directory, exist_ok=True)

        division = tour_data.divisions[division_name]
        try:
            with (open(f"{standing_directory_in}/tables.json", 'r') as tables_file,
                  open(f"{standing_directory_in}/players.json", 'r') as players_file):
                division.load_data(
                    [Player(player['name'], player['division'], int(player_id), player['late'], player['dqed'])
                     for player_id, player in json.load(players_file).items()],
                    json.load(tables_file))
        except FileNotFoundError:
            continue

        confirm = {}
        try:
            with open(f"{standing_directory_in}/confirm.json") as confirm_file:
                confirm = json.load(confirm_file)
        except FileNotFoundError:
            pass

        try:
            with open(f"{standing_directory_in}/published_standings.txt") as pub_standings_file:
                published_standings = [line.strip() for line in pub_standings_file.readlines()]
        except FileNotFoundError:
            published_standings = []

        standing = division.standing
        tour_players = standing.players
        print(f'{tour_data.event_id}/{division_name}')

        winner = None

        last_round_standings = None
        top_cut = None
        for (i, tables) in enumerate(standing.tables):
            current_round = i + 1
            players_dictionary = {}
            matched_dictionary = {}
            for player in tour_players:
                counter = 0
                while f"{player.name}#{counter}" in players_dictionary:
                    counter += 1
                players_dictionary[f"{player.name}#{counter}"] = player
                matched_dictionary[f"{player.name}#{counter}"] = False

            top_cut_round = None
            still_playing = 0
            for table in tables:
                players = []
                for (p, player) in enumerate(table['players']):
                    match = None
                    try:
                        candidate_key = f"{current_round}/{table['table']}"
                        match = [candidate for candidate in tour_players if candidate.id == confirm[candidate_key][p]][0]
                        print(candidate_key, p, confirm[candidate_key])
                    except KeyError:
                        result = []
                        counter = 0
                        while f"{player['name']}#{str(counter)}" in players_dictionary:
                            result.append([f"{player['name']}#{str(counter)}", players_dictionary[f"{player['name']}#{str(counter)}"]])
                            counter += 1
                        result.reverse()

                        if len(result) > 0:
                            for [player_hash, candidate] in result:
                                if matched_dictionary[player_hash] == True:
                                    continue

                                if player['result'] is None and (
                                        candidate.wins == player['record']['wins'] and
                                        candidate.losses <= player['record']['losses'] and
                                        candidate.ties == player['record']['ties']):
                                    match = candidate
                                    still_playing += 1
                                elif player['result'] == 'L' and (
                                        candidate.wins == player['record']['wins'] and
                                        candidate.losses + 1 <= player['record']['losses'] and
                                        candidate.ties == player['record']['ties']):
                                    match = candidate
                                elif player['result'] == 'T' and (
                                        candidate.wins == player['record']['wins'] and
                                        candidate.losses <= player['record']['losses'] and
                                        candidate.ties + 1 == player['record']['ties']):
                                    match = candidate
                                elif player['result'] == 'W' and (
                                        candidate.wins + 1 == player['record']['wins'] and
                                        candidate.losses <= player['record']['losses'] and
                                        candidate.ties == player['record']['ties']):
                                    match = candidate

                                if match:
                                    for i in range(current_round - match.wins - match.losses - match.ties - 1):
                                        match.add_match(None, 'L', False, False, False, 0)
                                    matched_dictionary[player_hash] = True
                                    result.append(players_dictionary[player_hash])
                                    break
                            else:
                                new_player = Player(player['name'], division_name, len(tour_players) + 2, True, False)
                                for i in range(current_round - 1):
                                    new_player.add_match(None, 'L', False, False, False, 0)
                                tour_players.add(new_player)
                                match = new_player

                    players.append((match, player['result'], player['dropped']))

                try:
                    if len(players) == 1 and players[0][0] is not None:
                        players[0][0].add_match(None, players[0][1], players[0][2], current_round > standing.rounds_day1,
                                                current_round > standing.rounds_day2, table['table'])
                    elif len(players) == 2:
                        players[0][0].add_match(players[1][0], players[0][1], players[0][2],
                                                current_round > standing.rounds_day1,
                                                current_round > standing.rounds_day2, table['table'])
                        players[1][0].add_match(players[0][0], players[1][1], players[1][2],
                                                current_round > standing.rounds_day1,
                                                current_round > standing.rounds_day2, table['table'])
                except AttributeError as e:
                    print(players, table)
                    raise e

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
                player.update_win_percentage(standing.rounds_day1, standing.rounds_day2, current_round)
            for player in tour_players:
                player.update_opponent_win_percentage(standing.rounds_day1, standing.rounds_day2, current_round)
            for player in tour_players:
                player.update_oppopp_win_percentage(standing.rounds_day1, standing.rounds_day2, current_round)

            if current_round <= standing.rounds_day2:
                tour_players.sort(key=lambda p: (
                    not p.dqed, p.points, round(p.opp_win_percentage * 100, 2),
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
                                                len(tour_players) - p.top_placement - 1, p.points,
                                                round(p.opp_win_percentage * 100, 2),
                                                round(p.oppopp_win_percentage * 100, 2)), reverse=True)
                                            place = place - 1

            if current_round == standing.rounds_day2 and still_playing == 0:
                last_round_standings = [player for player in tour_players]

            if current_round == standing.rounds_day2 + 1:
                top_cut = [[]]
                for match in top_cut_round:
                    top_cut[0].append({
                        'players': [
                            {
                                'name': player.name,
                                'id': player.id,
                            } for player in match['players']
                        ],
                        'winner': match['winner']
                    })

            if current_round >= standing.rounds_day2 + 2:
                last_round = top_cut[-1]
                this_round = []
                this_round_ids = []
                for table in last_round:
                    # grab winner ID
                    winner_id = table['players'][table['winner']]['id']
                    # check we don't have them in this_round
                    if winner_id in this_round_ids:
                        continue
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
                if not ("World Championships" in tour_data.name):
                    division.apply_points("International Championship" in tour_data.name)

        tour_players.sort(key=lambda p: p.dqed)

        if len(tour_players) > 0:
            tour_data.divisions[division_name].round_number = len(standing.tables)
            tour_data.divisions[division_name].player_count = len(tour_players)
            if winner is not None:
                tour_data.divisions[division_name].winner = winner.name

        tour_data.add_to_index(f"{output_dir}/tournaments.json")

        if top_cut is not None:
            with open(f"{standing_directory}/top-cut.json", 'w') as top_cut_export:
                json.dump({
                    'totalRounds': standing.rounds_cut,
                    'rounds': top_cut
                }, top_cut_export, separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/tables.csv", 'wb') as csvExport:
            for player in tour_players:
                if player:
                    player.to_csv(csvExport)

        teams = None
        try:
            with open(f"{standing_directory_in}/teams.json", 'r') as teams_file:
                teams = json.load(teams_file)
        except FileNotFoundError:
            # File is added by team scraping process (currently Flintstoned)
            pass

        with open(f"{standing_directory}/standings.json", 'w') as json_export:
            json.dump([player.id for player in tour_players], json_export,
                      separators=(',', ':'), ensure_ascii=False)

        with open(f'{standing_directory}/players.json', 'w') as json_export:
            json.dump({player.id: player for player in tour_players},
                    json_export, default=lambda o: o.to_json(tour_players, standing, teams),
                    separators=(',', ':'), ensure_ascii=False)

        with open(f"{standing_directory}/discrepancy.txt", 'w') as discrepancy_report:
            if len(published_standings) > 0:
                for player in tour_players:
                    if player and player.top_placement - 1 < len(published_standings) \
                            and player.name != published_standings[player.top_placement - 1]:
                        discrepancy_report.write(
                            f"{player.top_placement} {player.name} RK9: {published_standings[player.top_placement - 1]}\n")

    tour_data.last_updated = datetime.now(timezone.utc).isoformat()

    with open(f"{output_dir}/{tour_data.event_id}/tournament.json", "w") as tournament_export:
        json.dump(tour_data.to_dict(), tournament_export, separators=(',', ':'), ensure_ascii=False)

    print('Ending at ' + datetime.now().strftime("%Y/%m/%d - %H:%M:%S") + " with no issues")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--id")
    parser.add_argument("--output-dir", help="output directory", default='.')
    parser.add_argument("--input-dir", help="input directory", default='.')
    parser.add_argument("--season", help="VGC season the tournament is for", default='2025')

    args = parser.parse_args()

    """exemple: (Barcelona)
    id = 'special-barcelona'
    url = 'BA189xznzDvlCdfoQlBC'
    """
    os.makedirs(args.output_dir, exist_ok=True)
    main_worker(args.id, args.output_dir, args.input_dir, args.season)

