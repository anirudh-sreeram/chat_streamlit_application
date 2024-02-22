#!/usr/bin/env bash

cp Dockerfile_test Dockerfile
export IMAGE=registry.console.elementai.com/snow.core_llm/atg_platform_streamlit_test
docker build -t $IMAGE .
docker push $IMAGE
