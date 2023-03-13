# Rasa-Chatbot für Projekt ALFA-Bot - LT-Wahl NRW Prototyp

## Installation und Inbetriebnahme
###Python3 (venv)
Rasa wird in einer python3 virtual environment (venv) ausgeführt. Benötigt wird Pyhton3 und pip3
* Erstellen: `python3 -m venv ./venv`
* Aktivieren: `source ./venv/bin/activate`
* Deaktivieren: `deactivate`

###Installieren von Rasa
1. Aktivieren der virtuellen Umgebung
2. Update pip `pip3 install -U pip`
3. Installiere Rasa Open Source `pip3 install rasa`

Installieren von [Rasa X](https://rasa.com/docs/rasa-x/installation-and-setup/installation-guide) (GUI Wrapper):
Sicherstellen, dass man in der gleichen virtuellen Umgebung arbeitet, wo rasa selbst installiert wurde.

* Virtuelle Umgebung starten: `source ./venv/bin/activate`
* Rasa X installieren `pip install -U rasa-x --extra-index-url https://pypi.rasa.com/simple`

**Hinweis zur Installation von Rasa X (Stand 1.4.21):**
Maybe this is incorrect but I noticed I have to downgrade the pip version in the respective virtual environment as well. So make sure the virtual environment with rasa is active and:
```
pip install --upgrade pip==20.2
run pip -V to make sure the right version is installed
run pip install -U rasa-x --extra-index-url https://pypi.rasa.com/simple
```

###Rasa Open Source Befehle

* `rasa init`: Neues Projekt erstellen
* `rasa x`: Start rasa X Plattform
* `rasa train`: Trainiere ein CB-Model (models-Ordner steht in gitignore)
* `rasa shell`: Starte eine Unterhaltung über die Konsole
* `rasa interactive`: Starte eine Unterhaltung per Konsole mit Training
* `rasa run actions -vv`: Relevant für custom actions
* `rasa run -m models --enable-api --cors "*" -p 5021`: Wird benutzt, wenn ein Bot deployed ist und par API aktiviert werden soll.

## Zentrale Dateien und Konfigurationen

###Grundbegriffe im Rasa-Framework
**Intent**: Was der Nutzer meint (Intention). Zu finden in `nlu.yml` Beispiel: *Wie wird das Wetter?* -> Intent: *Wetterauskunft*

**Entity**: Modifier um Intents genauer zu beschreiben (Variablen). Beispiel: *Wie wird das Wetter **morgen** **in Berlin**?* -> Intent: *Wetterauskunft*, Entities: *Zeit: heute + 1* und *Ort: Berlin* 

**Response**: Eine textuelle Antwort. Zu finden in `domain.yml`. Beispiel: User: *Wie wird das Wetter morgen?* -> Bot: *Das Wetter wird morgen so ähnlich wie heute.*

**Action**: Reaktion des Bots in Kombination mit oder ohne einer *Response*. Unterschieden wird hier zwischen **Regular Actions** und **Custom Actions**. *Regular Actions* verwenden die vorgegebenen Responses aus der domain.yml, während *Custom Actions* erweiterte Programmlogik ausführen. Beispiel für Custom Actions: User: *Wie wird das Wetter morgen?* -> Action: *Wetter für aktuellen Ort und nächsten Tag per API abfragen* -> Bot: *Morgen ist für `{ORT}`, `{WETTERPROGNOSE}` vorhergesagt*

**Stories**: Bausteine eines Rasa-Chatbots. Jede Story stellt auf abstraktem Level Teile eines Dialogverlaufs dar. Zu finden in `stories.yml` Beispiel:

```yaml
-story: say_something_nice  // Name der Story
steps:                      // Dialogverlauf
    - intent: greet         // Intent, der die Story beginnt
    - action: utter_greet   // Reaktion des Bots, hier als Response *utter_greet* (s. domain.yml)
    - intent: tellSthNice   // Nächster Nutzerintent
    - action: utter_compliment // Reaktion per Response
    - intent: bye           // Intent für Verabschiedung
    - action: utter_bye     // Bot reagiert mit Verabschiedung
```
### Wichtigste yml-Dateien
* data/nlu.yml
* data/rules.yml
* data/stories.yml
* domain.yml

Hilfstool zum verifizieren der yml-Dateien: https://yamlchecker.com

####NLU.yml
Die NLU-Datei enthält Intents **zusammen** mit Beispielen. Zu jedem Intent gehört eine Liste an Beispielsätzen, die diesem Intent zugeordnet werden sollen. 
Es können auch mehrere NLU-Dateien verwendet werden, um eine bessere Übersicht zu gewährleisten.
Pro Intent sind 7-10 Beispielsätze empfehlenswert. Ggf. kann es auch nützlich sein, bei bestimmten Wörtern häufige Rechtschreibfehler mit aufzunehmen.
Beispiel. Ähnliche Eingaben, die so nicht in den Beispielsätzen stehen, werden über ML-Algorithmen auf den jeweiligen Intent geparst.
```yaml
- intent: greet
  examples: |
    - Hi
    - hey
    - moin
    - Hallo
    - Grüß dich
    - ...
```

####Domain.yml
Die Domain.yml besteht aus bis zu sieben Abschnitten:
1. Angabe der Rasa-Version, in diesem Projekt 2.0
2. Eine Auflistung aller Intents (**ohne** Beispiele), die der Chatbot "kennt".
3. *Eine Auflistung aller verwendeten Entities (Variablen)*
4. *Programmspeicher in Form von Slots*
5. Enthält alle **Responses**. Jede Response wird durch **utter_responsename** gekenntzeichnet. Siehe Beispiel unten.
6. *Übersicht von **Action-Names**. Diese Übersicht enthält die Namen aller selbst definierten *Custom-Actions**

Die Bereiche 3, 4 und 6 sind optional und kommen nur vor, wenn die Aspekte im Bot auch verwendet werden.
```yaml
version: "2.0"

intents: 
  - greet
  - goodbye
  - ...

entities:
  - name
    
slots:
  concerts:
    type: list
    influence_conversation: false
  slotname:
    type: type_of_slot // bspw. text
    influence_conversation: true // bool, muss true oder false sein
  
responses:
  utter_greet:
    - text: "Hey, wie geht es dir?" // Antworttext
  
  utter_cheer_up:
    - text: "Hier ist ein Bild, das dich zum Lachen bringt:"
    - image: "https://i.imgur.com/nGF1K8f.jpg" // lädt ein Bild nach 

  utter_mood:
    - text: "Ich bin echt happy"
    - text: "Mir geht es wirklich gut" // Alternative Antwort. Rasa wählt eine der Optionen zufällig aus
  
actions:
  - action_name_of_custom_action
```

####Stories.yml
Die Stories.yml enthält Beispiel-Konversationen, die dem einerseits vorgeben, auf welchen Intent er wie reagieren soll und darüber hinaus konkrete Dialoge mit mehreren Turn-Takings darstellen.
Im Sinne von [Conversation-Driven-Development](https://rasa.com/docs/rasa/conversation-driven-development/) sollten diese Stories am besten über die Interaktion mit dem Bot erstellt werden (bspw. über rasa interactive oder rasa x).


###Kurzdialoge: Chitchat und FAQs
Kurzdialoge wie Chitchat und FAQ unterscheiden sich vom sonstigen Dialog dahingehend, dass es sich um Fragen handelt, die i.d.R. mit einer Antwort erledigt sind. Längere Dialogverläufe sind nicht notwendig.
In Rasa werden diese Gesprächsformen wie folgt implementiert:
1. In der **config.yml** muss die `Rule Policy` zu den Policies hinzugefügt sein, damit **rules.yml** überhaupt vom Datenmodel beachtet wird.
```yaml
policies:
# other policies
- name: RulePolicy
```
2. Ebenfalls in der **config.yml** einen Responseselector pro Kurzdialog-Art anlegen. Der hier definierte Value zum Key `retrievel_intent` muss später in den nlu-Trainingsdaten und in den Responses wieder auftauchen.
```yaml
pipeline:
# Other components
- name: ResponseSelector
  epochs: 100
  retrieval_intent: faq // für FAQ-Kurzdialoge
- name: ResponseSelector
  epochs: 100
  retrieval_intent: chitchat // für Chitchat-Kurzdialoge
```
3. Regeln für die Kurzdialoge in **rules.yml** definieren. Es muss pro `retrievel_intent` nur eine Regel definiert werden. 
   Alle Subintents mit diesem Intent werden durch die Regel gleich behandelt. Wird der Retrievel Intent ausgelöst, ermittelt Rasa den wahrscheinlichsten Sub-Intent und gibt die definierte Response aus.
```yaml
rules:
  - rule: respond to FAQs
    steps:
    - intent: faq
    - action: utter_faq
  - rule: respond to chitchat
    steps:
    - intent: chitchat
    - action: utter_chitchat
```   
4. NLU-Trainingsdaten unter **nlu.yml** anpassen. 
Die Intents werden wie gewöhnlich definiert, allerdings mit gruppierendem Retrievel Intent, also bspw. `faq/`.
```yaml
nlu:
  - intent: faq/democracy
    examples: |
      - Ist Deutschland eine Demokratie?
      - Was ist eine Demokratie?
      - Was bedeutet Demokratie?
  - intent: chitchat/howAreYou
    examples: |
      - wie geht es dir?
      - geht es dir gut?
      - wie ist dein befinden?
```   
5. Domain-Datei **domain.yml** anpassen. Unter intents reicht es, die Retrievel Intent-Namen einzutragen. Die Einzelintents müssen nicht aufgeführt werden.
```yaml
intents:
# other intents
- faq
- chitchat
``` 
6. Ebenfalls in der **domain.yml** müssen die Responses wie die Intents behandelt werden
```yaml
responses:
  utter_chitchat/ask_name:
  - image: "https://i.imgur.com/zTvA58i.jpeg"
    text: Hello, my name is Retrieval Bot.
  - text: I am called Retrieval Bot!
  utter_chitchat/ask_weather:
  - text: Oh, it does look sunny right now in Berlin.
    image: "https://i.imgur.com/vwv7aHN.png"
  - text: I am not sure of the whole week but I can see the sun is out today.
``` 
7. Bot erneut mit `rasa train` trainieren. Danach sollte es funktionieren. 
   Eventuelle Warnings wie *UserWarning: Action 'utter_faq' is listed as a response action in the domain file, but there is no matching response defined. Please check your domain.* können ignoriert werden. Stand April 2021 ist das ein [offener Bug](https://github.com/RasaHQ/rasa/issues/7645) im Rasa-Github

###Sonstiges:
spaCy: https://spacy.io/usage/models#languages

Rasa und Docker:

https://rasa.com/docs/rasa-x/installation-and-setup/install/docker-compose/

https://rasa.com/docs/rasa/docker/building-in-docker/

https://hub.docker.com/r/rasa/rasa/

REST-Endpoint: https://rasa.com/docs/rasa/2.2.x/connectors/your-own-website
bei laufendem rasa x über `http://localhost:5005/webhooks/rest/webhook` per JSON-Objekt, bspw.
```JSON
{
    "message": "Wer ist der Kandidat der CDU?",
    "sender": "User-ID"
}
```
pypi-dotenv: https://pypi.org/project/python-dotenv/

### Docker Container für Rasa OSS bauen
Aktuell genutzt rasa version: 3.2.8

Docker Kommandos:

Container bauen: `docker build -t repo/images:tag .`

Container starten und interaktiv (-it) mit shell nutzen 
`docker run -it -p 8080:5005 -v $(pwd):/app repo/image:tag shell`

Container pushen `docker push repo/image:tag`

Custom Action Container selbst bauen: `docker build -f Dockerfile.customAction -t sjproost/alfabot-ca:tag .
`
Entscheidender Hinweis zum Custom-Action-Server SSL Problem:
https://stackoverflow.com/questions/52805115/certificate-verify-failed-unable-to-get-local-issuer-certificate
> I would like to provide a reference. I use cmd + space, then type Install Certificates.command, and then press Enter. After a short while, the command line interface pops up to start the installation.

Probleme bei `rasa interactive` -> 
> Bot generated from rasa init does not have any custom actions, so running the action server is unnecessary. I have various rasa test bots created on my local machine and bots with custom actions and action server running gives the same error. What's more, I solved the bug by uninstalling the uvloop==0.17.0 package.

Daher: `pip uninstall uvloop`

https://forum.rasa.com/t/solved-predicted-action-not-following-the-story/3364/8

Vielleicht auch hilfreich: RasaLit
`https://github.com/RasaHQ/rasalit`

### Chatroom zur einfachen lokalen Probe des Chatbots

```html
<head>
    <link rel="stylesheet" href="https://cdn.statically.io/gh/weberi/chatroom/master/dist/Chatroom.css" />
</head>
<body>
    <div class="chat-container"></div>
    <script src="https://cdn.statically.io/gh/weberi/chatroom/master/dist/Chatroom.js"></script>
    <script type="text/javascript">
    var chatroom = new window.Chatroom({
        host: "http://localhost:5005",
        title: "Chat with a bot",
        container: document.querySelector(".chat-container"),
        welcomeMessage: "Hallo!",
        speechRecognition: "de-DE",
        voiceLang: "de-DE"
    });
    chatroom.openChat();
    </script>
</body>
```
Um den Chatroom nutzen zu können, muss rasa als Server gestartet werden:

`rasa run --port 5005 --enable-api --cors "*"`

### Bot-Bestandteile für Befragung

#### Intents
````yaml
Intents:
- lot_number
- start_survey
````
#### Entities
````yaml
entities:
- lot_number
````

#### Slots
````yaml
lot_number:
    type: text
    influence_conversation: true
    mappings:
    - type: from_entity
      entity: lot_number
      conditions:
      - active_loop: simple_survey_form
        requested_slot: lot_number
  helpful:
    type: text
    influence_conversation: true
    mappings:
    - type: from_text
      conditions:
      - active_loop: simple_survey_form
        requested_slot: helpful
  smartphone:
    type: text
    influence_conversation: true
    mappings:
    - type: from_text
      conditions:
      - active_loop: simple_survey_form
        requested_slot: smartphone
  need_help:
    type: text
    influence_conversation: true
    mappings:
      - type: from_text
        conditions:
          - active_loop: simple_survey_form
            requested_slot: need_help
  read_answers:
    type: text
    influence_conversation: true
    mappings:
      - type: from_text
        conditions:
          - active_loop: simple_survey_form
            requested_slot: read_answers
  understand_answers:
    type: text
    influence_conversation: true
    mappings:
      - type: from_text
        conditions:
          - active_loop: simple_survey_form
            requested_slot: understand_answers
  critic_pos:
    type: text
    influence_conversation: true
    mappings:
      - type: from_text
        conditions:
          - active_loop: simple_survey_form
            requested_slot: critic_pos
  critic_neg:
    type: text
    influence_conversation: true
    mappings:
      - type: from_text
        conditions:
          - active_loop: simple_survey_form
            requested_slot: critic_neg
  learn_with_bot:
    type: text
    influence_conversation: true
    mappings:
    - type: from_text
      conditions:
      - active_loop: simple_survey_form
        requested_slot: learn_with_bot
  learn_why:
    type: text
    influence_conversation: true
    mappings:
    - type: from_text
      conditions:
      - active_loop: simple_survey_form
        requested_slot: learn_why
  learn_not:
    type: text
    influence_conversation: true
    mappings:
    - type: from_text
      conditions:
      - active_loop: simple_survey_form
        requested_slot: learn_not
````
#### Responses
```yaml
responses:
  utter_ask_lot_number:
  - text: 'Ok, du möchtest an der Befragung teilnehmen. Nenne mir dafür bitte eine Teilnahme-Nummer:'
  utter_ask_helpful:
  - buttons:
      - payload: Sehr hilfreich
        title: Sehr hilfreich
      - payload: Hilfreich
        title: Hilfreich
      - payload: Geht so
        title: Geht so
      - payload: Nicht hilfreich
        title: Nicht hilfreich
      - payload: Unbrauchbar
        title: Unbrauchbar
    text: Wie hilfreich fandest du meine Antworten?
  utter_ask_understand_answers:
  - buttons:
      - payload: Ja, alles gut verstanden
        title: Ja, alles gut verstanden
      - payload: Ja, das meiste verstanden
        title: Ja, das meiste verstanden
      - payload: Einiges nicht verstanden
        title: Einiges nicht verstanden
      - payload: Viele Antworten zu schwer
        title: Viele Antworten zu schwer
    text: Hast du meine Antworten gut verstanden?
  utter_ask_smartphone:
  - buttons:
      - payload: Ja
        title: Ja
      - payload: Nein
        title: Nein
    text: Hast du ein eigenes Smartphone?
  utter_ask_need_help:
  - buttons:
      - payload: Ja
        title: Ja
      - payload: Ja, aber nur am Anfang
        title: Ja, aber nur am Anfang
      - payload: Nein, ich konnte alles alleine
        title: Nein, ich konnte alles alleine
    text: Hast du Hilfe bei der Arbeit mit dem Chatbot benötigt?
  utter_ask_read_answers:
  - buttons:
      - payload: Alles selbst gelesen
        title: Alles selbst gelesen
      - payload: teils gelesen, teils vorlesen lassen
        title: teils gelesen, teils vorlesen lassen
      - payload: Alles vorlesen lassen
        title: Alles vorlesen lassen
    text: Hast du meine Antworten selbst gelesen oder sie dir vorlesen lassen?
  utter_ask_critic_pos:
  - buttons:
      - payload: Kein Kommentar
        title: Kein Kommentar
    text: Was hat dir an Lalo gut gefallen? Gib deine Antwort einfach unten ein.
  utter_ask_critic_neg:
  - buttons:
      - payload: Kein Kommentar
        title: Kein Kommentar
    text: Gibt es auch etwas, das wir besser machen sollten? Gib deine Antwort einfach unten ein.
  utter_ask_learn_with_bot:
    - buttons:
        - payload: Ja, im Kurs
          title: Ja, in einem Kurs
        - payload: Ja, Kurs und Alleine
          title: Ja, in einem Kurs und Alleine
        - payload: Nein, eher nicht
          title: Nein, eher nicht
      text: Könntest du dir vorstellen, mit einer App wie Lalo zu lernen?
  utter_ask_learn_why:
    - buttons:
        - payload: Kein Kommentar
          title: Kein Kommentar
      text: Welchen Vorteil siehst du in einem Chatbot?
  utter_ask_learn_not:
    - buttons:
       - payload: Kein Kommentar
         title: Kein Kommentar
      text: Warum würdest du nicht mit einem Chatbot lernen wollen?
  utter_submit_survey:
  - text: Super, ich habe alles. Danke, dass du uns dabei hilfst, Lalo zu verbessern!
```
#### Actions
```yaml
actions:
- action_submit_survey
 utter_ask_learn_with_bot
- utter_ask_learn_why
- utter_ask_learn_not
- utter_ask_smartphone
- utter_ask_need_help
- utter_ask_read_answers
- utter_ask_understand_answers
- utter_ask_critic_pos
- utter_ask_critic_neg
- utter_submit_survey
- validate_simple_survey_form
```

#### Forms
````yaml
forms:
  simple_survey_form:
    required_slots:
    - lot_number
    - smartphone
    - need_help
    - read_answers
    - understand_answers
    - helpful
    - learn_with_bot
    - learn_why
    - learn_not
    - critic_pos
    - critic_neg
````