Build with rasa version: 3.2.8

Docker Kommandos:

Container bauen: `docker build -t repo/images:tag .`

Container starten und interaktiv (-it) mit shell nutzen 
`docker run -it -p 8080:5005 -v $(pwd):/app repo/image:tag shell`

Container pushen `docker push repo/image:tag`