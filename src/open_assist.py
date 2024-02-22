#!/usr/bin/env python3

"""
This tool allows data investigation
"""
import os
import json
import copy
import streamlit as st
import src.predict as predict
from datasets import load_dataset



def load_labelling_schema():
    return json.loads(open("resources/labeling_schema.json", "r").read())


# Key Prefix
KP = "open_assist."


def predict_dialog(turns):
    # truns -> [{}, {}, {role: "", content: ""}]
    turns[-1]['content'] = '\n'.join([t['content'] for t in turns])
    prompt_string = ""

    for turn in turns[:-1]:
        prompt_string += turn["content"] + "<|endoftext|>"

    prediction = predict(
        model="Pythia-12B-Oassit-sft4",
        prompt=prompt_string,
        max_new_tokens=250,
        temperature=0.3,
        num_beams=1,
        no_repeat_ngram_size=25,
        do_sample=True,
        chat=True
    )

    prediction = prediction.replace("<|endoftext|>", "")
    turns[-1]["content"] = prediction
    return turns


def gen_message(idx):
    cur = st.session_state[KP+'crow']
    dialogs = []
    for i in range(idx):
        dialogs.append(st.session_state[KP+'wset'][cur][i])
    dialogs.append({'role': st.session_state[KP+'wset'][cur][idx]['role'], 'content': ''})
    turns = predict_dialog(dialogs)
    st.session_state[KP+'wset'][cur][idx]['content'] = turns[-1]['content']


def read_file(file_name):
    script = ''
    with open(file_name) as fh:
        script += fh.read()
    return script


def get_dir(mark):
    global_home = st.session_state['global.data_home']
    app = st.session_state['global.APP_SELECTED']
    name = st.session_state[KP+'name']
    return "%s/%s/%s/%s" % (global_home, app, mark, name)


def create_dir(dir):
    # print("Creating Dir", dir)
    os.makedirs(dir, exist_ok=True)


def get_marked_filename(mark, cur=-1):
    if cur == -1:
        cur = st.session_state[KP+'crow']
    return "%s/%s_%s.json" % (get_dir(mark), st.session_state[KP+'datatype'], cur)


def save_marked(mark, cur=-1):
    if cur == -1:
        cur = st.session_state[KP+'crow']
    create_dir(get_dir(mark))
    json.dump(st.session_state[KP+'wset'][cur], open(get_marked_filename(mark), 'w'))
    json.dump(st.session_state[KP+'prompt_sub_category'],
              open(get_marked_filename(mark).replace(".json", "_meta.json"), 'w'))


def remove_marked(mark):
    saved_filename = get_marked_filename(mark)
    if os.path.exists(saved_filename):
        os.remove(saved_filename)

    saved_filename = saved_filename.replace(".json", "_meta.json")
    if os.path.exists(saved_filename):
        os.remove(saved_filename)


def exist_marked(mark):
    return os.path.exists(get_marked_filename(mark))


def get_labelled_filename():
    return get_marked_filename(st.session_state[KP+'labelled_dir'])


def save_labelled():
    save_marked(st.session_state[KP+'labelled_dir'])


def remove_labelled():
    remove_marked(st.session_state[KP+'labelled_dir'])


def exist_labelled():
    return exist_marked(st.session_state[KP+'labelled_dir'])


def get_rejected_filename():
    return get_marked_filename(st.session_state[KP+'rejected_dir'])


def save_rejected():
    save_marked(st.session_state[KP+'rejected_dir'])


def remove_rejected():
    remove_marked(st.session_state[KP+'rejected_dir'])


def exist_rejected():
    return exist_marked(st.session_state[KP+'rejected_dir'])


def resetrow_callback():
    cur = st.session_state[KP+'crow']
    st.session_state[KP+'wset'][cur] = []
    for d in st.session_state[KP+'wset_org'][cur]:
        st.session_state[KP+'wset'][cur].append(d)
    remove_labelled()
    remove_rejected()


def prev_callback():
    if st.session_state[KP+'crow'] > 0:
        st.session_state[KP+'crow'] -= 1


def next_callback():
    if st.session_state[KP+'crow'] < len(st.session_state[KP+'wset']) - 1:
        st.session_state[KP+'crow'] += 1


def update_role(idx, role):
    cur = st.session_state[KP+'crow']
    st.session_state[KP+'wset'][cur][idx]['role'] = role


def update_chat(idx, key):
    cur = st.session_state[KP+'crow']
    st.session_state[KP+'wset'][cur][idx]['content'] = st.session_state[key]


def delete_item(idx):
    cur = st.session_state[KP+'crow']
    del st.session_state[KP+'wset'][cur][idx]


def add_item(idx, role):
    cur = st.session_state[KP+'crow']
    st.session_state[KP+'wset'][cur].insert(idx + 1, {'role': role, 'content': ""})


def add_new_row_callback():
    st.session_state[KP+'wset'].append([{'role': "user", 'content': "Brand New Chat"}])
    st.session_state[KP+'crow'] = len(st.session_state[KP+'wset']) - 1


def make_context(idx, role):
    cur = st.session_state[KP+'crow']
    # for i in range(idx):
    #     del st.session_state[KP+'wset'][cur][0]
    st.session_state[KP+'wset'][cur][idx]['role'] = "context"


def move_up(idx):
    cur = st.session_state[KP+'crow']
    st.session_state[KP+'wset'][cur].insert(idx - 1, st.session_state[KP+'wset'][cur].pop(idx))


def move_down(idx):
    cur = st.session_state[KP+'crow']
    st.session_state[KP+'wset'][cur].insert(idx + 1, st.session_state[KP+'wset'][cur].pop(idx))


def chat_box(idx, role, message, is_user):
    cur = st.session_state[KP+'crow']
    col1, col2 = st.columns(2)
    height = int(len(message) / 3)
    if role == "context":
        st.text_area(":cop:", value=message, height=height, key=KP+str(idx) + 'tx0',
                     on_change=update_chat, args=(idx, KP+str(idx) + 'tx0'))
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.button(":x:", on_click=delete_item, args=(idx,), key=KP+str(idx) + 'c1')
        c2.button(":heavy_plus_sign:", on_click=add_item, args=(idx, role,), key=KP+str(idx) + 'c2')
        c3.button(":male-technologist:", on_click=update_role, args=(idx, "assistant",), key=KP+str(idx) + 'c3')
        if idx > 0:
            c4.button(":arrow_up:", on_click=move_up, args=(idx,), key=KP+str(idx) + 'c4')
        if idx < len(st.session_state[KP+'wset'][cur]) - 1:
            c5.button(":arrow_down:", on_click=move_down, args=(idx,), key=KP+str(idx) + 'c5')
        c6.button(":man:", on_click=update_role, args=(idx, "user",), key=KP+str(idx) + 'c6')
        if idx > 0:
            c7.button(":robot_face:", on_click=gen_message, args=(idx,), key=KP+str(idx) + 'c7')
    elif is_user:
        col1.text_area(":man:", value=message, height=height, key=KP+str(idx) + 'tx1',
                       on_change=update_chat, args=(idx, KP+str(idx) + 'tx1'))
        c1, c2, c3, c4, c5, c6, c7 = col1.columns(7)
        c1.button(":x:", on_click=delete_item, args=(idx,), key=KP+str(idx) + 'c1')
        c2.button(":heavy_plus_sign:", on_click=add_item, args=(idx, role,), key=KP+str(idx) + 'c2')
        c3.button(":crown:", on_click=make_context, args=(idx, role,), key=KP+str(idx) + 'c3')
        if idx > 0:
            c4.button(":arrow_up:", on_click=move_up, args=(idx,), key=KP+str(idx) + 'c4')
        if idx < len(st.session_state[KP+'wset'][cur]) - 1:
            c5.button(":arrow_down:", on_click=move_down, args=(idx,), key=KP+str(idx) + 'c5')
        c6.button(":male-technologist:", on_click=update_role, args=(idx, "assistant",), key=KP+str(idx) + 'c6')
        if idx > 0:
            c7.button(":robot_face:", on_click=gen_message, args=(idx,), key=KP+str(idx) + 'c7')
    else:
        col2.text_area(":male-technologist:", value=message, height=height, key=KP+str(idx) + 'tx2',
                       on_change=update_chat, args=(idx, KP+str(idx) + 'tx2'))
        c1, c2, c3, c4, c5, c6, c7 = col2.columns(7)
        c1.button(":x:", on_click=delete_item, args=(idx,), key=KP+str(idx) + 'c1')
        c2.button(":heavy_plus_sign:", on_click=add_item, args=(idx, role,), key=KP+str(idx) + 'c2')
        c3.button(":crown:", on_click=make_context, args=(idx, role,), key=KP+str(idx) + 'c3')
        if idx > 0:
            c4.button(":arrow_up:", on_click=move_up, args=(idx,), key=KP+str(idx) + 'c4')
        if idx < len(st.session_state[KP+'wset'][cur]) - 1:
            c5.button(":arrow_down:", on_click=move_down, args=(idx,), key=KP+str(idx) + 'c5')
        c6.button(":man:", on_click=update_role, args=(idx, "user",), key=KP+str(idx) + 'c6')
        if idx > 0:
            c7.button(":robot_face:", on_click=gen_message, args=(idx,), key=KP+str(idx) + 'c7')


def show_chat():
    cur = st.session_state[KP+'crow']
    first_role = "user"
    for i, d in enumerate(st.session_state[KP+'wset'][cur]):
        chat_box(i, d['role'], d['content'], first_role == d['role'])


def show_upper_bar():
    scol1, scol2 = st.columns(2)
    scol1.button('Factory Reset this Chat', on_click=resetrow_callback)
    scol2.button(':latin_cross:', on_click=add_new_row_callback)
    st.divider()
    col1, colx, col2 = st.columns(3)
    col1.button('Prev', use_container_width=True, on_click=prev_callback)
    col2.button('Next', use_container_width=True, on_click=next_callback)
    st.session_state[KP+'prow'] = st.session_state[KP+'crow']
    srow = colx.selectbox("Select", range(len(st.session_state[KP+'wset'])),
                          index=st.session_state[KP+'crow'], label_visibility="collapsed")
    if srow != st.session_state[KP+'prow']:
        st.session_state[KP+'crow'] = srow


def show_middle_bar():
    if exist_labelled():
        st.header(":white_check_mark: :green[Labelled]")
    if exist_rejected():
        st.header(":x: :red[Rejected]")
    show_chat()


def show_lower_bar():
    col1, colx, col2 = st.columns(3)
    if col1.button("Finalize", use_container_width=True):
        save_labelled()
        remove_rejected()
        st.experimental_rerun()
    if col2.button("Reject", use_container_width=True):
        remove_labelled()
        save_rejected()
        st.experimental_rerun()


def display_page():
    show_upper_bar()
    show_middle_bar()
    show_lower_bar()


def load_data():
    cache_dir = st.session_state["global.cache_dir"]
    create_dir(cache_dir)
    st.session_state[KP+'dset'] = load_dataset("HuggingFaceH4/oasst1_en", cache_dir=cache_dir)
    print("Loading Dataset", type(st.session_state[KP+'dset']))


def create_workset(recreate=False):
    if KP+'wset' in st.session_state and recreate == False:
        return
    print("Creating Working Set using", st.session_state[KP+'datatype'], "for", st.session_state[KP+'name'])

    # Create a working set
    st.session_state[KP+'wset'] = []
    for d in st.session_state[KP+'dset'][st.session_state[KP+'datatype']]['messages']:
        st.session_state[KP+'wset'].append(d)

    for lf in os.listdir(get_dir(st.session_state[KP+'labelled_dir'])):
        if not lf.startswith(st.session_state[KP+'datatype']):
            continue
        labelled_filename = os.path.join(get_dir(st.session_state[KP+'labelled_dir']), lf)
        if lf.endswith("_meta.json"):
            st.session_state[KP+'prompt_sub_category'] = json.loads(read_file(labelled_filename))
            continue
        try:
            num = int(lf.split('.')[0].split('_')[-1])
        except:
            continue
        if num < len(st.session_state[KP+'wset']):
            st.session_state[KP+'wset'][num] = json.loads(read_file(labelled_filename))
        else:
            for i in range(len(st.session_state[KP+'wset']), num):
                add_new_row_callback()
            st.session_state[KP+'wset'].append(json.loads(read_file(labelled_filename)))
    for rf in os.listdir(get_dir(st.session_state[KP+'rejected_dir'])):
        if not rf.startswith(st.session_state[KP+'datatype']):
            continue
        if rf.endswith("_meta.json"):
            continue
        num = int(rf.split('.')[0].split('_')[1])
        rejected_filename = os.path.join(get_dir(st.session_state[KP+'rejected_dir']), rf)
        if num < len(st.session_state[KP+'wset']):
            st.session_state[KP+'wset'][num] = json.loads(read_file(rejected_filename))
        else:
            for i in range(len(st.session_state[KP+'wset']), num):
                add_new_row_callback()
            st.session_state[KP+'wset'].append(json.loads(read_file(rejected_filename)))
    st.session_state[KP+'wset_org'] = copy.deepcopy(st.session_state[KP+'wset'])
    st.session_state[KP+'crow'] = 0


def get_sub_categories():
    labeling_schema = load_labelling_schema()
    categories = list(labeling_schema.keys())

    if len(categories) == 1 and categories[0] == "N/A":
        return []

    sub_categories = []

    for cat in categories:
        if cat == "N/A":
            continue

        for sub_cat in labeling_schema[cat]:
            sub_categories.append("{} -> {}".format(cat, sub_cat))

    return sub_categories


def set_default_generation_params():
    st.session_state[KP+"max_new_tokens"] = 300
    st.session_state[KP+"temperature"] = 0.7
    st.session_state[KP+"num_beams"] = 1
    st.session_state[KP+"no_repeat_ngram_size"] = 50
    st.session_state[KP+"do_sample"] = True


def show_generation_params():
    # Set parameters for the editor
    st.sidebar.text_input("max_new_tokens", "128", key=KP+"max_new_tokens")

    # Set model temperature
    st.sidebar.text_input("temperature", "0.3", key=KP+"temperature")

    # Enter num beams
    st.sidebar.text_input("num_beams", "1", key=KP+"num_beams")

    # Enter no repeat n-gram size
    st.sidebar.text_input("no_repeat_ngram_size", "50", key=KP+"no_repeat_ngram_size")

    # Enter do sample
    st.sidebar.selectbox("do_sample", [True, False], key=KP+"do_sample")


def get_num_tokens():
    if KP+'crow' not in st.session_state:
        return ""

    cur = st.session_state[KP+'crow']
    dialog = ""

    for turn in st.session_state[KP+'wset'][cur]:
        if 'content' in turn:
            dialog += turn["content"]

    num_tokens = len(dialog.split(" "))
    return num_tokens


def init():
    st.session_state[KP+'labelled_dir'] = "labelled"
    st.session_state[KP+'rejected_dir'] = "rejected"
    st.session_state[KP+'category'] = []
    create_dir(get_dir(st.session_state[KP+'labelled_dir']))
    create_dir(get_dir(st.session_state[KP+'rejected_dir']))


def datatype_callback(datatype):
    st.session_state[KP+'crow'] = 0
    st.session_state[KP+'datatype'] = datatype
    init()
    create_workset()


def name_changed():
    if KP+'datatype' not in st.session_state:
        return
    print("Name Changed. Recreating... for", st.session_state[KP+"name"])
    del st.session_state[KP+'datatype']


def name_changed():
    if KP+'datatype' not in st.session_state:
        return
    print("Name Changed. Recreating... for", st.session_state[KP+"name"])
    del st.session_state[KP+'datatype']


def open_assist():
    st.sidebar.divider()

    st.sidebar.markdown("## Labeling config")

    st.sidebar.selectbox("labeler", ['Viktoriya', 'Ranjani', 'Simon', 'Srini', 'Sathwik', 'Partha', 'Govind', 'Toby', 'Ross'],
                         key=KP+'name', on_change=name_changed)

    st.sidebar.multiselect("prompt sub category", get_sub_categories(), key=KP+"prompt_sub_category")

    st.sidebar.text_input("Conversation word count", "{} words".format(get_num_tokens()))

    st.sidebar.divider()

    st.sidebar.markdown("## Model generation params")

    set_default_generation_params()

    show_params = st.sidebar.selectbox("Show generation options", [False, True])

    if show_params:
        show_generation_params()

    if KP+'dset' not in st.session_state:
        load_data()

    if KP+'datatype' not in st.session_state:
        st.header("Select DataType")
        datatype = st.selectbox("DataTypes:", list(st.session_state[KP+'dset'].keys()))
        st.button("Submit", on_click=lambda: datatype_callback(datatype))
    else:
        st.header(st.session_state[KP+'name'])
        display_page()


if __name__ == '__main__':
    open_assist()
