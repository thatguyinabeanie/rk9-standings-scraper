from datetime import datetime, timezone
import json
import math

from standing import Standing


class Division:
    def __init__(self):
        self.player_count = 0
        self.winner = None
        self.round_number = 0
        self.standing = Standing([], [])

    def load_data(self, players, tables):
        self.standing = Standing(players, tables)
        self.round_number = len(tables)
        self.player_count = len(players)

    def apply_points(self, is_internats):
        cutoff = 8
        if is_internats and len(self.standing.players) > 2046:
            cutoff = 1024
        elif len(self.standing.players) > 1024:
            cutoff = 512
        elif len(self.standing.players) > 512:
            cutoff = 256
        elif len(self.standing.players) > 256:
            cutoff = 128
        elif len(self.standing.players) > 128:
            cutoff = 64
        elif len(self.standing.players) > 80:
            cutoff = 32
        elif len(self.standing.players) > 48:
            cutoff = 16

        for player in self.standing.players:
            if player.top_placement <= cutoff:
                player.awards_placement = 2 ** math.ceil(math.log2(player.top_placement))

    def get_day_2_rounds(self):
        if self.standing.rounds_day2 is None:
            return 0
        return self.standing.rounds_day2 - self.standing.rounds_day1


class Event:
    def __init__(self, event_id, name, start_date, end_date, rk9_id):
        self.event_id = event_id
        self.name = name
        self.date_start = start_date
        self.date_end = end_date
        self.last_updated = datetime.now(timezone.utc).isoformat()
        self.rk9_id = rk9_id
        self.divisions = {
            'juniors': Division(),
            'seniors': Division(),
            'masters': Division()
        }

    def get_tournament_status(self):
        if (self.divisions['juniors'].winner is not None
                and self.divisions['seniors'].winner is not None
                and self.divisions['masters'].winner is not None):
            return 'finished'

        if (self.divisions['juniors'].player_count > 0
                or self.divisions['seniors'].player_count > 0
                or self.divisions['masters'].player_count > 0):
            return 'in-progress'

        return 'not-started'

    def to_dict(self):
        return {
            'id': self.event_id,
            'name': self.name,
            'date': {
                'start': self.date_start,
                'end': self.date_end
            },
            'players': {
                div: self.divisions[div].player_count for div in ['juniors', 'seniors', 'masters']
            },
            'winners': {
                div: self.divisions[div].winner for div in ['juniors', 'seniors', 'masters']
            },
            'tournamentStatus': self.get_tournament_status(),
            'roundNumbers': {
                div: self.divisions[div].round_number for div in ['juniors', 'seniors', 'masters']
            },
            'tournamentStructure': {
                div: {
                    'swissDay1': self.divisions[div].standing.rounds_day1,
                    'swissDay2': self.divisions[div].get_day_2_rounds(),
                    'topCut': self.divisions[div].standing.rounds_cut
                } for div in ['juniors', 'seniors', 'masters']
            },
            "lastUpdated": self.last_updated,
            "rk9link": self.rk9_id,
        }

    def add_to_index(self, index_filename):
        index_data = []

        try:
            with open(index_filename, 'r') as indexFile:
                index_data = json.load(indexFile)
        except OSError:
            pass

        for (i, tour) in enumerate(index_data):
            if tour['id'] == self.event_id:
                index_data[i] = {
                    "id": self.event_id,
                    "name": self.name
                }
                break
        else:
            index_data.append(self.to_dict())

        with open(index_filename, 'w') as indexFile:
            json.dump(index_data, indexFile)
