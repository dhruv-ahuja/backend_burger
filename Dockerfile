FROM python:3.11-slim AS builder-image

# use uv to install the locked application environment
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/

# install extra libraries needed for pycurl
RUN apt-get update && apt-get install -y curl libcurl4-openssl-dev build-essential libssl-dev

# copying dependency metadata first will avoid reinstalling dependencies when rebuilding the image
WORKDIR /home/myuser/webapp
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

FROM python:3.11-slim AS runner-image

# creating a separate user to run the docker commands, helps with security as root access is denied to this user
RUN useradd --create-home myuser

# copy over the virtualenv created in the previous layer
COPY --from=builder-image /home/myuser/webapp/.venv /home/myuser/venv

# re-install curl for AWS ECS healthcheck
RUN apt-get update && apt-get install -y curl

USER myuser
RUN mkdir /home/myuser/webapp 
WORKDIR /home/myuser/webapp
COPY --chown=myuser:myuser . .

# improves logging behaviour for containers
ENV PYTHONUNBUFFERED=1

ENV VIRTUAL_ENV=/home/myuser/venv
ENV PATH="/home/myuser/venv/bin:$PATH"

RUN mkdir -p /home/myuser/log

EXPOSE 8000

# using /dev/shm as the worker temp dir will help prevent random locks and freezes used for gunicorn heartbeat
CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--worker-tmp-dir", "/dev/shm", "src.main:app"]
