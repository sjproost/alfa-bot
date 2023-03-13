from typing import Any, Text, Dict
import arrow
import pandas as pd
import requests_cache
from datetime import date
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from typing import List
from bs4 import BeautifulSoup
from .A00_general_actions import QuickReplyButton, create_csv_from_url, remove_csv, err_print

# Helper vars and classes
# ----------------------------------
GAMES_START_DAY = 1


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


# Custom Action Code
# ----------------------------------
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
