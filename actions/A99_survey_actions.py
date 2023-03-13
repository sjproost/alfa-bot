from typing import Any, Text, Dict
import os
import smtplib
import csv
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from typing import List

# Util functions
# ----------------------------------
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


# Custom Action Code
# ----------------------------------
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

