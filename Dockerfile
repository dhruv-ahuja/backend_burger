# using a python docker base image
# using a multi-stage build to save space
FROM python:3.11-slim AS builder-image

# create a venv to make copying packages folder easier b/w the different stages declaring the path to avoid path issues
# w/ packages
RUN python3.11 -m venv /home/myuser/venv 
ENV PATH="/home/myuser/venv/bin:$PATH"

# install extra libraries needed for pycurl
RUN apt-get update && apt-get install -y  curl libcurl4-openssl-dev build-essential libssl-dev

# copying and installing requirements first will avoid a re-install of all dependencies when re-building the image
COPY requirements.txt .
RUN pip3 install --no-cache-dir wheel 
RUN pip3 install --no-cache-dir -r requirements.txt 

# now starting the next layer, the one that runs the program
# FROM ubuntu:22.04 AS runner-image 
FROM python:3.11-slim AS runner-image

# creating a separate user to run the docker commands, helps with security as root access is denied to this user
RUN useradd --create-home myuser

# copy over the virtualenv created in the previous layer to the current user's dir
COPY --from=builder-image /home/myuser/venv /home/myuser/venv

# create and set workdir, copy over all data to the folder 
USER myuser
RUN mkdir /home/myuser/webapp 
WORKDIR /home/myuser/webapp
COPY . . 

EXPOSE 8000 

# improves logging behaviour for containers
ENV PYTHONUNBUFFERED=1

# activate the virtualenv
ENV VIRTUAL_ENV=/home/myuser/venv
ENV PATH="/home/myuser/venv/bin:$PATH"

RUN mkdir -p /home/myuser/log

ENV NEW_RELIC_APP_NAME=backend_burger_docker
ENV NEW_RELIC_LOG=/home/myuser/log/newrelic.log

# using /dev/shm as the worker temp dir will help prevent random locks and freezes used for gunicorn heartbeat
CMD gunicorn -b 0.0.0.0:8000 -w 4 -k uvicorn.workers.UvicornWorker --worker-tmp-dir /dev/shm src.main:app