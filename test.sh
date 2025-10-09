#!/bin/bash

docker build -t ntw-test -f test.Dockerfile .

./npmw install
./npmw test
