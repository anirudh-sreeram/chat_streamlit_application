import copy
import os
import json
import yaml
import shutil
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_ace import st_ace
import time
import filecmp
from src import predict
from lib import common
from lib import token_counter as tc
from lib import metadata_manager as mm

APP_DIR = "rlhf"
APP_METADATA = "metadata.json"
APP_TOKEN_COUNTER = "token_counter.json"
APP_LABEL = "label"
# Key Prefix
KP = "rlhf."

# These are the only valid roles to be used in this code
roles = ["user", "robot", "context"]


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
    if keytag in st.session_state:
        if st.session_state[keytag]:
            return True
        if st.session_state[keytag] == "True":
            return True
        if st.session_state[keytag] == 1:
            return True
    return False


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


def banner(msg):
    print('*' * 50, msg)


def read_file(file_name):
    script = ''
    with open(file_name) as fh:
        script += fh.read()
    return script


def get_file_and_content_map_from_folder(folders, add_file_info=False):
    data_map = {}
    counter = 1
    for folder in folders.split(','):
        if not os.path.isdir(folder):
            continue
        for file in sorted(os.listdir(folder)):
            fpath = os.path.join(folder, file)
            if os.path.isfile(fpath):
                if add_file_info:
                    data_map[str(counter) + "-" + file] = str(counter) + "-" + file + "\n" + read_file(fpath)
                else:
                    data_map[str(counter) + "-" + file] = read_file(fpath)
                counter += 1
    return data_map


def get_default_chat_model():
    # dump_session_state("get_default_chat_model")
    if KP + "default_chat_model" in st.session_state:
        # print("Finding", st.session_state[KP+"default_chat_model"], "in", predict.get_model_names())
        if st.session_state[KP + "default_chat_model"] in predict.get_model_names():
            return st.session_state[KP + "default_chat_model"]
    # print("Requested Default Model not found")
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
    print("Robot Request:", model, ":", prompt_string)
    if KP + "print_model_input_output" in st.session_state and st.session_state[KP + "print_model_input_output"]:
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
    print("Robot Response:", model, ":", prediction)
    if KP + "print_model_input_output" in st.session_state and st.session_state[KP + "print_model_input_output"]:
        st.info("Robot Response:" + model + ":" + prediction)
    prediction = prediction.strip()
    if prediction:
        prediction = prediction.replace(prefix_dict["robot"].strip(), "").replace(prefix_dict["end"].strip(),
                                                                                  "").strip()
    else:
        prediction = "System Error:No response from Model"
    return prediction


def prepare_and_predict(idx, model="", content_type="both"):
    try:
        chosen_dialogs = []
        rejected_dialogs = []
        for i in range(idx + 1):
            role = st.session_state[KP + 'wset'][i]['role']
            if role == "robot":
                chosen_content = st.session_state[KP + 'wset'][i]['chosen']
                rejected_content = st.session_state[KP + 'wset'][i]['rejected']

                chosen_dialogs.append({'role': role, 'content': chosen_content})
                rejected_dialogs.append({'role': role, 'content': rejected_content})
            else:
                content = st.session_state[KP + 'wset'][i]['content']
                chosen_dialogs.append({'role': role, 'content': content})
                rejected_dialogs.append({'role': role, 'content': content})
        if content_type == "both":
            return predict_dialog(chosen_dialogs, model=model), predict_dialog(rejected_dialogs, model=model)
        if content_type == "chosen":
            return predict_dialog(chosen_dialogs, model=model), ""
        if content_type == "rejected":
            return "", predict_dialog(rejected_dialogs, model=model)
    except Exception as e:
        print("Exception:prepare_and_predict:", str(e))
        return "System Error:No response", "System Error:No response"


def gen_message(idx, model="", content_type="both"):
    print("Gen Message:", idx, model, content_type)
    chosen_content, rejected_content = prepare_and_predict(idx, model, content_type)
    # print("gen_message WSet", st.session_state[KP + 'wset'])
    if idx < len(st.session_state[KP + 'wset']) and st.session_state[KP + 'wset'][idx]['role'] == 'robot':
        if content_type in ["both", "chosen"]:
            st.session_state[KP + 'wset'][idx]['chosen'] = chosen_content
        if content_type in ["both", "rejected"]:
            st.session_state[KP + 'wset'][idx]['rejected'] = rejected_content
    else:
        st.session_state[KP + 'wset'].append(
            {"role": "robot", "chosen": chosen_content, "rejected": rejected_content, "model": model})
    st.session_state[KP + 'wset_changed'] = True
    # print("WSet:", st.session_state[KP+'wset'])


def add_robot_response():
    def reload_chat():
        # print("Save Chat:", len(st.session_state[KP+'wset']))
        if len(st.session_state[KP + 'wset']) < 1:
            return
        # Update Data
        fpath = get_chatstorefilepath()
        jobj = json.loads(open(fpath, "r").read())
        if isinstance(jobj, list):
            st.session_state[KP + 'wset'] = jobj
            # _vdel(KP + 'loaded_object')
        else:
            st.session_state[KP + 'loaded_object'] = jobj
            st.session_state[KP + 'wset'] = jobj["conversation"]

    reload_chat()
    gen_message(len(st.session_state[KP + 'wset']) - 1, model=st.session_state[KP + "model"])
    st.session_state[KP + 'wset_changed'] = True


def update_chat(idx, key):
    # print("Update Chat", idx, key)
    # print("Update Chat", st.session_state[key])
    if st.session_state[key]:
        if idx >= len(st.session_state[KP + 'wset']):
            return
        # print("Update Chat Entered")
        if key.endswith("robotchosen"):
            # print("Update Chat: Robot Chosen Updated as", st.session_state[key])
            st.session_state[KP + 'wset'][idx]['chosen'] = st.session_state[key]
        elif key.endswith("robotrejected"):
            # print("Update Chat: Robot Rejected Updated as", st.session_state[key])
            st.session_state[KP + 'wset'][idx]['rejected'] = st.session_state[key]
        else:
            # print("Update Chat: Non Robot Box getting updatedRobot", st.session_state[key])
            st.session_state[KP + 'wset'][idx]['content'] = st.session_state[key]
        st.session_state[KP + 'wset_changed'] = True
        save_chat_data()


def update_role(idx, role):
    st.session_state[KP + 'wset'][idx]['role'] = role
    if role == 'robot':
        if 'content' in st.session_state[KP + 'wset'][idx]:
            st.session_state[KP + 'wset'][idx]['chosen'] = st.session_state[KP + 'wset'][idx]["content"]
            st.session_state[KP + 'wset'][idx]['rejected'] = ''
            del st.session_state[KP + 'wset'][idx]["content"]
        else:
            st.session_state[KP + 'wset'][idx]['chosen'] = ''
            st.session_state[KP + 'wset'][idx]['rejected'] = ''
        st.session_state[KP + 'wset'][idx]['model'] = st.session_state[KP + "model"]
    else:
        st.session_state[KP + 'wset'][idx]["content"] = ''
        if 'chosen' in st.session_state[KP + 'wset'][idx]:
            st.session_state[KP + 'wset'][idx]["content"] = st.session_state[KP + 'wset'][idx]["chosen"]
        if 'rejected' in st.session_state[KP + 'wset'][idx]:
            del st.session_state[KP + 'wset'][idx]["rejected"]


def delete_item(idx):
    if idx < len(st.session_state[KP + 'wset']):
        del st.session_state[KP + 'wset'][idx]
        st.session_state[KP + 'wset_changed'] = True


def add_item(idx, role):
    if role == 'robot':
        st.session_state[KP + 'wset'].insert(idx + 1, {'role': role, 'chosen': "", 'rejected': "",
                                                       'model': st.session_state[KP + "model"]})
    else:
        st.session_state[KP + 'wset'].insert(idx + 1, {'role': role, 'content': ""})
    st.session_state[KP + 'wset_changed'] = True


def move_up(idx):
    rblock = len(st.session_state[KP + "models"])
    st.session_state[KP + 'wset'].insert(idx - rblock, st.session_state[KP + 'wset'].pop(idx))


def move_down(idx):
    rblock = len(st.session_state[KP + "models"])
    st.session_state[KP + 'wset'].insert(idx + rblock, st.session_state[KP + 'wset'].pop(idx))


def get_display_mode(edit_display):
    if KP + "chat_display_mode" in st.session_state:
        if st.session_state[KP + "chat_display_mode"] == "read_only":
            return False
        if st.session_state[KP + "chat_display_mode"] == "opt_in_edit":
            if KP + "chat_display_mode_edit" in st.session_state and st.session_state[KP + "chat_display_mode_edit"]:
                return True
            return False
    return edit_display


def display_chat_turn_box(keytag, label, idx, message):
    if _vcheck(KP + "chat_display_mode", "rich"):
        pre_keytag = keytag.replace(KP, KP + "pre_")
        st.markdown(label)
        st_ace(value=message, key=keytag)
        if pre_keytag not in st.session_state or st.session_state[pre_keytag] != st.session_state[keytag]:
            update_chat(idx, keytag)
            # st.rerun()
    else:
        st.text_area(label=label, value=message, on_change=update_chat, args=(idx, keytag),
                     key=keytag, height=max(300, min(600, int(len(message) / 3))))


def add_validators(idx, location, message):
    def validate_clear(report_key):
        for txt in ["_json", "_yaml"]:
            _vdel(report_key + txt + ".errors")
            _vdel(report_key + txt + ".success")

    def validate_json(report_key, message):
        try:
            # print("Validating JSON", message)
            jobj = json.loads(message)
            validate_clear(report_key)
            st.session_state[report_key + "_json.success"] = "JSON"
        except Exception as e:
            validate_clear(report_key)
            st.session_state[report_key + "_json.errors"] = "JSON-InValid:" + str(e)

    def validate_yaml(report_key, message):
        try:
            yobj = yaml.safe_load(message)
            validate_clear(report_key)
            st.session_state[report_key + "_yaml.success"] = "YAML"
        except Exception as e:
            validate_clear(report_key)
            st.session_state[report_key + "_yaml.errors"] = "YAML-InValid:" + str(e)

    if KP + "add_validator_json" in st.session_state or KP + "add_validator_yaml" in st.session_state:
        upcols = st.columns([1, 3, 1, 1, 1])
        if _vtrue(KP + "add_validator_json"):
            upcols[2].button(":rainbow[Json]", KP + str(idx) + location + '_json', on_click=validate_json,
                             args=(KP + str(idx) + location, message,))
        if _vtrue(KP + "add_validator_yaml"):
            upcols[3].button(":rainbow[YAML]", KP + str(idx) + location + '_yaml', on_click=validate_yaml,
                             args=(KP + str(idx) + location, message,))
        upcols[4].button(":rainbow[Clear]", KP + str(idx) + location + '_clear', on_click=validate_clear,
                         args=(KP + str(idx) + location,))


def display_validator_results(idx, location):
    if KP + str(idx) + location + '_json.success' in st.session_state:
        st.success(st.session_state[KP + str(idx) + location + '_json.success'])
    if KP + str(idx) + location + '_json.errors' in st.session_state:
        st.error(st.session_state[KP + str(idx) + location + '_json.errors'])

    if KP + str(idx) + location + '_yaml.success' in st.session_state:
        st.success(st.session_state[KP + str(idx) + location + '_yaml.success'])
    if KP + str(idx) + location + '_yaml.errors' in st.session_state:
        st.error(st.session_state[KP + str(idx) + location + '_yaml.errors'])


def display_chat_user_context(idx, message, role, edit_display):
    def delete_context(idx):
        if KP + 'add_context' in st.session_state:
            del st.session_state[KP + 'add_context']
        delete_item(idx)

    def add_tags(keytag, title, classified_tags=False):
        if st.session_state[keytag] == "%s Tags" % title:
            return
        field_name = "tags"
        if field_name not in st.session_state[KP + 'wset'][idx]:
            st.session_state[KP + 'wset'][idx][field_name] = []
        if classified_tags:
            st.session_state[KP + 'wset'][idx][field_name].append(title + '_' + st.session_state[keytag])
        else:
            st.session_state[KP + 'wset'][idx][field_name].append(st.session_state[keytag])
        save_chat()

    def rm_tag(tag, title, classified_tags=False):
        if tag == "%s Tags" % title:
            return
        field_name = "tags"
        # print("Tag to remove", tag)
        rmtag = tag
        if classified_tags:
            rmtag = title + '_' + tag
        if rmtag in st.session_state[KP + 'wset'][idx][field_name]:
            st.session_state[KP + 'wset'][idx][field_name].remove(rmtag)
            save_chat()

    def show_tags(idx, tags, title, classified_tags=False):
        selected_tags = []
        field_name = "tags"
        if field_name in st.session_state[KP + 'wset'][idx]:
            for i, tag in enumerate(st.session_state[KP + 'wset'][idx][field_name]):
                if classified_tags:
                    if tag.startswith(title + "_"):
                        selected_tags.append(tag.replace(title + "_", ''))
                else:
                    selected_tags.append(tag)
        remaining_tags = sorted(list(set(tags) - set(selected_tags)), key=str.casefold)
        st.selectbox("Select Tags", options=["%s Tags" % title] + remaining_tags,
                     label_visibility="collapsed", key=KP + str(idx) + 'c3' + title, index=0,
                     on_change=add_tags, args=(KP + str(idx) + 'c3' + title, title, classified_tags))

        if classified_tags:
            for i, tag in enumerate(selected_tags):
                st.button('%s :x:' % tag.replace(":", "\:"), key=KP + "untag_" + str(idx) + tag + title,
                          on_click=rm_tag, args=(tag, title, classified_tags,))
        else:
            num_tags_per_row = 1
            if KP + "show_tags_per_row" in st.session_state:
                num_tags_per_row = int(st.session_state[KP + "show_tags_per_row"])
            show_rows = st.columns(num_tags_per_row)
            for i, tag in enumerate(selected_tags):
                show_rows[i % num_tags_per_row].button('%s :x:' % tag.replace(":", "\:"),
                                                       key=KP + "untag_" + str(idx) + tag,
                                                       on_click=rm_tag, args=(tag, title, classified_tags,))

    edit_display = get_display_mode(edit_display)
    add_validators(idx, role, message)
    if role == "context":
        if edit_display:
            display_chat_turn_box(KP + "Sys" + str(idx) + role, "System", idx, message)
            dncols = st.columns([1, 1, 6, 1, 1, 1])
            dncols[0].button(":x:", on_click=delete_context, args=(idx,), key=KP + str(idx) + 'context')
        else:
            st.warning(message.replace('\n', '\n\n') if '|' not in message else message, icon="📌")
    else:
        if edit_display:
            display_chat_turn_box(KP + "Sys" + str(idx) + role, "Customer", idx, message)
            c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 6, 1, 1, 1])
            c1.button(":x:", on_click=delete_item, args=(idx,), key=KP + str(idx) + 'c1')
            c2.button(":heavy_plus_sign:", on_click=add_item, args=(idx, role,), key=KP + str(idx) + 'c2')
            if _vexists(KP + "tags"):
                with c3:
                    show_tags(idx, st.session_state[KP + "tags"].split(','), "Select",
                              False)
            else:
                classified_tags = sorted([key for key in st.session_state if key.startswith(KP + "tags_")],
                                         key=str.casefold)
                if len(classified_tags) > 0:
                    num_classified_tags_per_row = 3
                    ctcols = c3.columns(num_classified_tags_per_row)
                    for i, classified_tag in enumerate(classified_tags):
                        with ctcols[i % num_classified_tags_per_row]:
                            show_tags(idx, st.session_state[classified_tag].split(','),
                                      classified_tag.replace(KP + "tags_", ''), True)

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
            if "tags" in st.session_state[KP + 'wset'][idx]:
                st.markdown("#### Tags:")
                st.markdown(' + '.join(st.session_state[KP + 'wset'][idx]["tags"]))
    display_validator_results(idx, role)


def display_chat_robots(idx, chosen, rejected, edit_display):
    def add_robot_box_buttons(idx, content_type):
        def snap(idx, ct):
            # print("Taking Snapshot:", idx, ct)
            st.session_state[KP + 'wset'][idx]["snap" + ct] = st.session_state[KP + 'wset'][idx][ct]
            save_chat()

        def develop(idx, ct):
            # print("Developing Snapshot:", idx, ct)
            if "snap" + ct in st.session_state[KP + 'wset'][idx]:
                st.session_state[KP + 'wset'][idx][ct] = st.session_state[KP + 'wset'][idx]["snap" + ct]
                save_chat()

        c1, c2, cx, c7 = st.columns(4)
        if "snap" + content_type in st.session_state[KP + 'wset'][idx]:
            c1.button(":camera_with_flash:", key=KP + str(idx) + 'c1' + content_type,
                      on_click=snap, args=(idx, content_type))
            c2.button(":arrow_right_hook:", key=KP + str(idx) + 'c2' + content_type,
                      on_click=develop, args=(idx, content_type))
        else:
            c1.button(":camera:", key=KP + str(idx) + 'c1' + content_type,
                      on_click=snap, args=(idx, content_type))
            c2.button(":arrow_right_hook:", key=KP + str(idx) + 'c2' + content_type, disabled=True)

        if _vtrue(KP + "chatbox_delete_confirmation"):
            if _vtrue(KP + str(idx) + 'cx' + content_type):
                cx.button("Sure :boom:", on_click=delete_item, args=(idx,), key=KP + str(idx) + 'cx.2' + content_type)
            else:
                cx.button(":x:", key=KP + str(idx) + 'cx' + content_type)
        else:
            cx.button(":x:", on_click=delete_item, args=(idx,), key=KP + str(idx) + 'cx' + content_type)
        # cx.button(":x:", on_click=delete_item, args=(idx,), key=KP + str(idx) + 'cx' + content_type)

        if idx > 0 and st.session_state[KP + 'wset'][idx]['model'] in predict.get_models():
            c7.button(":robot_face:", on_click=gen_message,
                      args=(idx, st.session_state[KP + 'wset'][idx]['model'], content_type,),
                      key=KP + str(idx) + 'c7' + content_type)

    def swap_robot_content(idx):
        tmp = st.session_state[KP + 'wset'][idx]["chosen"]
        st.session_state[KP + 'wset'][idx]["chosen"] = st.session_state[KP + 'wset'][idx]["rejected"]
        st.session_state[KP + 'wset'][idx]["rejected"] = tmp

    edit_display = get_display_mode(edit_display)
    if _vtrue(KP + "add_agent_message_swap_button") or _vtrue(KP + "add_agent_duo_regenerate_button"):
        left, mid, right = st.columns([5, 1, 5])
        with mid:
            if _vtrue(KP + "add_agent_message_swap_button"):
                st.button(":arrows_counterclockwise:", key=KP + "Swapping_" + str(idx) + '_robot',
                          on_click=swap_robot_content, args=(idx,))
            if _vtrue(KP + "add_agent_duo_regenerate_button"):
                st.button(":robot_face:", on_click=gen_message,
                          args=(idx, st.session_state[KP + 'wset'][idx]['model'],),
                          key=KP + "Duo_Regenerate" + str(idx) + "both")
    else:
        left, right = st.columns(2)
    if edit_display:
        with left:
            add_validators(idx, "robot_left", chosen)
            label = ":blue[Agent (%s)]" % st.session_state[KP + 'wset'][idx]['model']
            display_chat_turn_box(KP + "Agent" + str(idx) + 'robot' + "chosen", label, idx, chosen)
            add_robot_box_buttons(idx, "chosen")
            display_validator_results(idx, "robot_left")
        with right:
            add_validators(idx, "robot_right", rejected)
            label = ":red[Agent (%s)]" % st.session_state[KP + 'wset'][idx]['model']
            display_chat_turn_box(KP + "Agent" + str(idx) + 'robot' + "rejected", label, idx, rejected)
            add_robot_box_buttons(idx, "rejected")
            display_validator_results(idx, "robot_right")
    else:
        with left:
            add_validators(idx, "robot_left", chosen)
            st.info(chosen.replace('\n', '\n\n') if '|' not in chosen else chosen, icon="👨‍💻")
            display_validator_results(idx, "robot_left")
        with right:
            add_validators(idx, "robot_right", rejected)
            st.info(rejected.replace('\n', '\n\n') if '|' in rejected else rejected, icon="👨‍💻")
            display_validator_results(idx, "robot_right")


def display_chat_summary(message):
    st.divider()
    st.markdown(":pencil: SUMMARY: :blue[{}]".format(message))


def add_chat(role, content="", auto_response=False, model=''):
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


def get_chatstorefilepath():
    if st.session_state[KP + "chat_store"] == '':
        st.session_state[KP + 'chat_store'] = os.path.join(st.session_state[KP + "appuser_data_home"],
                                                           datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p") +
                                                           "_" + st.session_state[KP + "name"] + ".json")
        if KP + "suggested_chat_label" in st.session_state and st.session_state[KP + "suggested_chat_label"]:
            st.session_state[KP + "chat_label"] = st.session_state[KP + "suggested_chat_label"]
            st.session_state[KP + "appuser_data_metadata"].set(st.session_state[KP + 'chat_store'],
                                                               label=st.session_state[KP + "chat_label"])
        else:
            st.session_state[KP + "chat_label"] = st.session_state[KP + "appuser_data_metadata"].set(
                st.session_state[KP + 'chat_store'],
                content=st.session_state[KP + 'wset'][0]['content'])
    return st.session_state[KP + "chat_store"]


def mark_completed():
    banner("Mark Completed")
    save_chat()
    chat_filepath = get_chatstorefilepath()
    if os.path.isfile(chat_filepath):
        shutil.copy(chat_filepath,
                    os.path.join(st.session_state[KP + "completed_dir"], os.path.basename(chat_filepath)))


def is_completed():
    if st.session_state[KP + "chat_store"] == "":
        return False
    completed_file = os.path.join(st.session_state[KP + "completed_dir"], os.path.basename(get_chatstorefilepath()))

    if not os.path.isfile(completed_file):
        return False
    return True if os.path.isfile(completed_file) else False


def unmark_completed():
    completed_file = os.path.join(st.session_state[KP + "completed_dir"], os.path.basename(get_chatstorefilepath()))
    if os.path.isfile(completed_file):
        os.remove(completed_file)


def show_chat():
    unselected_stored_chat_message = "Select Stored Chat"

    def selected_reference_chat():
        # print("selected_reference_chat called")
        if KP + "selected_reference_chat" not in st.session_state:
            return
        if not st.session_state[KP + "selected_reference_chat"]:
            return
        # print("selected_reference_chat:", st.session_state[KP + "selected_reference_chat"])
        if st.session_state[KP + "selected_reference_chat"] != unselected_stored_chat_message:
            filepath = os.path.join(st.session_state[KP + "reference_chat"],
                                    st.session_state[KP + "selected_reference_chat"])
            st.session_state[KP + 'wset'] = json.loads(open(filepath, "r").read())
            # print("Selected_reference_chat Chat:",st.session_state[KP + 'wset'])

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
                    # print("Context Msg:", st.session_state[KP + "context_msg"])
                    add_context_in_chat(1)
            else:
                st.text_area("Context", key=KP + "context_msg", on_change=add_context_in_chat, args=(0,))

    def show_context_box():
        if KP + 'add_context' not in st.session_state:
            if KP + "contexts" in st.session_state:
                if _vexists(KP + "no_manual_add_context_button"):
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

    def prompt_provided(keytag):
        add_chat("prompt", st.session_state[keytag], False, '')

    def prompt_submit(role, keytag, auto_response=False):
        if keytag not in st.session_state:
            return
        content = st.session_state[keytag]
        if content:
            add_chat(role, content, auto_response)
        _vdel(keytag)

    def has_completed_checklist():
        for key in st.session_state:
            if key.startswith(KP + "cmptask_"):
                return True
        return False

    def validate_completed_checklist():
        # dump_session_state("validate_completed_checklist")
        save_chat()
        for key in st.session_state:
            if key.startswith(KP + "cmptask_"):
                if key.endswith("_options"):
                    continue
                if key.endswith("_done"):
                    continue
                if not _vexists(key + "_done"):
                    # print(key + "_done", "Don't Exist")
                    _vdel(KP + "completed_checklist_done")
                    return
                if _vcheck(key + "_done", "None"):
                    # print(key+"_done", "None")
                    _vdel(KP + "completed_checklist_done")
                    return
                if not _vtrue(key + "_done"):
                    # print(key + "_done", "False")
                    _vdel(KP + "completed_checklist_done")
                    return
        st.session_state[KP + "completed_checklist_done"] = True

    def show_completed_checklist(disabled=False):
        checklists = {}
        keylist = {}
        for key in sorted(st.session_state.keys()):
            if key.startswith(KP + "cmptask_"):
                if key.endswith("_done"):
                    continue
                if key.endswith("_options"):
                    base_key = key.replace("_options", "")
                    checklists[st.session_state[base_key]] = st.session_state[key].split(',')
                else:
                    checklists[st.session_state[key]] = True
                    keylist[st.session_state[key]] = key
                    # print("keylist[+st.session_state["+key+"]] = ",key, "Value:", st.session_state[key])

        checklist_container = st.container()
        with checklist_container:
            if disabled:
                st.markdown("*Checklist*")
            else:
                st.markdown("# Checklist")
            for chk in checklists:
                if isinstance(checklists[chk], list):
                    st.radio(chk, options=["None"] + checklists[chk], key=keylist[chk] + "_done", horizontal=True,
                             disabled=disabled)
                else:
                    # print("***", chk, keylist[chk])
                    st.checkbox(chk, key=keylist[chk] + "_done", disabled=disabled)
            st.button("Done", key=KP + "completed_checklist_validate", on_click=validate_completed_checklist,
                      disabled=disabled)

    if KP + "reference_chat" in st.session_state and len(st.session_state[KP + 'wset']) < 1:
        show_reference_box()
    if KP + "context_none" not in st.session_state:
        show_context_box()
    if is_completed():
        show_completed()

    if _vcheck(KP + "chat_display_mode", "opt_in_edit"):
        if KP + "chat_display_mode_edit" not in st.session_state:
            st.button("Edit Mode", key=KP + "chat_display_mode_edit_x", on_click=change_mode_edit)
        else:
            st.button("Readonly Mode", key=KP + "chat_display_mode_readonly_x", on_click=change_mode_readonly)
    for i, turn in enumerate(st.session_state[KP + 'wset']):
        if turn['role'] not in ['prompt']:
            if turn['role'] != 'robot':
                display_chat_user_context(i, turn['content'], turn['role'], not is_completed())
            else:
                # print("Turn:", turn)
                display_chat_robots(i, turn["chosen"], turn["rejected"], not is_completed())

    st.divider()
    if is_completed():
        col1, col3, coll = st.columns([1, 3, 1])
        coll.button("Revert Completed", on_click=unmark_completed)
        if has_completed_checklist():
            with coll:
                show_completed_checklist(True)
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
        coll.button("Mark Completed", on_click=mark_completed,
                    disabled=len(st.session_state[KP + "wset"]) == 0)
        if len(st.session_state[KP + "wset"]) > 0 and has_completed_checklist():
            with coll:
                show_completed_checklist()
    lrow = len(st.session_state[KP + 'wset']) - 1
    if len(st.session_state[KP + 'wset']) > 1 and st.session_state[KP + 'wset'][lrow]['role'] == 'summary':
        display_chat_summary(st.session_state[KP + 'wset'][lrow]['content'])


def save_chat_data():
    banner("Save Chat Data ")
    # print("Save Chat:", len(st.session_state[KP+'wset']))
    if len(st.session_state[KP + 'wset']) < 1:
        return
    if KP + 'loaded_object' in st.session_state:
        save_obj = st.session_state[KP + 'loaded_object']
    else:
        save_obj = {"conversation": st.session_state[KP + 'wset']}
    # Add MetaTags
    if "metadata" not in save_obj:
        save_obj["metadata"] = {}
    metatags = {}
    for key in st.session_state:
        if key.startswith(KP + "cmptask_"):
            if key.endswith("_options"):
                continue
            if key.endswith("_done"):
                continue
            # print(key, "=", st.session_state[key])
            if key + "_done" in st.session_state:
                # print(key+"_done", "=", st.session_state[key+"_done"])
                metatags[st.session_state[key]] = st.session_state[key + "_done"]
    print("Saving Metatags:", metatags)
    save_obj["metadata"]["metatags"] = metatags

    # Update Data
    fpath = get_chatstorefilepath()
    json.dump(save_obj, open(fpath, 'w'))
    print("Chat Store File", fpath, "Label:", st.session_state[KP + "chat_label"])
    # print("save_chat_data[wset]", st.session_state[KP+"wset"])


def save_chat():
    if len(st.session_state[KP + 'wset']) < 1:
        return
    banner("Save Chat")
    save_chat_data()
    fpath = get_chatstorefilepath()
    # Update Metadata
    # print("Chat Label:", st.session_state[KP + "chat_label"])
    st.session_state[KP + "chat_label"] = st.session_state[KP + "appuser_data_metadata"].set(fpath,
                                                                                             label=st.session_state[
                                                                                                 KP + "chat_label"])
    st.session_state[KP + "appuser_data_metadata"].save()
    print("Saved: File", fpath, "Label:", st.session_state[KP + "chat_label"])


def update_current_chat_token_count():
    if len(st.session_state[KP + 'wset']) < 1:
        st.session_state[KP + "current_chat_token_count"] = 0
        return
    fpath = get_chatstorefilepath()
    wset = copy.copy(st.session_state[KP + 'wset'])
    st.session_state[KP + "current_chat_token_count"] = st.session_state[KP + "TokenCounter"].get_chat_token_count(
        wset, rlhf_robot=True)
    st.session_state[KP + "TokenCounter"].set_token_count(fpath, st.session_state[KP + "current_chat_token_count"])


def load_context_folders():
    # print("Loading Context Folders:", st.session_state[KP + "context_folders"])
    if KP + "loaded_context_folders" in st.session_state and st.session_state[KP + "loaded_context_folders"] == \
            st.session_state[KP + "context_folders"]:
        print("Not Loading Context Folders:", st.session_state[KP + "loaded_context_folders"],
              st.session_state[KP + "context_folders"])
        return
    st.session_state[KP + "contexts"] = get_file_and_content_map_from_folder(st.session_state[KP + "context_folders"],
                                                                             _vtrue(
                                                                                 "add_context_additional_info_in_chat"))
    st.session_state[KP + "loaded_context_folders"] = st.session_state[KP + "context_folders"]
    # print("Loaded Context Folders:", st.session_state[KP + "context_folders"])


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

    for project in get_visible_projects():
        if project == "legacy":
            continue
        pdir = os.path.join(st.session_state[KP + 'app_data_home'], st.session_state[KP + 'name'], project)
        if not os.path.exists(pdir):
            os.makedirs(pdir, exist_ok=True)
    for d in ["appuser_data_home", "completed_dir"]:
        if not os.path.exists(st.session_state[KP + d]):
            os.makedirs(st.session_state[KP + d], exist_ok=True)

    st.session_state[KP + "appuser_data_metadata"] = mm.MetadataManager(
        st.session_state[KP + "appuser_data_metadata_file"])
    _vdel(KP + 'llm_return_words_printed')
    _vdel(KP + 'llm_return_words')
    st.session_state[KP + "models"] = [get_default_chat_model()]
    if KP + "context_folders" in st.session_state:
        load_context_folders()
    if KP + "select_context_label" not in st.session_state:
        st.session_state[KP + "select_context_label"] = "Select Context"
    print("ENVs", st.session_state["global.env"])
    if "global.env" in st.session_state and st.session_state["global.env"] not in ["AIDE", "DART"]:
        if KP + "token_count_none" not in st.session_state or not st.session_state[KP + "token_count_none"]:
            st.session_state[KP + "TokenCounter"] = tc.TokenCounter.get_instance(
                os.path.join(st.session_state[KP + 'app_data_home'], APP_TOKEN_COUNTER),
                st.session_state[KP + "model_checkpoint"],
                predict.get_model_prompt_tags(get_default_chat_model()))


def get_approved_labellers():
    if KP + "approved_labellers" in st.session_state and st.session_state[KP + "approved_labellers"]:
        approved_labellers = [n.strip() for n in st.session_state[KP + "approved_labellers"].split(',')]
    else:
        approved_labellers = []
    data_home = os.path.join(st.session_state['global.data_home'], APP_DIR)
    if os.path.isdir(data_home):
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


def get_visible_projects():
    project_list = []
    visible_projects = []
    if KP + "ACL" in st.session_state:
        if "project_visibility" in st.session_state[KP + "ACL"]:
            visible_projects = st.session_state[KP + "ACL"]["project_visibility"]
    for category in list(st.session_state[KP + "config_loaded"].keys()):
        if category == "GLOBAL" or category.startswith("ACL_"):
            continue
        if len(visible_projects) > 0:
            if category in visible_projects:
                project_list.append(category)
        else:
            project_list.append(category)
    return project_list


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
                             on_change=init, args=(True, "sidebar_user_box",))

    def config_change_actions():
        if KP + "context_folders" in st.session_state:
            load_context_folders()

    def set_new_project():
        print("Project Changed", KP + "default_project", "to", st.session_state[KP + "select_project"])
        st.session_state[KP + "userselect_project"] = st.session_state[KP + "select_project"]

    def show_projectlist_box():
        project_list = get_visible_projects()
        if st.session_state[KP + "default_project"] in project_list:
            index = project_list.index(st.session_state[KP + "default_project"])
        else:
            index = 0
        st.sidebar.selectbox("Select Project", project_list, key=KP + "select_project",
                             index=index,
                             on_change=set_new_project)

    def set_page(page_tag):
        st.session_state[KP + "page"] = page_tag

    # Set multiselect options can be seen fully
    st.sidebar.markdown("## RLHF")
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
                args=([KP + "page", KP + "show_documentation", KP + "show_dashboard"],))
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


def show_documentation():
    st.markdown('# Documentations')
    if KP + "documentation" in st.session_state:
        for dl in st.session_state[KP + "documentation"].replace('\n', '').split(','):
            st.markdown('- %s' % dl)
    else:
        st.markdown("No Documentation")


def show_dashboard():
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

    def get_tag_filepath(comfile, project):
        fname = os.path.basename(comfile)
        labeler = get_labeler(comfile, True)
        return "%s/%s/%s/%s" % (st.session_state[KP + "app_data_home"], labeler, project, fname)

    def get_tag_from_filepath(tag_path):
        tags = []
        fileData = read_file(tag_path)
        fileData = json.loads(fileData)
        if isinstance(fileData, list):
            conversations = fileData
        else:
            conversations = fileData["conversation"]
        for item in conversations:
            if 'tags' in item:
                tags += item['tags']
        return tags

    def get_completed_task_df():
        transaction_data = []
        analytics_data = []
        completed_dir_path = st.session_state[KP + "app_data_home"] + "/DONE"
        for d in os.listdir(completed_dir_path):
            if d.startswith('.'):
                continue
            project = d
            dpath = os.path.join(completed_dir_path, d)
            for f in os.listdir(dpath):
                if f.startswith('.'):
                    continue
                fpath = os.path.join(dpath, f)
                if os.path.isfile(fpath):
                    labeler = get_labeler(fpath)
                    tag_fpath = get_tag_filepath(fpath, project)
                    tags = get_tag_from_filepath(tag_fpath)
                    if os.path.isfile(tag_fpath):
                        # print("Found:", fpath, labeler, tag_fpath)
                        fname = os.path.basename(tag_fpath)
                        tdata = {"filename": fname, "Labeler": labeler, "Project": project}
                        transaction_data.append(tdata)
                        for tag in tags:
                            analytics_data.append({"filename": fname, "Labeler": labeler, "Project": project,
                                                   "Tag": tag})
                    else:
                        print("Not Found:", fpath, labeler, tag_fpath)
        print(transaction_data)
        return pd.DataFrame(transaction_data), pd.DataFrame(analytics_data)

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
        # shutil.make_archive(filename, 'gztar', st.session_state[KP + "app_data_home"] + "/DONE/" + project)
        temp_loc = common.get_archive_file(project, st.session_state[KP + "app_data_home"])
        shutil.make_archive(filename, 'gztar', temp_loc)
        st.session_state[KP + project + ".download_zip.file"] = filename + ".tar.gz"

    def get_metadata_mgr(fdir):
        return mm.MetadataManager(fdir + '/metadata.json')

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
                    tags = get_tag_from_filepath(tag_fpath)
                    fdir = os.path.dirname(tag_fpath)
                    metadatamgr = get_metadata_mgr(fdir)
                    label = metadatamgr.get_label_from_filepath(tag_fpath)
                    tdata = {"Labeler": labeler, "Tags": tags, "Label": label, "filepath": fpath}
                    turns = json.loads(open(fpath, "r").read())
                    if isinstance(turns, dict):
                        turns = turns["conversation"]
                    prompt_count = 1
                    response_count = 1
                    for turn in turns:
                        if turn["role"] == "context":
                            tdata["context"] = turn["content"]
                        elif turn["role"] == "user":
                            tdata["prompt_%s" % str(prompt_count)] = turn["content"]
                            prompt_count += 1
                        elif turn["role"] == "robot":
                            tdata["chosen_response_%s" % str(response_count)] = turn["chosen"]
                            tdata["rejected_response_%s" % str(response_count)] = turn["rejected"]
                            response_count += 1
                    project_data.append(tdata)
        st.session_state[keytag] = project_data

    st.markdown('# Dashboard')
    tdf, adf = get_completed_task_df()
    danalysis = st.radio("Data Analysis", options=['Chats', 'Tags'], horizontal=True)
    if danalysis == 'Chats':
        df = tdf
        rings = ["Labeler", "Project"]
    else:
        df = adf
        rings = ["Tag", "Labeler", "Project"]
    with st.expander("More Filters"):
        sequence = st.multiselect("Sequence", options=rings, default=rings)
        for ring in rings:
            ring_data = sorted(df[ring].unique())
            ring_select = st.multiselect(ring, options=ring_data, default=ring_data)
            df = df.loc[df[ring].isin(ring_select)]
    display_map = {'SunBurst': px.sunburst, 'TreeMap': px.treemap, 'Icicle': px.icicle}
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
        if KP + project + ".download_zip.file" in st.session_state:
            with open(st.session_state[KP + project + ".download_zip.file"], "rb") as fh:
                cols[0].download_button(
                    label="Download " + os.path.basename(st.session_state[KP + project + ".download_zip.file"]),
                    data=fh,
                    file_name=os.path.basename(st.session_state[KP + project + ".download_zip.file"]),
                    mime='application/gzip',
                    type="primary"
                )
        else:
            cols[0].button(":arrow_double_down: Generate Zip Download Link", key=KP + project + ".download_zip",
                           on_click=make_archive, args=(project,))
        if KP + project + ".data" in st.session_state:
            st.data_editor(st.session_state[KP + project + ".data"])
        else:
            cols[1].button(":chart: Show Data", key=KP + project + ".show_data",
                           on_click=get_completed_project_dict, args=(project, KP + project + ".data",))


def sidebar():
    def add_other_model():
        st.session_state[KP + "model"] = st.session_state[KP + "OtherModel"]

    def save_labelchange():
        if KP + 'chat_new_label' not in st.session_state or st.session_state[KP + "chat_new_label"] == '':
            return
        st.session_state[KP + "appuser_data_metadata"].change_label(st.session_state[KP + "chat_label"],
                                                                    st.session_state[KP + "chat_new_label"])
        st.session_state[KP + "chat_label"] = st.session_state[KP + "chat_new_label"]
        st.session_state[KP + "appuser_data_metadata"].save()

    def chat_new():
        print("*" * 50, "New Chat")
        st.session_state[KP + 'wset'] = []
        st.session_state[KP + 'wset_changed'] = True
        st.session_state[KP + "chat_label"] = ""
        st.session_state[KP + "chat_store"] = ""
        _vdel(KP + 'loaded_object')
        _vdel(KP + 'add_context')
        st.session_state[KP + "model"] = get_default_chat_model()

    def save_chat_copy():
        print("save_chat_copy: Start")
        if len(st.session_state[KP + 'wset']) < 1:
            print("Insufficient WSet")
            return
        if KP + "copy_chat_to_user" in st.session_state and st.session_state[KP + "copy_chat_to_user"] != \
                st.session_state[KP + "name"]:
            st.session_state[KP + "appuser_data_metadata"].copy(st.session_state[KP + "chat_label"],
                                                                st.session_state[KP + "copy_chat_to_user"])
            st.session_state[KP + "copy_chat.message"] = "Copied [%s] to [%s]" % (st.session_state[KP + "chat_label"],
                                                                                  st.session_state[
                                                                                      KP + "copy_chat_to_user"])
        else:
            st.session_state[KP + "appuser_data_metadata"].copy(st.session_state[KP + "chat_label"])
            st.session_state[KP + "copy_chat.message"] = "Copied " + st.session_state[KP + "chat_label"]

    def load_chat():
        banner("Load Chat")
        filename = st.session_state[KP + "appuser_data_metadata"].get(st.session_state[KP + "load_chat"])
        print("Load Chat::Filename:", filename, "Label:", st.session_state[KP + "load_chat"])
        st.session_state[KP + "chat_label"] = st.session_state[KP + "load_chat"]
        st.session_state[KP + "chat_store"] = filename
        jobj = json.loads(open(filename, "r").read())
        if isinstance(jobj, list):
            # Original Chat
            st.session_state[KP + 'wset'] = jobj
            _vdel(KP + 'loaded_object')
        else:
            st.session_state[KP + 'loaded_object'] = jobj
            st.session_state[KP + 'wset'] = jobj["conversation"]
            if "metadata" in jobj and "metatags" in jobj["metadata"]:
                for key in st.session_state:
                    if key.startswith(KP + "cmptask_"):
                        if st.session_state[key] in jobj["metadata"]["metatags"]:
                            st.session_state[key + "_done"] = jobj["metadata"]["metatags"][st.session_state[key]]

        st.session_state[KP + 'wset_changed'] = True
        _vdel(KP + 'add_context')
        if st.session_state[KP + 'wset'][0]["role"] == "context":
            st.session_state[KP + 'add_context'] = False
        st.session_state[KP + "model"] = ""
        for d in st.session_state[KP + 'wset']:
            if d['role'] != "robot":
                continue
            if 'model' in d:
                if d['model'] not in predict.get_models():
                    d['model'] = get_default_chat_model()
                    continue
                if d['model'] not in st.session_state[KP + "model"] and d['model']:
                    st.session_state[KP + "model"] = d['model']
            else:
                if get_default_chat_model() not in st.session_state[KP + "model"]:
                    st.session_state[KP + "model"] = get_default_chat_model()
        # print(KP+'wset', "Data after Load Data:", st.session_state[KP+'wset'])
        if not st.session_state[KP + "model"]:
            st.session_state[KP + "model"] = get_default_chat_model()
        # print("Loaded Models:", st.session_state[KP+"model"])
        # print("load_chat[wset]", st.session_state[KP + "wset"])

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

        chat_list = st.session_state[KP + "appuser_data_metadata"].get_labels()
        # Sorting Chat List
        st.sidebar.radio("Sort Chat List", ["Time", "Alphabet"], index=0, key=KP + "chat_list_sort", horizontal=True)
        if len(chat_list) > 2:
            if st.session_state[KP + "chat_list_sort"] == "Time":
                chat_list.reverse()
            else:
                chat_list.sort()
        # Create Chat Categories
        chat_displayname = {}
        chat_to_display = []
        for chat in chat_list:
            chat_file = st.session_state[KP + "appuser_data_metadata"].get(chat)
            if not os.path.isfile(chat_file):
                continue
            if KP + "token_count_none" not in st.session_state or not st.session_state[KP + "token_count_none"]:
                token_count = st.session_state[KP + "TokenCounter"].get_token_count(chat_file, rlhf_robot=True)
                chat_displayname[chat] = "[%s]" % token_count
            else:
                chat_displayname[chat] = ""
            if os.path.isfile(os.path.join(st.session_state[KP + "completed_dir"], os.path.basename(chat_file))):
                chat_displayname[chat] += "[CMP]"
            chat_displayname[chat] += " " + chat
            chat_to_display.append(chat)
        st.sidebar.selectbox("Load Chat", chat_to_display, key=KP + "load_chat",
                             format_func=lambda x: chat_displayname[x])
        if len(chat_to_display) > 0:
            left, right = st.sidebar.columns([1, 3])
            left.button("Load", on_click=load_chat)
            projects = get_visible_projects()
            projects.remove(st.session_state[KP + "loaded_project"])
            right.selectbox("Move", ["Move Chat to Project"] + projects, label_visibility="collapsed",
                            key=KP + "move_chat", on_change=move_chat)

    def show_model_box():
        st.sidebar.markdown("## Chat Models")
        if KP + "model" not in st.session_state:
            default_model = get_default_chat_model()
            # print("Default Model 1:", default_model)
        else:
            default_model = st.session_state[KP + "model"]
            # print("Default Model 2:", default_model)
        for chat_turn in st.session_state[KP + 'wset']:
            if chat_turn['role'] == 'robot':
                if 'model' in chat_turn:
                    if chat_turn['model'] in predict.get_models():
                        default_model = chat_turn['model']
                        break
        available_models = predict.get_model_names()
        st.session_state[KP + "model"] = default_model
        # print("Available Models:", available_models)
        # print("Default Models:", default_model)
        st.sidebar.selectbox("## Choose Other Model", options=available_models, key=KP + "OtherModel",
                             index=available_models.index(default_model), on_change=add_other_model)
        # print("Model:", st.session_state[KP + "model"])
        label = ":blue[%s]" % (st.session_state[KP + "model"])
        st.sidebar.markdown(label)

    st.sidebar.button(":heavy_plus_sign: New Chat", on_click=chat_new)
    if st.session_state[KP + "chat_label"] != '':
        st.sidebar.text_input("Chat Label", key=KP + "chat_new_label", value=st.session_state[KP + "chat_label"],
                              on_change=save_labelchange)
        if KP + "current_chat_token_count" in st.session_state:
            st.sidebar.write("Token Count: **%s**" % st.session_state[KP + "current_chat_token_count"])
        left, right = st.sidebar.columns([1, 2])
        left.button("Copy Chat", key=KP + "copy_chat", on_click=save_chat_copy)
        right.selectbox("User", options=get_approved_labellers(), key=KP + "copy_chat_to_user",
                        label_visibility="collapsed")
        if KP + "copy_chat.message" in st.session_state:
            st.sidebar.info(st.session_state[KP + "copy_chat.message"])
            del st.session_state[KP + "copy_chat.message"]

    show_load_chat_box()
    show_model_box()


def clean_project_space():
    # delete transient project entries
    for entry in ["context_folders", "select_context_label", "allow_context_label_entry",
                  "context_none", "reference_chat", "tag_buttons", "tag_hide", "approved_labellers",
                  "default_chat_model", "token_count_none", "chat_display_mode", "print_model_input_output",
                  "suggested_chat_label", "add_context", "contexts", "no_manual_add_context_button",
                  "loaded_context_folders", "model", "tags", "loaded_object", "add_agent_message_swap_button",
                  "add_agent_duo_regenerate_button"]:
        _vdel(KP + entry)
    # Starts with project entries
    for key in st.session_state:
        for entry in ["tags_", "cmptask_"]:
            if key.startswith(KP + entry):
                _vdel(key)
    # Ends with project entries
    for key in st.session_state:
        for entry in ["_json.errors", "_json.success", "_yaml.errors", "_yaml.success"]:
            if key.endswith(entry):
                _vdel(key)


def load_global_config():
    for key in st.session_state[KP + "config_loaded"]["GLOBAL"]:
        st.session_state[KP + key] = st.session_state[KP + "config_loaded"]["GLOBAL"][key]


def load_selected_project(project):
    print("\nLoading selected Project:", project)
    for key in st.session_state[KP + "config_loaded"][project]:
        # print(KP + key, '=', st.session_state[KP + "config_loaded"][project][key])
        st.session_state[KP + key] = st.session_state[KP + "config_loaded"][project][key]
    st.session_state[KP + "model"] = get_default_chat_model()
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
            st.session_state[KP + "ACL"] = {}
            for acl, value in st.session_state[KP + "config_loaded"][key].items():
                st.session_state[KP + "ACL"][acl] = value.split(",")


def load_config():
    if KP + "config_loaded_checksum" in st.session_state and common.get_file_checksum(
            st.session_state[KP + "config"]) == st.session_state[KP + "config_loaded_checksum"]:
        return
    # dump_session_state("Loading Config")
    st.session_state[KP + "config_loaded"] = common.get_config_as_dict(st.session_state[KP + "config"])
    st.session_state[KP + "config_loaded_checksum"] = common.get_file_checksum(st.session_state[KP + "config"])
    load_global_config()
    load_acls()
    load_project()


def project_change():
    if KP + "userselect_project" in st.session_state and st.session_state[KP + "loaded_project"] != st.session_state[
        KP + "userselect_project"]:
        load_project()
        # dump_session_state("Project Change")


def rlhf():
    load_config()
    project_change()
    sidebar_user_box()
    # dump_session_state("Start of WORK")
    if _vcheck(KP + "page", KP + "show_documentation"):
        show_documentation()
        return
    if _vcheck(KP + "page", KP + "show_dashboard"):
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
    rlhf()
