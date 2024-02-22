import copy
import os
import json
import streamlit as st
import re
from src.now_llm_qa import QA, DEFAULT_DOCS

KP = "rag_labeller."

DATA_DIRS = [d for d in os.listdir('.') if os.path.isdir(d) and d.startswith("rag_chat_")]
APP_METADATA = "metadata.json"
APP_DIR="rag_labeller"
LABELLER_WORKSHEET = os.path.join(APP_DIR, "labeller_worksheet.json")


def load_datasets():
    datasets = st.session_state[KP+"APP_DIRS_SELECTED"]
    st.session_state[KP+"userdata"] = {}
    for dataset in datasets:
        datasetpath = os.path.join(st.session_state["global.data_home"], dataset)
        for user in os.listdir(datasetpath):
            if user != 'tokens_info.csv' and user != os.path.basename(LABELLER_WORKSHEET):
                upath = os.path.join(datasetpath, user)
                for file in os.listdir(upath):
                    if file != APP_METADATA and file.endswith(".json"):
                        fpath = os.path.join(upath, file)
                        st.session_state[KP+"userdata"][fpath] = json.loads(open(fpath, "r").read())
    filter_chatlist()


def load_chat():
    data = st.session_state[KP+'chatlist'][st.session_state[KP+"load_chat"]]
    st.session_state[KP+"chat_name"] = st.session_state[KP+"load_chat"]
    st.session_state[KP+"chat_label"] = st.session_state[KP+"chat_name"]
    st.session_state[KP+'wset'] = data
    st.session_state[KP+'wset_changed'] = True
    if KP+'add_context' in st.session_state:
        del st.session_state[KP+'add_context']
    if st.session_state[KP+'wset'][0]["role"] == "context":
        st.session_state[KP+'add_context'] = False
    for chat in st.session_state[KP+'wset']:
        if 'docs' not in chat:
            chat['docs'] = ""


def chat_new():
    st.session_state[KP+'wset'] = []
    st.session_state[KP+'wset_changed'] = True
    st.session_state[KP+"chat_name"] = ""
    st.session_state[KP+"chat_label"] = ""
    if KP+'add_context' in st.session_state:
        del st.session_state[KP+'add_context']


def find_in_chat(filter, chatlist):
    for chat in chatlist:
        # print(chat)
        if chat["role"] != "user":
            continue
        if re.search(filter, chat['content'], re.IGNORECASE):
            # print(filter, "Matched", re.search(filter, chat['content'], re.IGNORECASE), "::", chat['content'])
            return True
    return False


def filter_chatlist():
    chatfilter = ""
    if KP+"filter" in st.session_state:
        chatfilter = st.session_state[KP+"filter"].strip()

    if chatfilter:
        new_chatlist = {}
        for fpath in st.session_state[KP+'chatlist']:
            if find_in_chat(chatfilter, st.session_state[KP+'chatlist'][fpath]):
                # print("Adding",  st.session_state[KP+'chatlist'][fpath], "in", fpath)
                new_chatlist[fpath] = st.session_state[KP+'chatlist'][fpath]
        st.session_state[KP+'chatlist'] = new_chatlist
        st.session_state[KP+'chatlist_changed'] = True
    else:
        st.session_state[KP+'chatlist'] = copy.deepcopy(st.session_state[KP+"userdata"])
        st.session_state[KP+'chatlist_changed'] = True


def init():
    if KP+'init' in st.session_state:
        return
    st.session_state[KP+"init"] = True
    st.session_state[KP+'wset'] = []
    st.session_state[KP+"chats"] = []
    st.session_state[KP+"chat_label"] = ""
    st.session_state[KP+"chat_name"] = ""
    st.session_state[KP+"wset_changed"] = False
    if 'global.data_home' not in st.session_state:
        st.session_state['global.data_home'] = "./"
    st.session_state[KP+"app_data_home"] = os.path.join(st.session_state['global.data_home'], APP_DIR)
    # Load APP Data Users
    st.session_state[KP+'userdata'] = {}
    if os.path.exists(LABELLER_WORKSHEET):
        st.session_state[KP+'labeller_worksheet'] = json.loads(open(LABELLER_WORKSHEET, "r").read())
    else:
        st.session_state[KP+'labeller_worksheet'] = {}

    if KP+"qa_helper" not in st.session_state:
        st.session_state[KP+"qa_helper"] = QA()


def update_chat_with_generated_message(idx, turns):
    st.session_state[KP+'wset'][idx]['content'] = turns[-1]["content"]
    if 'docs' in turns[-1] and turns[-1]['docs']:
        if turns[-1]['docs'] != DEFAULT_DOCS:
            st.session_state[KP+'wset'][idx]['docs'] = "Answering using wikipedia"
        else:
            st.session_state[KP+'wset'][idx]['docs'] = "Answering using parametric memory"
        if 'search_query' in turns[-1]:
            st.session_state[KP+'wset'][idx - 1]['docs'] = turns[-1]['search_query']


def show_sidebar():
    with st.sidebar:
        st.markdown("# Select Datasets")
        st.multiselect("Datasets", DATA_DIRS, key=KP+"APP_DIRS_SELECTED", on_change=load_datasets)

        if KP+"chatlist" not in st.session_state:
            st.markdown("# :red[Select Datasets to Begin]")
            return
        st.markdown("# Filter Chats")
        st.sidebar.text_input("Filter", key=KP+"filter", on_change=filter_chatlist, label_visibility="collapsed")

        chat_list = sorted(list(st.session_state[KP+"chatlist"].keys()))
        if len(chat_list) < 1 and KP+"load_chat" in st.session_state:
            del st.session_state[KP+"load_chat"]
        if st.session_state[KP+"chatlist_changed"]:
            st.session_state[KP+"chatlist_changed"] = False
            if len(chat_list) > 0:
                st.session_state[KP+"load_chat"] = chat_list[0]
                load_chat()
            else:
                if KP+"load_chat" in st.session_state:
                    del st.session_state[KP+"load_chat"]
        st.markdown("# Load Chat (%s Chats)" % str(len(chat_list)))
        st.selectbox("Load Chat (%s Chats)" % str(len(chat_list)), chat_list , key=KP+"load_chat", on_change=load_chat,
                     label_visibility="collapsed")
        if st.session_state[KP+"load_chat"] in st.session_state[KP+'labeller_worksheet']:
            if st.session_state[KP+'labeller_worksheet'][st.session_state[KP+"load_chat"]] == "labelled":
                st.markdown("# :white_check_mark: :green[Labelled]")
            else:
                st.markdown("# :x: :red[Rejected]")

def save_chat():
    fpath = st.session_state[KP + "load_chat"]
    json.dump(st.session_state[KP + "wset"], open(fpath, 'w'))


def vote(idx, tag, v):
    # print(idx, st.session_state[KP+'wset'])
    if KP+tag not in st.session_state[KP+'wset'][idx]:
        st.session_state[KP+'wset'][idx][tag] = {'up': 0, 'dn': 0}
    if v > 0:
        st.session_state[KP+'wset'][idx][tag]['up'] += v
        st.session_state[KP+'wset'][idx][tag]['up'] = st.session_state[KP+'wset'][idx][tag]['up'] % 2
        if st.session_state[KP+'wset'][idx][tag]['up'] != 0:
            st.session_state[KP+'wset'][idx][tag]['dn'] = 0
    else:
        st.session_state[KP+'wset'][idx][tag]['dn'] -= v
        st.session_state[KP+'wset'][idx][tag]['dn'] = st.session_state[KP+'wset'][idx][tag]['dn'] % 2
        if st.session_state[KP+'wset'][idx][tag]['dn'] != 0:
            st.session_state[KP+'wset'][idx][tag]['up'] = 0
    save_chat()


def display_vote(idx):
    sections  = st.columns([1, 1, 1])
    col1, colv1, colv2 = sections[0].columns([12, 1, 1])
    up = st.session_state[KP+'wset'][idx]['vote']['up'] if 'vote' in st.session_state[KP+'wset'][idx] else 0
    dn = st.session_state[KP+'wset'][idx]['vote']['dn'] if 'vote' in st.session_state[KP+'wset'][idx] else 0
    colv1.button(':+1:' if up == 0 else '+'+str(up), key=KP+"up_vote_"+str(idx), on_click=vote, args=(idx, 'vote', 1,))
    colv2.button(':-1:' if dn == 0 else '-'+str(dn), key=KP+"down_vote_"+str(idx), on_click=vote, args=(idx, 'vote', -1,))
    col1, colv1, colv2 = sections[1].columns([12, 1, 1])
    up = st.session_state[KP+"wset"][idx]['vote_docs']['up'] if 'vote_docs' in st.session_state[KP+"wset"][idx] else 0
    dn = st.session_state[KP+"wset"][idx]['vote_docs']['dn'] if 'vote_docs' in st.session_state[KP+"wset"][idx] else 0
    colv1.button(':+1:' if up == 0 else '+'+str(up), key=KP+"up_vote_docs_"+str(idx), on_click=vote,
                 args=(idx, 'vote_docs', 1,))
    colv2.button(':-1:' if dn == 0 else '-'+str(dn), key=KP+"down_vote_docs_"+str(idx), on_click=vote,
                 args=(idx, 'vote_docs', -1,))


def update_chat(idx, field, key):
    st.session_state[KP+"wset"][idx][field] = st.session_state[key]
    save_chat()


def delete_chat(idx):
    del st.session_state[KP+'wset'][idx]


def role_chat(idx, new_role):
    st.session_state[KP+'wset'][idx]['role'] = new_role


def add_chat_box_edit_buttons(box, idx, chat_key):
    c = box.columns(6)
    c[0].button(":x:",key=chat_key+"c0", on_click=delete_chat, args=(idx,))
    # c[1].button(":heavy_plus_sign:",
    #             key=chat_key+"c1",
    #             on_click=lambda: st.session_state[KP+'wset'].insert(idx+1, {'role': st.session_state[KP+'wset'][idx]['role'], 'content': "", "docs":""}))
    c[2].button(":man:" if st.session_state[KP+"wset"][idx]["role"] != 'user' else ":robot_face:",
                key=chat_key+"c2",
                on_click=role_chat,
                args=(idx, 'robot' if st.session_state[KP+'wset'][idx]['role'] == 'user' else 'user',))
    
    
def chat_box(idx, chat):
    sections  = st.columns([1, 1, 1])

    if chat["role"] == 'user':
        sections[0].text_area(":man:", value=chat['content'], key=KP+str(idx)+'tx1',
                       on_change=update_chat, args=(idx, 'content', KP+str(idx)+'tx1'))
        add_chat_box_edit_buttons(sections[0], idx, KP+str(idx)+'tx1')
        if 'docs' in chat:
            sections[1].text_area(":man:", value=chat['docs'], key=KP+str(idx)+'tx2',
                           on_change=update_chat, args=(idx, 'docs', KP+str(idx)+'tx2'),
                           label_visibility="hidden")
    else:
        lines = chat['content'].split('\n')
        message = '\n\n'.join([line for line in lines])
        height = int(len(message) / 3)
        sections[0].text_area(":robot_face:", value=message, key=KP+str(idx)+'tx3',
                       on_change=update_chat, args=(idx, 'content', KP+str(idx)+'tx3'),
                       height=max(100, height))
        add_chat_box_edit_buttons(sections[0], idx, KP+str(idx)+'tx2')
        if 'docs' in chat:
            sections[1].text_area(":robot_face:", value=chat['docs'], key=KP+str(idx)+'tx4',
                            on_change=update_chat, args=(idx, 'docs', KP+str(idx)+'tx4'),
                            label_visibility="hidden")
    display_vote(idx)
    if "metadata" in chat:
        if "greeting" in chat["metadata"]:
            content, voteU, voteD = sections[2].columns([9, 1, 1])
            if chat["metadata"]["greeting"]:
                content.markdown(":green[greeting : True]")
            else:
                content.markdown(":red[greeting : False]")
            up = st.session_state[KP + 'wset'][idx]['vote_greeting']['up'] if 'vote_greeting' in st.session_state[KP + 'wset'][idx] else 0
            dn = st.session_state[KP + 'wset'][idx]['vote_greeting']['dn'] if 'vote_greeting' in st.session_state[KP + 'wset'][idx] else 0
            voteU.button(':+1:' if up == 0 else '+' + str(up), key=KP + "up_vote_greeting" + str(idx), on_click=vote,
                         args=(idx, 'vote_greeting', 1,))
            voteD.button(':-1:' if dn == 0 else '-' + str(dn), key=KP + "down_vote_greeting" + str(idx), on_click=vote,
                         args=(idx, 'vote_greeting', -1,))
        if "relevance" in chat["metadata"]:
            for ri, rel in enumerate(chat["metadata"]["relevance"]):
                content, voteU, voteD = sections[2].columns([9, 1, 1])
                with content.expander(":green[Relevant: %s]"%rel["document"][:40] if rel["relevant"] else ":red[Irrelevant: %s]"%rel["document"][:40]):
                    st.write(rel["document"])
                vkey = 'vote_relevance_' + str(ri)
                up = st.session_state[KP + 'wset'][idx][vkey]['up'] if vkey in st.session_state[KP + 'wset'][idx] else 0
                dn = st.session_state[KP + 'wset'][idx][vkey]['dn'] if vkey in st.session_state[KP + 'wset'][idx] else 0
                voteU.button(':+1:' if up == 0 else '+' + str(up), key=KP + "up_"+vkey + str(idx),
                             on_click=vote,
                             args=(idx, vkey, 1,))
                voteD.button(':-1:' if dn == 0 else '-' + str(dn), key=KP + "down_" + vkey + str(idx),
                             on_click=vote,
                             args=(idx, vkey, -1,))

def mark_chat(tag):
    if tag == "un":
        del st.session_state[KP+'labeller_worksheet'][st.session_state[KP+"load_chat"]]
    else:
        st.session_state[KP+'labeller_worksheet'][st.session_state[KP+"load_chat"]] = tag
    json.dump(st.session_state[KP+'labeller_worksheet'], open(LABELLER_WORKSHEET, 'w'))


def show_chat():
    if KP+"load_chat" not in st.session_state or st.session_state[KP+"load_chat"] is None:
        return
    chatpath_parts = st.session_state[KP+"load_chat"].split('/')
    st.markdown("Chat: "+chatpath_parts[-1])
    for i, d in enumerate(st.session_state[KP+'wset']):
        chat_box(i, d)

    # Labelled and Rejected/UnLabel and UnReject Buttons
    if st.session_state[KP+"wset"]:
        col1, col2, col3 = st.columns(3)
        if st.session_state[KP+"load_chat"] in st.session_state[KP+'labeller_worksheet']:
            cur_label = st.session_state[KP+'labeller_worksheet'][st.session_state[KP+"load_chat"]]
            if cur_label == "labelled":
                col1.button(":black[UnLabel]", on_click=mark_chat, args=("un",))
            if cur_label == "rejected":
                col1.button(":black[UnReject]", on_click=mark_chat, args=("un",))
        else:
            col1.button(":green[Labelled]", on_click=mark_chat, args=("labelled", ))
            col2.button(":red[Rejected]", on_click=mark_chat, args=("rejected", ))


def rag_labeller():
    init()
    show_sidebar()
    show_chat()


if __name__ == '__main__':
    st.set_page_config(layout="wide")
    rag_labeller()
