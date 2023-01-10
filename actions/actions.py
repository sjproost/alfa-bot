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
import requests_cache
import os
import json
import sys
import urllib.parse
import smtplib
import csv
from typing import List
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from typing import List
from bs4 import BeautifulSoup
from requests.exceptions import HTTPError

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

# Tell a random joke
def get_joke() -> str:
    JOKE_URL = "https://witzapi.de/api/joke/"
    msg = "Chuck Norris schreibt Software ohne Fehler"
    try:
        response = requests.get(JOKE_URL)
        response.raise_for_status()
        # access JSON content
        jsonResponse = response.json()
        joke = jsonResponse[0].get('text')
        if joke is not None:
            return joke

    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Error occurred: {err}')
    return msg


# Error-Printing
def err_print(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# Helper function to generate a polling station object from given city and station number.
# Currently working only for Münster or Cologne
def get_poll_station(city: str, stationnumber: int) -> Pollingstation:
    cologne: List[str] = ["Köln", "köln", "Koeln", "koeln", "cologne", "Cologne", "Kölln", "kölln", "K", "k"]
    muenster: List[str] = ["Münster", "münster", "Muenster", "muenster", "MS", "ms"]
    response = None

    # open csv-file
    url_ms = 'https://www.alfa-bot.de/wp-content/uploads/2022/03/wahllokaleMS.csv'
    url_k = 'https://www.alfa-bot.de/wp-content/uploads/2022/04/wahllokale_k.csv'

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


# Copies a csv-file from given url to server, naming it 'tempfile.csv'. File has to be deleted by function remove_csv(path: str)
def create_csv_from_url(url: str):
    response = requests.get(url)
    tempfile = open('tempfile.csv', 'wb')
    tempfile.write(response.content)
    tempfile.close()


# Create a csv file for survey values. File has to be deleted by function remove_csv(path: str)
def write_survey_csv(path: str, header: List[str], data: List[str]) -> None:
    with open(path, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerow(data)


# Removes local copy of file 'tempfile.csv', created by function create_csv_from_url
def remove_csv(path: str) -> None:
    file_to_remove = path
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
    base_url = 'https://www.kicker.de/weltmeisterschaft/spieltag/2022/'
    day = gameday
    url = base_url + day
    WINNER = 0
    LOOSER = 1
    game_results = []
    session = requests_cache.CachedSession('games_cache', backend='sqlite', expire_after=3600)
    try:
        # 1. Get website
        website = session.get(url)
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
    except Exception as e:
        err_print("Failure, retrieving game results: " + str(e))
    finally:
        # 5. Return results as list
        return game_results


# Looks up a match in all match data and return a string with match and score
def find_match(needle_1: str, needle_2: str, matches: List[Game]) -> str:
    if not needle_1 or not needle_2:
        fail = "Variablen nicht korrekt übermittelt"
        return fail
    for game in matches:
        if needle_1.lower() in game.get_teams() and needle_2.lower() in game.get_teams():
            result_string = ("Hier ist das Ergebnis: {} {} - {} {}".format(game.winner, game.goals_winner,
                                                                           game.goals_looser, game.looser))
            return result_string
    fail = "Diese Mannschaften haben noch nicht gegeneinander gespielt"
    return fail


# Lookup current playday or return playday maximum
def playday_lookup() -> str:
    playdays_dict = {
        "2011": "1",
        "2111": "1",
        "2211": "1",
        "2311": "1",
        "2411": "1",
        "2511": "2",
        "2611": "2",
        "2711": "2",
        "2811": "2",
        "2911": "3",
        "3011": "3",
        "0112": "3",
        "0212": "3",
        "0312": "4",
        "0412": "4",
        "0512": "4",
        "0612": "4",
        "0712": "4",
        "0812": "4",
        "0912": "5",
        "1012": "5",
        "1112": "5",
        "1212": "5",
        "1312": "6",
        "1412": "6",
        "1512": "6",
        "1612": "6",
        "1712": "7",
        "1812": "8",
    }
    PLAYDAY_MAX = "7"

    today = date.today()
    # start date of wm 2022 in format yyyy, mm, dd
    startday = date(2022, 11, 20)
    print(startday)
    daycode = str(today.day) + str(today.month)
    if daycode in playdays_dict:
        playday = playdays_dict.get(daycode)
    elif today < startday:
        playday = "-1"
    else:
        playday = PLAYDAY_MAX
    return playday


# Webscraper to geht tournament ranking tables
def get_rankings() -> TournamentTable:
    url = 'https://www.kicker.de/weltmeisterschaft/tabelle/2022'

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
    ranking_e = []
    ranking_f = []
    ranking_g = []
    ranking_h = []
    tournament_data = TournamentTable
    session = requests_cache.CachedSession('rankings_cache', backend='sqlite', expire_after=3600)
    try:
        # 1. Get website
        website = session.get(url)
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
            if data[PLACEMENT].strip().isnumeric():
                placement = data[PLACEMENT].strip()
            else:
                data.insert(PLACEMENT, "99")
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
            elif idx in range(16, 20):
                ranking = (Ranking('E', placement, team, games_played, vdd, goals, diff, points))
                ranking_e.append(ranking)
            elif idx in range(20, 24):
                ranking = (Ranking('F', placement, team, games_played, vdd, goals, diff, points))
                ranking_f.append(ranking)
            elif idx in range(24, 28):
                ranking = (Ranking('G', placement, team, games_played, vdd, goals, diff, points))
                ranking_g.append(ranking)
            elif idx in range(28, 32):
                ranking = (Ranking('H', placement, team, games_played, vdd, goals, diff, points))
                ranking_h.append(ranking)

        # Construct table objects
        table_a = Table('A', ranking_a)
        table_b = Table('B', ranking_b)
        table_c = Table('C', ranking_c)
        table_d = Table('D', ranking_d)
        table_e = Table('E', ranking_e)
        table_f = Table('F', ranking_f)
        table_g = Table('G', ranking_g)
        table_h = Table('H', ranking_h)
        # Construct tournament data-object
        tournament_data = TournamentTable([table_a, table_b, table_c, table_d, table_e, table_f, table_g, table_h])
    except Exception as e:
        err_print("Get Rankings: Failure retrieving tournament tables: " + str(e))

    finally:
        return tournament_data


def create_survey_msg(survey_result: List[List[str]]) -> str:
    # survey_result[[header][data]]
    # header = ['Losnummer', 'Datum', 'Smartphone', 'Hilfe benötigt', 'Antworten gelesen', 'Antworten verstanden',
    #          'Hilfreich', 'App akzeptiert', 'Warum', 'Warum nicht', 'Gut', 'Verbesserung']
    # data = [slot_lotnum, today, slot_smartphone, slot_need_help, slot_read, slot_understand, slot_helpful,
    #        slot_learn, slot_learn_why, slot_learn_not, slot_pos, slot_neg]
    HEADER = 0
    DATA = 1
    LOSNUMMER = 0
    DATUM = 1
    SMARTPHONE = 2
    HILFE = 3
    GELESEN = 4
    VERSTANDEN = 5
    HILFREICH = 6
    APP = 7
    WARUM = 8
    WARUMNICHT = 9
    POSITIV = 10
    NEGATIV = 11
    newline = '\n'
    tab = '\t'
    seperator = f"---------"
    text = f"""Neues Befragungsergebnis von ALFA-Bot
        {seperator}
        folgende Antworten zu Losnummer {survey_result[DATA][LOSNUMMER]} erhalten. CSV Datei im Anhang:{newline}
        {survey_result[HEADER][DATUM]}:{tab}{survey_result[DATA][DATUM]}
        {survey_result[HEADER][SMARTPHONE]}:{tab}{survey_result[DATA][SMARTPHONE]}
        {survey_result[HEADER][HILFE]}:{tab}{survey_result[DATA][HILFE]}
        {survey_result[HEADER][GELESEN]}:{tab}{survey_result[DATA][GELESEN]}
        {survey_result[HEADER][VERSTANDEN]}:{tab}{survey_result[DATA][VERSTANDEN]}
        {survey_result[HEADER][HILFREICH]}:{tab}{survey_result[DATA][HILFREICH]}        
        {survey_result[HEADER][APP]}:{tab}{survey_result[DATA][APP]} 
        {survey_result[HEADER][WARUM]}:{tab}{survey_result[DATA][WARUM]} 
        {survey_result[HEADER][WARUMNICHT]}:{tab}{survey_result[DATA][WARUMNICHT]} 
        {survey_result[HEADER][POSITIV]}:{tab}{survey_result[DATA][POSITIV]} 
        {survey_result[HEADER][NEGATIV]}:{tab}{survey_result[DATA][NEGATIV]} 
        {seperator}
        Viele Grüße Lalo
        """
    return text


def send_survey_mail(survey_result: List[List[str]]) -> None:
    load_dotenv('.env')
    attachment_path = 'survey_data.csv'
    sender = os.getenv('FROM')
    receivers = [os.getenv('TOFH'), os.getenv('TOBVAG')]

    write_survey_csv(attachment_path, survey_result[0], survey_result[1])

    msg = MIMEMultipart()
    body = MIMEText(create_survey_msg(survey_result))
    msg.attach(body)
    msg['Subject'] = 'Survey Result from ALFA-Bot'
    msg['From'] = sender
    msg['To'] = ", ".join(receivers)

    try:
        with open(attachment_path, "rb") as attachment:
            att = MIMEApplication(attachment.read(), _subtype="csv")
            att.add_header('Content-Disposition', "attachment; filename= %s" % attachment_path)
            msg.attach(att)
    except Exception as e:
        print(str(e))

    try:
        with smtplib.SMTP(os.getenv('DOMAIN'), int(os.getenv('PORT1'))) as server:
            server.connect(os.getenv('DOMAIN'), int(os.getenv('PORT2')))
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(os.getenv('USERNAME'), os.getenv('CREDENTIAL'))
            server.sendmail(sender, receivers, msg.as_string())
            server.quit()
    except Exception as error:
        err_msg = "Something went wrong: "
        err_msg = err_msg + str(error)
        print(err_msg)
    finally:
        remove_csv('survey_data.csv')


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


# Validation of variable in finals_team slot
class ValidateFinalsTeamForm(FormValidationAction):
    teams = ['argentinien', 'australien', 'belgien', 'brasilien', 'dänemark', 'deutschland', 'ecuador', 'england',
             'frankreich', 'ghana', 'iran', 'japan', 'kamerun', 'kanada', 'kroatien', 'marokko', 'mexiko', 'neuseeland',
             'niederlande', 'polen', 'portugal', 'qatar', 'saudi-arabien', 'schweiz', 'senegal', 'serbien', 'spanien',
             'südkorea', 'tunesien', 'uruguay', 'usa', 'wales']

    def name(self) -> Text:
        return "validate_finals_team_form"

    def validate_finals_team(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate `wm_finals_team' value."""

        # Handle case that user wants to abort form
        intent = tracker.latest_message['intent'].get('name')
        if intent == 'deny':
            return {"finals_team": "Abort"}

        # has to extract var this way, because value is extracted from text
        team = slot_value
        try:
            team_low = team.lower()
        except Exception as e:
            err_print("validate_finals_team: Failure could not set team to lower(): " + str(e))
            dispatcher.utter_message(text="Gebe bitte nochmal ein, nach welcher Mannschaft du suchst.")
            return {"finals_team": None}
        else:
            if team_low not in ValidateFinalsTeamForm.teams:
                dispatcher.utter_message(text=f"Die Mannschaft {team} gibt es bei dieser WM nicht. "
                                              f"Frage mich bitte nach einer anderen Mannschaft. Oder sage 'Ende'")
                return {"finals_team": None}
            return {"finals_team": team}


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
        access = [1092, 1126, 1263, 1518, 1645, 1931, 1932, 2063, 2147, 2656, 3094, 3349, 3507, 4098, 4297, 4667, 4935,
                  5010, 5025, 5050, 5299, 5320, 5325, 5382, 5733, 5800, 5929, 6101, 6350, 6374, 6493, 6513, 6621, 7062,
                  7147, 7249, 7373, 7469, 7509, 7926, 8043, 8772, 8963, 9165, 9300, 9540, 9674, 9693, 9797, 9820, 3310]
        lot_num = int(slot_value)
        if lot_num not in access:
            dispatcher.utter_message(text=f"Deine eingegebene Nummer ist leider nicht gültig")
            return {"lot_number": None}
        dispatcher.utter_message(
            text=f"Danke, deine Nummer {slot_value} ist korrekt. Wir können anfangen. Es geht um deine Meinung zu Chatbots, wie mir. Deine Antworten bleiben natürlich komplett anonym!")
        return {"lot_number": slot_value}

    def validate_learn_with_bot(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        affirm = ["ja", "klar", "jeden", "sicher", "natürlich", "gerne", "schon"]
        deny = ["nein", "nö", "nicht", "keinesfalls", "niemals", "nie"]

        answer = str(slot_value).lower()
        if any(element in answer for element in affirm):
            return {"learn_with_bot": slot_value, "learn_not": "Ausgefiltert"}
        elif any(element in answer for element in deny):
            return {"learn_with_bot": slot_value, "learn_why": "Ausgefiltert"}
        else:
            return {"learn_with_bot": slot_value}


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
        try:
            team_low = team.lower()

            if team_low in ValidateScoreForm.teams:
                return {"team": team}
        except Exception as e:
            err_print("validate_team: Failure to lower team var: " + str(e))
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
        try:
            team2_low = team2.lower()

            if team2_low in ValidateScoreForm.teams:
                return {"team2": team2}
        except Exception as e:
            err_print("validate_team: Failure to lower team var: " + str(e))
            dispatcher.utter_message(text=f"Die Mannschaft {team2} gibt es bei dieser WM nicht. "
                                          f"Frage mich bitte nach einer anderen Mannschaft.")
            return {"team2": None}


# Validate as_like_form
class AsLikeForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_as_like_form"

    def validate_as(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_as = str(slot_value).lower()
        if solution_as != 'als':
            dispatcher.utter_message(response="utter_test_as_wrong")
            return {"as": None}
        dispatcher.utter_message(text=f'Das ist richtig: "Meine Mutter ist älter *als* ich."')
        return {"as": slot_value}

    def validate_like(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_like = str(slot_value).lower()
        print(solution_like)
        if solution_like != 'wie':
            dispatcher.utter_message(response="utter_test_like_wrong")
            return {"like": None}
        dispatcher.utter_message(text=f'Das ist richtig: "Meine Freundin hat das gleiche Hobby *wie* ich."')
        return {"like": slot_value}


# Validate Nugget Apparently Seemingly
class ApparentlySeeminglyForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_apparently_seemingly_form"

    def validate_seemingly(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_seemingly = str(slot_value).lower()
        if solution_seemingly != 'scheinbar':
            dispatcher.utter_message(response="utter_test_seemingly_wrong")
            return {"seemingly": None}
        dispatcher.utter_message(
            text=f'Das ist richtig: Du vermutest, dass es scheinbar ein gutes Angebot ist. In Wahrheit könnte es aber Betrug sein.')
        return {"seemingly": slot_value}

    def validate_apparently(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_apparently = str(slot_value).lower()
        if solution_apparently != 'anscheinend':
            dispatcher.utter_message(response="utter_test_apparently_wrong")
            return {"apparently": None}
        dispatcher.utter_message(text=f'Das ist richtig: Der Gast wusste wirklich nicht, dass Hummer teuer ist.')
        return {"apparently": slot_value}


# Validate dasselbe gleiche form
class DasselbeGleicheForm(FormValidationAction):
    dasselbe: List[str] = ["dasselbe", "das selbe"]
    dasgleiche: List[str] = ["dasgleiche", "das gleiche"]

    def name(self) -> Text:
        return "validate_dasselbe_gleiche_form"


    def validate_dasselbe(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_dasselbe = str(slot_value).lower()
        if solution_dasselbe not in DasselbeGleicheForm.dasselbe:
            dispatcher.utter_message(response="utter_test_dasselbe_wrong")
            return {"dasselbe": None}
        dispatcher.utter_message(
            text=f'Das ist richtig: Hat man sich nicht umgezogen, trägt man noch immer dasselbe Shirt wie zuvor.')
        return {"dasselbe": slot_value}

    def validate_dasgleiche(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_dasgleiche = str(slot_value).lower()
        if solution_dasgleiche not in DasselbeGleicheForm.dasgleiche:
            dispatcher.utter_message(response="utter_test_dasgleiche_wrong")
            return {"dasgleiche": None}
        dispatcher.utter_message(
            text=f'Das ist richtig. Das Fahrrad von meinem Nachbarn hat mir so gut gefallen, dass ich mir das gleiche Rad gekauft habe.')
        return {"dasgleiche": slot_value}


# Custom Action Code
# ----------------------------------

# Text-Action for demo purposes only
class ActionTestAction(Action):

    def name(self) -> Text:
        return "action_test_action"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        msg = f"Das ist eine Testnachricht von einem rasa 3.0 custom Action server"
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


class ActionClearAsLike(Action):
    def name(self) -> Text:
        return "action_clear_as_like"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("as", None), SlotSet("like", None)]


class ActionClearSeeminglyApparently(Action):
    def name(self) -> Text:
        return "action_clear_seemingly_apparently"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("seemingly", None), SlotSet("apparently", None)]


class ActionClearSame(Action):
    def name(self) -> Text:
        return "action_clear_same"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("dasselbe", None), SlotSet("dasgleiche", None)]


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


# Returns current time for Germany and Qatar
class ActionTellJoke(Action):

    def name(self) -> Text:
        return "action_tell_joke"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        msg = get_joke()

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

        try:
            create_csv_from_url('https://www.alfa-bot.de/wp-content/uploads/2022/11/gruppenWM2022.csv')

            df = pd.read_csv('tempfile.csv', sep=';', header=0)
            res = get_teams(wm_final_group, df)
            msg = ('Die Mannschaften in Gruppe ' + wm_final_group.upper() + ' sind: {}'
                   .format(', '.join([str(i) for i in res])))
        finally:
            remove_csv('tempfile.csv')

        dispatcher.utter_message(text=msg)

        return [SlotSet("group", None)]


# Returns group of a given team at Fifa WM 2022
class ActionTellGroup(Action):
    def name(self) -> Text:
        return "action_tell_group"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        team = (tracker.get_slot("finals_team"))
        msg = "Tut mir Leid, ich konnte gerade leider nicht nach deiner Mannschaft suchen. Versuche es später noch mal."
        res = "None"

        # Handle case that user wants to skip form
        if team == "Abort":
            dispatcher.utter_message(response="utter_something_else")
            return [SlotSet("finals_team", None), SlotSet("group", str(res))]

        try:
            create_csv_from_url('https://www.alfa-bot.de/wp-content/uploads/2022/11/gruppenWM2022.csv')
            df = pd.read_csv('tempfile.csv', sep=';', header=0)
            res = get_group(team, df)

            msg = f"Die Mannschaft von {team} spielt in Gruppe {res}."
            remove_csv('tempfile.csv')
        finally:
            buttons = [{"title": f"Wer spielt noch in Gruppe {res}?",
                        "payload": f"Wer spielt noch in Gruppe {res}?"}]
            dispatcher.utter_message(text=msg)
            dispatcher.utter_message(text=f"Frage mich gerne, wer noch in Gruppe {res} spielt.", buttons=buttons)
        # dispatcher.utter_message(response="utter_ask_other_teams")
        return [SlotSet("group", res), SlotSet("finals_team", None)]


# Custom Actions for Surveys
class ActionSubmitSurvey(Action):
    def name(self) -> Text:
        return "action_submit_survey"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        slot_lotnum = tracker.get_slot('lot_number')
        today = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        slot_smartphone = tracker.get_slot('smartphone')
        slot_need_help = tracker.get_slot('need_help')
        slot_read = tracker.get_slot('read_answers')
        slot_understand = tracker.get_slot('understand_answers')
        slot_helpful = tracker.get_slot('helpful')
        slot_learn = tracker.get_slot('learn_with_bot')
        slot_learn_why = tracker.get_slot('learn_why')
        slot_learn_not = tracker.get_slot('learn_not')
        slot_pos = tracker.get_slot('critic_pos')
        slot_neg = tracker.get_slot('critic_neg')

        header = ['Losnummer', 'Datum', 'Smartphone', 'Hilfe benötigt', 'Antworten gelesen', 'Antworten verstanden',
                  'Hilfreich', 'App akzeptiert', 'Warum', 'Warum nicht', 'Gut', 'Verbesserung']
        data = [slot_lotnum, today, slot_smartphone, slot_need_help, slot_read, slot_understand, slot_helpful,
                slot_learn, slot_learn_why, slot_learn_not, slot_pos, slot_neg]
        survey_result = [header, data]

        send_survey_mail(survey_result)

        dispatcher.utter_message(response="utter_submit_survey")

        return [SlotSet("lot_number", None), SlotSet("helpful", None), SlotSet("smartphone", None),
                SlotSet("learn_with_bot", None), SlotSet("learn_why", None), SlotSet("learn_not", None),
                SlotSet("need_help", None), SlotSet("read_answers", None), SlotSet("understand_answers", None),
                SlotSet("critic_pos", None), SlotSet("critic_neg", None)]


# Custom action returning team phase
class ActionTellPhase(Action):
    phases = {"gruppenphase": "20. November bis 2. Dezember 2022", "achtelfinale": "vom 3. bis 6. Dezember",
              "viertelfinale": "am 9. und 10. Dezember 2022", "halbfinale": "am 13. und 14. Dezember 2022",
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
                msg = f"Die Gruppenphase findet vom {self.phases[needle]} statt."
            else:
                msg = f"Das {phase} ist {self.phases[needle]}."

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


# Custom action returning a game result
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
            playday = playday_lookup()
            if int(playday) == -1:
                msg = "Das Turnier hat noch nicht begonnen. Daher kann ich dir keine Spielergebnisse zeigen."
            else:
                for day in range(GAMES_START_DAY, int(playday)):
                    game_list = game_list + get_games(str(day))
                msg = find_match(team, team2, game_list)
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
            if playday_lookup() == "-1":
                msg = "Das Turnier hat noch nicht begonnen. Daher kann ich dir keine Spielergebnisse zeigen."
            else:
                all_ranking_tables = get_rankings()
                msg = f'Ok, hier ist die Tabelle:\n{all_ranking_tables.get_table_string(group)}'
        finally:
            dispatcher.utter_message(text=msg)

        return [SlotSet("group", None)]
