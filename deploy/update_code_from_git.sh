#!/usr/bin/env bash
set -x

cd /mnt/core_llm_home/code/atg_platform_streamlit/backup && ./backup.sh && cd .. && \
cp -r backup /tmp/ &&\
cp -r config /tmp/ &&\
cp -r data /tmp/ &&\
cp -r endpoints /tmp/ &&\
now=$(date +%F_%H-%M-%S) && cd .. && [ -d atg_platform_streamlit ] && mv atg_platform_streamlit atg_platform_streamlit_${now}; \
git clone -b prod --single-branch https://parthamukherjeesnow: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@github.com/ServiceNow/atg_platform_streamlit.git && \
cd atg_platform_streamlit &&\
cp -r /tmp/backup . && \
cp -r /tmp/config . && \
cp -r /tmp/data . && \
cp -r /tmp/endpoints .
