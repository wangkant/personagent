# syntax=docker/dockerfile:1
# personagent in a container: `personagent up` with the page open to other
# devices behind the page password. docs/deploy.md has the first-run steps.

FROM python:3.12-slim-bookworm AS build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /src
COPY . .
# A virtual environment of its own, copied whole into the image below.
RUN python -m venv /opt/personagent \
    && /opt/personagent/bin/pip install .

FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.title="personagent" \
      org.opencontainers.image.description="An agent that behaves like a person, on every platform you use." \
      org.opencontainers.image.source="https://github.com/wangkant/personagent" \
      org.opencontainers.image.licenses="PolyForm-Noncommercial-1.0.0 AND MIT AND CC-BY-NC-SA-4.0"
# PERSONAGENT_IN_CONTAINER: a first start with no page password makes one and prints it once,
# and update notices say to pull the new image.
ENV PATH=/opt/personagent/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AGENT_HOME=/data \
    PAGE_HOST=0.0.0.0 \
    PAGE_PORT=8090 \
    PERSONAGENT_IN_CONTAINER=1
RUN useradd --uid 1000 --create-home --home-dir /home/personagent --shell /usr/sbin/nologin personagent \
    && mkdir /data \
    && chown personagent:personagent /data
COPY --from=build /opt/personagent /opt/personagent
USER personagent
WORKDIR /data
# Settings, persona, memory, platform logins and the managed AstrBot all live here.
VOLUME ["/data"]
EXPOSE 8090
# The page answers once it listens; no proxy in the environment is asked.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, sys, urllib.request as r; o = r.build_opener(r.ProxyHandler({})); sys.exit(0 if o.open('http://127.0.0.1:' + os.environ.get('PAGE_PORT', '8090') + '/health', timeout=4).status == 200 else 1)"]
CMD ["personagent", "up"]
