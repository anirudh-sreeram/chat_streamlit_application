import os
import json

# data_dir = "/mnt/core_llm_home/streamlit/now_chat"
data_dir = "./mnt/core_llm_home/streamlit/now_chat"
completed_dir_path = data_dir + "/DONE"

turn_prompts = []
for d in os.listdir(completed_dir_path):
    dpath = os.path.join(completed_dir_path, d)
    for f in os.listdir(dpath):
        fpath = os.path.join(dpath, f)
        if os.path.isfile(fpath):
            if not fpath.endswith(".json"):
                continue
            wset = json.loads(open(fpath, "r").read())
            for turn in wset:
                if turn['role'] not in ['user', "robot", "context"]:
                    print(fpath, "Unknown Role", turn['role'])
