#!/usr/bin/env bash

cp Dockerfile_prod Dockerfile
export IMAGE=registry.console.elementai.com/snow.core_llm/atg_platform_streamlit
docker build -t $IMAGE .
docker push $IMAGE
