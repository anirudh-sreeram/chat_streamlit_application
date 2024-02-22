#!/usr/bin/env python3

"""
This tool for Metadata management
"""
import os.path
import json
import time
import shutil


class MetadataManager:
    RELOAD_PERIOD = 300  # 5 mins

    def __init__(self, filename):
        self.last_load = None
        self.metadata = {}
        self.metadata_filepath = filename
        self.data_dir = os.path.dirname(self.metadata_filepath)
        self.refresh()

    def refresh(self):
        self.load()
        self.last_load = time.time()
        
    def reverse_metadata(self):
        return {v: k for k, v in self.metadata.items()}

    def get(self, label):
        if time.time() - self.last_load > MetadataManager.RELOAD_PERIOD:
            self.refresh()
        if label in self.metadata:
            return self.metadata[label]
        return ''

    def get_label_from_filepath(self, filepath):
        if time.time() - self.last_load > MetadataManager.RELOAD_PERIOD:
            self.refresh()
        # print("Searching Metadata for", filepath)
        print(self.metadata, self.metadata_filepath)
        for label in self.metadata:
            # print("get_label_from_filepath:", filepath, self.metadata[label])
            if self.metadata[label] == filepath:
                return label
        return ''

    def set(self, fpath, content='', label=''):
        if not label:
            if not content:
                conversation = json.loads(open(fpath, "r").read())
                if isinstance(conversation, list):
                    if len(conversation) > 0 and "content" in conversation[0]:
                        content = conversation[0]["content"]
                    else:
                        print("Error: List Metadata:Set: No content in", fpath)
                        return
                elif isinstance(conversation, dict):
                    if "conversation" in conversation:
                        content = conversation["conversation"][0]["content"]
                    else:
                        print("Error: Dict Metadata:Set: No content in", fpath)
                        return
                else:
                    print("Error: Metadata:Set:File content not in list or dict format", fpath)
                    return
            label = self.get_label(content)
        rev_metadata = self.reverse_metadata()
        # if os.path.realpath(fpath) not in rev_metadata:
        #     print("Adding Metadata:", label, "=>", fpath)
        #     self.metadata[label] = os.path.realpath(fpath)
        if fpath not in rev_metadata:
            print("Adding Metadata:", label, "=>", fpath)
            self.metadata[label] = fpath
        return label

    def get_labels(self):
        return list(self.metadata.keys())

    def change_label(self, old_label, new_label):
        if old_label:
            self.metadata[new_label] = self.metadata.pop(old_label)

    def get_label(self, content):
        if len(content) > 20:
            label = content[:20].strip() + " >"
        else:
            label = content.strip() + " >"
        while label in self.metadata:
            label += '>'
        return label

    def load(self):
        print("Loading Metadata:", self.metadata_filepath)
        if os.path.exists(self.metadata_filepath):
            self.metadata = json.loads(open(self.metadata_filepath, "r").read())
        # self.display("Loaded")
        filtered_metadata = {}
        for label in self.metadata:
            if os.path.isfile(self.metadata[label]):
                # if os.path.realpath(self.metadata[label]) not in filtered_metadata.values():
                #     filtered_metadata[label] = os.path.realpath(self.metadata[label])
                if self.metadata[label] not in filtered_metadata.values():
                    filtered_metadata[label] = self.metadata[label]
            else:
                print("File[%s] Missing for Label[%s]" % (self.metadata[label], label))
        self.metadata = filtered_metadata
        self.load_missing()
        self.save()

        # self.display("Missing Label Added")

    def load_missing(self):
        for file in os.listdir(self.data_dir):
            if file == "metadata.json":
                continue
            if not file.endswith(".json"):
                continue
            # fpath = os.path.realpath(os.path.join(self.data_dir, file))
            fpath = os.path.join(os.path.join(self.data_dir, file))
            rev_metadata = self.reverse_metadata()
            if fpath not in rev_metadata:
                print("++ Adding New label:", fpath)
                self.set(fpath)

    def save(self):
        print("Saving Metadata:", self.metadata_filepath)
        json.dump(self.metadata, open(self.metadata_filepath, 'w'))

    def copy(self, label, user=''):
        if label not in self.metadata:
            print("Error", label, "not in Metadata", self.metadata)
            return ''
        label_filepath = self.metadata[label]
        lfparts = label_filepath.split('/')
        same_location_copy = True
        # File Copy
        if user and user != lfparts[-3]:
            lfparts[-3] = user
            copied_filepath = "/".join(lfparts)
            same_location_copy = False
        else:
            copied_filepath = label_filepath.replace(".json", "_copy.json")

        num = 1
        while os.path.isfile(copied_filepath):
            if copied_filepath.endswith("_" + str(num-1) + ".json"):
                copied_filepath = copied_filepath.replace("_" + str(num-1) + ".json", "_%s.json" % num)
            else:
                copied_filepath = copied_filepath.replace(".json", "_%s.json" % num)
            num += 1
        print("shutil.copy(",label_filepath, copied_filepath, ")")
        shutil.copy(label_filepath, copied_filepath)

        # Update Metadata
        if same_location_copy:
            copied_chat_label = label + " copy"
            while copied_chat_label in self.metadata:
                copied_chat_label += '>'
            self.metadata[copied_chat_label] = copied_filepath
            self.save()
        else:
            mm = MetadataManager(os.path.join(os.path.dirname(copied_filepath), "metadata.json"))
            # Loading the Metadata above registers non-added files with default label
            mm.change_label(mm.get_label_from_filepath(copied_filepath), label)
            print("Setting", copied_filepath, "label", label)
            mm.save()

    def display(self, display_tag):
        print('+' * 40, display_tag)
        for label in self.metadata:
            print(label.replace('\n', ' '), "=>", self.metadata[label])


def test():
    # mm = MetadataManager("/Users/partha.mukherjee/data_api/llm/atg_platform_streamlit/mnt/core_llm_home/streamlit/now_chat/Partha/metadata.json")
    mm = MetadataManager("/Users/partha.mukherjee/data_api/llm/atg_platform_streamlit/data/metadata.json")
    # mm.display("At End")
    mm.save()


def change_path(nfpath):
    with open(nfpath) as fh:
        obj = json.load(fh)
    print(obj)
    for key, value in obj.items():
        if value.startswith("/mnt"):
            obj[key] = '.' + value
        elif value.startswith("/Users"):
            obj[key] = value.replace("/Users/partha.mukherjee/data_api/llm/atg_platform_streamlit", ".")
    with open(nfpath, "w") as fh:
        json.dump(obj, fh)


def traverse_dir(dpath):
    for f in os.listdir(dpath):
        fpath = os.path.join(dpath, f)
        if f == "metadata.json":
            change_path(fpath)
        elif os.path.isdir(fpath):
            traverse_dir(fpath)


def convert_path_to_local():
    traverse_dir("./mnt/core_llm_home/streamlit/now_chat")


if __name__ == '__main__':
    # test()
    convert_path_to_local()
