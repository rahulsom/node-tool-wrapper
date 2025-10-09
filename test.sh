#!/bin/bash

docker build -t ntw-test -f test.Dockerfile .

uv run pytest -v tests/test_install.py
