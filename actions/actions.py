# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

from typing import Any, Text, Dict, List

import arrow
import pandas as pd
import requests
import os
import json
import datetime
import urllib.parse
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from typing import List
from bs4 import BeautifulSoup

# Helper vars and classes
# ----------------------------------
GAMES_START_DAY = 1
polling_cities = ["Köln", "köln", "Koeln", "koeln", "cologne", "Cologne", "Kölln", "kölln", "K", "k",
                  "Münster", "münster", "Muenster", "muenster", "MS", "ms"]


# Helper class to create polling station objects with number and complete address and strings for bot answers
class Pollingstation:
    def __init__(self, street, number, plz, city):
        self.street = street
        self.number = number
        self.plz = plz
        self.city = city

    # Generate a Google Maps Request link with objects properties
    def getGMapsRequest(self) -> str:
        # Example: https://www.google.com/maps/search/?api=1&query=Uppenkampstiege+17,+48147+Münster
        link = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(self.street)}+{self.number}+" \
               f"{self.plz}+{urllib.parse.quote(self.city)}"
        return link

    # Generate address String to be displayed in bot response message
    def getAddress(self) -> str:
        address = f"{self.street} {self.number}, {self.plz} {self.city}"
        return address


# Helper class for soccer games
class Game:
    def __init__(self, winner: str, looser: str, goals_winner: str, goals_looser: str, gameday: str):
        self.winner = winner
        self.looser = looser
        self.goals_winner = goals_winner
        self.goals_looser = goals_looser
        self.gameday = gameday

    # Returns a tuple with both teams (winner, looser)
    def get_teams(self) -> tuple:
        match_teams = (self.winner.lower(), self.looser.lower())
        return match_teams

    # Returns the gameday as int
    def get_gameday(self) -> int:
        return int(self.gameday)


# Helper class to contain a single ranking entry
class Ranking:
    def __init__(self, group: str, placement: str, team: str, games_played: str,
                 vdd: str, goals: str, diff: str, points: str):
        self.group = group
        self.placement = placement
        self.team = team
        self.games_played = games_played
        self.vdd = vdd
        self.goals = goals
        self.diff = diff
        self.points = points

    def print_entry(self) -> None:
        print("Gruppe: {} | #{} - {}: {}-{}  {} {} -- {}".format(self.group, self.placement, self.team,
                                                                 self.games_played, self.vdd, self.goals,
                                                                 self.diff, self.points))


# Class to define a contest group table
class Table:
    def __init__(self, group: str, teams: List[Ranking]):
        self.group = group
        self.teams = teams

    # Return group as string
    def get_group(self) -> str:
        return self.group

    def print_table(self) -> str:
        table_string = "Gruppe {} \n| Platz | Team | Spiele | S-U-N | Tore | Diff. | Punkte |\n" \
                       "|--|--|--|--|--|--|--|\n".format(self.group)
        for team in self.teams:
            entry = "| {} | {} | {} | {} | {} | {} | {} |\n".format(team.placement, team.team, team.games_played,
                                                                    team.vdd, team.goals, team.diff, team.points)

            table_string = table_string + entry
        table_string = table_string + "\n"

        return table_string


# Class that contains all group tables in one object
class TournamentTable:
    def __init__(self, tables: List[Table]):
        self.tables = tables

    # Generate a string to print out all information
    def create_table_string(self) -> str:
        result = ''
        for table in self.tables:
            tab1 = table.print_table()
            result = result + tab1
        return result

    # Look up a single table in all tables and return table string
    def get_table_string(self, needle: str) -> str:
        for table in self.tables:
            if table.get_group().lower() == needle.lower():
                return table.print_table()


# Util functions
# ----------------------------------

# Helper function to generate a polling station object from given city and station number.
# Currently working only for Münster or Cologne
def get_poll_station(city: str, stationnumber: int) -> Pollingstation:
    cologne: List[str] = ["Köln", "köln", "Koeln", "koeln", "cologne", "Cologne", "Kölln", "kölln", "K", "k"]
    muenster: List[str] = ["Münster", "münster", "Muenster", "muenster", "MS", "ms"]
    response = None

    # open csv-file
    url_ms = 'https://alfacms.se-labor.de/wp-content/uploads/2022/03/wahllokaleMS.csv'
    url_k = 'https://alfacms.se-labor.de/wp-content/uploads/2022/04/wahllokale_k.csv'

    if city in cologne:
        response = requests.get(url_k)
    elif city in muenster:
        response = requests.get(url_ms)

    # create temp file to store csv-values
    tempfile = open('tempfile.csv', 'wb')
    tempfile.write(response.content)

    # read csv-data, seperator ; with headers and select row where "lokalnummer" is equal to given number
    # pd = pandas, df = usual shortcut for pandas.dataframe
    df = pd.read_csv('tempfile.csv', sep=";", header=0)
    result = df[df["lokalnummer"] == stationnumber]

    if not result.empty:
        street = result["strasse"].item()
        number = result["hausnummer"].item()
        plz = result["plz"].item()
        city = result["ort"].item()

        pollstation = Pollingstation(street, number, plz, city)

    else:
        pollstation = Pollingstation('n.a.', 'n.a.', 'n.a.', 'n.a.')

    # close and delete temp-file
    tempfile.close()
    file_to_remove = "tempfile.csv"
    if os.path.exists(file_to_remove):
        os.remove(file_to_remove)
    else:
        print("%s does not exist!" % file_to_remove)

    return pollstation


# Pollingstation numbers may occur as numbers with leading zero. reformatStationNumber will remove a leading zero
def reformatStationNumber(station_number) -> int:
    number: int = int(station_number)
    return number


# Generate a Google Search request from given string (Assumption: string = utterance)
def googleSearchRequest(utterance: str) -> str:
    # sample url: https://www.google.com/search?q=was+läuft+im+kino&cr=countryDE&lr=lang_de
    base_url = 'https://www.google.com/search?q='
    country = '&cr=countryDE'
    langcode = '&lr=lang_de'

    request_string = utterance.replace(" ", "+")
    search_string: str = base_url + request_string + country + langcode
    return search_string


# Copies a csv-file from given url to server, naming it 'tempfile.csv'. File have to be deleted by function remove_csv()
def create_csv_from_url(url: str):
    response = requests.get(url)
    tempfile = open('tempfile.csv', 'wb')
    tempfile.write(response.content)
    tempfile.close()


# Removes local copy of file 'tempfile.csv', created by function create_csv_from_url
def remove_csv():
    file_to_remove = 'tempfile.csv'
    if os.path.exists(file_to_remove):
        os.remove(file_to_remove)
    else:
        print("%s does not exist!" % file_to_remove)


# Returns group character of competing team of Fifa WM 2022
def get_group(team: str, df: pd.DataFrame) -> str:
    result = df[df["teamlower"] == team.lower()]

    if not result.empty:
        group = result["gruppe"].item()
        group = str(group).upper()
        return group
    else:
        result = "None"
        return result


# Returns teams of a given group competing in the Fifa WM 2022 as array
def get_teams(group: str, df: pd.DataFrame):
    teams = []
    result = df[df["gruppe"] == group.lower()]

    if not result.empty:
        for row in result.index:
            teams.append(result["mannschaft"][row])
        return teams
    else:
        teams.append("None")
        return teams


# Webscraper for game results from Kicker.de for Women EM 2022, returns a list with Game-objects
def get_games(gameday: str) -> list:
    base_url = 'https://www.kicker.de/frauen-europameisterschaft/spieltag/2022/'
    day = gameday
    url = base_url + day
    WINNER = 0
    LOOSER = 1
    game_results = []

    # 1. Get website
    website = requests.get(url)
    # 2. Parse website with beautifulSoup html-parser
    results = BeautifulSoup(website.content, 'html.parser')
    # 3. Find all divs containing game entries
    matches = results.find_all('div', class_='kick__v100-gameList__gameRow')
    # 4. Iterate through entries to fetch competing teams and score. Kicker uses Winner Score : Score Looser - order
    for match in matches:
        players = match.find_all('div', class_='kick__v100-gameCell__team__name')
        scores = match.find_all('div', class_='kick__v100-scoreBoard__scoreHolder__score')
        # Create a new Game-object with results
        game_results.append(
            Game(players[WINNER].text.strip(), players[LOOSER].text.strip(),
                 scores[WINNER].text.strip(), scores[LOOSER].text.strip(), day))
    # 5. Return results as list
    return game_results


# Looks up a match in all match data and return a string with match and score
def find_match(needle_1: str, needle_2: str, matches: List[Game]) -> str:
    if not needle_1 or not needle_2:
        fail = ("Variablen nicht korrekt übermittelt")
        return fail
    for game in matches:
        if needle_1.lower() in game.get_teams() and needle_2.lower() in game.get_teams():
            result_string = ("{} {} : {} {}".format(game.winner, game.goals_winner,
                                                    game.goals_looser, game.looser))
            return result_string
    fail = ("Diese Mannschaften haben noch nicht gegeneinander gespielt")
    return fail


# Lookup current playday or return playday maximum
def playday_lookup() -> str:
    playdays_dict = {
        "2111": "2",
        "2211": "2",
        "2311": "2",
        "2411": "2",
        "2511": "2",
        "2611": "3",
        "2711": "3",
        "2811": "3",
        "2911": "3",
        "3011": "4",
        "0112": "4",
        "0212": "4",
        "0312": "4",
        "0412": "5",
        "0512": "5",
        "0612": "5",
        "0712": "5",
        "0912": "6",
        "1012": "6",
        "1112": "6",
        "1312": "7",
        "1412": "7",
        "1512": "7",
        "1712": "8",
        "1812": "8",
        "1912": "9",
        #    "0208": "3", #Demodate!
    }
    PLAYDAY_MAX = "7"

    today = datetime.datetime.today()
    daycode = today.strftime('%d') + today.strftime('%m')
    if daycode in playdays_dict:
        playday = playdays_dict.get(daycode)
    else:
        playday = PLAYDAY_MAX
    return playday


# Webscraper to geht tournament ranking tables
def get_rankings() -> TournamentTable:
    url = 'https://www.kicker.de/frauen-europameisterschaft/tabelle/2022'

    FIRST_ELEMENT = 0
    PLACEMENT = 0
    TEAM = 1
    GAMES_PLAYED = 2
    VIC_DRA_DEF = 3
    GOALS = 6
    DIFFERENCE = 7
    POINTS = 8
    table_data = []
    ranking_a = []
    ranking_b = []
    ranking_c = []
    ranking_d = []
    tournament_data = TournamentTable

    # 1. Get website
    website = requests.get(url)
    # 2. Parse website with beautifulSoup html-parser
    results = BeautifulSoup(website.content, 'html.parser')
    # 3. Find all divs containing ranking entries
    tables = results.find_all('table', class_='kick__table '
                                              'kick__table--ranking kick__table--alternate kick__table--resptabelle')
    # 4. Iterate through all table entries to fetch ranking data.
    for table in tables:
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            table_data.append([ele for ele in cols if ele])
    table_data = list(filter(None, table_data))  # Remove empty sublists
    for idx, data in enumerate(table_data):  # Extracting data
        placement = data[PLACEMENT].strip()
        team = data[TEAM].split("\n")[TEAM].strip()  # Original form repeats team name
        games_played = data[GAMES_PLAYED].strip()
        vdd = data[VIC_DRA_DEF].split("\n")[FIRST_ELEMENT].strip()  # Original form would be like 3-1-0\n3
        goals = data[GOALS].strip()
        diff = data[DIFFERENCE].strip()
        points = data[POINTS].strip()
        # Generate ranking lists for the four contest groups A-D
        if idx in range(0, 4):
            ranking = (Ranking('A', placement, team, games_played, vdd, goals, diff, points))
            ranking_a.append(ranking)
        elif idx in range(4, 8):
            ranking = (Ranking('B', placement, team, games_played, vdd, goals, diff, points))
            ranking_b.append(ranking)
        elif idx in range(8, 12):
            ranking = (Ranking('C', placement, team, games_played, vdd, goals, diff, points))
            ranking_c.append(ranking)
        elif idx in range(12, 16):
            ranking = (Ranking('D', placement, team, games_played, vdd, goals, diff, points))
            ranking_d.append(ranking)

    # Construct table objects
    table_a = Table('A', ranking_a)
    table_b = Table('B', ranking_b)
    table_c = Table('C', ranking_c)
    table_d = Table('D', ranking_d)

    # Construct tournament data-object
    tournament_data = TournamentTable([table_a, table_b, table_c, table_d])

    return tournament_data


# Validation actions
# ----------------------------------

# Validation of extracted vars polling_num and polling_city for Landtagswahl
# Important: Made with rasa 2.X Syntax. Next usage should use rasa 3.X Syntax
class ValidatePollingStation(Action):

    def name(self) -> Text:
        return "action_tell_pollingstation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # rasa 2.X Syntax
        station_number = tracker.get_slot('polling_num')
        station_city = tracker.get_slot('polling_city')

        # rasa 3.x syntax
        #        station_number = (next(tracker.get_latest_entity_values("polling_num"), None))
        #        station_city = (next(tracker.get_latest_entity_values("polling_city"), None))

        # Check if a featured city is asked
        if station_city not in polling_cities:
            msg = f"Es tut mir Leid. Derzeit kann ich dir nur Wahllokale in Münster oder Köln nennen."
            dispatcher.utter_message(text=msg)
            return [SlotSet("polling_num", None), SlotSet("polling_city", None)]

        # format station number to get rid of leading zeros
        formatted_station_number = reformatStationNumber(station_number)
        station_data = get_poll_station(station_city, formatted_station_number)

        if not station_data.street == 'n.a.':
            msg = f"Dein Wahllokal findest du unter folgender Adresse: [{station_data.getAddress()}]({station_data.getGMapsRequest()})"
            dispatcher.utter_message(text=msg)
            return [SlotSet("polling_num", None), SlotSet("polling_city", None)]
        else:
            msg = f"In {station_city} gibt es kein Wahllokal mit der Nummer {station_number}."
            dispatcher.utter_message(text=msg)
            return [SlotSet("polling_num", None), SlotSet("polling_city", None)]


# Validation of variable in group slot
class ValidateGroupForm(FormValidationAction):
    wm_group2 = None

    def name(self) -> Text:
        return "validate_group_form"

    def validate_group(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `group` value."""
        groups = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

        wm_group = str(tracker.get_slot("group")) or None

        if wm_group.lower() not in groups:
            dispatcher.utter_message(
                text=f"Die Gruppe {wm_group.upper()} "
                     f"gibt es bei dieser WM nicht. Wähle bitte eine andere Gruppe aus A - H.")
            return {"group": None}
        elif wm_group is None:
            dispatcher.utter_message(
                text=f"Ich konnte leider nicht erkennen, nach welcher Gruppe du suchst. "
                     f"Kannst du das bitte wiederholen?")
            return {"group": None}

        return {"group": wm_group.upper()}


# Validation of variable in group slot for ranking
class ValidateRankingForm(FormValidationAction):

    def name(self) -> Text:
        return "validate_ranking_form"

    def validate_group(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `group` value."""
        groups = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

        wm_group = str(tracker.get_slot("group")) or None

        if wm_group.lower() not in groups:
            dispatcher.utter_message(
                text=f"Die Gruppe {wm_group.upper()} "
                     f"gibt es bei dieser WM nicht. Wähle bitte eine andere Gruppe aus A - H.")
            return {"group": None}
        elif wm_group is None:
            dispatcher.utter_message(
                text=f"Ich konnte leider nicht erkennen, nach welcher Gruppe du suchst. "
                     f"Kannst du das bitte wiederholen?")
            return {"group": None}

        return {"group": wm_group.upper()}


# Validation of variable in team slot
class ValidateTeamForm(FormValidationAction):
    teams = ['argentinien', 'australien', 'belgien', 'brasilien', 'dänemark', 'deutschland', 'ecuador', 'england',
             'frankreich', 'ghana', 'iran', 'japan', 'kamerun', 'kanada', 'kroatien', 'marokko', 'mexiko', 'neuseeland',
             'niederlande', 'polen', 'portugal', 'qatar', 'saudi-arabien', 'schweiz', 'senegal', 'serbien', 'spanien',
             'südkorea', 'tunesien', 'uruguay', 'usa', 'wales']

    def name(self) -> Text:
        return "validate_team_form"

    async def run(self, dispatcher: "CollectingDispatcher", tracker: Tracker, domain: "DomainDict") -> List[
        Dict[Text, Any]]:
        pass

    def validate_team(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `wm_final_group` value."""

        team = str(next(tracker.get_latest_entity_values("team"), None))
        team_low = team.lower()

        if team_low not in ValidateTeamForm.teams:
            dispatcher.utter_message(
                text=f"Die Mannschaft {team} gibt es bei dieser WM nicht. Frage mich bitte nach einer anderen Mannschaft. Oder sage 'Ende'")
            return {"team": None}
        return {"team": team}


# Validation of entering code for survey
class ValidateSimpleSurveyForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_simple_survey_form"

    def validate_lot_number(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `pizza_size` value."""

        lot_num = int(slot_value)
        if not 10000 <= lot_num <= 99999:
            dispatcher.utter_message(text=f"Deine eingegebene Nummer ist leider nicht gültig")
            return {"lot_number": None}
        dispatcher.utter_message(text=f"Danke, deine Nummer {slot_value} ist korrekt. Wir können anfangen")
        return {"lot_number": slot_value}


# Validation of entering team variable in score request
class ValidateScoreForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_score_form"

    teams = ['argentinien', 'australien', 'belgien', 'brasilien', 'dänemark', 'deutschland', 'ecuador', 'england',
             'frankreich', 'ghana', 'iran', 'japan', 'kamerun', 'kanada', 'kroatien', 'marokko', 'mexiko',
             'neuseeland',
             'niederlande', 'polen', 'portugal', 'qatar', 'saudi-arabien', 'schweiz', 'senegal', 'serbien',
             'spanien',
             'südkorea', 'tunesien', 'uruguay', 'usa', 'wales']

    def validate_team(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `team` value."""

        team = (next(tracker.get_latest_entity_values("team"), None))
        team_low = team.lower()
        print(f"Validiere {team}")

        if team_low in ValidateScoreForm.teams:
            return {"team": team}
        else:
            dispatcher.utter_message(text=f"Die Mannschaft {team} gibt es bei dieser WM nicht. "
                                          f"Frage mich bitte nach einer anderen Mannschaft.")
            return {"team": None}

    def validate_team2(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `team2` value."""

        team2 = (next(tracker.get_latest_entity_values("team2"), None))
        team2_low = team2.lower()
        print(f"Validiere {team2}")

        if team2_low in ValidateScoreForm.teams:
            return {"team2": team2}
        else:
            dispatcher.utter_message(text=f"Die Mannschaft {team2} gibt es bei dieser WM nicht. "
                                          f"Frage mich bitte nach einer anderen Mannschaft.")
            return {"team2": None}


# Custom Action Code
# ----------------------------------

# Text-Action for demo purposes only
class ActionTestAction(Action):

    def name(self) -> Text:
        return "action_test_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        msg = f"Das ist eine Testnachricht von einem selbst gehosteten rasa custom Action server. {str(tracker.sender_id)}"
        dispatcher.utter_message(text=msg)
        return []


# Clear Slots Action for polling station search (Landtagswahl NRW 2022)
class ActionClearSlots(Action):
    def name(self) -> Text:
        return "action_clear_slots"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("polling_num", None), SlotSet("polling_city", None)]


# Returns current time for Germany and Qatar
class ActionTellTime(Action):

    def name(self) -> Text:
        return "action_tell_time"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        utc = arrow.utcnow()

        berlin_time = utc.to('Europe/Berlin')
        qatar_time = utc.to('Asia/Qatar')

        msg = f"In Deutschland ist es gerade {berlin_time.format('HH:mm')} Uhr. In Qatar ist es" \
              f" {qatar_time.format('HH:mm')} Uhr."

        dispatcher.utter_message(text=msg)
        return []


# Returns all teams in a given group at Fifa WM 2022
class ActionTellTeams(Action):
    def name(self) -> Text:
        return "action_tell_teams"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        wm_final_group = str(tracker.get_slot("group")) or None
        msg = 'Tut mir Leid, ich habe leider keine Antwort auf deine Frage'

        create_csv_from_url('https://alfacms.se-labor.de/wp-content/uploads/2022/08/gruppenWM2022.csv')

        try:
            df = pd.read_csv('tempfile.csv', sep=';', header=0)
            res = get_teams(wm_final_group, df)
            msg = ('Die Mannschaften in Gruppe ' + wm_final_group.upper() + ' sind: {}'
                   .format(', '.join([str(i) for i in res])))
        finally:
            remove_csv()

        dispatcher.utter_message(text=msg)

        return [SlotSet("group", None)]


# Returns group of a given team at Fifa WM 2022
class ActionTellGroup(Action):
    def name(self) -> Text:
        return "action_tell_group"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        team = (next(tracker.get_latest_entity_values("team"), None))

        msg = "Tut mir Leid, ich konnte gerade leider nicht nach deiner Mannschaft suchen. Versuche es später noch mal."
        res = "None"
        try:
            create_csv_from_url('https://alfacms.se-labor.de/wp-content/uploads/2022/05/gruppenWM2022.csv')

            df = pd.read_csv('tempfile.csv', sep=';', header=0)
            res = get_group(team, df)

            msg = f"Die Mannschaft von {team} spielt in Gruppe {res}."

            remove_csv()
        finally:
            dispatcher.utter_message(text=msg)

        return [SlotSet("team", None), SlotSet("group", str(res))]


# Custom Actions for Surveys
class ActionSubmitSurvey(Action):
    def name(self) -> Text:
        return "action_submit_survey"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        slot_lotnum = tracker.get_slot('lot_number')
        slot_helpful = tracker.get_slot('helpful')
        slot_length = tracker.get_slot('length')

        print("Folgende Befragungswerte erhalten: Losnummer: ", slot_lotnum, " | Hilfreich: ", slot_helpful,
              " | Länge: ", slot_length)

        dispatcher.utter_message(response="utter_submit_survey")
        return []


# Custom action returning team phase
class ActionTellPhase(Action):
    phases = {"gruppenphase": "21. November bis 02. Dezember 2022", "achtelfinale": "vom 03. bis 06. Dezember",
              "viertelfinale": "vom 09. und 10. Dezember 2022", "halbfinale": "am 13. und 14. Dezember 2022",
              "spiel um platz 3": "am 17. Dezember 2022", "platz 3": "am 17. Dezember 2022",
              "kleines finale": "am 17. Dezember 2022", "finale": "am 18. Dezember 2022"}

    def name(self) -> Text:
        return "action_tell_phase"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        phase = (next(tracker.get_latest_entity_values("phase"), None))

        msg = "Tut mir Leid, ich konnte deine Spielzeit nicht ermitteln, versuche es bitte noch mal mit " \
              "einer anderen Eingabe."
        res = "None"

        needle = phase.lower()

        if needle in self.phases.keys():
            if needle == "gruppenphase":
                msg = f"Die {phase} findet vom {self.phases[needle]} statt."
            else:
                msg = f"Das {phase} findet {self.phases[needle]} statt."

        dispatcher.utter_message(text=msg)

        return [SlotSet("phase", None)]


# Custom action returning a Google Search request
class ActionAskGoogle(Action):

    def name(self) -> Text:
        return "action_ask_google"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        latest_msg = tracker.latest_message
        j_obj = json.dumps(latest_msg)
        j_obj = json.loads(j_obj)
        utterance = j_obj["text"]

        request_string = googleSearchRequest(utterance)

        msg = f"Leider kann ich deine Nachricht nicht verstehen. Frag mich gerne noch mal. Wenn du möchtest," \
              f"kannst du deine Frage auch bei [Google suchen]({request_string})"

        dispatcher.utter_message(text=msg)

        return []


# Custom action returning a Google Search request
class ActionTellScore(Action):

    def name(self) -> Text:
        return "action_tell_score"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        team = (next(tracker.get_latest_entity_values("team"), None))
        team2 = (next(tracker.get_latest_entity_values("team2"), None))

        game_list = []
        msg = "Tut mir Leid, ich konnte gerade leider nicht nach dem Spielergebnis suchen. Versuche es später noch mal."
        res = "None"

        try:
            msg = "Das Turnier hat noch nicht begonnen. Daher kann ich dir keine Spielergebnisse zeigen."
        #            playday = playday_lookup()
        #            print(f"Spieltag: {playday}")
        #            for day in range(GAMES_START_DAY,int(playday)):
        #                game_list = game_list + get_games(str(day))
        #            msg = find_match(team, team2, game_list)

        finally:
            dispatcher.utter_message(text=msg)

        return [SlotSet("team", None), SlotSet("team2", None)]


# Custom action returning a ranking table to a given group
class ActionTellRanking(Action):

    def name(self) -> Text:
        return "action_tell_ranking"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        group = (next(tracker.get_latest_entity_values("group"), None))

        msg = "Tut mir Leid, ich konnte gerade leider nicht nach der Tabelle suchen. Versuche es später noch mal."
        res = "None"

        try:
            msg = "Das Turnier hat noch nicht begonnen. Daher kann ich dir keine Tabellen zeigen."
        #    all_ranking_tables = get_rankings()
        #    msg = f'Ok, hier ist die Tabelle:\n{all_ranking_tables.get_table_string(group)}'

        finally:
            dispatcher.utter_message(text=msg)

        return [SlotSet("group", None)]
