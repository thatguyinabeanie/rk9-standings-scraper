# class Match : VS a player, with a status [W/L/T -> 2/0/1] and a table number
class Match:
    def __init__(self, player, status, table):
        self.player = player
        self.status = status
        self.table = table


# class Player
class Player:
    # player constructor
    # (name, level[junior, senior, master], id [unique number, incremental], late [0 if not, -1 if late])
    def __init__(self, name, level, player_id, late, dqed):
        self.name = name
        self.level = level

        # W/T/L counters
        self.wins = 0
        self.ties = 0
        self.losses = 0
        # W/T/L counters for day 2
        self.wins2 = 0
        self.ties2 = 0
        self.losses2 = 0

        # minimum/maximum points. Used for the R/Y/G colors for Day2/TopCut (not 100% working)
        self.min_points = 0
        self.max_points = 0

        # nb matches completed
        self.completed_matches = 0

        # points (3*W+T)
        self.points = 0

        # list of matches
        self.matches = []
        # player id in tournament (from 1 to ...) : incremented everytime a new player is found on the pairings' page
        self.id = player_id

        # resistances, minimum 0
        # source:
        # - https://www.pokemon.com/us/play-pokemon/about/tournaments-rules-and-resources
        # - Play! Pokémon Tournament Rules Handbook

        # player resistance
        self.win_percentage = 0.25
        # opponents' resistance
        self.opp_win_percentage = 0.25
        # opponents' opponents' resistance
        self.oppopp_win_percentage = 0.25

        # if player is dropped, dropRound > 0
        self.drop_round = -1

        # placement after sorting players
        self.top_placement = 0
        self.awards_placement = None

        # country if found in /roster/ or within the player's name in the pairings (between [])
        self.country = ""

        # if late : loss round 1 with a drop but back playing round 2
        self.late = late

        # dqed flag : manually added if known, or if player is not in the final published standings
        self.dqed = dqed

        # country extraction ISO 3166-1 alpha-2 (2 letters)
        if self.name[len(self.name) - 1] == ']':
            self.country = self.name[len(self.name) - 3:len(self.name) - 1].lower()

    # addMatch function : adding a game versus another player
    # player : VS player
    # status : -1 still playing / 0 loss / 1 tie / 2 win
    # drop : drop found (loss+drop attributes)
    # isDay2 : is a day 2 match
    # isTop : is a top cut match
    # table : table #
    def add_match(self, player, status, dropped, is_day2, is_top, table):
        if self.drop_round > -1:
            # reset for late players
            self.drop_round = -1
        if status == 'L':
            if player is None:
                # player is late
                player = Player("LATE", "none", 0, 0, False)
            self.losses += 1
            if is_day2 and not is_top:
                # day 2 swiss
                self.losses2 += 1
            self.completed_matches += 1
        if status == 'T':
            self.ties += 1
            if is_day2 and not is_top:
                # day 2 swiss
                self.ties2 += 1
            self.completed_matches += 1
        if status == 'W':
            if player is None:
                # player got a bye
                player = Player("BYE", "none", 0, 0, False)
            self.wins += 1
            if is_day2 and not is_top:
                # day 2 swiss
                self.wins2 += 1
            self.completed_matches += 1
        self.points = self.wins * 3 + self.ties
        self.matches.append(Match(player, status, table))
        if dropped:
            self.drop_round = len(self.matches)

    # update player's win percentage
    # day1Rounds : number of round in day 1
    # day2Rounds : number of round in day 2
    # currentRound...
    # resistance is calculated every round
    def update_win_percentage(self, day1_rounds, day2_rounds, current_round):
        if self.drop_round == -1 or self.drop_round == current_round:
            self.win_percentage = 0
            val = 0
            count = 0
            counter = 0
            for match in self.matches:
                if ((len(self.matches) >= day1_rounds and day1_rounds <= counter < day2_rounds)
                        or len(self.matches) <= day1_rounds or day1_rounds == 0):
                    if match.player is not None and not (match.player.name == "BYE"):
                        if match.status == 'W':
                            val = val + 1
                        if match.status == 'T':
                            val = val + 0.5
                        if match.status == 'L':
                            val = val + 0
                        if match.status is not None:
                            count = count + 1
                counter = counter + 1
            if count > 0:
                val = val / count
            if val < 0.25:
                val = 0.25
            if self.drop_round > 0 and self.drop_round != day1_rounds and self.drop_round != day2_rounds:
                if val > 0.75:
                    val = 0.75
            self.win_percentage = val

    # same as update_win_percentage but Opp Win percentage
    def update_opponent_win_percentage(self, day1_rounds, day2_rounds, current_round):
        if ((self.drop_round == -1 or self.drop_round == current_round)
                and (len(self.matches) > day1_rounds or current_round <= day1_rounds)):
            val = 0
            count = 0
            counter = 0
            for match in self.matches:
                if match.player is not None and not (match.player.id == 0):
                    win_percentage = match.player.win_percentage
                    if win_percentage > 0:
                        val = val + win_percentage
                        count = count + 1
                counter = counter + 1
            if count > 0:
                val = val / count
            if val < 0.25:
                val = 0.25
            self.opp_win_percentage = val

    # same as UpdateWinP but Opp Opp Win percentage
    def update_oppopp_win_percentage(self, day1_rounds, day2_rounds, current_round):
        if (self.drop_round == -1 or self.drop_round == current_round) and (
                (current_round > day1_rounds and len(self.matches) > day1_rounds) or (current_round <= day1_rounds)):
            val = 0
            count = 0
            counter = 0
            for match in self.matches:
                if match.player is not None and not (match.player.id == 0):
                    val = val + match.player.opp_win_percentage
                    count = count + 1
                counter = counter + 1
            if count > 0:
                val = val / count
            if val < 0.25:
                val = 0.25
            self.oppopp_win_percentage = val

    # special logging/debug methods to output some data
    def __repr__(self):
        output = f"{self.name}{'*' if self.late else ''} ({self.level}) {self.wins}-{self.losses}-{self.ties} -- {self.points}pts"
        return output

    def __str__(self):
        output = f"{self.name} ({self.level}) {self.wins}-{self.losses}-{self.ties} -- {self.points}pts"
        for match in self.matches:
            output += "\n"
            output += "\tVs. " + match.player.name + " "
            if match.status == 0:
                output += "L"
            if match.status == 1:
                output += "T"
            if match.status == 2:
                output += "W"
        output += "\n\n"
        return output

    # ToCSV
    def to_csv(self, file):
        current_round = 1
        points = 0
        for match in self.matches:
            file.write((self.name + '\t').encode())
            if match.player is not None:
                file.write((match.player.name + '\t').encode())
            if match.status == 'L':
                file.write('L\t'.encode())
            if match.status == 'T':
                file.write('T\t'.encode())
                points += 1
            if match.status == 'W':
                file.write('W\t'.encode())
                points += 3
            file.write((str(points) + '\t').encode())
            file.write((str(current_round) + '\n').encode())
            current_round += 1

    # toJson
    def to_json(self, players, standing, teams):
        matches = [
            {
                'id': getattr(match.player, 'id', 0),
                'result': match.status,
                'table': int(match.table)
            } for match in self.matches
        ]
        round_sets = []
        round_sets.append({
            'name': 'Swiss' if standing.rounds_day2 == standing.rounds_day1 else 'Day 1 Swiss',
            'rounds': matches[:standing.rounds_day1]
        })

        if standing.rounds_day2 > standing.rounds_day1 and len(matches) > standing.rounds_day1:
            round_sets.append({
                'name': 'Day 2 Swiss',
                'rounds': matches[standing.rounds_day1:standing.rounds_day2]
            })

        if standing.rounds_cut != 0 and len(matches) > standing.rounds_day2:
            round_sets.append({
                'name': 'Top Cut',
                'rounds': matches[standing.rounds_day2:]
            })

        result = {
            'id': self.id,
            'name': self.name,
            'placing': self.top_placement,
            'top': self.awards_placement,
            'record': {
                'wins': self.wins,
                'losses': self.losses,
                'ties': self.ties
            },
            'resistances': {
                'self': self.win_percentage,
                'opp': self.opp_win_percentage,
                'oppopp': self.oppopp_win_percentage
            },
            'drop': self.drop_round,
            'rounds': round_sets
        }

        if teams is not None:
            result['team'] = teams[f'{self.id}']['fullTeam']
            result['paste'] = teams[f'{self.id}']['paste']

        return result

    def summary_json(self, teams):
        result = {
            'id': self.id,
            'name': self.name,
            'placing': self.top_placement,
            'record': {
                'wins': self.wins,
                'losses': self.losses,
                'ties': self.ties
            },
            'resistances': {
                'self': self.win_percentage,
                'opp': self.opp_win_percentage,
                'oppopp': self.oppopp_win_percentage
            },
            'drop': self.drop_round
        }

        if teams is not None:
            result['team'] = teams[f'{self.id}']['team']
            result['paste'] = teams[f'{self.id}']['paste']

        return result
