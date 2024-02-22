#!/usr/bin/env bash

cp Dockerfile_code_deploy_prod Dockerfile
export IMAGE=registry.console.elementai.com/snow.core_llm/atg_platform_streamlit_code_deploy_prod
docker build -t $IMAGE .
docker push $IMAGE
