import math

round_structures = [
    (3, 0, False),
    (4, 0, True),
    (5, 0, True),
    (5, 0, True),
    (6, 0, True),
    (7, 0, True),
    (8, 0, True),
    (9, 5, True),
    (9, 6, True)
]


def get_round_count(players, tables):
    index = 0
    if players >= 800:
        index = 8
    elif players > 226:
        index = 7
    elif players > 128:
        index = 6
    elif players > 64:
        index = 5
    elif players > 32:
        index = 4
    elif players > 20:
        index = 3
    elif players > 12:
        index = 2
    elif players > 8:
        index = 1

    if index == 0 and len(tables) > 3:
            index = 1
    if index == 1 and len(tables) > 4 and len(tables[4]) > 2:
            index = 2
    if index == 2 and len(tables) > 5 and len(tables[5]) > 2:
            index = 3
    if index == 3 and len(tables) > 5 and len(tables[5]) > 4:
            index = 4
    if index == 4 and len(tables) > 6 and len(tables[6]) > 4:
            index = 5
    if index == 5 and len(tables) > 7 and len(tables[7]) > 4:
            index = 6
    if index == 6 and len(tables) > 8 and len(tables[8]) > 4:
            index = 7
    if index == 7 and len(tables) > 15 and len(tables[15]) > 4:
            index = 8

    (rounds_day1, rounds_day2, has_cut) = round_structures[index]
    rounds_swiss = rounds_day1 + rounds_day2
    rounds_cut = 0
    if has_cut and len(tables) >= (rounds_swiss + 1):
        rounds_cut = math.log2(len(tables[rounds_swiss]) * 2)

    return (rounds_day1, rounds_day2, rounds_cut)


class Standing:
    def __init__(self, players, tables):
        self.players = players
        self.tables = tables
        starting_players = len(players) - len([entry for entry in filter(lambda p: p.late, players)])
        structure = get_round_count(starting_players, tables)
        self.rounds_day1 = structure[0]
        self.rounds_day2 = structure[0] + structure[1]
        self.rounds_cut = structure[2]

    def __repr__(self):
        output = f'{self.rounds_day1}/{self.rounds_day2}/{self.rounds_cut}'
        return output

    def __str__(self):
        output = f'{self.rounds_day1}/{self.rounds_day2}/{self.rounds_cut}'
        return output
