import os
import json
import shutil
from datetime import datetime
import streamlit as st
from streamlit_ace import st_ace
import time
import filecmp
import pandas as pd
from src import predict
from lib import common
from lib import tag_manager as tm
from lib import token_counter as tc
from lib import metadata_manager as mm

APP_DIR = "now_chat"
APP_METADATA = "metadata.json"
APP_TOKEN_COUNTER = "token_counter.json"
APP_LABEL = "label"
# Key Prefix
KP = "now_chat."

# These are the only valid roles to be used in this code
roles = ["user", "robot", "context", "summary"]


def _vexists(keytag):
    if keytag in st.session_state:
        return True
    return False


def _vnotnone(keytag):
    if keytag in st.session_state and st.session_state[keytag] is not None:
        return True
    return False


def _vcheck(keytag, value):
    if keytag in st.session_state:
        if st.session_state[keytag] == value:
            return True
    return False


def _vtrue(keytag):
    return _vcheck(keytag, True)


def _vdel(keytag):
    if isinstance(keytag, list):
        for kt in keytag:
            if kt in st.session_state:
                del st.session_state[kt]
    else:
        if keytag in st.session_state:
            del st.session_state[keytag]


def dump_session_state(msg):
    print("*" * 50, msg)
    for k in sorted(st.session_state):
        if k != "global.EMOJI_LIST":
            print(k, "==>", st.session_state[k])
    print("-" * 50)


def get_model_text_color(model):
    markup_colors = ["blue", "orange", "green", "red", "violet"]
    if model not in st.session_state[KP + "models"]:
        st.session_state[KP + "models"].append(model)
    return markup_colors[st.session_state[KP + "models"].index(model) % len(markup_colors)]


def read_file(file_name):
    script = ''
    with open(file_name) as fh:
        script += fh.read()
    return script


def get_file_and_content_map_from_folder(folders):
    data_map = {}
    counter = 1
    for folder in folders.split(','):
        if not os.path.isdir(folder):
            continue
        for file in sorted(os.listdir(folder)):
            fpath = os.path.join(folder, file)
            if os.path.isfile(fpath):
                data_map[str(counter) + "-" + file] = str(counter) + "-" + file + "\n" + read_file(fpath)
                counter += 1
    return data_map


def get_default_chat_model():
    if KP+"default_chat_model" in st.session_state:
        if st.session_state[KP+"default_chat_model"] in predict.get_model_names():
            return st.session_state[KP+"default_chat_model"]
    return predict.get_default_chat_model()


def predict_dialog(turns, model=""):
    if not model:
       model = get_default_chat_model()
    if model not in predict.get_models():
        content = "Model ['%s'] is no longer in service" % model
        return content
    prefix_dict = predict.get_model_prompt_tags(model)
    prompt_string = ""

    vturns = turns[:-1] if turns[-1]['role'] == 'robot' else turns
    for turn in vturns:
        prompt_string = prompt_string + prefix_dict[turn["role"]] + turn["content"] + prefix_dict["end"]
    prompt_string += prefix_dict["robot"]
    if KP+"print_model_input_output" in st.session_state and st.session_state[KP+"print_model_input_output"]:
        print("Robot Request:", model, ":", prompt_string)
        st.info("Robot Request:" + model + ":" + prompt_string)
    prediction = predict.predict(
        model=model,
        prompt=prompt_string,
        max_new_tokens=500,
        temperature=0.3,
        num_beams=1,
        no_repeat_ngram_size=30,
        do_sample=True,
        chat=True
    )
    if KP+"print_model_input_output" in st.session_state and st.session_state[KP+"print_model_input_output"]:
        print("Robot Response:", model, ":", prediction)
        st.info("Robot Response:" + model + ":" + prediction)
    prediction = prediction.replace(prefix_dict["robot"].strip(), "").replace(prefix_dict["end"].strip(), "").strip()
    return prediction


def prepare_and_predict(idx, model=""):
    try:
        dialogs = []
        for i in range(idx + 1):
            content = st.session_state[KP + 'wset'][i]['content']
            role = st.session_state[KP + 'wset'][i]['role']
            if role == "robot":
                if model:
                    if 'model' not in st.session_state[KP + 'wset'][i] or \
                            st.session_state[KP + 'wset'][i]['model'] != model:
                        continue
                else:
                    if 'model' in st.session_state[KP + 'wset'][i] and \
                            st.session_state[KP + 'wset'][i]['model'] != get_default_chat_model():
                        continue
            dialogs.append({'role': role, 'content': content})
        return predict_dialog(dialogs, model=model)
    except Exception as e:
        print("Exception:prepare_and_predict:", str(e))
        return None


def gen_message(idx, model=""):
    content = prepare_and_predict(idx, model)
    # print("Turns:", turns)
    # print("WSet:[%s]" % idx, st.session_state[KP+'wset'][idx])
    if content:
        if st.session_state[KP + 'wset'][idx]['role'] == 'robot':
            if 'model' not in st.session_state[KP + 'wset'][idx]:
                st.session_state[KP + 'wset'][idx]['model'] = get_default_chat_model()
            if st.session_state[KP + 'wset'][idx]['model'] == model:
                st.session_state[KP + 'wset'][idx]['content'] = content
            else:
                add_chat("robot", content, model=model)
        else:
            add_chat("robot", content, model=model)
        st.session_state[KP + 'wset_changed'] = True
    # print("WSet:", st.session_state[KP+'wset'])


def add_robot_response():
    def reload_chat():
        # print("Save Chat:", len(st.session_state[KP+'wset']))
        if len(st.session_state[KP + 'wset']) < 1:
            return
        # Update Data
        fpath = get_chatstorefilepath()
        st.session_state[KP + 'wset'] = json.loads(open(fpath, "r").read())

    # print("Robot Start", st.session_state[KP+"models"])
    reload_chat()
    for model in st.session_state[KP + "models"]:
        gen_message(len(st.session_state[KP + 'wset']) - 1, model=model)
    # print("Robot Done", st.session_state[KP+'wset'])
    st.session_state[KP + 'wset_changed'] = True


def update_chat(idx, key):
    if st.session_state[key]:
        st.session_state[KP + 'wset'][idx]['content'] = st.session_state[key]
        st.session_state[KP + 'wset_changed'] = True
        save_chat_data()


def update_role(idx, role):
    st.session_state[KP + 'wset'][idx]['role'] = role


def vote(idx, v):
    # print(idx, st.session_state[KP+'wset'])
    if KP + 'vote' not in st.session_state[KP + 'wset'][idx]:
        st.session_state[KP + 'wset'][idx]['vote'] = {'up': 0, 'dn': 0}
    if v > 0:
        st.session_state[KP + 'wset'][idx]['vote']['up'] += v
        st.session_state[KP + 'wset'][idx]['vote']['up'] = st.session_state[KP + 'wset'][idx]['vote']['up'] % 2
        if st.session_state[KP + 'wset'][idx]['vote']['up'] != 0:
            st.session_state[KP + 'wset'][idx]['vote']['dn'] = 0
    else:
        st.session_state[KP + 'wset'][idx]['vote']['dn'] -= v
        st.session_state[KP + 'wset'][idx]['vote']['dn'] = st.session_state[KP + 'wset'][idx]['vote']['dn'] % 2
        if st.session_state[KP + 'wset'][idx]['vote']['dn'] != 0:
            st.session_state[KP + 'wset'][idx]['vote']['up'] = 0


def display_vote(idx):
    col1, colv1, colv2 = st.columns([12, 1, 1])
    up = st.session_state[KP + 'wset'][idx]['vote']['up'] if 'vote' in st.session_state[KP + 'wset'][idx] else 0
    dn = st.session_state[KP + 'wset'][idx]['vote']['dn'] if 'vote' in st.session_state[KP + 'wset'][idx] else 0
    colv1.button(':+1:' if up == 0 else '+' + str(up), key=KP + "up_vote_" + str(idx), on_click=vote, args=(idx, 1,))
    colv2.button(':-1:' if dn == 0 else '-' + str(dn), key=KP + "down_vote_" + str(idx), on_click=vote, args=(idx, -1,))
    st.session_state[KP + 'wset_changed'] = True


def delete_item(idx):
    del st.session_state[KP + 'wset'][idx]
    st.session_state[KP + 'wset_changed'] = True


def add_item(idx, role):
    st.session_state[KP + 'wset'].insert(idx + 1, {'role': role, 'content': ""})
    st.session_state[KP + 'wset_changed'] = True


def move_up(idx):
    rblock = len(st.session_state[KP + "models"])
    st.session_state[KP + 'wset'].insert(idx - rblock, st.session_state[KP + 'wset'].pop(idx))


def move_down(idx):
    rblock = len(st.session_state[KP + "models"])
    st.session_state[KP + 'wset'].insert(idx + rblock, st.session_state[KP + 'wset'].pop(idx))


def get_display_mode(edit_display):
    if KP+"chat_display_mode" in st.session_state:
        if st.session_state[KP+"chat_display_mode"] == "read_only":
            return False
        if st.session_state[KP+"chat_display_mode"] == "opt_in_edit":
            if KP+"chat_display_mode_edit" in st.session_state and st.session_state[KP+"chat_display_mode_edit"]:
                return True
            return False
    return edit_display


def display_chat_turn_box(keytag, label, idx, message):
    if _vcheck(KP + "chat_display_mode", "rich"):
        pre_keytag = keytag.replace(KP, KP+"pre_")
        st.markdown(label)
        st_ace(value=message, key=keytag)
        if pre_keytag not in st.session_state or st.session_state[pre_keytag] != st.session_state[keytag]:
            update_chat(idx, keytag)
            # st.rerun()
    else:
        st.text_area(label=label, value=message, on_change=update_chat, args=(idx, keytag),
                     key=keytag, height=max(300, min(600, int(len(message) / 3))))


def display_chat_user_context(idx, message, role, edit_display):
    edit_display = get_display_mode(edit_display)
    if role == "context":
        if edit_display:
            display_chat_turn_box(KP + "Sys" + str(idx) + role, "System", idx, message)
        else:
            st.warning(message.replace('\n', '\n\n') if '|' not in message else message, icon="📌")
    else:
        if edit_display:
            display_chat_turn_box(KP + "Sys" + str(idx) + role, "Customer", idx, message)
            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
            c1.button(":x:", on_click=delete_item, args=(idx,), key=KP + str(idx) + 'c1')
            c2.button(":heavy_plus_sign:", on_click=add_item, args=(idx, role,), key=KP + str(idx) + 'c2')
            first_user_msg = 0
            if st.session_state[KP + 'wset'][0]['role'] == "context":
                first_user_msg += 1
            if idx > first_user_msg:
                c4.button(":arrow_up:", on_click=move_up, args=(idx,), key=KP + str(idx) + 'c4')
            if idx < len(st.session_state[KP + 'wset']) - 1:
                c5.button(":arrow_down:", on_click=move_down, args=(idx,), key=KP + str(idx) + 'c5')
            if len(st.session_state[KP + "models"]) < 2:
                c6.button(":male-technologist:", on_click=update_role, args=(idx, "robot",), key=KP + str(idx) + 'c6')
        else:
            st.success(message.replace('\n', '\n\n') if '|' not in message else message, icon="👨")


def display_chat_robots(idx_start, robots, edit_display):
    edit_display = get_display_mode(edit_display)
    robot_count = len(robots)
    robot_seg = st.columns(robot_count)
    # print("display_chat_robots: Num=", robot_count)
    if edit_display:
        for ridx, robot in enumerate(robots):
            model = get_default_chat_model()
            original_model = model
            if 'model' in robot:
                original_model = robot['model']
                if robot['model'] in predict.get_models():
                    model = robot['model']
            label = ":%s[Agent (%s)]" % (get_model_text_color(model), original_model)
            message = robot['content']
            role = robot['role']
            idx = idx_start + ridx
            with robot_seg[ridx]:
                display_chat_turn_box(KP + "Agent" + str(idx) + role, label, idx, message)
            c1, c2, c3, c4, c5, c6, c7 = robot_seg[ridx].columns(7)
            if len(robots) == 1:
                c1.button(":x:", on_click=delete_item, args=(idx,), key=KP + str(idx) + 'c1')
                c2.button(":heavy_plus_sign:", on_click=add_item, args=(idx, role,), key=KP + str(idx) + 'c2')
                if idx > 0:
                    c4.button(":arrow_up:", on_click=move_up, args=(idx,), key=KP + str(idx) + 'c4')
                if idx < len(st.session_state[KP + 'wset']) - 1:
                    c5.button(":arrow_down:", on_click=move_down, args=(idx,), key=KP + str(idx) + 'c5')
                c6.button(":man:", on_click=update_role, args=(idx, "user",), key=KP + str(idx) + 'c6')
                if idx > 0 and original_model in predict.get_models():
                    c7.button(":robot_face:", on_click=gen_message, args=(idx, model,), key=KP + str(idx) + 'c7')
            else:
                if idx > 0 and original_model in predict.get_models():
                    c7.button(":robot_face:", on_click=gen_message, args=(idx, model,), key=KP + str(idx) + 'c7')
    else:
        for ridx, robot in enumerate(robots):
            robot_seg[ridx].info(robot['content'].replace('\n', '\n\n') if '|' not in robot['content'] else robot['content'], icon="👨‍💻")


def display_chat_summary(message):
    st.divider()
    st.markdown(":pencil: SUMMARY: :blue[{}]".format(message))


def add_chat(role, content="", auto_response=False, model=''):
    print("*** Add Chat[%s] Autoresponse[%s]" % (role, auto_response))
    print(content)
    print('***')
    if content:
        # print("Adding Chat")
        if role == 'context':
            st.session_state[KP + 'wset'].insert(0, {'role': role, 'content': content})
            st.session_state[KP + 'add_context'] = False
        else:
            if model:
                st.session_state[KP + 'wset'].append({'role': role, 'content': content, 'model': model})
            else:
                if len(st.session_state[KP + 'wset']) > 0 and st.session_state[KP + 'wset'][-1]['role'] == "prompt":
                    st.session_state[KP + 'wset'][-1]['role'] = role
                    st.session_state[KP + 'wset'][-1]['content'] = content
                else:
                    st.session_state[KP + 'wset'].append({'role': role, 'content': content})
        # print("Wset", st.session_state[KP+'wset'])
        st.session_state[KP + 'wset_changed'] = True
        st.session_state[KP + 'auto_response'] = auto_response
        save_chat_data()


def regenerate():
    last_row = len(st.session_state[KP + 'wset']) - 1
    if st.session_state[KP + 'wset'][last_row]['role'] == 'robot':
        gen_message(last_row)
    save_chat()


def get_chatstorefilepath():
    if st.session_state[KP + "chat_store"] == '':
        st.session_state[KP + 'chat_store'] = os.path.join(st.session_state[KP + "appuser_data_home"],
                                                           datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p") +
                                                           "_" + st.session_state[KP + "name"] + ".json")
        if KP+"suggested_chat_label" in st.session_state and st.session_state[KP+"suggested_chat_label"]:
            st.session_state[KP + "chat_label"] = st.session_state[KP + "suggested_chat_label"]
            st.session_state[KP + "appuser_data_metadata"].set(st.session_state[KP + 'chat_store'],
                                                               label=st.session_state[KP + "chat_label"])
        else:
            st.session_state[KP + "chat_label"] = st.session_state[KP + "appuser_data_metadata"].set(
                st.session_state[KP + 'chat_store'],
                content=st.session_state[KP + 'wset'][0]['content'])
    return st.session_state[KP + "chat_store"]


def add_tags(tag_key):
    for nt in st.session_state[tag_key]:
        # st.session_state[KP+"TagManager"].tag(st.session_state[KP+"new_label"], get_chatstorefilepath())
        st.session_state[KP + "TagManager"].tag(nt, get_chatstorefilepath())
    st.session_state[KP + "TagManager"].save()
    del st.session_state[tag_key]


def add_custom_tags():
    st.session_state[KP + "new_label"] = st.session_state[KP + "new_label"].split(" ")
    add_tags(KP + "new_label")


def add_selected_tags(selected_label=""):
    if selected_label:
        st.session_state[KP + "selected_label"] = [selected_label.replace('\:', ':')]
    else:
        st.session_state[KP + "selected_label"] = [st.session_state[KP + "selected_label"]]
    add_tags(KP + "selected_label")


def untag(tag):
    st.session_state[KP + "TagManager"].untag(tag, get_chatstorefilepath())
    st.session_state[KP + "TagManager"].save()


def mark_completed():
    chat_filepath = get_chatstorefilepath()
    if os.path.isfile(chat_filepath):
        is_mturn = 0
        for w in st.session_state[KP+"wset"]:
            if w["role"] == "user":
                is_mturn += 1
        st.session_state[KP + "TagManager"].tag("CMP-M" if is_mturn > 1 else "CMP-S", get_chatstorefilepath())
        st.session_state[KP + "TagManager"].save()
        shutil.copy(chat_filepath,
                    os.path.join(st.session_state[KP + "completed_dir"], os.path.basename(chat_filepath)))


def is_completed():
    if st.session_state[KP + "chat_store"] == "":
        return False
    completed_file = os.path.join(st.session_state[KP + "completed_dir"], os.path.basename(get_chatstorefilepath()))

    if not os.path.isfile(completed_file):
        return False
    tags = st.session_state[KP + "TagManager"].get_tags_for_object(get_chatstorefilepath())
    if "CMP-M" in tags or "CMP-S" in tags:
        return True
    return True if os.path.isfile(completed_file) else False


def unmark_completed():
    completed_file = os.path.join(st.session_state[KP + "completed_dir"], os.path.basename(get_chatstorefilepath()))
    if os.path.isfile(completed_file):
        tags = st.session_state[KP + "TagManager"].get_tags_for_object(get_chatstorefilepath())
        if "CMP-M" in tags:
            st.session_state[KP + "TagManager"].untag("CMP-M", get_chatstorefilepath())
        if "CMP-S" in tags:
            st.session_state[KP + "TagManager"].untag("CMP-S", get_chatstorefilepath())
        os.remove(completed_file)


def save_note():
    notes = {"Notes": st.session_state[KP + "new_note"].strip()}
    with open(os.path.join(st.session_state[KP + "notes_dir"], os.path.basename(get_chatstorefilepath())), "w") as fh:
        json.dump(notes, fh)


def display_notes():
    if st.session_state[KP + "chat_store"] == '':
        return
    fpath = os.path.join(st.session_state[KP + "notes_dir"], os.path.basename(get_chatstorefilepath()))
    notes = ""
    if os.path.isfile(fpath):
        with open(fpath) as fh:
            notes = json.load(fh)["Notes"]
    st.text_area("Notes", key=KP + "new_note", value=notes, on_change=save_note)


def show_chat():
    unselected_stored_chat_message = "Select Stored Chat"

    def selected_reference_chat():
        print("selected_reference_chat called")
        if KP + "selected_reference_chat" not in st.session_state:
            return
        if not st.session_state[KP + "selected_reference_chat"]:
            return
        print("selected_reference_chat:", st.session_state[KP + "selected_reference_chat"])
        if st.session_state[KP + "selected_reference_chat"] != unselected_stored_chat_message:
            filepath = os.path.join(st.session_state[KP + "reference_chat"],
                                    st.session_state[KP + "selected_reference_chat"])
            st.session_state[KP + 'wset'] = json.loads(open(filepath, "r").read())
            print("Selected_reference_chat Chat:",st.session_state[KP + 'wset'])

    def show_reference_box():
        if KP + "reference_chat" in st.session_state and os.path.isdir(st.session_state[KP + "reference_chat"]):
            files = os.listdir(st.session_state[KP + "reference_chat"])
            st.selectbox("Reference Chats",
                        options=[unselected_stored_chat_message] + files,
                        key=KP + "selected_reference_chat",
                        on_change=selected_reference_chat)

    def add_context():
        st.session_state[KP + 'add_context'] = True

    def selected_context():
        # print("Selected Context", st.session_state[KP+'selected_context'])
        if st.session_state[KP + 'selected_context'] is not None:
            add_chat("context", st.session_state[KP + "contexts"][st.session_state[KP + 'selected_context']])

    def add_context_in_chat(rerun):
        add_chat("context", st.session_state[KP + 'context_msg'])
        st.session_state[KP + 'add_context'] = False
        if rerun:
            st.rerun()

    def display_chat_add_context_box():
        if _vexists(KP + "add_context_submit_button"):
            if _vexists(KP + "allow_context_label_entry"):
                st.text_input("Chat Label", key=KP + "suggested_chat_label")
            if _vcheck(KP + "chat_display_mode", "rich"):
                st.markdown("Context")
                st_ace(value="", placeholder="", key=KP + "context_msg")
            else:
                st.text_area("Context", key=KP + "context_msg")
            st.button("Submit", on_click=add_context_in_chat, key=KP + "context_add_key")
        else:
            if _vexists(KP + "allow_context_label_entry"):
                st.text_input("Chat Label", key=KP + "suggested_chat_label")
            if _vcheck(KP + "chat_display_mode", "rich"):
                st.markdown("Context")
                st_ace(placeholder="", key=KP + "context_msg")
                if _vnotnone(KP + "context_msg"):
                    print("Context Msg:", st.session_state[KP + "context_msg"])
                    add_context_in_chat(1)
            else:
                st.text_area("Context", key=KP + "context_msg", on_change=add_context_in_chat, args=(0,))

    def show_context_box():
        if KP + 'add_context' not in st.session_state:
            if KP + "contexts" in st.session_state:
                if _vexists(KP+"no_manual_add_context_button"):
                    st.selectbox(st.session_state[KP + "select_context_label"],
                                    options=[None] + list(st.session_state[KP + "contexts"].keys()),
                                    key=KP + "selected_context",
                                    on_change=selected_context)
                else:
                    left, right = st.columns(2)
                    left.button("Add Context", on_click=add_context)
                    right.selectbox(st.session_state[KP + "select_context_label"],
                                    options=[None] + list(st.session_state[KP + "contexts"].keys()),
                                    key=KP + "selected_context",
                                    on_change=selected_context)
            else:
                if not _vexists(KP + "no_manual_add_context_button"):
                    st.button("Add Context", on_click=add_context)
            st.divider()
        elif st.session_state[KP + 'add_context']:
            display_chat_add_context_box()
            st.divider()

    def show_completed():
        if not filecmp.cmp(get_chatstorefilepath(),
                           os.path.join(st.session_state[KP + "completed_dir"],
                                        os.path.basename(get_chatstorefilepath())), True):
            st.header(":white_check_mark: :green[Completed] :heavy_plus_sign:")
        else:
            st.header(":white_check_mark: :green[Completed]")

    def change_mode_edit():
        st.session_state[KP + "chat_display_mode_edit"] = True

    def change_mode_readonly():
        _vdel(KP + "chat_display_mode_edit")
        # if KP + "chat_display_mode_edit" in st.session_state:
        #     del st.session_state[KP + "chat_display_mode_edit"]

    def prompt_provided(keytag):
        add_chat("prompt", st.session_state[keytag], False, '')

    def prompt_submit(role, keytag, auto_response=False):
        if keytag not in st.session_state:
            return
        content = st.session_state[keytag]
        if content:
            add_chat(role, content, auto_response)
        _vdel(keytag)

    if KP+"reference_chat" in st.session_state and len(st.session_state[KP + 'wset']) < 1:
        show_reference_box()
    if KP+"context_none" not in st.session_state:
        show_context_box()
    if is_completed():
        show_completed()

    if _vcheck(KP + "chat_display_mode", "opt_in_edit"):
        if KP + "chat_display_mode_edit" not in st.session_state:
            st.button("Edit Mode", key=KP + "chat_display_mode_edit_x", on_click=change_mode_edit)
        else:
            st.button("Readonly Mode", key=KP + "chat_display_mode_readonly_x", on_click=change_mode_readonly)
    i = 0
    while i < len(st.session_state[KP + 'wset']):
        if st.session_state[KP + 'wset'][i]['role'] not in ['summary', 'prompt']:
            if st.session_state[KP + 'wset'][i]['role'] != 'robot':
                display_chat_user_context(i, st.session_state[KP + 'wset'][i]['content'],
                                          st.session_state[KP + 'wset'][i]['role'], not is_completed())
                i += 1
            else:
                robots = []
                idx = i
                while i < len(st.session_state[KP + 'wset']) and st.session_state[KP + 'wset'][i]['role'] == 'robot' \
                        and len(robots) < len(st.session_state[KP + "models"]):
                    robots.append(st.session_state[KP + 'wset'][i])
                    i += 1
                display_chat_robots(idx, robots, not is_completed())
        else:
            i += 1

    st.divider()
    col1, col2, colgm, colg, colv1, colv2 = st.columns([3, 3, 1, 3, 3, 1])
    # col1.button("Clear Chat", on_click=chat_new)
    # col2.button("Regenerate", on_click=regenerate)
    if len(st.session_state[KP + 'wset']) > 0:
        object_tags = st.session_state[KP + "TagManager"].get_tags_for_object(get_chatstorefilepath())
        all_tags = st.session_state[KP + "TagManager"].get_tags()
        remaining_tags = set(all_tags) - set(object_tags)
        if KP + "tag_hide" in st.session_state:
            hide_tags = st.session_state[KP + "tag_hide"].split(',')
            hide_tags.append("CMP-S")
            hide_tags.append("CMP-M")
            remaining_tags = remaining_tags - set(hide_tags)
            # print("**** Hide Tags", hide_tags)
            # print("**** Remaining Tags", remaining_tags)
        # print("Button Tags", st.session_state[KP+"tag_buttons"].split(','))
        remaining_tags = sorted(list(remaining_tags), key=str.casefold)
        colgm.markdown("#### Tags:")
        if not is_completed():
            colg.text_input("Tags:", on_change=add_custom_tags, key=KP + "new_label", label_visibility="collapsed")
            if len(remaining_tags) > 0:
                colv1.selectbox("Select Tag", options=["Select Tags"] + remaining_tags,
                                key=KP + "selected_label", on_change=add_selected_tags, label_visibility="collapsed")
                if KP + "tag_buttons" in st.session_state:
                    for tag in st.session_state[KP + "tag_buttons"].split(','):
                        if tag.replace('\:', ':') not in object_tags:
                            colv1.button("%s" % tag, key=KP + "selected_label_%s" % tag, on_click=add_selected_tags,
                                         args=(tag,))
            for tag in object_tags:
                colg.button('%s :x:' % tag.replace(":", "\:"), key=KP + "untag_" + tag, on_click=untag, args=(tag,))
        else:
            for tag in object_tags:
                colg.markdown('%s' % tag.replace(":", "\:"))
    if is_completed():
        col1, col3, coll = st.columns([1, 3, 1])
        coll.button("Revert Completed", on_click=unmark_completed)
    else:
        main_msg_key = "main_msg" + str(len(st.session_state[KP + 'wset']))
        main_msg = ""
        if len(st.session_state[KP + 'wset']) > 0 and st.session_state[KP + 'wset'][-1]["role"] == "prompt":
            main_msg = st.session_state[KP + 'wset'][-1]["content"]
        if _vcheck(KP + "chat_display_mode", "rich"):
            st.markdown("Prompt here")
            st_ace(value="", placeholder=main_msg, key=KP + main_msg_key)
        else:
            st.text_area("Prompt here", key=KP + main_msg_key, value=main_msg, on_change=prompt_provided,
                         args=(KP + main_msg_key,))
        col1, col3, coll = st.columns([1, 3, 1])
        col1.button("Submit", on_click=prompt_submit, args=("user", KP + main_msg_key, True,),
                    key=KP + "content_add_key")
        coll.button("Mark Completed", on_click=mark_completed)
    lrow = len(st.session_state[KP + 'wset']) - 1
    if len(st.session_state[KP + 'wset']) > 1 and st.session_state[KP + 'wset'][lrow]['role'] == 'summary':
        display_chat_summary(st.session_state[KP + 'wset'][lrow]['content'])
    display_notes()


def save_chat_data():
    # print("Save Chat:", len(st.session_state[KP+'wset']))
    if len(st.session_state[KP + 'wset']) < 1:
        return
    # Update Data
    fpath = get_chatstorefilepath()
    json.dump(st.session_state[KP + 'wset'], open(fpath, 'w'))
    print("Chat Store File", fpath, "Label:", st.session_state[KP + "chat_label"])


def save_chat():
    if len(st.session_state[KP + 'wset']) < 1:
        return
    save_chat_data()
    fpath = get_chatstorefilepath()
    # Update Metadata
    print("Chat Label:", st.session_state[KP + "chat_label"])
    st.session_state[KP + "chat_label"] = st.session_state[KP + "appuser_data_metadata"].set(fpath,
                                                                                             label=st.session_state[
                                                                                                 KP + "chat_label"])
    st.session_state[KP + "appuser_data_metadata"].save()
    print("Saved: File", fpath, "Label:", st.session_state[KP + "chat_label"])


def update_current_chat_token_count():
    if KP+"token_count_none" in st.session_state and st.session_state[KP+"token_count_none"]:
        return
    if len(st.session_state[KP + 'wset']) < 1:
        st.session_state[KP + "current_chat_token_count"] = 0
        return
    fpath = get_chatstorefilepath()
    dialogs = []
    for wset in st.session_state[KP + 'wset']:
        role = wset['role']
        content = wset['content']
        dialogs.append({'role': role, 'content': content})
    st.session_state[KP + "current_chat_token_count"] = st.session_state[KP + "TokenCounter"].get_chat_token_count(
        dialogs)
    st.session_state[KP + "TokenCounter"].set_token_count(fpath, st.session_state[KP + "current_chat_token_count"])


def load_context_folders():
    print("Loading Context Folders:", st.session_state[KP + "context_folders"])
    if KP + "loaded_context_folders" in st.session_state and st.session_state[KP + "loaded_context_folders"] == \
            st.session_state[KP + "context_folders"]:
        print("Not Loading Context Folders:", st.session_state[KP + "loaded_context_folders"], st.session_state[KP + "context_folders"])
        return
    st.session_state[KP + "contexts"] = get_file_and_content_map_from_folder(st.session_state[KP + "context_folders"])
    st.session_state[KP + "loaded_context_folders"] = st.session_state[KP + "context_folders"]
    print("Loaded Context Folders:", st.session_state[KP + "context_folders"])


def init(force=False, info=""):
    if KP + 'wset' in st.session_state and not force:
        return
    get_approved_labellers()
    print("\nInitializing Stack: Info=", info, "User=", st.session_state[KP + 'name'])
    st.session_state[KP + 'wset'] = []
    st.session_state[KP + "chats"] = []
    st.session_state[KP + "chat_label"] = ""
    st.session_state[KP + "chat_store"] = ""
    st.session_state[KP + "wset_changed"] = False
    if 'global.data_home' not in st.session_state:
        st.session_state['global.data_home'] = '.'
    st.session_state[KP + "app_data_home"] = os.path.join(st.session_state['global.data_home'], APP_DIR)
    st.session_state[KP + "appuser_data_home"] = os.path.join(st.session_state[KP + 'app_data_home'],
                                                              st.session_state[KP + 'name'])
    if st.session_state[KP + "loaded_project"] != "legacy":
        st.session_state[KP + "appuser_data_home"] = os.path.join(st.session_state[KP + "appuser_data_home"],
                                                              st.session_state[KP + "loaded_project"])
    st.session_state[KP + "appuser_data_metadata_file"] = os.path.join(st.session_state[KP + 'appuser_data_home'],
                                                                       APP_METADATA)
    st.session_state[KP + "completed_dir"] = os.path.join(st.session_state[KP + 'app_data_home'], "DONE",
                                                          st.session_state[KP + "loaded_project"])
    st.session_state[KP + "notes_dir"] = os.path.join(st.session_state[KP + 'app_data_home'], "notes")

    for project in get_visible_projects():
        if project == "legacy":
            continue
        pdir = os.path.join(st.session_state[KP + 'app_data_home'], st.session_state[KP + 'name'], project)
        if not os.path.exists(pdir):
            os.makedirs(pdir, exist_ok=True)
    for d in ["appuser_data_home", "completed_dir", "notes_dir"]:
        if not os.path.exists(st.session_state[KP + d]):
            os.makedirs(st.session_state[KP + d], exist_ok=True)

    st.session_state[KP + "appuser_data_metadata"] = mm.MetadataManager(
        st.session_state[KP + "appuser_data_metadata_file"])
    _vdel(KP + 'llm_return_words_printed')
    _vdel(KP + 'llm_return_words')
    st.session_state[KP + "models"] = [get_default_chat_model()]
    if KP + "context_folders" in st.session_state:
        load_context_folders()
    st.session_state[KP + "TagManager"] = \
        tm.TagManager.get_instance(os.path.join(st.session_state[KP + 'app_data_home'], APP_LABEL))
    if KP + "select_context_label" not in st.session_state:
        st.session_state[KP + "select_context_label"] = "Select Context"
    print("ENVs", st.session_state["global.env"])
    if "global.env" in st.session_state and st.session_state["global.env"] not in ["AIDE", "DART"]:
        if KP+"token_count_none" not in st.session_state or not st.session_state[KP+"token_count_none"]:
            st.session_state[KP + "TokenCounter"] = tc.TokenCounter.get_instance(os.path.join(st.session_state[KP + 'app_data_home'], APP_TOKEN_COUNTER),
                                         st.session_state[KP + "model_checkpoint"],
                                         predict.get_model_prompt_tags(get_default_chat_model()))


def get_approved_labellers():
    if KP + "approved_labellers" in st.session_state and st.session_state[KP + "approved_labellers"]:
        approved_labellers = [n.strip() for n in st.session_state[KP + "approved_labellers"].split(',')]
    else:
        approved_labellers = []
    data_home = os.path.join(st.session_state['global.data_home'], APP_DIR)
    for user in os.listdir(data_home):
        if os.path.isdir(os.path.join(data_home, user)):
            if not user.startswith('.') and user not in ['DONE']:
                if user not in approved_labellers:
                    approved_labellers.append(user)
    if "global.username" in st.session_state:
        if st.session_state["global.username"] not in approved_labellers:
            approved_labellers.insert(0, st.session_state["global.username"])
        else:
            idx = approved_labellers.index(st.session_state["global.username"])
            if idx > 0:
                approved_labellers.pop(idx)
                approved_labellers.insert(0, st.session_state["global.username"])
        if KP + "name" not in st.session_state:
            st.session_state[KP + "name"] = st.session_state["global.username"]
    return approved_labellers


def sidebar_user_box():
    def show_labeller_box():
        approved_labellers = get_approved_labellers()
        userindex = 0
        if KP + 'name' in st.session_state:
            st.session_state[KP + 'name_last'] = st.session_state[KP + 'name']
            userindex = 0
            if st.session_state[KP + 'name'] in approved_labellers:
                userindex = approved_labellers.index(st.session_state[KP + 'name'])
        elif KP + 'name_last' in st.session_state:
            userindex = approved_labellers.index(st.session_state[KP + 'name_last'])

        st.sidebar.selectbox("Labeler", approved_labellers, key=KP + 'name', index=userindex,
                             on_change=init, args=(True,"sidebar_user_box",))

    def config_change_actions():
        if KP + "context_folders" in st.session_state:
            load_context_folders()

    def set_new_project():
        print("Project Changed", KP + "default_project", "to", st.session_state[KP+"select_project"])
        st.session_state[KP + "userselect_project"] = st.session_state[KP+"select_project"]

    def show_projectlist_box():
        project_list = get_visible_projects()
        if st.session_state[KP+"default_project"] in project_list:
            index = project_list.index(st.session_state[KP+"default_project"])
        else:
            index = 0
        st.sidebar.selectbox("Select Project", project_list, key=KP+"select_project",
                             index=index,
                             on_change=set_new_project)

    def set_page(page_tag):
        st.session_state[KP+"page"] = page_tag

    # Set multiselect options can be seen fully
    st.markdown(
        f"""
                    <style>
                        .stMultiSelect [data-baseweb=select] span {{
                            max-width: 1000px;
                            font-size: 1.2rem;
                        }}
                    </style>""",
        unsafe_allow_html=True,
    )
    left, mid, right = st.sidebar.columns(3)
    left.button(":house:", key=KP + "show_home", help="Home", on_click=_vdel,
                args=([KP+"page", KP + "show_documentation", KP + "show_dashboard"],))
    mid.button(":book:", key=KP + "show_documentation", help="Documentation", on_click=set_page,
               args=(KP + "show_documentation",))
    right.button(":bar_chart:", key=KP + "show_dashboard", help="Dashboard", on_click=set_page,
               args=(KP + "show_dashboard",))
    if "global.username" in st.session_state:
        st.sidebar.markdown('# Hi ' + st.session_state["global.username"].split('.')[0].capitalize())

    show_projectlist_box()
    st.sidebar.markdown("## Chat Details")
    show_labeller_box()
    # KP+'name' is needed in init
    init(info="sidebar_user_box at end")


def sidebar():
    def add_other_models():
        st.session_state[KP + "models"] = st.session_state[KP + "OtherModels"]
        # Update chat with this new model requirement

        selected_models = set(st.session_state[KP + "models"])
        print("Chat", st.session_state[KP + 'wset'])
        cur_chat_models = set()
        for chat_turn in st.session_state[KP + 'wset']:
            if chat_turn['role'] == 'robot':
                if 'model' in chat_turn:
                    cur_chat_models.add(chat_turn['model'])
                else:
                    cur_chat_models.add(get_default_chat_model())

        add_models = list(selected_models - cur_chat_models)
        remove_models = list(cur_chat_models - selected_models)
        print("Adding Model:", add_models)
        print("Remove Model:", remove_models)
        new_chat_turns = []
        models_used = set()
        previous_turn_robot = False
        if len(st.session_state[KP + 'wset']) < 1:
            for model in add_models:
                models_used.add(model)
        for chat_turn in st.session_state[KP + 'wset']:
            if chat_turn['role'] == 'robot':
                model = chat_turn['model'] if 'model' in chat_turn else get_default_chat_model()
                if model not in remove_models:
                    new_chat_turns.append(chat_turn)
                    models_used.add(model)
                previous_turn_robot = True
            else:
                if previous_turn_robot:
                    for model in add_models:
                        new_chat_turns.append({'role': 'robot', 'content': '', 'model': model})
                        models_used.add(model)
                new_chat_turns.append(chat_turn)
                previous_turn_robot = False
        if previous_turn_robot:
            for model in add_models:
                new_chat_turns.append({'role': 'robot', 'content': '', 'model': model})
                models_used.add(model)
        st.session_state[KP + 'wset'] = new_chat_turns
        st.session_state[KP + "models"] = list(models_used)
        if len(st.session_state[KP + "models"]) < 1:
            st.session_state[KP + "models"] = [get_default_chat_model()]
        print("New Chat Turns:", st.session_state[KP + 'wset'])
        print("Models used:", st.session_state[KP + "models"])
        save_chat()

    def save_labelchange():
        if KP + 'chat_new_label' not in st.session_state or st.session_state[KP + "chat_new_label"] == '':
            return
        st.session_state[KP + "appuser_data_metadata"].change_label(st.session_state[KP + "chat_label"],
                                                                    st.session_state[KP + "chat_new_label"])
        st.session_state[KP + "chat_label"] = st.session_state[KP + "chat_new_label"]
        st.session_state[KP + "appuser_data_metadata"].save()

    def chat_new():
        st.session_state[KP + 'wset'] = []
        st.session_state[KP + 'wset_changed'] = True
        st.session_state[KP + "chat_label"] = ""
        st.session_state[KP + "chat_store"] = ""
        _vdel(KP + 'add_context')
        st.session_state[KP + "models"] = [get_default_chat_model()]

    def save_chat_copy():
        print("save_chat_copy: Start")
        if len(st.session_state[KP + 'wset']) < 1:
            print("Insufficient WSet")
            return
        copied_filepath = st.session_state[KP + "appuser_data_metadata"].copy(st.session_state[KP + "chat_label"])
        if not copied_filepath:
            return

        # Tags
        object_tags = st.session_state[KP + "TagManager"].get_tags_for_object(get_chatstorefilepath())
        for otag in object_tags:
            st.session_state[KP + "TagManager"].tag(otag, copied_filepath)
        st.session_state[KP + "TagManager"].save()

    def load_chat():
        filename = st.session_state[KP + "appuser_data_metadata"].get(st.session_state[KP + "load_chat"])
        print("Load Chat::Filename:", filename, "Label:", st.session_state[KP + "load_chat"])
        st.session_state[KP + "chat_label"] = st.session_state[KP + "load_chat"]
        st.session_state[KP + "chat_store"] = filename
        st.session_state[KP + 'wset'] = json.loads(open(filename, "r").read())
        st.session_state[KP + 'wset_changed'] = True
        _vdel(KP + 'add_context')
        if st.session_state[KP + 'wset'][0]["role"] == "context":
            st.session_state[KP + 'add_context'] = False
        st.session_state[KP + "models"] = []
        for d in st.session_state[KP + 'wset']:
            if d['role'] != "robot":
                continue
            if 'model' in d:
                if d['model'] not in predict.get_models():
                    d['model'] = get_default_chat_model()
                    continue
                if d['model'] not in st.session_state[KP + "models"] and d['model']:
                    st.session_state[KP + "models"].append(d['model'])
            else:
                if get_default_chat_model() not in st.session_state[KP + "models"]:
                    st.session_state[KP + "models"].append(get_default_chat_model())
        # print(KP+'wset', "Data after Load Data:", st.session_state[KP+'wset'])
        if len(st.session_state[KP + "models"]) < 1:
            st.session_state[KP + "models"].append(get_default_chat_model())
        # print("Loaded Models:", st.session_state[KP+"models"])

    def show_filter_tag_box():
        hide_tags = set()
        if KP + "tag_hide" in st.session_state:
            hide_tags = set(st.session_state[KP + "tag_hide"].split(','))
        tags = sorted(list(set(st.session_state[KP + "TagManager"].get_tags()) - hide_tags), key=str.casefold)
        st.sidebar.multiselect("Filter By Tags", options=tags, key=KP + "filter_select_tags")

    def show_load_chat_box():
        def move_chat():
            if st.session_state[KP + "move_chat"] == "Move Chat to Project":
                return
            fpath = st.session_state[KP + "appuser_data_metadata"].get(st.session_state[KP + "load_chat"])
            fname = os.path.basename(fpath)
            nfpath = os.path.join(st.session_state[KP + 'app_data_home'], st.session_state[KP + 'name'])
            if st.session_state[KP + "move_chat"] != "legacy":
                nfpath = os.path.join(nfpath, st.session_state[KP + "move_chat"])
            nfpath = os.path.join(nfpath, fname)
            shutil.move(fpath, nfpath)
            st.session_state[KP + 'chat_store'] = nfpath
            # Update Metadata
            st.session_state[KP + "appuser_data_metadata"].set(st.session_state[KP + 'chat_store'],
                                                               label=st.session_state[KP + "chat_label"])
            # Update Token
            token_count = st.session_state[KP + "TokenCounter"].get_token_count(fpath)
            st.session_state[KP + "TokenCounter"].set_token_count(nfpath,token_count)

            # Move Tags
            st.session_state[KP + "TagManager"].rename_object(fpath, nfpath)
            st.session_state[KP + "TagManager"].save()

        chat_list = st.session_state[KP + "appuser_data_metadata"].get_labels()
        # Sorting Chat List
        st.sidebar.radio("Sort Chat List", ["Time", "Alphabet"], index=0, key=KP + "chat_list_sort", horizontal=True)
        if len(chat_list) > 2:
            if st.session_state[KP + "chat_list_sort"] == "Time":
                chat_list.reverse()
            else:
                chat_list.sort()
        show_filter_tag_box()
        # Create Chat Categories
        chat_displayname = {}
        chat_to_display = []
        for chat in chat_list:
            chat_file = st.session_state[KP + "appuser_data_metadata"].get(chat)
            if not os.path.isfile(chat_file):
                continue
            tags = st.session_state[KP + "TagManager"].get_tags_for_object(chat_file)
            if KP+"token_count_none" not in st.session_state or not st.session_state[KP+"token_count_none"]:
                token_count = st.session_state[KP + "TokenCounter"].get_token_count(chat_file)
                # token_count = 0
                chat_displayname[chat] = "[%s]" % token_count
            else:
                chat_displayname[chat] = ""
            if len(st.session_state[KP + "filter_select_tags"]) > 0:
                eliminate_chat = True
                for stags in st.session_state[KP + "filter_select_tags"]:
                    if stags in tags:
                        eliminate_chat = False
                if eliminate_chat:
                    continue
            if len(tags) > 0:
                if "CMP-M" in tags:
                    chat_displayname[chat] += "[CMP-M]"
                elif "CMP-S" in tags:
                    chat_displayname[chat] += "[CMP-S]"
                else:
                    chat_displayname[chat] += "[Tagged]"
            else:
                chat_displayname[chat] += ""

            chat_displayname[chat] += " " + chat

            chat_to_display.append(chat)
        st.sidebar.selectbox("Load Chat", chat_to_display, key=KP + "load_chat",
                             format_func=lambda x: chat_displayname[x])
        if len(chat_to_display) > 0:
            left, right = st.sidebar.columns([1,3])
            left.button("Load", on_click=load_chat)
            projects = get_visible_projects()
            projects.remove(st.session_state[KP + "loaded_project"])
            right.selectbox("Move", ["Move Chat to Project"] + projects, label_visibility="collapsed",
                            key=KP+"move_chat", on_change=move_chat)

    def set_tag_fav():
        st.session_state[KP + "TagManager"].tag("Favourite", get_chatstorefilepath())

    def unset_tag_fav():
        st.session_state[KP + "TagManager"].untag("Favourite", get_chatstorefilepath())

    def is_chat_fav():
        if "Favourite" in st.session_state[KP + "TagManager"].get_tags_for_object(get_chatstorefilepath()):
            return True
        return False

    def show_model_box():
        st.sidebar.markdown("## Chat Models")
        default_models = set()
        for chat_turn in st.session_state[KP + 'wset']:
            if chat_turn['role'] == 'robot':
                if 'model' in chat_turn:
                    if chat_turn['model'] in predict.get_models():
                        default_models.add(chat_turn['model'])
                else:
                    default_models.add(get_default_chat_model())
        if len(default_models) < 1:
            default_models.add(get_default_chat_model())
        st.sidebar.multiselect("## Choose Other Models",
                               options=predict.get_models(),
                               key=KP + "OtherModels",
                               default=list(default_models),
                               on_change=add_other_models)

        for i, model in enumerate(st.session_state[KP + "models"]):
            label = ":%s[%s]" % (get_model_text_color(model), model)
            if i == 0:
                label += " (Default)"
            st.sidebar.markdown(label)

    st.sidebar.button(":heavy_plus_sign: New Chat", on_click=chat_new)
    if st.session_state[KP + "chat_label"] != '':
        st.sidebar.text_input("Chat Label", key=KP + "chat_new_label", value=st.session_state[KP + "chat_label"],
                              on_change=save_labelchange)

        left, right = st.sidebar.columns(2)
        if KP + "current_chat_token_count" in st.session_state:
            left.write("Token Count: **%s**" % st.session_state[KP + "current_chat_token_count"])
        if is_chat_fav():
            right.button(":heart:", key=KP + "fav_chat", on_click=unset_tag_fav)
        else:
            right.button(":white_heart:", key=KP+"fav_chat", on_click=set_tag_fav)
        st.sidebar.button("Copy Chat", key=KP + "copy_chat", on_click=save_chat_copy)

    show_load_chat_box()
    show_model_box()


def show_page_end(tag):
    _vdel(KP + tag)


def show_documentation():
    st.markdown('# Documentations')
    if KP+"documentation" in st.session_state:
        for dl in st.session_state[KP+"documentation"].replace('\n', '').split(','):
            st.markdown('- %s' % dl)
    else:
        st.markdown("No Documentation")


def show_dashboard():
    def get_labeler(comfile, nickname=True):
        # Only nicknames who marked task as completed
        nickname_to_name_map = {
            "Partha":"partha.mukherjee",
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

    def get_tag_filepath(comfile, project):
        fname = os.path.basename(comfile)
        labeler = get_labeler(comfile, True)
        return "%s/%s/%s/%s" % (st.session_state[KP + "app_data_home"], labeler, project, fname)

    @st.cache_resource
    def get_metadata_mgr(fdir):
        return mm.MetadataManager(fdir + '/metadata.json')

    # @st.cache_resource
    def get_completed_project_dict(project, keytag):
        project_data = []
        completed_dir_path = st.session_state[KP + "app_data_home"] + "/DONE/"
        dpath = os.path.join(completed_dir_path, project)
        for f in os.listdir(dpath):
            fpath = os.path.join(dpath, f)
            if os.path.isfile(fpath):
                labeler = get_labeler(fpath)
                tag_fpath = get_tag_filepath(fpath, project)
                if os.path.isfile(tag_fpath):
                    tags = st.session_state[KP + "TagManager"].get_tags_for_object(tag_fpath)
                    fdir = os.path.dirname(tag_fpath)
                    metadatamgr = get_metadata_mgr(fdir)
                    label = metadatamgr.get_label_from_filepath(tag_fpath)
                    tdata = {"Labeler": labeler, "Tags": tags, "Label": label}
                    turns = json.loads(open(fpath, "r").read())
                    prompt_count = 1
                    response_count = 1
                    for turn in turns:
                        if turn["role"] == "context":
                            tdata["context"] = turn["content"]
                        elif turn["role"] == "user":
                            tdata["prompt_%s" % str(prompt_count)] = turn["content"]
                            prompt_count += 1
                        elif turn["role"] == "robot":
                            tdata["response_%s" % str(response_count)] = turn["content"]
                            response_count += 1
                    project_data.append(tdata)
        st.session_state[keytag] = project_data

    @st.cache_resource
    def get_completed_task_df():
        transaction_data = []
        analytics_data = []
        completed_dir_path = st.session_state[KP + "app_data_home"] + "/DONE"
        for d in os.listdir(completed_dir_path):
            # project = get_project_name(d)
            project = d
            dpath = os.path.join(completed_dir_path, d)
            for f in os.listdir(dpath):
                fpath = os.path.join(dpath, f)
                if os.path.isfile(fpath):
                    labeler = get_labeler(fpath)
                    tag_fpath = get_tag_filepath(fpath, project)
                    if os.path.isfile(tag_fpath):
                        # print("Found:", fpath, labeler, tag_fpath)
                        fname = os.path.basename(tag_fpath)
                        tags = st.session_state[KP + "TagManager"].get_tags_for_object(tag_fpath)
                        # print(tag_fpath, tags)
                        completed_type = ''
                        for cmptag in ['CMP-S', 'CMP-M']:
                            if cmptag in tags:
                                tags.remove(cmptag)
                                completed_type = cmptag
                        if not completed_type:
                            continue
                        tdata = {"filename": fname, "Labeler": labeler, "Project": project, "Type": completed_type}
                        transaction_data.append(tdata)
                        for tag in tags:
                            analytics_data.append({"filename": fname, "Labeler": labeler, "Project": project,
                                                   "Type": completed_type, "Tag": tag})
                    else:
                        print("Not Found:", fpath, labeler, tag_fpath)
        return pd.DataFrame(transaction_data), pd.DataFrame(analytics_data)

    @st.cache_resource
    def get_completed_projects():
        projects = []
        completed_dir_path = st.session_state[KP + "app_data_home"] + "/DONE"
        for d in os.listdir(completed_dir_path):
            dpath = os.path.join(completed_dir_path, d)
            if os.path.isdir(dpath):
                if sum(1 for entry in os.listdir(dpath) if os.path.isfile(os.path.join(dpath, entry))) > 0:
                    projects.append(d)
        return sorted(projects, key=str.casefold)

    def make_archive(project):
        filename = st.session_state["global.code_home"] + "/data/" + project
        shutil.make_archive(filename, 'gztar', st.session_state[KP + "app_data_home"] + "/DONE/" + project)
        st.session_state[KP + project + ".download_zip.file"] = filename + ".tar.gz"

    import plotly.express as px
    st.markdown('# Dashboard')
    tdf, adf = get_completed_task_df()
    # tdf.to_csv("transaction_data.csv")
    # adf.to_csv("analytics_data.csv")
    danalysis = st.radio("Data Analysis", options=['Chats', 'Tags'], horizontal=True)
    if danalysis == 'Chats':
        df = tdf
        rings = ["Type", "Labeler", "Project"]
    else:
        df = adf
        rings = ["Tag", "Type", "Labeler", "Project"]
    # print("Rings:", )
    with st.expander("More Filters"):
        sequence = st.multiselect("Sequence", options=rings, default=rings)
        for ring in rings:
            ring_data = sorted(df[ring].unique())
            ring_select = st.multiselect(ring, options=ring_data, default=ring_data)
            df = df.loc[df[ring].isin(ring_select)]

    display_map = {'SunBurst' : px.sunburst, 'TreeMap': px.treemap, 'Icicle': px.icicle}
    display_chart = st.radio("Display", options=['TreeMap', 'SunBurst', 'Icicle'], horizontal=True)
    fig = display_map[display_chart](
        df,
        title='-'.join(sequence),
        path=reversed(sequence)
    )
    fig.update_traces(textinfo="label+value+percent entry")
    st.plotly_chart(fig, theme="streamlit", use_container_width=True)
    st.divider()
    for project in get_completed_projects():
        st.markdown("### %s" % project)
        cols = st.columns(4)
        if KP+project+".download_zip.file" in st.session_state:
            with open(st.session_state[KP+project+".download_zip.file"], "rb") as fh:
                cols[0].download_button(
                    label="Download " + os.path.basename(st.session_state[KP+project+".download_zip.file"]),
                    data=fh,
                    file_name=os.path.basename(st.session_state[KP+project+".download_zip.file"]),
                    mime='application/gzip',
                    type="primary"
                )
        else:
            cols[0].button(":arrow_double_down: Generate Zip Download Link", key=KP+project+".download_zip",
                           on_click=make_archive, args=(project,))
        if KP + project + ".data" in st.session_state:
            st.data_editor(st.session_state[KP + project + ".data"])
        else:
            cols[1].button(":chart: Show Data", key=KP + project + ".show_data",
                           on_click=get_completed_project_dict, args=(project, KP + project + ".data",))


def get_visible_projects():
    project_list = []
    visible_projects = []
    if KP+"ACL" in st.session_state:
        if "project_visibility" in st.session_state[KP+"ACL"]:
            visible_projects = st.session_state[KP+"ACL"]["project_visibility"]
    for category in list(st.session_state[KP + "config_loaded"].keys()):
        if category == "GLOBAL" or category.startswith("ACL_"):
            continue
        if len(visible_projects) > 0:
            if category in visible_projects:
                project_list.append(category)
        else:
            project_list.append(category)
    return project_list


def clean_project_space():
    # delete transient project entries
    for entry in ["context_folders", "select_context_label", "allow_context_label_entry",
                  "context_none", "reference_chat", "tag_buttons", "tag_hide", "approved_labellers",
                  "default_chat_model", "token_count_none", "chat_display_mode", "print_model_input_output",
                  "suggested_chat_label", "add_context", "contexts","no_manual_add_context_button",
                  "loaded_context_folders"]:
        _vdel(KP + entry)


def load_global_config():
    for key in st.session_state[KP + "config_loaded"]["GLOBAL"]:
        st.session_state[KP + key] = st.session_state[KP + "config_loaded"]["GLOBAL"][key]


def load_selected_project(project):
    print("\nLoading selected Project:", project)
    for key in st.session_state[KP + "config_loaded"][project]:
        print(KP + key, '=', st.session_state[KP + "config_loaded"][project][key])
        st.session_state[KP + key] = st.session_state[KP + "config_loaded"][project][key]
    st.session_state[KP + "models"] = [get_default_chat_model()]
    st.session_state[KP + "loaded_project"] = project
    init(True, info="Loaded User Select Box")
    # dump_session_state("Loaded Project " + project)


def load_project():
    # User already selected the project
    if KP + "userselect_project" in st.session_state:
        clean_project_space()
        load_global_config()
        load_selected_project(st.session_state[KP + "userselect_project"])
        return

    visible_projects = get_visible_projects()
    if KP + "default_project" in st.session_state and st.session_state[KP + "default_project"] in visible_projects:
        print("Default Project:", st.session_state[KP + "default_project"])
        load_selected_project(st.session_state[KP + "default_project"])
    else:
        for category in st.session_state[KP + "config_loaded"]:
            if category in visible_projects:
                load_selected_project(category)
                return


def load_acls():
    for key in st.session_state[KP + "config_loaded"]:
        if key.startswith("ACL_%s" % st.session_state["global.username"]):
            st.session_state[KP+"ACL"] = {}
            for acl, value in st.session_state[KP + "config_loaded"][key].items():
                st.session_state[KP+"ACL"][acl] = value.split(",")


def load_config():
    if KP + "config_loaded_checksum" in st.session_state and common.get_file_checksum(st.session_state[KP + "config"]) == st.session_state[KP + "config_loaded_checksum"]:
        return
    # dump_session_state("Loading Config")
    st.session_state[KP + "config_loaded"] = common.get_config_as_dict(st.session_state[KP + "config"])
    st.session_state[KP + "config_loaded_checksum"] = common.get_file_checksum(st.session_state[KP + "config"])
    load_global_config()
    load_acls()
    load_project()


def project_change():
    if KP + "userselect_project" in st.session_state and st.session_state[KP + "loaded_project"] != st.session_state[KP + "userselect_project"]:
        load_project()
        # dump_session_state("Project Change")


def now_chat():
    load_config()
    project_change()
    sidebar_user_box()
    # dump_session_state("Start of WORK")
    if _vcheck(KP + "page", KP + "show_documentation"):
        show_documentation()
        return
    if _vcheck(KP + "page", KP+"show_dashboard"):
        show_dashboard()
        return
    if len(st.session_state[KP + 'wset']) > 0 and st.session_state[KP + 'wset'][-1]['role'] == 'user':
        if KP + 'auto_response' in st.session_state and st.session_state[KP + 'auto_response']:
            add_robot_response()
            _vdel(KP + 'auto_response')
            # del st.session_state[KP + 'auto_response']

    if KP + 'llm_return_words' in st.session_state:
        st.session_state[KP + 'wset_changed'] = True
        if KP + 'llm_return_words_printed' not in st.session_state:
            st.session_state[KP + 'llm_return_words_printed'] = 1
        else:
            st.session_state[KP + 'llm_return_words_printed'] += 1
        st.session_state[KP + 'wset'][-1]['content'] = ' '.join(
            st.session_state[KP + 'llm_return_words'][:st.session_state[KP + 'llm_return_words_printed']])
        if st.session_state[KP + 'llm_return_words_printed'] == len(st.session_state[KP + 'llm_return_words']):
            _vdel(KP + 'llm_return_words_printed')
            _vdel(KP + 'llm_return_words')

    if KP + 'wset_changed' in st.session_state and st.session_state[KP + 'wset_changed']:
        # print("Wset changed")
        st.session_state[KP + 'wset_changed'] = False
        if KP + 'llm_return_words' not in st.session_state:
            save_chat()
            update_current_chat_token_count()
    # print("Data before display:", KP+'wset', st.session_state[KP+'wset'])
    sidebar()
    show_chat()
    if KP + 'llm_return_words' in st.session_state:
        time.sleep(0.005)
        st.rerun()


if __name__ == '__main__':
    now_chat()






#### conversation history
"""import streamlit as st
import openai

# Set your OpenAI API key
openai.api_key = "your_openai_api_key"

# Function to generate response from OpenAI
def generate_response(prompt, model="text-davinci-002", max_tokens=100):
    response = openai.Completion.create(
        engine=model,
        prompt=prompt,
        max_tokens=max_tokens
    )
    return response.choices[0].text.strip()

# Streamlit App
def main():
    st.title("OpenAI Chat with LangChain Chaining")

    # Initialize conversation
    conversation_history = []

    # Start the conversation
    user_input = st.text_input("You:")
    if st.button("Send"):
        if user_input:
            conversation_history.append("You: " + user_input)
            st.write("You:", user_input)

            # Generate response from OpenAI
            ai_response = generate_response("\n".join(conversation_history))
            conversation_history.append("AI: " + ai_response)
            st.write("AI:", ai_response)

if __name__ == "__main__":
    main()
"""

## generate response
"""
import time

def generate_text_char_by_char(text, delay=0.05):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)

# Example usage:
input_text = "Hello, world!"
generate_text_char_by_char(input_text)
"""