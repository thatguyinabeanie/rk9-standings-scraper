class Standing:
    def __init__(self, folder, division_name):
        self.division_name = str(division_name)
        self.level = ""
        self.rounds_day1 = 999
        self.rounds_day2 = 999
        self.rounds_cut = 999
        self.players = []
        self.player_id = 1
        self.directory = folder
        self.dqed = []
        self.hidden = []
        self.current_round = 0
        self.tables = []

    def __repr__(self):
        output = self.division_name
        return output

    def __str__(self):
        output = self.division_name
        return output
