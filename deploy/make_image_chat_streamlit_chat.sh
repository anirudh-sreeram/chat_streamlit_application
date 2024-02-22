#!/usr/bin/env bash

cp Dockerfile_chat_streamlit_job Dockerfile
export IMAGE=registry.console.elementai.com/snow.task_intel_org/chat_streamlit_job
docker build -t $IMAGE .
docker push $IMAGE
