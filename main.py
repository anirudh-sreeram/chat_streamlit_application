import streamlit as st
import os
import sys
import importlib
import traceback
import lib.common as common
import lib.app_manager as appmg

# Key Prefix
KP = "global."
#GLOBAL_CONFIG_FILE="/mnt/core_llm_home/code/atg_platform_streamlit/config/global.ini"
GLOBAL_CONFIG_FILE="config/global.ini"


def custom_excepthook(exc_type, exc_value, exc_traceback):
    # Do not print exception when user cancels the program
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    print("Main::An uncaught exception occurred:")
    print("Type: %s", exc_type)
    print("Value: %s", exc_value)

    if exc_traceback:
        format_exception = traceback.format_tb(exc_traceback)
        for line in format_exception:
            print("Main::", repr(line))


sys.excepthook = custom_excepthook


def exec_app(package, entry_point, workflow='', workflow_dir=''):
    sys.path.append(os.getcwd())
    module = importlib.import_module(package)
    func = getattr(module, entry_point)
    if workflow:
        func(workflow, workflow_dir)
    else:
        func()


def start_app():
    for key in st.session_state["GLOBAL_CONFIG"]["GLOBAL"]:
        st.session_state['global.' + key] = st.session_state["GLOBAL_CONFIG"]["GLOBAL"][key]
    app = st.session_state[KP+"CURRENT_PAGE_DATA"]
    if app in st.session_state["GLOBAL_CONFIG"]:
        for key in st.session_state["GLOBAL_CONFIG"][app]:
            st.session_state[app + '.' + key] = st.session_state["GLOBAL_CONFIG"][app][key]
    app_config = st.session_state["APP_CONFIG"][app]
    g_config = st.session_state["GLOBAL_CONFIG"]
    return exec_app(app_config['package'],
                    app_config['entry_point'],
                    app_config['workflow'] if "workflow" in app_config else '',
                    g_config['workflow_dir'] if "workflow_dir" in g_config else '')


def dump_session_state(msg):
    print("*" * 50, msg)
    for k in st.session_state:
        if k != "global.EMOJI_LIST":
            print(k, "==>", st.session_state[k])


def set_user():
    # AIDE and DART sets username after LDAP authentication
    if KP+"username" not in st.session_state:
        print("Username to be set")
        if KP+"env" not in st.session_state:
            st.session_state[KP+"username"] = "local.user"
        elif st.session_state[KP + "env"] == "LOCAL":
            st.session_state[KP + "username"] = "local.user"
        elif st.session_state[KP + "env"] == "EAI":
            st.session_state[KP + "username"] = common.eai_whoami()
        else:
            st.session_state[KP + "username"] = "local.user"


def main():
    st.session_state["GLOBAL_CONFIG"] = common.get_config_as_dict(GLOBAL_CONFIG_FILE)
    st.session_state["APP_CONFIG"] = common.get_config_as_dict(st.session_state["GLOBAL_CONFIG"]["GLOBAL"]["app_config"])
    for key in st.session_state["GLOBAL_CONFIG"]["GLOBAL"]:
        st.session_state['global.' + key] = st.session_state["GLOBAL_CONFIG"]["GLOBAL"][key]
    host = common.get_host()
    if host.startswith("localhost"):
        st.session_state[KP + "env"] = "LOCAL"
    # Set a user before any APP is invoked
    set_user()
    cmd_page_map = {}
    if st.session_state["GLOBAL_CONFIG"]["GLOBAL"]["env"] in st.session_state["GLOBAL_CONFIG"]["GLOBAL"]["enable_auth"].split(','):
        cmd_page_map[KP+"CMD_APP_AUTH"] = appmg.page_auth

    cmd_page_map[KP + "CMD_APP_SELECTED"] = start_app
    cmd_page_map[KP + "CMD_APP_MAIN"] = appmg.page_app_selector
    if st.session_state["GLOBAL_CONFIG"]["GLOBAL"]["app_manager_extended"] == "1":
        cmd_page_map[KP+"CMD_APP_NEW"] = appmg.page_new_app
        cmd_page_map[KP+"CMD_APP_EDIT"] = appmg.page_edit_apps
        cmd_page_map[KP+"CMD_APP_EDIT_ONE"] = appmg.page_app_edit
        cmd_page_map[KP+"CMD_FILE_UPLOAD"] = appmg.page_upload_files
        cmd_page_map[KP + "CMD_APP_MAIN"] = appmg.page_app_selector_and_editor
    if KP+"CURRENT_PAGE" not in st.session_state:
        appmg.reset_page("Start Page")
    # dump_session_state("Start")
    print("Current Page:", st.session_state[KP+"CURRENT_PAGE"])
    cmd_page_map[st.session_state[KP+"CURRENT_PAGE"]]()


if __name__ == '__main__':
    st.set_page_config(layout="wide")
    main()
