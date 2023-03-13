from typing import Any, Text, Dict
import pandas as pd
import requests
import os
import urllib.parse
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from typing import List

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


# Util functions
# ----------------------------------
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


# Copies a csv-file from given url to server, naming it 'tempfile.csv'. File has to be deleted by function remove_csv(path: str)
def create_csv_from_url(url: str):
    response = requests.get(url)
    tempfile = open('tempfile.csv', 'wb')
    tempfile.write(response.content)
    tempfile.close()


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


# Custom Action Code
# ----------------------------------
# Clear Slots Action for polling station search (Landtagswahl NRW 2022)
class ActionClearSlots(Action):
    def name(self) -> Text:
        return "action_clear_slots"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("polling_num", None), SlotSet("polling_city", None)]



