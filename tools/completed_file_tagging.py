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

data_dir = "/mnt/core_llm_home/streamlit/now_chat"
completed_dir_path = data_dir + "/DONE"

tagm = tm.TagManager.get_instance(os.path.join(data_dir, "label"))


def get_tag_filepath(comfile, project):
    fname = os.path.basename(comfile)
    fname_without_extension = fname.replace('.json', '')
    if "_PM_" in fname_without_extension:
        labeler = fname_without_extension.split("_PM_")[1]
    elif "_AM_" in fname_without_extension:
        labeler = fname_without_extension.split("_AM_")[1]
    else:
        print("Labeller time not having AM/PM", fname_without_extension)
        labeler= "invalid"
    if '_copy' in labeler:
        labeler = labeler.split('_copy')[0]
    return "%s/%s/%s/%s" % (data_dir, labeler, project, fname)


shutil.copy("%s/label.pickle" % data_dir, "%s/label_backup2.pickle" % data_dir)
for d in os.listdir(completed_dir_path):
    dpath = os.path.join(completed_dir_path, d)
    for f in os.listdir(dpath):
        fpath = os.path.join(dpath, f)
        if os.path.isfile(fpath):
            print("Loading:", fpath)
            if not fpath.endswith(".json"):
                continue
            wset = json.loads(open(fpath, "r").read())
            mturn = 0
            for w in wset:
                if w["role"] == "user":
                    mturn += 1
            tag_fpath = get_tag_filepath(fpath, d)
            if os.path.isfile(tag_fpath):
                tagm.tag("CMP-M" if mturn > 1 else "CMP-S", tag_fpath)
                print("Tagging:", fpath, "->", "CMP-M" if mturn > 1 else "CMP-S")
            else:
                print("Tag File[%s] not found" % tag_fpath)
tagm.save()

