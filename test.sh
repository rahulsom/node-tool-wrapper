#!/bin/bash

docker build -t ntw-test -f test.Dockerfile .

exec uv run pytest -v -n auto tests/
