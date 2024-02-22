#!/usr/bin/env bash
set -x

now=$(date +%Y_%m_%d_%H_%M_%S)
#eai job new --restartable --account snow.core_llm -d snow.core_llm.home:/mnt/core_llm_home --cpu 2 --mem 2 \
#    --name "snow_core_llm_labeling_code_deploy_prod" -- /bin/bash -c "apt-get install -y git;cd /mnt/core_llm_home/code/atg_platform_streamlit/backup && ./backup.sh && cd .. && \
#    cp -r backup /tmp/ && cp -r config /tmp/ && cp -r data /tmp/ && cp -r endpoints /tmp/ &&\
#    now=$(date +%F_%H-%M-%S) && cd .. && mv atg_platform_streamlit atg_platform_streamlit_${now} &&\
#    git clone -b prod --single-branch https://parthamukherjeesnow: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@github.com/ServiceNow/atg_platform_streamlit.git && \
#    cd atg_platform_streamlit && cp -r /tmp/backup . && cp -r /tmp/config . && cp -r /tmp/data . && cp -r /tmp/endpoints ."
# eai job set b08675a5-a58d-408f-a214-fb25a17d5260 --name snow_core_llm_labeling_code_deploy_prod_decomisioned_11

eai job new --restartable --account snow.core_llm -d snow.core_llm.home:/mnt/core_llm_home --cpu 2 --mem 2 \
    -i registry.console.elementai.com/snow.core_llm/atg_platform_streamlit_code_deploy_prod \
    --name "snow_core_llm_labeling_code_deploy_prod_"${now}
