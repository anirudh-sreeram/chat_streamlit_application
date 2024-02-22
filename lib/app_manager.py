import os
import sys
import streamlit as st
from io import StringIO
from lib import common

KP = "global."


def save_app_registry_config(app_config_file):
    # Rewrite app_registry.ini
    with open(app_config_file, "w") as fh:
        for tag in st.session_state["APP_CONFIG"]:
            fh.write("\n[%s]\n" % tag)
            for key in st.session_state["APP_CONFIG"][tag]:
                fh.write("%s=%s\n" % (key, st.session_state["APP_CONFIG"][tag][key]))


def load_emojis():
    if KP+"EMOJI_LIST" not in st.session_state:
        st.session_state[KP+"EMOJI_LIST"] = {}
        with open("resources/emojis.csv") as fh:
            line = fh.readline()
            while line:
                emoji_char, emoji_tag = line.split(',')
                st.session_state[KP+"EMOJI_LIST"][emoji_char] = emoji_tag.strip()
                line = fh.readline()


def init_values():
    if KP+"APP_NEW_NUM_FILES" not in st.session_state:
        st.session_state[KP+"APP_NEW_NUM_FILES"] = 1


def next_page(key, app):
    print("Next Page", key, app)
    st.session_state[KP+"CURRENT_PAGE"] = key
    st.session_state[KP+"CURRENT_PAGE_DATA"] = app
    print("Next Page:", st.session_state[KP + "CURRENT_PAGE"])


def reset_page(app=''):
    print("RESET PAGE", app)
    if st.session_state["GLOBAL_CONFIG"]["GLOBAL"]["enable_auth"] == "1":
        if KP + "AUTH_SUCCESSFUL" in st.session_state and st.session_state[KP + "AUTH_SUCCESSFUL"]:
            st.session_state[KP + "CURRENT_PAGE"] = KP + "CMD_APP_MAIN"
        else:
            st.session_state[KP + "CURRENT_PAGE"] = KP + "CMD_APP_AUTH"
    else:
        st.session_state[KP+"CURRENT_PAGE"] = KP+"CMD_APP_MAIN"
    st.session_state[KP+"CURRENT_PAGE_DATA"] = True


def do_add_file_upload():
    st.session_state[KP+"APP_NEW_NUM_FILES"] += 1
    # dump_session_state("Do Add File Upload")


def do_delete_file(nf, app):
    os.remove(nf)
    st.session_state["APP_CONFIG"][app]['new_files'].remove(nf)


def do_upload_files():
    new_files_uploaded = []
    init_values()
    # dump_session_state("Do Upload Files")
    for i in range(st.session_state[KP+"APP_NEW_NUM_FILES"]):
        # bytes_data = st.session_state[KP+"FILE_UPLOAD_"+str(i)].getvalue()
        stringio = StringIO(st.session_state[KP+"FILE_UPLOAD_"+str(i)].getvalue().decode("utf-8"))
        if stringio:
            with open(st.session_state[KP+"FILE_PATH_"+str(i)], "w") as fh:
                fh.write(stringio.read())
        new_files_uploaded.append(st.session_state[KP+"FILE_PATH_"+str(i)])
    reset_page(KP+"CMD_FILE_UPLOAD")


def do_add_new_app():
    load_emojis()
    init_values()
    # Create the new APP dict
    new_app_dict = {'label': st.session_state[KP+"APP_NEW_NAME"],
                    'entry_point': st.session_state[KP+"APP_NEW_FUNCION_NAME"],
                    'package': st.session_state[KP+"APP_NEW_PACKAGE"],
                    'emoji': st.session_state[KP+"EMOJI_LIST"][st.session_state[KP+"APP_NEW_EMOJI"]]}

    # Update st.session_state["APP_CONFIG"] dict
    ini_tag = new_app_dict['label'].replace(' ', '_')
    if ini_tag in st.session_state["APP_CONFIG"]:
        i = 0
        try_tag = ini_tag+"_"+str(i)
        while try_tag in st.session_state["APP_CONFIG"]:
            i += 1
            try_tag = ini_tag+"_"+str(i)
        ini_tag = try_tag
    st.session_state["APP_CONFIG"][ini_tag] = new_app_dict
    save_app_registry_config(st.session_state["global.app_config"])

    st.session_state["APP_CONFIG"][ini_tag]['new_add'] = True
    # Clear out KP+"CMD_APP_NEW" from session state
    reset_page(KP+"CMD_APP_NEW")


def do_update_app(app):
    common.get_config_as_dict(st.session_state["global.app_config"])
    del st.session_state["APP_CONFIG"][app]
    do_add_new_app()
    reset_page(KP+"CMD_APP_EDIT")


def find_key_index(lookup_map, value_to_find):
    for i, k in enumerate(list(lookup_map.keys())):
        if lookup_map[k] == value_to_find:
            return i
    return 0


def page_app_edit():
    load_emojis()
    init_values()

    app = st.session_state[KP+"CURRENT_PAGE_DATA"]
    st.markdown("### Edit APP "+app)
    st.text_input("APP Name (Like :blue[Now Chat]):", key=KP+"APP_NEW_NAME",
                  value=st.session_state["APP_CONFIG"][app]["label"])
    st.text_input("APP Entry Function Name (Like :blue[now_chat] as `def now_chat()` is its entry point):",
                  key=KP+"APP_NEW_FUNCION_NAME", value=st.session_state["APP_CONFIG"][app]["entry_point"])
    st.text_input("APP Package (Like :blue[src.now_chat]):", key=KP+"APP_NEW_PACKAGE",
                  value=st.session_state["APP_CONFIG"][app]["package"])
    st.selectbox("Emoji:", options=list(st.session_state[KP+"EMOJI_LIST"].keys()), key=KP+"APP_NEW_EMOJI",
                 index=find_key_index(st.session_state[KP+"EMOJI_LIST"],
                                      st.session_state["APP_CONFIG"][app]["emoji"]))
    st.button("Update APP", on_click=do_update_app, args=(app,))


def page_upload_files():
    init_values()
    st.markdown("### Upload Files")
    left, right = st.columns(2)
    for i in range(st.session_state[KP+"APP_NEW_NUM_FILES"]):
        if KP+"FILE_UPLOAD_"+str(i) in st.session_state:
            left.text_input("Relative FilePath:", key=KP + "FILE_PATH_" + str(i), value=st.session_state[KP+"FILE_UPLOAD_"+str(i)].name)
        else:
            left.text_input("Relative FilePath:", key=KP+"FILE_PATH_"+str(i))
        right.file_uploader("Upload File:", key=KP+"FILE_UPLOAD_"+str(i))
    left.button(":heavy_plus_sign:", key=KP+"FILE_MORE_FILE", on_click=do_add_file_upload)
    st.button("Upload Files", on_click=do_upload_files)


def page_edit_apps():
    st.markdown("### Edit APPS")
    st.markdown("<br /><br /><br />", unsafe_allow_html=True)
    apps = list(st.session_state["APP_CONFIG"].keys())
    apps_per_row = 6
    # for col_num, app in enumerate(edit_buttons):
    for col_num, app in enumerate(apps):
        if col_num % apps_per_row == 0:
            cols = st.columns(apps_per_row)
        app_label = ""
        if "emoji" in st.session_state["APP_CONFIG"][app]:
            app_label += st.session_state["APP_CONFIG"][app]["emoji"] + "\n\n"
        if "label" in st.session_state["APP_CONFIG"][app]:
            app_label += st.session_state["APP_CONFIG"][app]["label"]
        else:
            app_label += app
        cols[col_num % apps_per_row].button("Edit " + app_label, key=KP+"APP_SELECTED_EDIT"+app,
                                            on_click=next_page, args=(KP + "CMD_APP_EDIT_ONE", app,))


def page_new_app():
    load_emojis()
    init_values()

    st.markdown("### Add APPS")
    st.text_input("APP Name (Like :blue[Now Chat]):", key=KP+"APP_NEW_NAME")
    st.text_input("APP Entry Function Name (Like :blue[now_chat] as `def now_chat()` is its entry point):",
                  key=KP+"APP_NEW_FUNCION_NAME")
    st.text_input("APP Package (Like :blue[src.now_chat]):", key=KP+"APP_NEW_PACKAGE")
    st.selectbox("Emoji:", options=list(st.session_state[KP+"EMOJI_LIST"].keys()), key=KP+"APP_NEW_EMOJI")
    st.button("Add APP", on_click=do_add_new_app)


def verify_admin_pass():
    if st.session_state[KP + "admin_pass"] == "mll_won_nimda":
        st.session_state[KP + "mode"] = "admin"


def page_app_selector():
    def get_visible_apps(apps):
        if KP + "mode" in st.session_state and st.session_state[KP + "mode"] == "admin":
            return apps
        allowed_apps = []
        for app in st.session_state["APP_CONFIG"]:
            if "mode" not in st.session_state["APP_CONFIG"][app] or st.session_state["APP_CONFIG"][app]['mode'] != 'admin':
                allowed_apps.append(app)
        return allowed_apps

    def is_universal_host(host):
        if "universal_visibility" in st.session_state["APP_CONFIG"]["GLOBAL"]:
            host_parts = host.split('.')
            for universal_host  in st.session_state["APP_CONFIG"]["GLOBAL"]["universal_visibility"].split(','):
                if host_parts[0].startswith(universal_host):
                    return True
        return False

    apps = get_visible_apps(list(st.session_state["APP_CONFIG"].keys()))
    ask_admin_pass = False
    if len(apps) < len(list(st.session_state["APP_CONFIG"].keys())):
        ask_admin_pass = True

    apps_per_row = 6
    cols = None
    m = st.markdown("""
    <style>
    div.stButton > button:first-child {
        // background-color: #ce1126;
        color: black;
        height: 8em;
        width: 8em;
        border-radius:8px;
        border:1px solid #000000;
        font-size:20px;
        font-weight: bold;
        margin: auto;
        display: block;
    }

    div.stButton > button:hover {
        box-shadow: 0 12px 16px 0 rgba(0,0,0,0.24), 0 17px 50px 0 rgba(0,0,0,0.19);
    }

    div.stButton > button:active {
        position:relative;
        top:3px;
    }

    </style>""", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>Select an APP</h1>", unsafe_allow_html=True)
    st.markdown("<p></p>", unsafe_allow_html=True)
    st.markdown("<p></p>", unsafe_allow_html=True)
    st.markdown("<p></p>", unsafe_allow_html=True)
    host = common.get_host()
    showed_apps = 0
    for col_num, app in enumerate(apps):
        if app == "GLOBAL":
            continue
        if not is_universal_host(host):
            if "visibility" in st.session_state["APP_CONFIG"][app]:
                allow_show = False
                for allowed_host in st.session_state["APP_CONFIG"][app]["visibility"].split(','):
                    # print("Allowed Host:", allowed_host, "starts with:", host)
                    if host.startswith(allowed_host):
                        allow_show = True
                        # print("Show Host:", allowed_host)
                        break
                if not allow_show:
                    continue

        if showed_apps % apps_per_row == 0:
            cols = st.columns(apps_per_row)
        app_label = ""
        if "emoji" in st.session_state["APP_CONFIG"][app]:
            app_label += st.session_state["APP_CONFIG"][app]["emoji"]+"\n\n"
        if "label" in st.session_state["APP_CONFIG"][app]:
            app_label += st.session_state["APP_CONFIG"][app]["label"]
        else:
            app_label += app
        cols[showed_apps%apps_per_row].button(app_label, key=KP+"APP_SELECTED_"+app, on_click=next_page,
                                          args=(KP+"CMD_APP_SELECTED", app,))
        showed_apps += 1
    if ask_admin_pass:
        st.markdown("<br /><br /><br />", unsafe_allow_html=True)
        st.text_input("Admin Password:", key=KP + "admin_pass", on_change=verify_admin_pass)


def page_app_selector_and_editor():
    page_app_selector()
    st.markdown("<br /><br /><br />", unsafe_allow_html=True)
    st.divider()
    st.markdown("<h1 style='text-align: center;'>APP Operations</h1><br /><br />", unsafe_allow_html=True)
    left, center, right = st.columns(3)
    left.button(":heavy_plus_sign: Add Apps", key=KP + "CMD_APP_NEW", on_click=next_page,
                args=(KP + "CMD_APP_NEW", True,))
    center.button(":spiral_note_pad: Edit Apps", key=KP + "CMD_APP_EDIT", on_click=next_page,
                  args=(KP + "CMD_APP_EDIT", True,))
    right.button(":sun_behind_cloud: Upload Files", key=KP + "CMD_FILE_UPLOAD", on_click=next_page,
                 args=(KP + "CMD_FILE_UPLOAD", True,))


def page_auth():
    if KP + "AUTH_SUCCESSFUL" not in st.session_state:
        st.session_state[KP + "AUTH_SUCCESSFUL"] = False

    for k in st.session_state:
        print("Main::", k, "==>", st.session_state[k])
    if "LDAP_SERVER_URL".lower() not in st.session_state["GLOBAL_CONFIG"]["GLOBAL"]:
        st.markdown("# :red[LDAP_SERVER_URL not set in global.ini]")
        sys.exit(1)
    if not st.session_state[KP + "AUTH_SUCCESSFUL"]:
        from lib import auth
        cola, authc, colz = st.columns([2, 4, 2])
        ret, username = auth.auth_window(authc, st.session_state["GLOBAL_CONFIG"]["GLOBAL"]["ldap_server_url"],
                                       st.session_state[KP + "AUTH_FAILED_REASON"]
                                       if KP + "AUTH_FAILED_REASON" in st.session_state else "")
        if ret:
            st.session_state[KP + "AUTH_SUCCESSFUL"] = True
            if KP + "AUTH_FAILED_REASON" in st.session_state:
                del st.session_state[KP + "AUTH_FAILED_REASON"]
            st.session_state[KP+"username"] = username
            reset_page("After Successful Login")
            st.experimental_rerun()