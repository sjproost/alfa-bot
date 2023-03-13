from typing import Any, Text, Dict
import random
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from typing import List


# Helper vars and classes
similarWords = {"Als | Wie": "/enter_as_like", "Launisch | Launig": "/enter_moody_witty",
                "Dasselbe | Das Gleiche": "/enter_same",
                "Waage |Vage": "/enter_scale_vague", "Scheinbar | Anscheinend": "/enter_seemingly_apparently",
                "Seit | Seid": "/enter_since_be",
                "Ein Paar | ein paar": "/enter_few_couple", "Saite | Seite": "/enter_string_page",
                "Gewähr | Gewehr": "/enter_warranty_rifle",
                "Wieder | Wider": "/enter_again_against", "Seelisch | Selig": "/enter_mental_blessed",
                "Check | Scheck": "/enter_cheque_check", "Das | dass": "/enter_das_dass",
                "Mehr | Meer": "/enter_more_sea", "Malen | Mahlen": "/enter_paint_grain",
                "Wart | Ward": "/enter_ward_were", "War | Wahr": "/enter_was_truth"}
niceToKnow = {"Sicheres Passwort": "/enter_password", "Warum heißt es Silvester": "/enter_silvester",
              "Advent und Weihnachten": "/enter_christmas"}

smart_nuggets = similarWords
smart_nuggets.update(niceToKnow)


class QuickReplyButton:
    def __init__(self, title: str, payload: str):
        self.title = title
        self.payload = payload

    def getButton(self) -> dict:
        button = {"title": self.title, "payload": self.payload}
        return button


# Helper function to randomise praising answers
def randomise_praising_answer() -> str:
    praise_answers = ["Korrekt!", "Toll, das war die richtige Lösung",
                      "Richtig ausgewählt", "Gut gewählt", "Deine Lösung ist richtig", "So ist es"]
    msg = random.choice(praise_answers)
    return msg


# Get array of buttons
def getButtonsFromDict(pool: dict) -> list:
    buttons = []
    for entry in pool:
        qrButton = QuickReplyButton(entry, pool[entry])
        buttons.append(qrButton.getButton())
    return buttons


# Getting random subset out of dictionary
def randomSelection(pool: dict, size: int) -> list:
    buttons = []
    sample = dict(random.sample(pool.items(), size))
    buttons = getButtonsFromDict(sample)
    return buttons


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
        dispatcher.utter_message(text=randomise_praising_answer())
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
        dispatcher.utter_message(text=randomise_praising_answer())
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


# Validate Nugget since_be
class SinceBeForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_since_be_form"

    def validate_since(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_since = str(slot_value).lower()
        if solution_since != 'seit':
            dispatcher.utter_message(response="utter_test_since_wrong")
            return {"since": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"since": slot_value}

    def validate_be(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_be = str(slot_value).lower()
        if solution_be != 'seid':
            dispatcher.utter_message(response="utter_test_be_wrong")
            return {"be": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"be": slot_value}


# Validate Nugget scale_vague
class ScaleVagueForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_scale_vague_form"

    def validate_scale(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_scale = str(slot_value).lower()
        if solution_scale != 'waage':
            dispatcher.utter_message(response="utter_test_scale_wrong")
            return {"scale": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"scale": slot_value}

    def validate_vague(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_vague = str(slot_value).lower()
        if solution_vague != 'vagen':
            dispatcher.utter_message(response="utter_test_vague_wrong")
            return {"vague": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"vague": slot_value}


# Validate Nugget few_couple
class FewCoupleForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_few_couple_form"

    def validate_few(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_few = str(slot_value)
        if solution_few != 'ein paar':
            dispatcher.utter_message(response="utter_test_few_wrong")
            return {"few": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"few": slot_value}

    def validate_couple(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_couple = str(slot_value)
        if solution_couple != 'ein neues Paar':
            dispatcher.utter_message(response="utter_test_couple_wrong")
            return {"couple": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"couple": slot_value}


# Validate Nugget string page
class StringPageForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_string_page_form"

    def validate_string(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_string = str(slot_value).lower()
        if solution_string != 'saiten':
            dispatcher.utter_message(response="utter_test_string_wrong")
            return {"string": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"string": slot_value}

    def validate_page(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_page = str(slot_value).lower()
        if solution_page != 'seiten':
            dispatcher.utter_message(response="utter_test_page_wrong")
            return {"page": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"page": slot_value}


# Validate Nugget string page
class PaintGrainForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_paint_grain_form"

    def validate_paint(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_paint = str(slot_value).lower()
        if solution_paint != 'malen':
            dispatcher.utter_message(response="utter_test_paint_wrong")
            return {"paint": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"paint": slot_value}

    def validate_grain(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_grain = str(slot_value).lower()
        if solution_grain != 'mahlt':
            dispatcher.utter_message(response="utter_test_grain_wrong")
            return {"grain": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"grain": slot_value}


# Validate Nugget cheque check
class ChequeCheckForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_cheque_check_form"

    def validate_cheque(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_cheque = str(slot_value).lower()
        if solution_cheque != 'check':
            dispatcher.utter_message(response="utter_test_cheque_wrong")
            return {"cheque": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"cheque": slot_value}

    def validate_check(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_check = str(slot_value).lower()
        if solution_check != 'scheck':
            dispatcher.utter_message(response="utter_test_check_wrong")
            return {"check": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"check": slot_value}


# Validate Nugget warranty rifle
class WarrantyRifleForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_warranty_rifle_form"

    def validate_warranty(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_warranty = str(slot_value).lower()
        if solution_warranty != 'gewähr':
            dispatcher.utter_message(response="utter_test_warranty_wrong")
            return {"warranty": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"warranty": slot_value}

    def validate_rifle(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_rifle = str(slot_value).lower()
        if solution_rifle != 'gewehr':
            dispatcher.utter_message(response="utter_test_rifle_wrong")
            return {"rifle": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"rifle": slot_value}


# Validate Nugget since_be
class MoodyWittyForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_moody_witty_form"

    def validate_moody(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_moody = str(slot_value).lower()
        if solution_moody != 'launisch':
            dispatcher.utter_message(response="utter_test_moody_wrong")
            return {"moody": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"moody": slot_value}

    def validate_witty(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_witty = str(slot_value).lower()
        if solution_witty != 'launig':
            dispatcher.utter_message(response="utter_test_witty_wrong")
            return {"witty": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"witty": slot_value}


# Validate Nugget was / truth
class WasTruthForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_was_truth_form"

    def validate_was(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_was = str(slot_value).lower()
        if solution_was != 'war':
            dispatcher.utter_message(response="utter_test_was_wrong")
            return {"was": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"was": slot_value}

    def validate_truth(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_truth = str(slot_value).lower()
        if solution_truth != 'wahr':
            dispatcher.utter_message(response="utter_test_truth_wrong")
            return {"truth": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"truth": slot_value}


# Validate Nugget das / dass
class DasDassForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_das_dass_form"

    def validate_das(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_das = str(slot_value).lower()
        if solution_das != 'das':
            dispatcher.utter_message(response="utter_test_das_wrong")
            return {"das": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"das": slot_value}

    def validate_dass(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_dass = str(slot_value).lower()
        if solution_dass != 'dass':
            dispatcher.utter_message(response="utter_test_dass_wrong")
            return {"dass": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"dass": slot_value}


# Validate Nugget was / were
class WardWereForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_ward_were_form"

    def validate_ward(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_ward = str(slot_value).lower()
        if solution_ward != 'ward':
            dispatcher.utter_message(response="utter_test_ward_wrong")
            return {"ward": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"ward": slot_value}

    def validate_were(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_were = str(slot_value).lower()
        if solution_were != 'wart':
            dispatcher.utter_message(response="utter_test_were_wrong")
            return {"were": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"were": slot_value}


# Validate Nugget again / against
class AgainAgainstForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_again_against_form"

    def validate_again(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_again = str(slot_value).lower()
        if solution_again != 'wieder':
            dispatcher.utter_message(response="utter_test_again_wrong")
            return {"again": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"again": slot_value}

    def validate_against(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_against = str(slot_value).lower()
        if solution_against != 'wider':
            dispatcher.utter_message(response="utter_test_against_wrong")
            return {"against": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"against": slot_value}


# Validate Nugget mental / blessed
class MentalBlessedForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_mental_blessed_form"

    def validate_mental(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_mental = str(slot_value).lower()
        if solution_mental != 'seelische':
            dispatcher.utter_message(response="utter_test_mental_wrong")
            return {"mental": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"mental": slot_value}

    def validate_blessed(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_blessed = str(slot_value).lower()
        if solution_blessed != 'selig':
            dispatcher.utter_message(response="utter_test_blessed_wrong")
            return {"blessed": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"blessed": slot_value}


# Validate Nugget more / sea
class MoreSeaForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_more_sea_form"

    def validate_more(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
            firstTry=bool(True)
    ) -> Dict[Text, Any]:
        solution_more = str(slot_value).lower()
        if solution_more != 'mehr':
            dispatcher.utter_message(response="utter_test_more_wrong")
            return {"more": None}
        dispatcher.utter_message(
            text=randomise_praising_answer())
        return {"more": slot_value}

    def validate_sea(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
    ) -> Dict[Text, Any]:
        solution_sea = str(slot_value).lower()
        if solution_sea != 'meer':
            dispatcher.utter_message(response="utter_test_sea_wrong")
            return {"sea": None}
        dispatcher.utter_message(text=randomise_praising_answer())
        return {"sea": slot_value}


class ActionClearMoreSea(Action):
    def name(self) -> Text:
        return "action_clear_more_sea"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("more", None), SlotSet("sea", None)]


class ActionClearMentalBlessed(Action):
    def name(self) -> Text:
        return "action_clear_mental_blessed"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("mental", None), SlotSet("blessed", None)]


class ActionClearAgainAgainst(Action):
    def name(self) -> Text:
        return "action_clear_again_against"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("again", None), SlotSet("against", None)]


class ActionClearWasTruth(Action):
    def name(self) -> Text:
        return "action_clear_was_truth"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("was", None), SlotSet("truth", None)]


class ActionClearWardWere(Action):
    def name(self) -> Text:
        return "action_clear_ward_were"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("ward", None), SlotSet("were", None)]


class ActionClearDasDass(Action):
    def name(self) -> Text:
        return "action_clear_das_dass"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("das", None), SlotSet("dass", None)]


class ActionClearAsLike(Action):
    def name(self) -> Text:
        return "action_clear_as_like"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("as", None), SlotSet("like", None)]


class ActionClearSinceBe(Action):
    def name(self) -> Text:
        return "action_clear_since_be"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("since", None), SlotSet("be", None)]


class ActionClearMoodyWitty(Action):
    def name(self) -> Text:
        return "action_clear_moody_witty"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("moody", None), SlotSet("witty", None)]


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


class ActionClearScaleVague(Action):
    def name(self) -> Text:
        return "action_clear_scale_vague"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("scale", None), SlotSet("vague", None)]


class ActionClearFewCouple(Action):
    def name(self) -> Text:
        return "action_clear_few_couple"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("few", None), SlotSet("couple", None)]


class ActionClearStringPage(Action):
    def name(self) -> Text:
        return "action_clear_string_page"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("string", None), SlotSet("page", None)]


class ActionClearWarrantyRifle(Action):
    def name(self) -> Text:
        return "action_clear_warranty_rifle"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("warranty", None), SlotSet("rifle", None)]


class ActionClearChequeCheck(Action):
    def name(self) -> Text:
        return "action_clear_cheque_check"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("cheque", None), SlotSet("check", None)]


class ActionClearPaintGrain(Action):
    def name(self) -> Text:
        return "action_clear_paint_grain"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("paint", None), SlotSet("grain", None)]


# Select random subset of random nuggets
class ActionGetRandomNuggets(Action):
    def name(self) -> Text:
        return "action_get_random_nuggets"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        randomButtons = 3
        buttons = randomSelection(smart_nuggets, randomButtons)
        buttons.append({"title": "Neue Auswahl", "payload": "/random_smart_nuggets"})
        dispatcher.utter_message(text=f"Hier sind ein paar Vorschläge für kluge Häppchen", buttons=buttons)
        # dispatcher.utter_message(response="utter_ask_other_teams")
        return []


# List all similar words
class ActionGetSimilarWords(Action):
    def name(self) -> Text:
        return "action_get_similar_words"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        buttons = getButtonsFromDict(similarWords)
        dispatcher.utter_message(text=f"Hier sind alle ähnlichen Wörter", buttons=buttons)
        return []


# List all nice to knows
class ActionGetNiceToKnow(Action):
    def name(self) -> Text:
        return "action_get_nice_to_know"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        buttons = getButtonsFromDict(niceToKnow)
        dispatcher.utter_message(text=f"Hier sind alle interessanten Fakten", buttons=buttons)
        return []
