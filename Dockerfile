FROM python:3.8-slim

USER root
# Install Rasa version 3.2.8
RUN /usr/local/bin/python3 -m pip install --upgrade pip
RUN pip3 install rasa==3.2.8

RUN pip3 install spacy

RUN python -m spacy download de_core_news_md
#&& python -m spacy link de_core_news_md

WORKDIR /app

COPY . .

RUN rasa train --fixed-model-name german-model

# Set User to run, don't run as root
RUN chgrp -R 0 /app && chmod -R g=u /app && chmod o+wr /app
USER 1001

# Set entrypoint for interactive shells
ENTRYPOINT ["rasa"]

# command to run when the container is called to run
 CMD ["run", "--enable-api", "--port", "5005"]