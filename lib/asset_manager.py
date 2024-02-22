#!/usr/bin/env python3

"""
This tool for tag management
"""
import os.path
import json
import uuid


class OneXOneRelationship:
    """
        Stores 1x1 relationship between tag -> object
        Examples:
            Completed Chat -> User who marked it
    """
    __instance = None

    @staticmethod
    def get_instance(app_path):
        if OneXOneRelationship.__instance is None:
            OneXOneRelationship(app_path)
        return OneXOneRelationship.__instance

    def __init__(self, app_path):
        if OneXOneRelationship.__instance is not None:
            raise Exception("Code Error: OneXOneRelationship Framework is a singleton!")
        else:
            self.app_path = app_path
            self.data = self.load()
            OneXOneRelationship.__instance = self

    def map(self, key, value):
        self.data[key] = value

    def get_value(self, key):
        if key in self.data:
            return self.data[key]
        return ""

    def get_filepath(self):
        return "%s.json" % self.app_path

    def save(self):
        # Merge the data from persistent store
        cur_data = self.load()
        for k in cur_data:
            if k not in self.data:
                self.map(k, cur_data[k])
        # Store the data
        json.dump(self.data, open(self.get_filepath(), 'w'))
        print("Saved %s: %s" % (self.app_path, self.get_filepath()))

    def load(self):
        fpath = self.get_filepath()
        if os.path.exists(fpath):
            print(fpath, "exists")
            json.loads(open(fpath, "r").read())
        return {}


class Nx1Relationship:
    """
    Stores 1xN relationship between ChatPath -> /User1/Note, /User2/Note
    3 Objects
    /User1/Note -> note_id1
    ChatPath -> [note_id1, note_id2]
    """
    __instance = None

    @staticmethod
    def get_instance(app_path):
        if Nx1Relationship.__instance is None:
            Nx1Relationship(app_path)
        return Nx1Relationship.__instance

    def __init__(self, app_path):
        if Nx1Relationship.__instance is not None:
            raise Exception("Code Error: Nx1Relationship Framework is a singleton!")
        else:
            self.app_path = app_path
            [self.n_object,self.onexN_nodes_map] = self.load()
            Nx1Relationship.__instance = self

    def map(self, n_object, one_object):
        if n_object not in self.n_object:
            self.n_object[n_object] = uuid.uuid4().hex
        if one_object not in self.onexN_nodes_map:
            self.onexN_nodes_map[one_object] = []
        self.onexN_nodes_map[one_object].append(self.n_object[n_object])

    def get_filepath(self):
        return "%s.json" % self.app_path

    def save(self):
        [snotes, schatpath_nodes_map] = self.load()
        for sid in snotes:
            if sid not in self.n_object:
                self.n_object[sid] = snotes[sid]
            else:
                if snotes[sid] != self.n_object[sid]:
                    # Change current space id to saved id
                    for sn_map in self.onexN_nodes_map:
                        self.onexN_nodes_map[sn_map] = [snotes[sid] if x==self.n_object[sid] else x for x in self.onexN_nodes_map[sn_map]]
                    self.n_object[sid] = snotes[sid]
        for sn_map in schatpath_nodes_map:
            if sn_map not in self.onexN_nodes_map:
                self.onexN_nodes_map[sn_map] = schatpath_nodes_map[sn_map]
            else:
                # Make sure all contents are merged
                self.onexN_nodes_map[sn_map] = list(set(schatpath_nodes_map[sn_map]).union(set(self.onexN_nodes_map[sn_map])))
        oneXmap = {}
        objects = [self.n_object, self.onexN_nodes_map]
        json.dump(objects, open(self.get_filepath(), 'w'))
        print("Saved %s: %s" % (self.app_path, self.get_filepath()))

    def load(self):
        fpath = self.get_filepath()
        print("Nx1Relationship:", fpath)
        if os.path.exists(fpath):
            json.loads(open(fpath, "r").read())
        return [{}, {}]

    def get_n_objects(self):
        return list(self.n_object.keys())

    def get_n_objects_for_object(self, object):
        if object not in self.onexN_nodes_map:
            return []
        rev_n_object = {v: k for k, v in self.n_object.items()}
        return [rev_n_object[nid] for nid in list(self.onexN_nodes_map[object])]


class NxMRelationship:
    """
    Save NxM between Tag and Object
    4 Objects
    Tag -> tag_id
    Object -> Object_id
    tag_objects_map: tag_id -> Object_ids
    object_tags_map: object_id -> tag_ids
    """
    __instance = None

    @staticmethod
    def get_instance(app_path):
        if NxMRelationship.__instance is None:
            NxMRelationship(app_path)
        return NxMRelationship.__instance

    def __init__(self, app_path):
        if NxMRelationship.__instance is not None:
            raise Exception("Code Error: Tag Framework is a singleton!")
        else:
            self.app_path = app_path
            [self.tags, self.objects, self.tag_objects_map, self.object_tags_map] = self.load()
            NxMRelationship.__instance = self

    def get_filepath(self):
        return "%s.json" % self.app_path

    def save(self):
        [stags, sobjects, stag_objects_map, sobject_tags_map] = self.load()
        for t in stags:
            if t not in self.tags:
                self.tags[t] = stags[t]
        for o in sobjects:
            if o not in self.objects:
                self.objects[o] = sobjects[o]
        for t in stag_objects_map:
            if t not in self.tag_objects_map:
                self.tag_objects_map[t] = stag_objects_map[t]
        for o in sobject_tags_map:
            if o not in sobject_tags_map:
                self.object_tags_map[o] = sobject_tags_map[o]
        objects = [self.tags, self.objects, self.tag_objects_map, self.object_tags_map]
        json.dump(objects, open(self.get_filepath(), 'w'))
        # print("Saved Label:", self.get_filepath())

    def load(self):
        fpath = self.get_filepath()
        if os.path.exists(fpath):
            json.loads(open(fpath, "r").read())
        return [{}, {}, {}, {}]

    def tag(self, tag, object):
        print("Tagging", tag, object)
        if object not in self.objects:
            self.objects[object] = uuid.uuid4().hex
        if tag not in self.tags:
            self.tags[tag] = uuid.uuid4().hex
        if self.tags[tag] not in self.tag_objects_map:
            self.tag_objects_map[self.tags[tag]] = set()
        self.tag_objects_map[self.tags[tag]].add(self.objects[object])
        if self.objects[object] not in self.object_tags_map:
            self.object_tags_map[self.objects[object]] = set()
        self.object_tags_map[self.objects[object]].add(self.tags[tag])

    def untag(self, tag, object):
        print("Untagging", tag, object)
        if object not in self.objects:
            print("Object[%s] not found" % object)
            return
        object_id = self.objects[object]
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
            del self.objects[object]

    def get_tags(self):
        return list(self.tags.keys())

    def get_objects(self):
        return list(self.objects.keys())

    def get_tags_for_object(self, object):
        if object not in self.objects:
            return []
        if self.objects[object] not in self.object_tags_map:
            return []
        rev_tags = {v: k for k, v in self.tags.items()}
        return [rev_tags[t] for t in self.object_tags_map[self.objects[object]]]

    def get_objects_for_tag(self, tag):
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


def test_OneXOneRelationship_create():
    tm = OneXOneRelationship.get_instance("Testing1")
    tm.map("Completed1", "partha")
    tm.map("Completed1", "govind")
    tm.map("Completed2", "govind")
    tm.save()


def test_OneXOneRelationship_show():
    tm = OneXOneRelationship.get_instance("Testing1")
    print("Get Users for Completed1", tm.get_value("Completed1"))
    print("Get Users for Completed2", tm.get_value("Completed2"))
    print("Get Users for Completed3", tm.get_value("Completed3"))


def test_NxMRelationship_create():
    tm = NxMRelationship.get_instance("Testing")
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
    # tm.display()
    tm.save()


def test_NxMRelationship_show():
    tm = NxMRelationship.get_instance("Testing")
    print("Get Tags:", tm.get_tags())
    print("Get Objects:", tm.get_objects())
    print("Tag for Test 1", tm.get_tags_for_object("Test 1"))
    print("Objects for tag t1", tm.get_objects_for_tag("t1"))
    print("Objects for tag t3", tm.get_objects_for_tag("t3"))


if __name__ == '__main__':
    test_OneXOneRelationship_create()
    test_OneXOneRelationship_show()
    # test_NxMRelationship_create()
    # test_NxMRelationship_show()
