from datetime import datetime, timezone
import json

from standing import Standing


class Division:
    def __init__(self):
        self.player_count = 0
        self.winner = None
        self.round_number = 0
        self.standing = Standing()

    def get_highest_kicker(self, is_internats):
        if is_internats and len(self.standing.players) > 2046:
            return 1024
        if len(self.standing.players) > 1024:
            return 512
        if len(self.standing.players) > 512:
            return 256
        if len(self.standing.players) > 256:
            return 128
        if len(self.standing.players) > 128:
            return 64
        if len(self.standing.players) > 80:
            return 32
        if len(self.standing.players) > 48:
            return 16
        return 8


class Event:
    def __init__(self, event_id, name, start_date, end_date, rk9_id):
        self.event_id = event_id
        self.name = name
        self.date_start = start_date
        self.date_end = end_date
        self.last_updated = datetime.now(timezone.utc).isoformat()
        self.rk9_id = rk9_id
        self.tournament_status = 'not-started'
        self.divisions = {
            'juniors': Division(),
            'seniors': Division(),
            'masters': Division()
        }

    def to_dict(self):
        return {
            'id': self.event_id,
            'name': self.name,
            'date': {
                'start': self.date_start,
                'end': self.date_end
            },
            'players': {
                'juniors': self.divisions['juniors'].player_count,
                'seniors': self.divisions['seniors'].player_count,
                'masters': self.divisions['masters'].player_count
            },
            'winners': {
                'juniors': self.divisions['juniors'].winner,
                'seniors': self.divisions['seniors'].winner,
                'masters': self.divisions['masters'].winner
            },
            'tournamentStatus': self.tournament_status,
            'roundNumbers': {
                'juniors': self.divisions['juniors'].round_number,
                'seniors': self.divisions['seniors'].round_number,
                'masters': self.divisions['masters'].round_number
            },
            'tournamentStructure': {
                div: {
                    'swiss_day_1': self.divisions[div].standing.rounds_day1,
                    'swiss_day_2': self.divisions[div].standing.rounds_day2 - self.divisions[div].standing.rounds_day1,
                    'top_cut': self.divisions[div].standing.rounds_cut
                } for div in ['juniors', 'seniors', 'masters']
            },
            'pointsAwards': {
                div: self.divisions[div].get_highest_kicker('International Championship' in self.name) for div in [
                    'juniors',
                    'seniors',
                    'masters'
                ]
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
