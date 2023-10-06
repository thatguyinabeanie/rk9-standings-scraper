from bs4 import BeautifulSoup
import requests
import re
import concurrent.futures


class Player:
    def __init__(self, name, level, decklist):
        self.name = name
        self.level = level
        self.ptcgo_decklist = rk9_to_ptcgo(decklist)
        self.json_decklist = rk9_to_json(decklist)


class PlayerData:
    def __init__(self, name, level, country):
        self.name = name
        self.level = level
        self.country = country


def rk9_to_ptcgo(page):
    output = ""
    data = page.text
    start = 0
    start = data.find('data-setnum="', start)
    while start != -1:
        end = data.find('"', start + 13)
        if end != -1 and end != start + 13:
            card_data = data[start + 13:end]
            basic = card_data.find('misc-')
            if basic == 0:
                temp = card_data.replace("misc-", "")
                card_data = temp + " Energy Energy "
                if temp.lower() == "Grass".lower():
                    card_data = card_data + " 1"
                if temp.lower() == "Fire".lower():
                    card_data = card_data + " 2"
                if temp.lower() == "Water".lower():
                    card_data = card_data + " 3"
                if temp.lower() == "Lightning".lower():
                    card_data = card_data + " 4"
                if temp.lower() == "Psychic".lower():
                    card_data = card_data + " 5"
                if temp.lower() == "Fighting".lower():
                    card_data = card_data + " 6"
                if temp.lower() == "Darkness".lower():
                    card_data = card_data + " 7"
                if temp.lower() == "Metal".lower():
                    card_data = card_data + " 8"
                if temp.lower() == "Fairy".lower():
                    card_data = card_data + " 9"

            if card_data.find('-') == 3:
                card_data = card_data.replace('-', ' ')
            else:
                card_set = card_data[0:5]
                if basic == 0:
                    number = card_data[5]
                else:
                    number = re.sub("/[^0-9]/", "", card_data[5])
                card_data = card_set + " " + number
            start = data.find('data-language="', end + 1)
            if start != -1:
                end = data.find('"', start + 15)
                if end != -1:
                    lang = data[start + 15:end]
                    if lang == "EN":
                        start = data.find('data-quantity="', end + 1)
                        if start != -1:
                            end = data.find('"', start + 15)
                            if end != -1:
                                count = data[start + 15:end]
                                output = output + "* " + count + " " + card_data + "\n"
                                start = data.find('data-setnum="', end + 1)
                    else:
                        start = -1
        else:
            start += 1
    return output


def rk9_to_json(page):
    output = '{'
    soup = BeautifulSoup(page.content, "lxml")
    table = soup.find("table", {"class": "decklist"})
    pokemon_list = table.find("ul", {"class": "pokemon"})
    trainer_list = table.find("ul", {"class": "trainer"})
    energy_list = table.find("ul", {"class": "energy"})
    pokemons = None
    if pokemon_list is not None:
        pokemons = pokemon_list.find_all("li")
    trainers = None
    if trainer_list is not None:
        trainers = trainer_list.find_all("li")
    energies = None
    if energy_list is not None:
        energies = energy_list.find_all("li")
    output = output + '"pokemon":['
    group_data = ""
    if pokemons is not None:
        for card in pokemons:
            count = card.get("data-quantity")
            name = card.get("data-cardname")
            setnumber = card.get("data-setnum")
            number = setnumber.split("-")[1]
            card_set = setnumber.split("-")[0]
            data = f'{{"count": {count}, "name": {name}, "number": {number}, "set": {card_set}}}'
            if len(group_data) > 0:
                group_data = group_data + ","
            group_data = group_data + data
    output = output + group_data
    output = output + ']'

    output = output + ',"trainer":['
    group_data = ""
    if trainers is not None:
        for card in trainers:
            count = card.get("data-quantity")
            name = card.get("data-cardname")
            setnumber = card.get("data-setnum")
            if len(setnumber) > 0:
                number = setnumber.split("-")[1]
                card_set = setnumber.split("-")[0]
                data = f'{{"count": {count}, "name": {name}, "number": {number}, "set": {card_set}}}'
                if len(group_data) > 0:
                    group_data = group_data + ","
                group_data = group_data + data
    output = output + group_data
    output = output + ']'

    output = output + ',"energy":['
    group_data = ""
    if energies is not None:
        for card in energies:
            count = card.get("data-quantity")
            name = card.get("data-cardname")
            setnumber = card.get("data-setnum")
            number = setnumber.split("-")[1]
            card_set = setnumber.split("-")[0]
            data = f'{{"count": {count}, "name": {name}, "number": {number}, "set": {card_set}}}'
            if len(group_data) > 0:
                group_data = group_data + ","
            group_data = group_data + data
    output = output + group_data
    output = output + ']'

    output = output + '}'
    return output


def get_status(url, name, level):
    return Player(name, level, requests.get(url=url))


class PlayersData:
    def __init__(self, url):
        self.players = []
        url = 'https://rk9.gg/roster/' + url
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "lxml")
        table = soup.find("table", {"id": "dtLiveRoster"})
        thead = table.find("thead")
        tr = thead.find('tr')
        ths = tr.find_all('th')
        fn_index = -1
        ln_index = -1
        cn_index = -1
        div_index = -1
        current_index = 0
        for th in ths:
            if th is not None:
                if 'FIRST' in th.text.upper():
                    fn_index = current_index
                if 'LAST' in th.text.upper():
                    ln_index = current_index
                if 'COUNTRY' in th.text.upper():
                    cn_index = current_index
                if 'DIV' in th.text.upper():
                    div_index = current_index
                current_index += 1
        tbody = table.find("tbody")
        trs = tbody.find_all("tr")
        for tr in trs:
            if tr is not None:
                tds = tr.find_all("td")
                surname = ''
                if fn_index > -1:
                    surname = tds[fn_index].text.replace("\n\n", " ").strip()
                name = ''
                if ln_index > -1:
                    name = tds[ln_index].text.replace("\n\n", " ").strip()
                country = ''
                if cn_index > -1:
                    country = tds[cn_index].text.replace("\n\n", " ").strip()
                level = ''
                if div_index > -1:
                    level = tds[div_index].text.replace("\n\n", " ").strip()
                if level == "Junior":
                    level = "Juniors"
                if level == "Senior":
                    level = "Seniors"
                self.players.append(PlayerData(surname + " " + name, level, country))

    def get_country(self, p):
        for player in self.players:
            if player.name == p.name and player.level == p.level:
                return player.country.lower()
        return ''


class Decklists:
    def __init__(self, url):
        self.players = []
        urls = []
        names = []
        levels = []
        url = 'https://rk9.gg/roster/' + url
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "lxml")
        table = soup.find("table", {"id": "dtLiveRoster"})
        thead = table.find("thead")
        tr = thead.find('tr')
        ths = tr.find_all('th')
        fn_index = -1
        ln_index = -1
        div_index = -1
        dl_index = -1
        current_index = 0
        for th in ths:
            if th is not None:
                if 'FIRST' in th.text.upper():
                    fn_index = current_index
                if 'LAST' in th.text.upper():
                    ln_index = current_index
                if 'DIV' in th.text.upper():
                    div_index = current_index
                if 'LIST' in th.text.upper():
                    dl_index = current_index
                current_index += 1
        tbody = table.find("tbody")
        trs = tbody.find_all("tr")
        for tr in trs:
            if tr is not None:
                tds = tr.find_all("td")
                surname = ''
                if fn_index > -1:
                    surname = tds[fn_index].text.replace("\n\n", " ").strip()
                name = ''
                if ln_index > -1:
                    name = tds[ln_index].text.replace("\n\n", " ").strip()
                level = ''
                if div_index > -1:
                    level = tds[div_index].text.replace("\n\n", " ").strip()
                if level == "Junior":
                    level = "Juniors"
                if level == "Senior":
                    level = "Seniors"
                list_text = ''
                if dl_index > -1:
                    list_text = tds[dl_index].text.strip().replace(" ", "").replace("\n\n", " ")
                if list_text == "View":
                    a = tds[dl_index].find('a', href=True)
                    urls.append("https://rk9.gg/" + a['href'])
                    names.append(surname + " " + name)
                    levels.append(level)
        # threading
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for i in range(0, len(urls)):
                futures.append(executor.submit(get_status, url=urls[i], name=names[i], level=levels[i]))

            for future in concurrent.futures.as_completed(futures):
                self.players.append(future.result())
