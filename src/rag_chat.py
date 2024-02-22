import sys
sys.path.append("/Users/toby.liang/dev/atg_platform_streamlit")

import random
import os
import json
import csv
from datetime import datetime
import streamlit as st
import streamlit_scrollable_textbox as stx
import time
# from src.predict import MODELS
from src.predict import predict
from src.now_llm_qa import QA, DEFAULT_DOCS
import getpass


KP = "rag_chat."
IS_PROD = True if os.getcwd() == '/' else False


APP_DIR = "rag_chat"
APP_METADATA = "metadata.json"
# Set CONTENT_HOP_COUNT_FOR_DISPLAY = 0 for word by word printing
CONTENT_HOP_COUNT_FOR_DISPLAY = 5
MAX_NUMBER_OF_QUESTIONS_ALLOWED = 20
# Key Prefix

if IS_PROD:
    USER_DETAILS_CSV = "/mnt/core_llm_home/code/atg_platform_streamlit/resources/PatCaseyOrgEmailAddr.csv"
else:
    USER_DETAILS_CSV = "resources/PatCaseyOrgEmailAddr.csv"

# if KP+"trace_log" not in st.session_state:
#     st.session_state[KP+"trace_log"] = []
# trace_log = st.session_state[KP+"trace_log"]


def predict_dialog(turns, add_text="",user_name=""):
    # trace_log.append("%s %s" % (time.time(),"predict_dialog"))
    conv_stack = [t["content"] for t in turns[:-1]]
    #print("Conv Stack ======",conv_stack)
    # idx, pseudo_query = st.session_state[KP+"qa_helper"].fetch_docs(conv_stack)

    # prefix_dict = {"assistant": "<|agent|>", "user": "<|customer|>", "context": "<|system|>", "robot": "<|agent|>"}

    # truns -> [{}, {}, {role: "", content: ""}]
    turns[-1]['content'] = '\n'.join([t['content'] for t in turns])
    prompt_string = ""
    if add_text:
        model = "NOW_LLM_llama13b_v0_4_091223_targetonly_loss" #NOW_LLM_V0.2_12B"
        for turn in turns[:-1]:
            actor = ''
            if turn['role'] == 'user':
                actor = "CUSTOMER"
            elif turn['role'] == 'robot':
                actor = "AGENT"
            if actor:
                prompt_string = prompt_string + actor + ' : ' + turn["content"] + "\n\n"
        prompt_string = prompt_string + "\n\n\nSummarize the above conversation<|endoftext|>"
        prediction = predict(
            model=model,
            prompt=prompt_string,
            max_new_tokens=500,
            temperature=0.3,
            num_beams=1,
            no_repeat_ngram_size=30,
            do_sample=True,
            chat=True
        )
    else:
        model = "NOW_LLM_llama13b_v0_4_091223_targetonly_loss" #NOW_LLM_V0.2_15.5B_CHAT"
        prediction, search_query, docs,_ = st.session_state[KP+"qa_helper"].get_prediction(model, conv_stack,search_type='wiki')
        # print("Pred = ",len(st.session_state[KP+"qa_helper"].get_prediction(model, conv_stack)))
        # prediction = st.session_state[KP+"qa_helper"].get_prediction(model, conv_stack)
        # st.session_state[KP+"qa_helper"].prev_doc = doc_str
        # print("Update prev doc", st.session_state[KP+"qa_helper"].prev_doc)

    prediction = prediction.replace("<|endoftext|>", "")
    # pseudo_query = pseudo_query.replace("<|endoftext|>", "")
    turns[-1]["content"] = prediction
    turns[-1]["docs"] = docs
    turns[-1]["search_query"] = search_query
    return turns


def gen_message(idx, add_text=""):
    # trace_log.append("%s %s" % (time.time(), "gen_message"))
    dialogs = []
    for i in range(idx + 1):
        dialogs.append(st.session_state[KP+'wset'][i])
    turns = predict_dialog(dialogs, add_text, st.session_state[KP+"name"])
    st.session_state[KP+'llm_return_words'] = turns[-1]["content"].split(' ')
    st.session_state[KP+'wset'][idx]['content'] = ''
    # st.session_state[KP+'wset'][idx]['content'] = turns[-1]["content"]
    if 'docs' in turns[-1] and turns[-1]['docs']:
        st.session_state[KP + 'wset'][idx]['docs'] = turns[-1]['docs']
        if 'search_query' in turns[-1]:
            st.session_state[KP + 'wset'][idx-1]['docs'] = turns[-1]['search_query']


def update_chat(idx, key):
    # trace_log.append("%s %s" % (time.time(), "update_chat"))
    if st.session_state[key]:
        st.session_state[KP+'wset'][idx]['content'] = st.session_state[key]
        st.session_state[KP+'wset_changed'] = True


def update_role(idx, role):
    # trace_log.append("%s %s" % (time.time(), "update_role"))
    st.session_state[KP+'wset'][idx]['role'] = role


def make_context(idx, role):
    # trace_log.append("%s %s" % (time.time(), "make_context"))
    st.session_state[KP+'wset'][idx]['role'] = "context"


def vote(idx, v, vtag):
    # trace_log.append("%s %s" % (time.time(), "vote"))
    if vtag not in st.session_state[KP+'wset'][idx]:
        st.session_state[KP+'wset'][idx][vtag] = {'up': 0, 'dn': 0}
    if v > 0:
        st.session_state[KP+'wset'][idx][vtag]['up'] += v
        st.session_state[KP+'wset'][idx][vtag]['up'] = st.session_state[KP+'wset'][idx][vtag]['up'] % 2
        if st.session_state[KP+'wset'][idx][vtag]['up'] != 0:
            st.session_state[KP+'wset'][idx][vtag]['dn'] = 0
    else:
        st.session_state[KP+'wset'][idx][vtag]['dn'] -= v
        st.session_state[KP+'wset'][idx][vtag]['dn'] = st.session_state[KP+'wset'][idx][vtag]['dn'] % 2
        if st.session_state[KP+'wset'][idx][vtag]['dn'] != 0:
            st.session_state[KP+'wset'][idx][vtag]['up'] = 0


def display_vote(dis, idx, tag='', col1_msg=''):
    # trace_log.append("%s %s" % (time.time(), "display_vote"))
    col1, colv1, colv2 = dis.columns([10, 1, 1])
    vtag = 'vote_' + tag if tag else 'vote'
    up = st.session_state[KP+'wset'][idx][vtag]['up'] if vtag in st.session_state[KP+'wset'][idx] else 0
    dn = st.session_state[KP+'wset'][idx][vtag]['dn'] if vtag in st.session_state[KP+'wset'][idx] else 0
    colv1.button(':+1:' if up == 0 else ':heavy_check_mark:', key=KP+"up_vote_" + str(idx) + tag, on_click=vote,
                 args=(idx, 1, vtag,))
    colv2.button(':-1:' if dn == 0 else ':heavy_multiplication_x:', key=KP+"down_vote_" + str(idx) + tag, on_click=vote,
                 args=(idx, -1, vtag,))
    if col1_msg:
        col1.write(col1_msg)
    st.session_state[KP+'wset_changed'] = True


def display_chat(dis, message, role, idx):
    # trace_log.append("%s %s" % (time.time(), "display_chat"))
    if role == "context":
        dis.warning(message, icon="📌")
    elif role == "user":
        dis.success(message, icon="👨")
    elif role == "robot":
        dis.info(message, icon="👨‍💻")
        if KP+'llm_return_words' not in st.session_state:
            display_vote(dis, idx)
    else:
        dis.markdown(":pencil: SUMMARY: :blue[{}]".format(message))


def chat_box(idx, role, message, docs):
    # trace_log.append("%s %s" % (time.time(), "chat_box"))
    lines = message.split('\n')
    message = '\n\n'.join([line for line in lines])
    left, right = st.columns(2)
    display_chat(left, message, role, idx)
    with right:
        if docs and KP+'llm_return_words' not in st.session_state:
        # if docs:
            if role == "user":
                display_vote(st, idx, "docs", col1_msg="**Generated Search Query**:(:red[Experimental feature, might be incorrect])\n\n" + docs)
            else:
                if docs != DEFAULT_DOCS:
                    print("Non Default Docs", docs)
                    # stx.scrollableTextbox(docs.replace("DOCUMENTS", "Searched Document"),
                    #                       height=min(max(50, len(lines) * 30), 500),
                    #                       key=str(idx) + "_scrollableTextbox")
                    st.write("Answering using wikipedia")
                else:
                    st.write("Answering using parametric memory")

    st.divider()


def add_chat(role, content=""):
    # trace_log.append("%s %s" % (time.time(), "add_chat"))
    if content:
        if role == 'context':
            st.session_state[KP+'wset'].insert(0, {'role': role, 'content': content, 'docs': ''})
            st.session_state[KP+'add_context'] = False
        else:
            st.session_state[KP+'wset'].append({'role': role, 'content': content, 'docs': ''})
        st.session_state[KP+'wset_changed'] = True


def add_context():
    # trace_log.append("%s %s" % (time.time(), "add_context"))
    st.session_state[KP+'add_context'] = True


def add_summary():
    # trace_log.append("%s %s" % (time.time(), "add_summary"))
    st.session_state[KP+'request_summarize_chat'] = True


def regenerate():
    # trace_log.append("%s %s" % (time.time(), "regenerate"))
    last_row = len(st.session_state[KP+'wset']) - 1
    if st.session_state[KP+'wset'][last_row]['role'] == 'robot':
        gen_message(last_row)


def chat_end():
    # Compute Tokens
    tokens = 0
    # Number of chat back and forth
    tokens += len(st.session_state[KP+'wset'])
    for chat in st.session_state[KP+'wset']:
        # Number of chat votes
        if 'vote' in chat:
            tokens += 2
        # Number of docs votes
        if 'vote_docs' in chat:
            tokens += 2
        if chat['role'] == 'user' and len(chat['content']) > 40:
            tokens += len(chat['content'])
    st.session_state[KP + 'tokens'] = tokens
    st.session_state[KP + 'end_chat'] = True


def set_css(element, tag):
    st.markdown("""
        <style>
            %s {
                %s
            }
        </style>
        """ % (element, tag), unsafe_allow_html=True)


def middle_box():
    set_css("div[data-testid='stExpander'] div[role='button'] p", "font-size: 1.5rem;")
    # with st.expander(":red[**Click here to know how the demo works**]"):
    #     st.write("Video here")
    if KP+"name" not in st.session_state or st.session_state[KP+"name"] == "Anonymous":
        st.write("## :arrow_backward: **Please select your name**")
    else:
        st.markdown("## Hi " + st.session_state[KP+"name"])
    # trace_log.append("%s %s" % (time.time(), "middle_box"))
    for i, d in enumerate(st.session_state[KP + 'wset']):
        chat_box(i, d['role'], d['content'], d['docs'])


def input_box():
    # trace_log.append("%s %s" % (time.time(), "input_box"))
    col1, col2, colg, colv1, colv2 = st.columns([3, 3, 6, 1, 1])
    main_msg_key = "main_msg" + str(len(st.session_state[KP + 'wset']))
    if len(st.session_state[KP + 'wset']) > 0:
        col1.button("Regenerate Response", on_click=regenerate)
    num_questions = int(len(st.session_state[KP + 'wset']) / 2)
    if num_questions < MAX_NUMBER_OF_QUESTIONS_ALLOWED:
        st.text_input("%s of %s allowed questions" % (num_questions,
                                                      MAX_NUMBER_OF_QUESTIONS_ALLOWED),
                      key=KP + main_msg_key, value="")

        col1, col2, colg, colv1, colv2 = st.columns([3, 3, 6, 1, 1])
        col1.button("Enter", on_click=add_chat, args=("user", st.session_state[KP + main_msg_key],),
                    key=KP + "content_add_key")
    else:
        st.button("New Chat", on_click=chat_new, key="Chat_New" + str(MAX_NUMBER_OF_QUESTIONS_ALLOWED))


def congratulation_box():
    celebrations = {"balloons": st.balloons, "snow": st.snow}
    with st.spinner('Calculating your tokens...'):
        time.sleep(2)
    st.markdown('# :tada: Congratulations!!! %s :champagne:' % st.session_state[KP+"name"])
    celebrations[random.choice(list(celebrations.keys()))]()
    st.markdown('## You got ' + str(st.session_state[KP+'tokens']) + ' Tokens')
    st.markdown("".join([":beers:" * st.session_state[KP+'tokens']]))

    if not os.path.exists(st.session_state[KP + "tokens_file"]):
        with open(st.session_state[KP + "tokens_file"], 'w') as fh:
            fh.write("Name,Email,Tokens\n")
    with open(st.session_state[KP + "tokens_file"], 'a') as fh:
        fh.write("%s,%s,%s\n" % (st.session_state[KP+"name"],
                               st.session_state[KP+"userdetails"][st.session_state[KP+"name"]],
                               st.session_state[KP+'tokens']))
    st.button('Ok', on_click=init, args=(True, True))


def show_chat():
    # trace_log.append("%s %s" % (time.time(), "show_chat"))
    if KP+'end_chat' in st.session_state:
        congratulation_box()
    else:
        middle_box()
        input_box()


def save_labelchange():
    # trace_log.append("%s %s" % (time.time(), "save_labelchange"))
    if KP+'chat_name' not in st.session_state or st.session_state[KP+"chat_name"] == '':
        return
    st.session_state[KP+"appuser_data_metadata"][st.session_state[KP+"chat_name"]] = st.session_state[KP+
        "appuser_data_metadata"].pop(st.session_state[KP+"chat_label"])
    st.session_state[KP+"chat_label"] = st.session_state[KP+"chat_name"]
    # Update Metadata
    json.dump(st.session_state[KP+"appuser_data_metadata"],
              open(st.session_state[KP+"appuser_data_metadata_file"], 'w'))


def save_chat():
    # trace_log.append("%s %s" % (time.time(), "save_chat"))
    if len(st.session_state[KP+'wset']) < 1:
        return
    if st.session_state[KP+"chat_label"] == '':
        if len(st.session_state[KP+'wset'][0]['content']) > 30:
            st.session_state[KP+"chat_label"] = st.session_state[KP+'wset'][0]['content'][:30] + " >"
        else:
            st.session_state[KP+"chat_label"] = st.session_state[KP+'wset'][0]['content'] + " >"
        while st.session_state[KP+"chat_label"] in st.session_state[KP+"appuser_data_metadata"]:
            st.session_state[KP+"chat_label"] += '>'
    if st.session_state[KP+"chat_store"] == '':
        st.session_state[KP+'chat_store'] = os.path.join(st.session_state[KP+"appuser_data_home"],
                                                      datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p") +
                                                      "_" + st.session_state[KP+"name"] + ".json")
        st.session_state[KP+"appuser_data_metadata"][st.session_state[KP+"chat_label"]] = \
            st.session_state[KP+"chat_store"]

    # Update Data
    json.dump(st.session_state[KP+'wset'], open(st.session_state[KP+"chat_store"], 'w'))
    # Update Metadata
    json.dump(st.session_state[KP+"appuser_data_metadata"],
              open(st.session_state[KP+"appuser_data_metadata_file"], 'w'))


def load_chat():
    # trace_log.append("%s %s" % (time.time(), "load_chat"))
    filename = st.session_state[KP+"appuser_data_metadata"][st.session_state[KP+"load_chat"]]
    st.session_state[KP+"chat_name"] = st.session_state[KP+"load_chat"]
    st.session_state[KP+"chat_label"] = st.session_state[KP+"chat_name"]
    st.session_state[KP+"chat_store"] = filename
    st.session_state[KP+'wset'] = json.loads(open(filename, "r").read())
    st.session_state[KP+'wset_changed'] = True
    if KP+'add_context' in st.session_state:
        del st.session_state[KP+'add_context']
    if st.session_state[KP+'wset'][0]["role"] == "context":
        st.session_state[KP+'add_context'] = False
    for chat in st.session_state[KP+'wset']:
        if 'docs' not in chat:
            chat['docs'] = ""


def chat_new():
    # trace_log.append("%s %s" % (time.time(), "chat_new"))
    st.session_state[KP+'wset'] = []
    st.session_state[KP+'wset_changed'] = True
    st.session_state[KP+"chat_name"] = ""
    st.session_state[KP+"chat_label"] = ""
    st.session_state[KP+"chat_store"] = ""
    if KP+'add_context' in st.session_state:
        del st.session_state[KP+'add_context']


def load_users():
    if KP+"userdetails" not in st.session_state:
        st.session_state[KP + "userdetails"] = {}
        # print("Loading", USER_DETAILS_CSV)
        with open(USER_DETAILS_CSV, 'r') as theFile:
            for line in theFile.readlines():
                line = line.strip()
                if not line:
                    continue
                name, email = line.split(',')
                st.session_state[KP+"userdetails"][name] = email
        # print("Loaded", len(st.session_state[KP+"userdetails"].keys()), "Top 5",
        #       [st.session_state[KP+"userdetails"][k] for k in list(st.session_state[KP+"userdetails"].keys())[:5]])


def init(force=False, end=False):
    if KP+'wset' in st.session_state and not force:
        return
    # trace_log.append("%s %s" % (time.time(), "init"))
    st.session_state[KP+'wset'] = []
    st.session_state[KP+"chats"] = []
    st.session_state[KP+"chat_label"] = ""
    st.session_state[KP+"chat_name"] = ""
    st.session_state[KP+"chat_store"] = ""
    st.session_state[KP+"wset_changed"] = False
    if 'global.data_home' not in st.session_state:
        st.session_state['global.data_home'] = os.getcwd()
    st.session_state[KP+"app_data_home"] = os.path.join(st.session_state['global.data_home'], APP_DIR)

    if KP+"name" not in st.session_state or force:
        st.session_state[KP+'name'] = "Anonymous"

    if KP+"new_name" in st.session_state and not end:
        st.session_state[KP + 'name'] = st.session_state[KP + 'new_name']

    st.session_state[KP+"appuser_data_home"] = os.path.join(st.session_state[KP+'app_data_home'],
                                                            st.session_state[KP+'name'])
    st.session_state[KP + "tokens_file"] = os.path.join(st.session_state[KP + 'app_data_home'],
                                                        "tokens_info.csv")
    st.session_state[KP+"appuser_data_metadata_file"] = os.path.join(st.session_state[KP+'appuser_data_home'],
                                                                     APP_METADATA)

    if not os.path.exists(st.session_state[KP+"appuser_data_home"]):
        os.makedirs(st.session_state[KP+"appuser_data_home"], exist_ok=True)
    if os.path.exists(st.session_state[KP+"appuser_data_metadata_file"]):
        st.session_state[KP+"appuser_data_metadata"] = json.loads(
            open(st.session_state[KP+"appuser_data_metadata_file"], "r").read())
    else:
        st.session_state[KP+"appuser_data_metadata"] = {}
    if KP+"qa_helper" not in st.session_state:
        st.session_state[KP+"qa_helper"] = QA()
    for tag in [KP+'end_chat', KP+'tokens', KP+'llm_return_words', KP + 'llm_words_hops']:
        if tag in st.session_state:
            del st.session_state[tag]
    load_users()


def print_trace_logs():
    for t in st.session_state[KP+"trace_log"]:
        print(t)


def clear_trace_logs():
    st.session_state[KP + "trace_log"] = []


def show_sidebar():
    with st.sidebar:
        if KP+"usernames" not in st.session_state:
            st.session_state[KP+"usernames"] = ["Type your name"] + sorted(st.session_state[KP+"userdetails"].keys())
        st.markdown("# Name")
        st.selectbox("# Name:", st.session_state[KP+"usernames"], key=KP+"new_name", on_change=init,
                     args=(True,), label_visibility="collapsed",
                     index=st.session_state[KP+"usernames"].index(st.session_state[KP+"name"]) if st.session_state[KP+"name"] != "Anonymous" else 0)
        st.sidebar.text_input("Enter a password", type="password", key=KP + "password")
        
        if KP + 'end_chat' not in st.session_state:
            if len(st.session_state[KP + 'wset']) > 0:
                st.button("New Chat", on_click=chat_new)
            if st.session_state[KP + 'name'] != "Anonymous" and len(st.session_state[KP + 'wset']) > 0:
                st.button("End Session", on_click=chat_end)
        st.divider()


def rag_chat():
    # trace_log.append("%s %s" % (time.time(), "rag_chat"))
    word_printing = True if KP+'llm_return_words' in st.session_state else False
    init()
    if not word_printing:
        show_sidebar()
        if len(st.session_state[KP+'wset']) > 0 and st.session_state[KP+'wset'][-1]['role'] == 'user':
            add_chat("robot", "llm_output")
            gen_message(len(st.session_state[KP+'wset']) - 1)
            word_printing = True if KP + 'llm_return_words' in st.session_state else False
    if word_printing:
        if not st.session_state[KP + 'wset'][-1]['content']:
            st.session_state[KP + 'llm_words_hops'] = 1
            if 0 < CONTENT_HOP_COUNT_FOR_DISPLAY < len(st.session_state[KP + 'llm_return_words']):
                st.session_state[KP + 'llm_words_hops'] = \
                    int(len(st.session_state[KP + 'llm_return_words']) / CONTENT_HOP_COUNT_FOR_DISPLAY)
        word_display_num = min(st.session_state[KP + 'llm_words_hops'], len(st.session_state[KP + 'llm_return_words']))
        display_words = st.session_state[KP + 'llm_return_words'][:word_display_num]
        st.session_state[KP + 'llm_return_words'] = st.session_state[KP + 'llm_return_words'][word_display_num:]
        if st.session_state[KP + 'wset'][-1]['content']:
            st.session_state[KP + 'wset'][-1]['content'] += ' '
        st.session_state[KP + 'wset'][-1]['content'] += " ".join(display_words)
        if len(st.session_state[KP + 'llm_return_words']) == 0:
            del st.session_state[KP + 'llm_return_words']
            del st.session_state[KP + 'llm_words_hops']

    if KP+'request_summarize_chat' in st.session_state:
        lrow = len(st.session_state[KP+'wset']) - 1
        if st.session_state[KP+'wset'][lrow]['role'] != 'summary':
            add_chat("summary", "summary")
        gen_message(lrow, add_text="Summarize the above conversation")
        del st.session_state[KP+'request_summarize_chat']

    if st.session_state[KP+'wset_changed'] and not word_printing:
        st.session_state[KP+'wset_changed'] = False
        save_chat()
    show_chat()
    if word_printing:
        # trace_log.append("%s %s" % (time.time(), "sleep"))
        time.sleep(0.002)
        st.experimental_rerun()


if __name__ == '__main__':
    # trace_log.append("%s %s" % (time.time(), "main"))
    st.set_page_config(layout="wide")
    rag_chat()