FROM python:3.9

RUN pip3 install streamlit==1.29.0
RUN pip3 install streamlit-ace==0.1.1
RUN pip3 install langchain==0.0.209
RUN pip3 install datasets==2.12.0
RUN pip3 install requests
RUN pip3 install wikipedia
RUN pip3 install transformers==4.30.1
RUN pip3 install ldap3==2.9.1
RUN pip3 install plotly==5.17.0
RUN pip3 install pandas==2.0.2
RUN pip3 install openpyxl==3.1.2
RUN pip3 install plotly==5.17.0
RUN pip3 install streamlit-float==0.3.2
RUN pip3 install icecream==2.1.3
RUN pip3 install fuzzywuzzy
RUN curl https://console.elementai.com/cli/install | sh && chmod +x ./eai && mv ./eai /usr/local/bin/ && eai upgrade
RUN apt-get install -y apt-transport-https
RUN apt-get update
RUN apt-get install -y vim
#WORKDIR /mnt/core_llm_home/code/atg_platform_streamlit
ENV TZ="America/Los_Angeles"
CMD set -x;cd ~;pwd;ls;\
    git clone -b main --single-branch https://anirudh-sreeram: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@github.com/anirudh-sreeram/chat_streamlit_application.git && \
    cd chat_streamlit_application && rm -rf results && ln -s /mnt/task_intel_org_home/chat_streamlit_job_data results && pip install fuzzywuzzy &&\
    streamlit run main.py --server.port=8080 --browser.serverAddress=https://${EAI_JOB_ID}.job.console.elementai.com --server.enableXsrfProtection=false --server.enableCORS=false
