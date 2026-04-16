FROM python:3.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        build-essential \
        ca-certificates \
        can-utils \
        cmake \
        git \
        iproute2 \
        libglib2.0-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY communication ./communication
COPY examples ./examples

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install .

CMD ["/bin/bash"]
