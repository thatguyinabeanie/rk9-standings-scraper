class Standing:
    def __init__(self):
        self.level = ""
        self.rounds_day1 = None
        self.rounds_day2 = None
        self.rounds_cut = None
        self.players = []
        self.player_id = 1
        self.tables = []

    def __repr__(self):
        output = f'{self.level}/{self.rounds_day1}/{self.rounds_day2}/{self.rounds_cut}'
        return output

    def __str__(self):
        output = f'{self.level}/{self.rounds_day1}/{self.rounds_day2}/{self.rounds_cut}'
        return output
