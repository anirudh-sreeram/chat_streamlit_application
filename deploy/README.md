# Deploy Commands

Start the docker and then run the following shell commands

```shell
export IMAGE=registry.console.elementai.com/snow.core_llm/atg_platform_streamlit
docker build -t $IMAGE .
docker push $IMAGE
```

# Shell on a job
```shell
eai job exec <JOBID> /bin/bash
# Job 8
eai job exec 6c4214ab-27f7-4f7c-b72e-e904788974ba /bin/bash

# Job 9
eai job exec eac889c3-2d88-4b99-a8ef-a04ed521233b /bin/bash

# Job test
eai job exec e26389fc-fb68-470c-a8c0-484902a090c7 /bin/bash

# job DPO
eai job exec 4c180f9f-eed7-4fdc-a00a-9cdb4529a42d /bin/bash
```

# Docker Image Management
## List Images
```shell
docker images
```

## Remove Images
```shell
docker rmi --force 948de828a027 e742468a2249
```

# Renaming Jobs
```shell
% eai job set 3f0bf9ac-d5da-4898-9800-1f07239fe7bf --name "decommisioning"
id                                   state     name           account       creator               created              command runs.exitCode accessUrl
3f0bf9ac-d5da-4898-9800-1f07239fe7bf SUCCEEDED decommisioning snow.core_llm snow.partha_mukherjee 2023-12-19T22:55:38Z []      0             
% eai job set 410d3fa6-d176-4675-910e-6936290fd745 --name "decommisioning_1"
id                                   state      name             account       creator               created              command runs.exitCode accessUrl
410d3fa6-d176-4675-910e-6936290fd745 CANCELLING decommisioning_1 snow.core_llm snow.partha_mukherjee 2023-12-20T00:09:38Z []      -             
% eai job set 8cf60cf4-c7d5-4e45-9c5c-fb80282315e6 --name "core_llm_labelling_test"  
id                                   state   name                    account       creator               created              command runs.exitCode accessUrl
8cf60cf4-c7d5-4e45-9c5c-fb80282315e6 RUNNING core_llm_labelling_test snow.core_llm snow.partha_mukherjee 2023-12-21T05:16:00Z []      -

eai job set  1c9d5fb0-9c4e-4a07-851f-c98cb0bb6720 --name "atg_solution_eng_dpo_decommisioning_1"            
```