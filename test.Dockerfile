FROM ubuntu:latest
RUN apt-get update \
    && apt-get install -y curl jq git \
    && rm -rf /var/lib/apt/lists/*
