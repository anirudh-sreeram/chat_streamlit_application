#!/usr/bin/env python3

"""
Library to compute token count in chat
"""
import os
import json
import fcntl
import threading
from transformers import AutoTokenizer


class TokenCounter:
    __instance = None

    @staticmethod
    def get_instance(store_path, checkpoint, prefix_dict):
        print("TokenCounter: Path =", store_path, "Checkpoint =", checkpoint)
        if TokenCounter.__instance is None:
            TokenCounter(store_path, checkpoint, prefix_dict)
        else:
            TokenCounter.__instance.prefix_dict = prefix_dict
        return TokenCounter.__instance

    def __init__(self, store_path, checkpoint, prefix_dict):
        if TokenCounter.__instance is not None:
            raise Exception("Code Error: Token Counter is a singleton!")
        self.requests = []
        self._lock = threading.Lock()
        self.store_path = store_path
        self.checkpoint = checkpoint
        self.file_token_map = {}
        self.prefix_dict = prefix_dict
        if os.path.isfile(store_path):
            self.load()
        self.tokenizer = AutoTokenizer.from_pretrained(self.checkpoint, use_fast=True)
        TokenCounter.__instance = self

    def get_prompt_token_count(self, prompt_string):
        try:
            # print("get_prompt_token_count:Prompt String", prompt_string)
            tokenized = self.tokenizer(prompt_string)
            # print("get_prompt_token_count:Tokenized", tokenized)
            inputs = tokenized["input_ids"]
            # print("get_prompt_token_count:Tokens", len(inputs))
            return len(inputs)
        except Exception as e:
            print("Exception:get_prompt_token_count:", prompt_string, "::", str(e))
            return -1

    def get_prompt_string(self, wset, robot_response='content'):
        if len(wset) < 1:
            return ""
        prompt_string = ""
        for turn in wset:
            if "role" in turn and turn["role"] in list(self.prefix_dict.keys()):
                # print("TURN based data: ", turn)
                if turn["role"] == "robot":
                    prompt_string += self.prefix_dict[turn["role"]] + turn[robot_response] + self.prefix_dict["end"]
                else:
                    prompt_string += self.prefix_dict[turn["role"]] + turn["content"] + self.prefix_dict["end"]
        return prompt_string

    def get_chat_token_count(self, wset, rlhf_robot=False):
        if rlhf_robot:
            prompt_string_success = self.get_prompt_string(wset, 'chosen')
            prompt_string_rejected = self.get_prompt_string(wset, 'rejected')
            count_success = 0
            count_rejected = 0
            if prompt_string_success:
                count_success = self.get_prompt_token_count(prompt_string_success)
            if prompt_string_rejected:
                count_rejected = self.get_prompt_token_count(prompt_string_rejected)
            return max([count_success, count_rejected])
        else:
            count = 0
            prompt_string = self.get_prompt_string(wset)
            if prompt_string:
                count = self.get_prompt_token_count(prompt_string)
            return count

    def get_token_count(self, filename, rlhf_robot=False):
        if filename in self.file_token_map:
            return self.file_token_map[filename]
        wset = []
        with open(filename) as fh:
            wset = json.load(fh)
        token_count = self.get_chat_token_count(wset, rlhf_robot)
        if token_count > 0:
            self.set_token_count(filename, token_count)
            self.save()
        return token_count

    def set_token_count(self, filename, token_count):
        self.file_token_map[filename] = token_count

    def save(self):
        with self._lock:
            with open(self.store_path, "w") as fh:
                fcntl.lockf(fh, fcntl.LOCK_EX)
                json.dump(self.file_token_map, fh)
                fcntl.lockf(fh, fcntl.LOCK_UN)

    def load(self):
        with self._lock:
            with open(self.store_path) as fh:
                self.file_token_map = json.load(fh)
