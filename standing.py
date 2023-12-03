class Standing:
    def __init__(self):
        self.level = ""
        self.rounds_day1 = 999
        self.rounds_day2 = 999
        self.rounds_cut = 999
        self.players = []
        self.player_id = 1
        self.tables = []

    def __repr__(self):
        output = f'{self.level}/{self.rounds_day1}/{self.rounds_day2}/{self.rounds_cut}'
        return output

    def __str__(self):
        output = f'{self.level}/{self.rounds_day1}/{self.rounds_day2}/{self.rounds_cut}'
        return output
