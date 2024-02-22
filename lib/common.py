import os
import configparser
from streamlit.web.server.websocket_headers import _get_websocket_headers
import requests
import hashlib
import urllib.parse
import streamlit as st
import collections
import json
import shutil
from icecream import ic

def eai_whoami():
    headers = _get_websocket_headers()
    headers = {'Authorization': headers["Authorization"]}
    response = requests.get('https://console.elementai.com/v1/me', headers=headers)
    return response.json()["mail"].split('@')[0]


class ExtendedEnvInterpolation(configparser.ExtendedInterpolation):
    """Interpolation which expands environment variables in values."""

    def before_get(self, parser, section, option, value, defaults):
        value = os.path.expandvars(value)
        # print(value)
        return super().before_get(parser, section, option, value, defaults)


def config_to_dict(app_config):
    config = {}
    for section in app_config.sections():
        config[section] = {}
        for key in app_config[section]:
            config[section][key] = app_config[section][key]
    return config


def get_config_as_dict(config_file):
    global_parser = configparser.ConfigParser(interpolation=ExtendedEnvInterpolation())
    # global_parser.read("/mnt/core_llm_home/code/atg_platform_streamlit/config/global.ini")
    global_parser.read(config_file)
    return config_to_dict(global_parser)


def get_file_checksum(config_file):
    with open(config_file, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()
    return -1


def get_host():
    session = st.runtime.get_instance()._session_mgr.list_active_sessions()[0]
    # url = urllib.parse.urlunparse(
    #     [session.client.request.protocol, session.client.request.host, "", "", "", ""])
    # print("url", url)
    return session.client.request.host

def get_archive_file(project, app_data_home):
    processed_data = {}
    location = app_data_home + "/DONE/" + project
    if not os.path.isdir(app_data_home+'/TMP/'):
        os.mkdir(app_data_home+'/TMP/')
    temp = app_data_home+'/TMP/' + project
    if not os.path.isdir(temp):
        os.mkdir(temp)
    diff_files = collections.Counter(os.listdir(location)) - collections.Counter(os.listdir(temp))
    for file_name in diff_files:
        if file_name.startswith('.'):
            continue
        metafile = file_name.split('.')
        if len(metafile) > 2:
            metafile = metafile[0]+'.'+metafile[1]
            author_name = metafile.split('_')[-1]
        with open(location+'/'+file_name) as fh:
            ic(location+'/'+file_name)
            file_data = json.loads(fh.read())
            if isinstance(file_data, list):
                processed_data['conversation'] = file_data
                processed_data['metadata'] = {}
                processed_data['metadata']['author'] = author_name
            elif 'metadata' in file_data:
                if 'author' not in file_data['metadata']:
                    file_data['metadata']['author'] = author_name
                processed_data = file_data
        dupe_filename = temp+'/'+file_name
        with open(dupe_filename, 'w') as f:
            json.dump(processed_data, f)
    return temp


def test():
    print("*" * 40, "config/global.ini")
    config = get_config_as_dict("config/global.ini")
    for key in config:
        print(key, config[key])
    print("*" * 40, "config/now_chat.ini")
    config = get_config_as_dict("config/now_chat.ini")
    for key in config:
        print(key, config[key])


if __name__ == "__main__":
    test()
