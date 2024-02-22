#!/usr/bin/env python3

"""
Tag Completed Chats as COM-S or COM-M
S -> Single Turn. No user prompt
M -> Multi Turn

Set PYTHONPATH=.:$PYTHONPATH
Run from /mnt/core_llm_home/code/atg_platform_streamlit
python3 tools/completed_file_tagging.py

Revert:
cp /mnt/core_llm_home/streamlit/now_chat/label_backup.pickle /mnt/core_llm_home/streamlit/now_chat/label.pickle
"""
import os
import sys
import json
import shutil
from lib import tag_manager as tm
from lib import token_counter as tk

data_dir = "./mnt/core_llm_home/streamlit/now_chat"
completed_dir_path = data_dir + "/DONE"

tagm = tm.TagManager.get_instance(os.path.join(data_dir, "label"))


def get_labeler(comfile, nickname=True):
    # Only nicknames who marked task as completed
    nickname_to_name_map = {
        "Partha": "partha.mukherjee",
        "Ranjani": "ranjani.iyer",
        "Ross": "ross.young",
        "Simon": "simon.rosen",
        "Viktoriya": "viktoriya.gubaidullina",
        "Anne": "anne.heaton-dunlap",
        "Dante": "dante.camargo",
        "Rachel": "rachel.hansen",
        "Maggie": "maggie.baird"
    }

    fname = os.path.basename(comfile)
    fname_without_extension = fname.replace('.json', '')
    if "_PM_" in fname_without_extension:
        labeler = fname_without_extension.split("_PM_")[1]
    elif "_AM_" in fname_without_extension:
        labeler = fname_without_extension.split("_AM_")[1]
    else:
        print("Labeller time not having AM/PM", comfile)
        labeler = "invalid"
    if '_copy' in labeler:
        labeler = labeler.split('_copy')[0]
    if nickname and labeler in nickname_to_name_map:
        return nickname_to_name_map[labeler]
    return labeler


def get_tag_filepath(comfile):
    fname = os.path.basename(comfile)
    labeler = get_labeler(comfile, False)
    return "%s/%s/%s" % (data_dir, labeler, fname)


projects = ["DPO", "PROJECT_1", "PROJECT_2", "PROJECT_3", "GSM8K", "CHAT_SUMMARIZATION", "Research", "RequesterAssist",
            "StrategyQa", "intent_classification", "Playground", "AIDEResearch", "PROJECT_KB_prompting",
            "AISS_LightHouse"]
# projects = ["intent_classification"]
shutil.copy("%s/label.pickle" % data_dir, "%s/label_backup.pickle" % data_dir)
for project in os.listdir(completed_dir_path):
    if project not in projects:
        continue
    dpath = os.path.join(completed_dir_path, project)
    for fname in os.listdir(dpath):
        # if fname != "2023_08_16-02_12_35_PM_Anne.json":
        #     continue
        fpath = os.path.join(dpath, fname)
        if os.path.isfile(fpath):
            labeler = get_labeler(fpath)
            tag_fpath = get_tag_filepath(fpath)
            nfpath = "%s/%s/%s/%s" % (data_dir, labeler, project, fname)
            print(fpath, os.path.isfile(fpath))
            print(tag_fpath, os.path.isfile(tag_fpath))
            print(nfpath, os.path.isfile(nfpath))
            if os.path.isfile(tag_fpath):
                path = os.path.dirname(nfpath)
                if not os.path.isdir(path):
                    os.makedirs(path)
                print("mv", tag_fpath, nfpath)
                shutil.move(tag_fpath, nfpath)
                print("Old:", tag_fpath, tagm.get_tags_for_object(tag_fpath))
                tagm.rename_object(tag_fpath, nfpath)
                print("New:", nfpath, tagm.get_tags_for_object(nfpath))
print("Before Save")
print(tagm.get_tags_for_object("./mnt/core_llm_home/streamlit/now_chat/Anne/2023_08_16-02_12_35_PM_Anne.json"))
print(tagm.get_tags_for_object("./mnt/core_llm_home/streamlit/now_chat/anne.heaton-dunlap/PROJECT_2/2023_08_16-02_12_35_PM_Anne.json"))
tagm.save()
print("After Save")
# ./mnt/core_llm_home/streamlit/now_chat/DONE/PROJECT_2/2023_08_16-02_12_35_PM_Anne.json
# ./mnt/core_llm_home/streamlit/now_chat/Anne/2023_08_16-02_12_35_PM_Anne.json
print(tagm.get_tags_for_object("./mnt/core_llm_home/streamlit/now_chat/Anne/2023_08_16-02_12_35_PM_Anne.json"))
print(tagm.get_tags_for_object("./mnt/core_llm_home/streamlit/now_chat/anne.heaton-dunlap/PROJECT_2/2023_08_16-02_12_35_PM_Anne.json"))
