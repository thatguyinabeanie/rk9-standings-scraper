# Standings

A Python script to generate Pokémon standings from RK9 pairings' page

This project was started to be able to follow an event from home: seeing who played against who, the standings, the resistances to be able to watch the top cut race.
The streams only showed sometimes some part of the standings.

This script loads a RK9 pairing page and produces json and csv files for each division.

## Parameters

This script accepts 4 parameters :

- `--url` : mandatory, to specify the RK9 tournament id. Only the id is needed, the rest of the url is added by the script. NAIC 2023 would be NA1KYsUUz7fBID8XkZHZ
- `--id` : mandatory, to specify the internal id of the tournament. Used by pokedata and pokestats.

Some standings get broken by bad encoding during tournaments, just hope it will be fixed.
DQs not being made public, the last parameter of the Standing() constructor is to manually add the names of DQed players.
After the tournament is over, DQs are found by not seeing a player in the standings.

Some parts could probably be optimized, most parts are probably looking bad code-wise, ¯\\_(ツ)_/¯

## Install Dependencies

> pip install -r requirements.txt
