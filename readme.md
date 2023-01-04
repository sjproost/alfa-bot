Build with rasa version: 3.2.8

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
        welcomeMessage: "Nice to meet you.",
        speechRecognition: "en-US",
        voiceLang: "en-US"
    });
    chatroom.openChat();
    </script>
</body>
```
Um den Chatroom nutzen zu können, muss rasa als Server gestartet werden:

`rasa run --port 5005 --enable-api --cors "*"`