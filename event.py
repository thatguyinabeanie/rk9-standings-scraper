from datetime import datetime, timezone
import json

from standing import Standing


class Division:
    def __init__(self):
        self.player_count = 0
        self.winner = None
        self.round_number = 0
        self.standing = Standing()


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

    def standings_list(self):
        return [self.divisions['juniors'].standing,
                self.divisions['seniors'].standing,
                self.divisions['masters'].standing]

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
