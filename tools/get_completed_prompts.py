import os
import json
import openpyxl

# data_dir = "/mnt/core_llm_home/streamlit/now_chat"
data_dir = "./mnt/core_llm_home/streamlit/now_chat"
completed_dir_path = data_dir + "/DONE"

turn_prompts = []
for d in os.listdir(completed_dir_path):
    dpath = os.path.join(completed_dir_path, d)
    for f in os.listdir(dpath):
        fpath = os.path.join(dpath, f)
        if os.path.isfile(fpath):
            # print("Loading:", fpath)
            if not fpath.endswith(".json"):
                continue
            wset = json.loads(open(fpath, "r").read())
            turn_prompt = []
            for turn in wset:
                if turn['role'] == 'user':
                    turn_prompt.append(turn['content'])
            turn_prompts.append(turn_prompt)
wb = openpyxl.Workbook()
ws = wb.active
for tp in turn_prompts:
    ws.append(tp)
    # for col, cv in enumerate(tp):
    #     ws[row][col] = cv

wb.save("Completed_Prompts.xlsx")
