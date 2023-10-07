class Standing:
    def __init__(self, tournament_name, tournament_directory, folder, division_name, url, dqed):
        self.tournament_name = str(tournament_name)
        self.tournament_directory = str(tournament_directory)
        self.division_name = str(division_name)
        self.url = url
        self.level = ""
        self.rounds_day1 = 999
        self.rounds_day2 = 999
        self.rounds_cut = 999
        self.players = []
        self.player_id = 1
        self.directory = folder
        self.dqed = dqed
        self.hidden = []
        self.current_round = 0
        self.tables = []

    def __repr__(self):
        output = self.tournament_name + " (in " + self.tournament_directory + ") " + self.division_name
        output += f"\n\tURLS:\n{self.url}"
        return output

    def __str__(self):
        output = self.tournament_name + " (in " + self.tournament_directory + ") " + self.division_name
        output += f"\n\tURLS:\n\t\t{self.url}"
        return output
