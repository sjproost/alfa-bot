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
from typing import Any, Text, Dict
import requests
import os
import json
import sys
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from typing import List
from requests.exceptions import HTTPError


# Helper vars and classes
# ----------------------------------

# Helper class for soccer games
class QuickReplyButton:
    def __init__(self, title: str, payload: str):
        self.title = title
        self.payload = payload

    def getButton(self) -> dict:
        button = {"title": self.title, "payload": self.payload}
        return button


# Util functions
# ----------------------------------
# Copies a csv-file from given url to server, naming it 'tempfile.csv'. File has to be deleted by function remove_csv(path: str)
def create_csv_from_url(url: str):
    response = requests.get(url)
    tempfile = open('tempfile.csv', 'wb')
    tempfile.write(response.content)
    tempfile.close()


# Removes local copy of file 'tempfile.csv', created by function create_csv_from_url
def remove_csv(path: str) -> None:
    file_to_remove = path
    if os.path.exists(file_to_remove):
        os.remove(file_to_remove)
    else:
        print("%s does not exist!" % file_to_remove)


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


# Generate a Google Search request from given string (Assumption: string = utterance)
def googleSearchRequest(utterance: str) -> str:
    # sample url: https://www.google.com/search?q=was+läuft+im+kino&cr=countryDE&lr=lang_de
    base_url = 'https://www.google.com/search?q='
    country = '&cr=countryDE'
    langcode = '&lr=lang_de'

    request_string = utterance.replace(" ", "+")
    search_string: str = base_url + request_string + country + langcode
    return search_string


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