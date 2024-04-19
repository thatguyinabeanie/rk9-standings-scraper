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
        if len(tables) > 4 and len(tables[4]) > 2:
            index = 2
    if index == 2:
        if len(tables) > 5 and len(tables[5]) > 2:
            index = 3
    if index == 3:
        if len(tables) > 5 and len(tables[5]) > 4:
            index = 4
    if index == 4:
        if len(tables) > 6 and len(tables[6]) > 4:
            index = 5
    if index == 5:
        if len(tables) > 7 and len(tables[7]) > 4:
            index = 6
    if index == 6:
        if len(tables) > 8 and len(tables[8]) > 4:
            index = 7
    if index == 7:
        if len(tables) > 15 and len(tables[15]) > 4:
            index = 8
    return round_structures[index]


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
