FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        can-utils \
        git \
        iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY communication ./communication
COPY examples ./examples
COPY third_party/pyAgxArm ./third_party/pyAgxArm

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install .

CMD ["/bin/bash"]
