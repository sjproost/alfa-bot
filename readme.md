Build with rasa version: 3.2.8

Docker Kommandos:

Container bauen: `docker build -t repo/images:tag .`

Container starten und interaktiv (-it) mit shell nutzen 
`docker run -it -p 8080:5005 -v $(pwd):/app repo/image:tag shell`

Container pushen `docker push repo/image:tag`

Custom Action Container selbst bauen: `docker build -f name_bzw._pfad_zum_Dockerfile -t repo/image:tag .
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
