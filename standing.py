import math

round_structures = [
        (3, 0, False),
        (4, 0, True),
        (6, 0, True),
        (7, 0, True),
        (6, 2, True),
        (7, 2, True),
        (8, 2, True),
        (8, 3, True),
        (8, 4, True),
        (9, 4, True),
        (9, 5, True)
]


def get_round_count(players, tables):
    index = 0
    if players > 4096:
        index = 10
    elif players > 2048:
        index = 9
    elif players > 1024:
        index = 8
    elif players > 512:
        index = 7
    elif players > 256:
        index = 6
    elif players > 128:
        index = 5
    elif players > 64:
        index = 4
    elif players > 32:
        index = 3
    elif players > 16:
        index = 2
    elif players > 8:
        index = 1

    (rounds_day1, rounds_day2, has_cut) = round_structures[index]
    rounds_swiss = rounds_day1 + rounds_day2
    rounds_cut = 0
    if has_cut and len(tables) >= (rounds_swiss + 1):
        rounds_cut = math.ceil(math.log2(len(tables[rounds_swiss]) * 2))

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
