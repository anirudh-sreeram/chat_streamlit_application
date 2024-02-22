#!/usr/bin/env bash

cp Dockerfile_dpo Dockerfile
export IMAGE=registry.console.elementai.com/snow.task_intel_org/atg_solution_eng_dpo
docker build -t $IMAGE .
docker push $IMAGE
