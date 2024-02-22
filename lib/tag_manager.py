#!/usr/bin/env python3

"""
This tool for tag management
"""
import os.path
import pickle
import shutil
import threading
import fcntl
import time

import pandas as pd


class TagManager:
    __instance = None
    TAG_RELOAD_PERIOD = 300 # 5 mins
    @staticmethod
    def get_instance(app_path):
        if TagManager.__instance is None:
            TagManager(app_path)
        return TagManager.__instance

    def __init__(self, app_path):
        if TagManager.__instance is not None:
            raise Exception("Code Error: glide is a singleton!")
        self.requests = []
        self._lock = threading.Lock()
        self.app_path = app_path
        self.last_load = 0
        [self.tags, self.objects, self.tag_objects_map, self.object_tags_map] = self.load()
        TagManager.__instance = self

    def get_filepath(self):
        return "%s.pickle" % self.app_path

    def save(self):
        with self._lock:
            # print("save: Lock acquired")
            [self.tags, self.objects, self.tag_objects_map, self.object_tags_map] = self.load()
            print("Save:Processing Tag Requests", self.requests)
            for pair in self.requests:
                for key in pair["relation"]:
                    if pair["mode"] == "tag":
                        self.tag(key, pair["relation"][key], lock_acquired=True)
                    elif pair["mode"] == "untag":
                        self.untag(key, pair["relation"][key], lock_acquired=True)
                    elif pair["mode"] == "rename":
                        self.rename_object(key, pair["relation"][key], lock_acquired=True)
            self.requests = []
            objects = [self.tags, self.objects, self.tag_objects_map, self.object_tags_map]
            with open(self.get_filepath(), "wb") as fh:
                fcntl.lockf(fh, fcntl.LOCK_EX)
                pickle.dump(objects, fh)
                fcntl.lockf(fh, fcntl.LOCK_UN)
        # print("Saved Label:", self.get_filepath())

    def load(self):
        self.last_load = time.time()
        fpath = self.get_filepath()
        if os.path.exists(fpath):
            with open(fpath, "rb") as fh:
                return pickle.load(fh)
        return [{}, {}, {}, {}]

    def timed_reload(self):
        if time.time() - self.last_load > TagManager.TAG_RELOAD_PERIOD:
            self.save()

    def get_lowest_new_object_id(self):
        rev_objects = {v: k for k, v in self.objects.items()}
        for object_id in range(len(self.objects)):
            if object_id not in rev_objects:
                return object_id
        return len(self.objects)

    def get_lowest_new_tag_id(self):
        rev_tags = {v: k for k, v in self.tags.items()}
        for tag_id in range(len(self.tags)):
            if tag_id not in rev_tags:
                return tag_id
        return len(self.tags)

    def tag(self, tag, obj, lock_acquired=False):
        # print("tag: About to obtain Lock", self._lock)
        if not lock_acquired:
            self._lock.acquire()
            self.requests.append({"relation":{tag: obj}, "mode": "tag"})
        # print("tag: Lock acquired")

        # print("Tagging", tag, object)
        if obj not in self.objects:
            self.objects[obj] = self.get_lowest_new_object_id()
        if tag not in self.tags:
            self.tags[tag] = self.get_lowest_new_tag_id()
        if self.tags[tag] not in self.tag_objects_map:
            self.tag_objects_map[self.tags[tag]] = []
        self.tag_objects_map[self.tags[tag]].append(self.objects[obj])
        self.tag_objects_map[self.tags[tag]] = list(set(self.tag_objects_map[self.tags[tag]]))
        if self.objects[obj] not in self.object_tags_map:
            self.object_tags_map[self.objects[obj]] = []
        self.object_tags_map[self.objects[obj]].append(self.tags[tag])
        self.object_tags_map[self.objects[obj]] = list(set(self.object_tags_map[self.objects[obj]]))
        if not lock_acquired:
            self._lock.release()
        # print("tag:Lock released", self._lock)

    def untag(self, tag, obj, lock_acquired=False):
        # print("untag: About to obtain Lock", self._lock)
        if not lock_acquired:
            self._lock.acquire()
            self.requests.append({"relation": {tag: obj}, "mode": "untag"})

        # print("untag: Lock acquired", self._lock)
        # print("Untagging", tag, object)
        if obj not in self.objects:
            print("Object[%s] not found" % obj)
            return
        object_id = self.objects[obj]
        if tag not in self.tags:
            print("Tag[%s] not found" % tag)
            return
        tag_id = self.tags[tag]
        self.tag_objects_map[tag_id].remove(object_id)
        if len(self.tag_objects_map[tag_id]) < 1:
            del self.tag_objects_map[tag_id]
            del self.tags[tag]
        self.object_tags_map[object_id].remove(tag_id)
        if len(self.object_tags_map[object_id]) < 1:
            del self.object_tags_map[object_id]
            del self.objects[obj]
        if not lock_acquired:
            self._lock.release()
        # print("untag: Lock released", self._lock)

    def untag_all(self, tag):
        for obj in self.get_objects_for_tag(tag):
            self.untag(tag, obj)

    def get_tags(self):
        self.timed_reload()
        with self._lock:
            # print("get_tags: Lock acquired", self._lock)
            return list(self.tags.keys())

    def get_objects(self):
        self.timed_reload()
        with self._lock:
            # print("get_objects: Lock acquired", self._lock)
            return list(self.objects.keys())

    def get_tags_for_object(self, obj):
        self.timed_reload()
        with self._lock:
            # print("get_tags_for_object: Lock acquired", self._lock)
            # print("get_tags_for_object:", obj)
            if obj not in self.objects:
                print("get_tags_for_object:", obj, "not found")
                return []
            if self.objects[obj] not in self.object_tags_map:
                print("get_tags_for_object:", obj, "not found in map")
                return []
            rev_tags = {v: k for k, v in self.tags.items()}
            return [rev_tags[t] for t in self.object_tags_map[self.objects[obj]]]

    def get_objects_for_tag(self, tag):
        self.timed_reload()
        with self._lock:
            # print("get_objects_for_tag: Lock acquired", self._lock)
            if tag not in self.tags:
                return []
            if self.tags[tag] not in self.tag_objects_map:
                return []
            rev_objects = {v: k for k, v in self.objects.items()}
            return [rev_objects[o] for o in self.tag_objects_map[self.tags[tag]]]

    def display(self):
        print('*' * 50, "Tags")
        for t in self.tags.keys():
            print(t, "=>", self.tags[t])
        print('*' * 50, "Objects")
        for t in self.objects.keys():
            print(t, "=>", self.objects[t])
        print('*' * 50, "Tag Objects")
        for t in self.tag_objects_map.keys():
            print(t, "=>", self.tag_objects_map[t])
        print('*' * 50, "Object Tags")
        for t in self.object_tags_map.keys():
            print(t, "=>", self.object_tags_map[t])

    def get_tag_df(self):
        data = []
        for file in self.objects.keys():
            fname = os.path.basename(file)
            creator = fname.split('.json')[0].split('_')[-1]
            tags = self.get_tags_for_object(file)
            for tag in tags:
                data.append({"filename": fname, "creator": creator, "tag": tag})
        return pd.DataFrame(data)

    def rename_object(self, old_obj, new_obj, lock_acquired=False):
        if not lock_acquired:
            self._lock.acquire()
            self.requests.append({"relation": {old_obj: new_obj}, "mode": "rename"})

        if old_obj not in self.objects:
            print("TagManager:Obj not found", old_obj)
            if not lock_acquired:
                self._lock.release()
            return
        # print("TagManager:Rename", old_obj, new_obj)
        self.objects[new_obj] = self.objects.pop(old_obj)
        if not lock_acquired:
            self._lock.release()


def test1():
    if os.path.exists("../src/Testing.pickle"):
        os.remove("../src/Testing.pickle")
    tm = TagManager.get_instance("Testing")
    tm.tag("t1", "Test 1")
    # tm.display()
    tm.tag("t2", "Test 2")
    # tm.display()
    tm.tag("t3", "Test 3")
    # tm.display()
    tm.tag("t2", "Test 3")
    # tm.display()
    tm.tag("t3", "Test 1")
    # tm.display()
    tm.tag("t3", "Test 2")
    tm.display()
    tm.save()


def test2():
    tm = TagManager.get_instance("Testing")
    print("Get Tags:", tm.get_tags())
    print("Get Objects:", tm.get_objects())
    print("Tag for Test 1", tm.get_tags_for_object("Test 1"))
    print("Objects for tag t1", tm.get_objects_for_tag("t1"))
    print("Objects for tag t3", tm.get_objects_for_tag("t3"))


def test3():
    tm = TagManager.get_instance("Testing")
    tm.tag("t1", "Test 1")
    tm.tag("t2", "Test 2")
    tm.tag("t3", "Test 3")
    tm.tag("t2", "Test 3")
    tm.tag("t3", "Test 1")
    tm.tag("t3", "Test 2")
    tm.untag("t3", "Test 3")
    tm.display()
    shutil.copy("/Users/partha.mukherjee/Downloads/label.pickle", "../src/Testing.pickle")
    tm.save()
    tm.display()


def test4():
    shutil.copy("/llm/atg_platform_streamlit/mnt/core_llm_home/streamlit/now_chat/label.pickle", "Testing.pickle")
    tm = TagManager.get_instance("Testing")
    df = tm.get_tag_df()
    print(df.head())


def convert_path_to_local():
    nfpath = "./mnt/core_llm_home/streamlit/now_chat/label.pickle"
    shutil.copy(nfpath, "./mnt/core_llm_home/streamlit/now_chat/label_backup.pickle")
    with open(nfpath, 'rb') as fh:
        obj = pickle.load(fh)
    print(obj)
    new_map = {}
    for key in obj[1]:
        if key.startswith("/mnt"):
            new_map["." + key] = obj[1][key]
        else:
            print(key)
    obj[1] = new_map
    with open(nfpath, "wb") as fh:
        pickle.dump(obj, fh)


if __name__ == '__main__':
    test1()
    test2()
    test3()
    test4()
    # convert_path_to_local()