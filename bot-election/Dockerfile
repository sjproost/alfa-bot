# Generate a custom rasa docker container
# Start from python 3.8 environment
FROM python:3.8-slim

USER root
# Install Rasa version 3.2.8
RUN /usr/local/bin/python3 -m pip install --upgrade pip
RUN python -m pip install rasa==3.2.8

WORKDIR /app
ENV HOME=/app

COPY . .

# Set User to run, don't run as root
RUN chgrp -R 0 /app && chmod -R g=u /app && chmod o+wr /app
USER 1001

# Set entrypoint for interactive shells
ENTRYPOINT ["rasa"]

# command to run when the container is called to run
CMD ["run", "--enable-api", "--port", "5005"]