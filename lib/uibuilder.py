import json
import streamlit as st
import os
import sys
import re
import importlib

KP = "uibuilder."


def display_session_state_vars(location):
    print('+' * 50, location)
    for key in sorted(st.session_state.keys()):
        if key in ["contexts", "predict.MODELS"]:
            continue
        print(key, "=", st.session_state[key])
    print('+' * 50)


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


def context_box(jobj):
    debug = True

    def init():
        if "context_box_init" in st.session_state:
            return
        st.session_state["context_box_init"] = True

    def context_add():
        if debug:
            print("context_box:Added Context")
        st.session_state['context_add'] = True

    def context_selected(context_key, contexts_key):
        if st.session_state['selected_context'] is not None:
            if debug:
                print("context_box:Selected Context")
            st.session_state[context_key] = st.session_state[contexts_key][
                st.session_state['selected_context']]
            st.session_state["context_done"] = True

    def add_chat(key):
        if debug:
            print("context_box:Added Context through add_chat")
        # st.session_state[context_key] = st.session_state['context_msg']
        if key in st.session_state and st.session_state[key]:
            st.session_state["context_done"] = True

    def context_back():
        if debug:
            print("context_box:Context Back")
        del st.session_state['context_add']

    print(jobj)
    init()
    if "context_done" in st.session_state:
        return
    if 'context_add' not in st.session_state:
        if "selection" in jobj and jobj["selection"] in st.session_state:
            left, right = st.columns(2)
            left.button("Add Context", on_click=context_add)
            if isinstance(st.session_state[jobj["selection"]], dict):
                right.selectbox("Select Context", options=[None] + list(st.session_state[jobj["selection"]].keys()),
                                key="selected_context", on_change=context_selected, args=(jobj["key"],
                                                                                               jobj["selection"]))
            else:
                right.selectbox("Select Context", options=[None] + st.session_state[jobj["selection"]],
                                key="selected_context", on_change=context_selected, args=(jobj["key"],
                                                                                          jobj["selection"]))
        else:
            st.button("Add Context", on_click=context_add)
    elif st.session_state['context_add']:
        st.text_area("Context", key=jobj["key"], on_change=add_chat, args=(jobj["key"],))
        st.button("Cancel", on_click=context_back, key="context_back")


def nowchat_box(jobj):
    def delete_item(wset, idx):
        if not wset.startswith(KP):
            wset = wset
        print("*** delete_item:", idx, wset)
        del st.session_state[wset][idx]

    def add_item(wset, idx, role, content_tag="", model=""):
        if not wset.startswith(KP):
            wset = wset
        if content_tag and not content_tag.startswith(KP):
            content_tag = content_tag
        content = ""
        if content_tag in st.session_state:
            content = st.session_state[content_tag]

        bag = {'role': role, 'content': content}
        print("*** Adding to wset:", bag)
        if idx == -1:
            print("Appending Bag")
            st.session_state[wset].append(bag)
        else:
            print("Inserting Bag")
            st.session_state[wset].insert(idx + 1, bag)
        if content_tag.endswith("user_prompt"):
            st.session_state["add_model_responses"] = True

    def move_up(wset, idx):
        if not wset.startswith(KP):
            wset = wset
        st.session_state[wset].insert(idx - 1, st.session_state[wset].pop(idx))

    def move_down(wset, idx):
        if not wset.startswith(KP):
            wset = wset
        st.session_state[wset].insert(idx + 1, st.session_state[wset].pop(idx))

    def update_item(wset, idx, role, content_tag="", model=""):
        if not wset.startswith(KP):
            wset = wset
        if content_tag and not content_tag.startswith(KP):
            content_tag = content_tag
        st.session_state[wset][idx]['role'] = role
        if content_tag:
            st.session_state[wset][idx]['content'] = st.session_state[content_tag]

    def display_chat(wset, idx, message, role, model="", readonly=False):
        role_map = {
            "context": {"icon": "📌", "label": "System", "non_editor_fn": st.warning},
            "user": {"icon": "👨", "label": "Customer", "non_editor_fn": st.success},
            "robot": {"icon": "👨‍💻", "label": "Agent", "non_editor_fn": st.info},
            "summary": {"icon": "📝", "label": "", "non_editor_fn": st.markdown, "format": "{0} SUMMARY: :blue[{1}]"}
        }
        if readonly:
            if "format" not in role_map[role]:
                role_map[role]["non_editor_fn"](message, icon=role_map[role]["icon"])
            else:
                role_map[role]["non_editor_fn"](role_map[role]["non_editor_fn"].format(role_map[role]["icon"], message))
            return
        label = ":%s[Agent (%s)]" % (get_model_text_color(model), model) if role == "robot" else role_map[role]["label"]
        st.text_area(label=label, value=message, on_change=update_item,
                     args=(wset, idx, role, label + str(idx) + role), key=label + str(idx) + role)
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.button(":x:", on_click=delete_item, args=(wset, idx,), key=str(idx) + 'c1')
        c2.button(":heavy_plus_sign:", on_click=add_item, args=(wset, idx, role,), key=str(idx) + 'c2')
        if idx > 0:
            c4.button(":arrow_up:", on_click=move_up, args=(wset, idx,), key=str(idx) + 'c4')
        if idx < len(st.session_state[wset]) - 1:
            c5.button(":arrow_down:", on_click=move_down, args=(wset, idx,), key=str(idx) + 'c5')
        print("*** Num Models=", len(st.session_state["models"]), "Role=", role, "Models:",
              st.session_state["models"])
        if len(st.session_state["models"]) < 2 and role in ["user", "robot"]:
            c6.button(":male-technologist:" if role == "user" else ":man:",
                      on_click=update_item, args=(wset, idx, "robot" if role == "user" else "user",),
                      key=str(idx) + 'c6')

    def get_model_text_color(model):
        markup_colors = ["blue", "orange", "green", "red", "violet"]
        if model not in st.session_state["models"]:
            st.session_state["models"].append(model)
        return markup_colors[st.session_state["models"].index(model) % len(markup_colors)]

    print("nowchat_box", jobj)
    if jobj["key"] in st.session_state:
        print("***NowBox start: wset=", st.session_state[jobj["key"]])
    else:
        print("***NowBox start: wset=Not Initialized")
    display_session_state_vars("Inside NowBox")
    if jobj["key"] not in st.session_state:
        st.session_state[jobj["key"]] = []
    # Context Added. Add it to the Top
    if "context_key" in jobj and jobj["context_key"] in st.session_state and st.session_state[
        jobj["context_key"]] is not None:
        t_output = jobj["key"]
        if len(st.session_state[t_output]) == 0 or st.session_state[t_output][0]['role'] != 'context':
            print("Adding Chat Context:", t_output)
            add_item(t_output, 0, "context", jobj["context_key"])
            del st.session_state[jobj["context_key"]]
    print("Chats", jobj["key"], ":", st.session_state[jobj["key"]])
    if st.session_state[jobj["key"]] is not None:
        for idx, chat_bite in enumerate(st.session_state[jobj["key"]]):
            display_chat(jobj["key"], idx, chat_bite['content'], chat_bite['role'],
                         model=chat_bite["model"] if "model" in chat_bite else "")
    if jobj["key"] in st.session_state:
        print("***NowBox end: wset=", st.session_state[jobj["key"]])
    else:
        print("***NowBox end: wset=Not Initialized")


def function_call(jobj):
    print(jobj)
    sys.path.append(os.getcwd())
    jparts = jobj["call"].split('.')
    if len(jparts) < 2:
        module = sys.modules[__name__]
    else:
        module = importlib.import_module(".".join(jparts[:-1]))
    func = getattr(module, jparts[-1])
    if "args" in jobj:
        return func(jobj["args"])
    else:
        return func()


def st_operation(fn, jobj):
    import inspect
    print("st_operation:", fn, "=>", jobj)
    func = getattr(st, fn.split(".")[1])
    sig = inspect.signature(func)
    print("+" * 40, fn)
    params = {}
    for fkey in sig.parameters:
        if fkey in jobj:
            if fkey in "key":
                params[fkey] = jobj[fkey]
            elif fkey in "options":
                if isinstance(jobj[fkey], str):
                    if jobj[fkey] in st.session_state:
                        params[fkey] = st.session_state[jobj[fkey]]
                    else:
                        params[fkey] = []
                else:
                    params[fkey] = jobj[fkey]
            elif jobj[fkey] in st.session_state:
                params[fkey] = st.session_state[jobj[fkey]]
            else:
                params[fkey] = jobj[fkey]
    print("Params:", params)
    func(**params)



operations = {
    "display_session_state_vars": display_session_state_vars,
    "context_box": context_box,
    "fn": function_call,
    "nowchat_box": nowchat_box
}


def uibuilder_work(ins_json_task):
    print("uibuilder_work(", ins_json_task, ")")
    for work_req in ins_json_task:
        print("Working On:", work_req)
        if work_req.startswith("st."):
            st_operation(work_req, ins_json_task[work_req])
        elif work_req in operations:
            print("Work Req:", work_req)
            print("Ins[Work Req]:", ins_json_task[work_req])
            output = operations[work_req](ins_json_task[work_req])
            print("Output:", output)
            if "key" in ins_json_task[work_req]:
                print("Key", ins_json_task[work_req]["key"], "value", output)
                if ins_json_task[work_req]["key"] not in st.session_state:
                    st.session_state[ins_json_task[work_req]["key"]] = output
            else:
                print("Key not there in", ins_json_task[work_req])
        else:
            print("***** No Such Work[%s]" % work_req)


def uibuilder(uijson):
    if isinstance(uijson, str):
        ins_json = json.loads(uijson)
    else:
        ins_json = uijson

    # Is requesting tabs
    if isinstance(ins_json, list):
        ins_json = ins_json[0]
        main_partitions = list(ins_json.keys())
        if "sidebar" in main_partitions:
            main_partitions.remove("sidebar")
        parts = st.tabs(main_partitions)
    else:
        main_partitions = list(ins_json.keys())
        if "sidebar" in main_partitions:
            main_partitions.remove("sidebar")
        parts = st.columns(len(main_partitions))

    for i, main in enumerate(main_partitions):
        print("Main Partition", i, ins_json[main])
        with parts[i]:
            for row_data in ins_json[main]:
                print("Main Partition", i, "Row", row_data)
                if isinstance(row_data, list):
                    print("Row Partition", row_data)
                    rows = st.columns(len(row_data))
                    for j, work in enumerate(row_data):
                        with rows[j]:
                            uibuilder_work(work)
                else:
                    print("No Row Partition", row_data)
                    uibuilder_work(row_data)
    if "sidebar" in ins_json:
        print("Sidebar", ins_json["sidebar"])
        with st.sidebar:
            for row_data in ins_json["sidebar"]:
                uibuilder_work(row_data)


def uiplay():
    def update_data():
        for line in st.session_state["data_input"].split('\n'):
            print("update_data:", line)
            print("update_data:", line.split(" "))
            key, operation, data_type, value = line.split(" ")
            if data_type == "json":
                value = json.loads(value)
            if operation == "append":
                st.session_state[key].append(value)

    if "json_input" in st.session_state and st.session_state["json_input"]:
        uibuilder(st.session_state["json_input"])
        st.session_state["json_input"] = st.session_state["json_input"]

    st.text_area("JSON:", key="json_input",
                 value=st.session_state["json_input"] if "json_input" in st.session_state else "",
                 height=400)
    st.text_area("Data:", key="data_input",
                 value="",
                 height=200, on_change=update_data)


if __name__ == '__main__':
    uiplay()
