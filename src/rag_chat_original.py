import random
import os
import json
from datetime import datetime
import streamlit as st
import time
import src.predict as predict
from src.now_llm_qa import QA, DEFAULT_DOCS


KP = "rag_chat."

APP_DIR = "rag_chat"
APP_METADATA = "metadata.json"
# Set CONTENT_HOP_COUNT_FOR_DISPLAY = 0 for word by word printing
CONTENT_HOP_COUNT_FOR_DISPLAY = 5
MAX_NUMBER_OF_QUESTIONS_ALLOWED = 20
# Key Prefix

FLAG_SHOW_DOCS=1
FLAG_SHOW_TEXTBOXES=1
SEARCH_QUERY_START_MESSAGE=""


def predict_dialog(turns, add_text=""):
    conv_stack = [t["content"] for t in turns]
    if add_text:
        model = predict.get_default_summarization_model()
    else:
        model = predict.get_default_chat_model()
    # prefix_dict = {"user": "<|customer|>", "context": "<|system|>", "robot": "<|agent|>"}
    prefix_dict = predict.get_model_prompt_tags(model)
    st.session_state[KP+"qa_helper"].prefix_dict = prefix_dict
    turns[-1]['content'] = '\n'.join([t['content'] for t in turns])
    prompt_string = ""
    if add_text:
        for turn in turns[:-1]:
            actor = ''
            if turn['role'] == 'user':
                actor = "CUSTOMER"
            elif turn['role'] == 'robot':
                actor = "AGENT"
            if actor:
                prompt_string = prompt_string+actor+' : '+turn["content"]+"\n\n"
        prompt_string = prompt_string+"\n\n\nSummarize the above conversation" + prefix_dict["end"]
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
    else:
        try:
            print("Rag Chat:Predict using Model:", model)
            print("Rag Chat:Predict conversations:", conv_stack)
            prediction, search_query, docs, metadata = st.session_state[KP + "qa_helper"].get_prediction(model,
                                                                                                         conv_stack)
        except Exception as e:
            print("Exception:predict_dialog:", str(e))
        # prediction = st.session_state[KP+"qa_helper"].get_prediction(model, conv_stack)
        # st.session_state[KP+"qa_helper"].prev_doc = doc_str
        # print("Update prev doc", st.session_state[KP+"qa_helper"].prev_doc)

    prediction = prediction.replace("<|endoftext|>", "")
    # pseudo_query = pseudo_query.replace("<|endoftext|>", "")
    turns[-1]["content"] = prediction
    turns[-1]["docs"] = docs
    turns[-1]["search_query"] = search_query
    turns[-1]["metadata"] = metadata

    return turns


def gen_message(idx, user_ask="", add_text=""):
    # print("%s %s %s %s %s" % (time.time(), "gen_message", idx, user_ask, add_text))
    try:
        dialogs = []
        for i in range(idx+1):
            role = st.session_state[KP+'wset'][i]['role']
            content = st.session_state[KP+'wset'][i]['content']
            dialogs.append({'role': role, 'content': content})
        if user_ask:
            dialogs.append({'role':'user', 'content': user_ask})
        return predict_dialog(dialogs, add_text)
    except Exception as e:
        print("Gen Message Exception", str(e))
        return None


def update_chat(idx, key, in_docs=0):
    # print("Update Chat", key)
    if st.session_state[key]:
        if in_docs:
            # print("Docs Change", key, st.session_state[KP + 'wset'][idx]['docs'], " = ", st.session_state[key])
            st.session_state[KP + 'wset'][idx]['docs'] = st.session_state[key].replace(SEARCH_QUERY_START_MESSAGE, "")
        else:
            # print("Content Change", key, st.session_state[KP + 'wset'][idx]['content'], " = ", st.session_state[key])
            st.session_state[KP+'wset'][idx]['content'] = st.session_state[key]
        st.session_state[KP+'wset_changed'] = True


def update_role(idx, role):
    st.session_state[KP+'wset'][idx]['role'] = role


def make_context(idx, role):
    st.session_state[KP+'wset'][idx]['role'] = "context"


def vote(idx, v, vtag):
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
    col1, colv1, colv2 = dis.columns([10, 1, 1])
    vtag = 'vote_'+tag if tag else 'vote'
    up = st.session_state[KP+'wset'][idx][vtag]['up'] if vtag in st.session_state[KP+'wset'][idx] else 0
    dn = st.session_state[KP+'wset'][idx][vtag]['dn'] if vtag in st.session_state[KP+'wset'][idx] else 0
    colv1.button(':+1:' if up == 0 else ':heavy_check_mark:', key=KP+"up_vote_"+str(idx)+tag, on_click=vote,
                 args=(idx, 1, vtag,))
    colv2.button(':-1:' if dn == 0 else ':heavy_multiplication_x:', key=KP+"down_vote_"+str(idx)+tag, on_click=vote,
                 args=(idx, -1, vtag,))
    if col1_msg:
        if FLAG_SHOW_TEXTBOXES:
            col1.text_area(":book:", value=col1_msg, key=KP+"TB"+str(idx)+tag, on_change=update_chat,
                           args=(idx, KP+"TB"+str(idx)+tag, 1),)
        else:
            col1.write(col1_msg)
    st.session_state[KP+'wset_changed'] = True


def display_chat(dis, message, role, idx):
    if FLAG_SHOW_TEXTBOXES:
        if role == "user":
            dis.text_area(":man:", value=message, key=KP+"TB_User"+str(idx), on_change=update_chat,
                          args=(idx, KP+"TB_User"+str(idx),))
        else:
            dis.text_area(":male-technologist:", value=message, key=KP+"TB_Tech"+str(idx), on_change=update_chat,
                          args=(idx, KP+"TB_Tech"+str(idx),))
            if KP+'llm_return_words' not in st.session_state:
                display_vote(dis, idx)
    else:
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
    lines = message.split('\n')
    message = '\n\n'.join([line for line in lines])
    left, right = st.columns([2,1])
    display_chat(left, message, role, idx)
    with right:
        if docs and KP+'llm_return_words' not in st.session_state:
        # if docs:
            if role == "user":
                display_vote(st, idx, "docs", col1_msg=docs)
            else:
                display_vote(st, idx, "docs", col1_msg=docs)
    st.divider()


def add_chat(role, content=""):
    if content:
        if role == 'context':
            st.session_state[KP+'wset'].insert(0, {'role': role, 'content': content, 'docs': ''})
            st.session_state[KP+'add_context'] = False
        else:
            st.session_state[KP+'wset'].append({'role': role, 'content': content, 'docs': ''})
        st.session_state[KP+'wset_changed'] = True


def chat_input(key):
    # Do not allow inputs after the first enter
    if len(st.session_state[KP+"inputs"]) == 0:
        st.session_state[KP+"inputs"].append(st.session_state[key])


def add_context():
    st.session_state[KP+'add_context'] = True


def regenerate():
    last_row = len(st.session_state[KP+'wset']) - 1
    if st.session_state[KP+'wset'][last_row]['role'] == 'robot':
        turns = gen_message(last_row)
        update_chat_with_generated_message(turns)


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
    st.session_state[KP+'tokens'] = tokens
    st.session_state[KP+'end_chat'] = True


def set_css(element, tag):
    st.markdown("""
        <style>
            %s {
                %s
            }
        </style>
        """ % (element, tag), unsafe_allow_html=True)


def middle_box():
    # set_css("div[data-testid='stExpander'] div[role='button'] p", "font-size: 1.5rem;")
    # if st.button(":red[**Click here to see the video of how the demo works**]"):
    #     if KP+"video_loaded" not in st.session_state:
    #         video_file = open(HOME_DIR+'/resources/demo_video.mov', 'rb')
    #         st.session_state[KP+"video_bytes"] = video_file.read()
    #         st.session_state[KP+"video_loaded"] = 1
    #     st.video(st.session_state[KP+"video_bytes"])

    if KP+"name" not in st.session_state or st.session_state[KP+"name"] == "Anonymous":
        st.write("## :arrow_backward: **Please select your name**")
    else:
        st.markdown("## Hi "+st.session_state[KP+"name"])
    for i, d in enumerate(st.session_state[KP+'wset']):
        chat_box(i, d['role'], d['content'], d['docs'])


def input_box():
    word_printing = True if KP+'llm_return_words' in st.session_state else False
    if not word_printing:
        col1, col2, colg, colv1, colv2 = st.columns([3, 3, 6, 1, 1])
        main_msg_key = "main_msg"+str(len(st.session_state[KP+'wset']))
        if len(st.session_state[KP+'wset']) > 0:
            col1.button("Regenerate Response", on_click=regenerate)
        num_questions = int(len(st.session_state[KP+'wset']) / 2)
        if num_questions < MAX_NUMBER_OF_QUESTIONS_ALLOWED:
            st.session_state[KP+"inputs"] = []
            st.text_input("%s of %s allowed questions" % (num_questions, MAX_NUMBER_OF_QUESTIONS_ALLOWED),
                          key=KP+main_msg_key, value="", on_change=chat_input, args=(KP+main_msg_key,))
        else:
            st.button("New Chat", on_click=chat_new, key="Chat_New"+str(MAX_NUMBER_OF_QUESTIONS_ALLOWED))


def congratulation_box():
    celebrations = {"balloons": st.balloons, "snow": st.snow}
    with st.spinner('Calculating your tokens...'):
        time.sleep(2)
    st.markdown('# :tada: Congratulations!!! %s :champagne:' % st.session_state[KP+"name"])
    celebrations[random.choice(list(celebrations.keys()))]()
    st.markdown('## You got '+str(st.session_state[KP+'tokens'])+' Tokens')
    st.markdown("".join([":beers:" * st.session_state[KP+'tokens']]))

    if not os.path.exists(st.session_state[KP+"tokens_file"]):
        with open(st.session_state[KP+"tokens_file"], 'w') as fh:
            fh.write("Name,Email,Tokens\n")
    with open(st.session_state[KP+"tokens_file"], 'a') as fh:
        fh.write("%s,%s,%s\n" % (st.session_state[KP+"name"],
                               st.session_state[KP+"userdetails"][st.session_state[KP+"name"]],
                               st.session_state[KP+'tokens']))
    st.button('Ok', on_click=init, args=(True, True))


def show_chat():
    if KP+'end_chat' in st.session_state:
        congratulation_box()
    else:
        middle_box()
        input_box()


def save_labelchange():
    if KP+'chat_name' not in st.session_state or st.session_state[KP+"chat_name"] == '':
        return
    st.session_state[KP+"appuser_data_metadata"][st.session_state[KP+"chat_name"]] = st.session_state[KP+
        "appuser_data_metadata"].pop(st.session_state[KP+"chat_label"])
    st.session_state[KP+"chat_label"] = st.session_state[KP+"chat_name"]
    # Update Metadata
    json.dump(st.session_state[KP+"appuser_data_metadata"],
              open(st.session_state[KP+"appuser_data_metadata_file"], 'w'))


def save_chat():
    if len(st.session_state[KP+'wset']) < 1:
        return
    if st.session_state[KP+"chat_label"] == '':
        if len(st.session_state[KP+'wset'][0]['content']) > 30:
            st.session_state[KP+"chat_label"] = st.session_state[KP+'wset'][0]['content'][:30]+" >"
        else:
            st.session_state[KP+"chat_label"] = st.session_state[KP+'wset'][0]['content']+" >"
        while st.session_state[KP+"chat_label"] in st.session_state[KP+"appuser_data_metadata"]:
            st.session_state[KP+"chat_label"] += '>'
    if st.session_state[KP+"chat_store"] == '':
        st.session_state[KP+'chat_store'] = os.path.join(st.session_state[KP+"appuser_data_home"],
                                                      datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p") +
                                                      "_"+st.session_state[KP+"name"]+".json")
        st.session_state[KP+"appuser_data_metadata"][st.session_state[KP+"chat_label"]] = \
            st.session_state[KP+"chat_store"]

    # Update Data
    json.dump(st.session_state[KP+'wset'], open(st.session_state[KP+"chat_store"], 'w'))
    # Update Metadata
    json.dump(st.session_state[KP+"appuser_data_metadata"],
              open(st.session_state[KP+"appuser_data_metadata_file"], 'w'))


def load_chat():
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
    st.session_state[KP+'wset'] = []
    st.session_state[KP+'wset_changed'] = True
    st.session_state[KP+"chat_name"] = ""
    st.session_state[KP+"chat_label"] = ""
    st.session_state[KP+"chat_store"] = ""
    if KP+'add_context' in st.session_state:
        del st.session_state[KP+'add_context']


def load_users():
    if KP+"userdetails" not in st.session_state:
        st.session_state[KP+"userdetails"] = {}
        # print("Loading", USER_DETAILS_CSV)
        # with open(USER_DETAILS_CSV, 'r') as theFile:
        #     for line in theFile.readlines():
        #         line = line.strip()
        #         if not line:
        #             continue
        #         name, email = line.split(',')
        #         st.session_state[KP+"userdetails"][name] = email
        st.session_state[KP+"userdetails"]["Vasuki"] = "madiraju.vasuki@servicenow.com"
        st.session_state[KP+"userdetails"]["Alka"] = "alka.singh@servicenow.com"
        st.session_state[KP+"userdetails"]["Amit"] = "amit.srivastava2@servicenow.com"
        st.session_state[KP+"userdetails"]["Sampath"] = "sampath.talupula@servicenow.com"


def init(force=False, end=False):
    if KP+'wset' in st.session_state and not force:
        return
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
        st.session_state[KP+'name'] = st.session_state[KP+'new_name']

    st.session_state[KP+"appuser_data_home"] = os.path.join(st.session_state[KP+'app_data_home'],
                                                            st.session_state[KP+'name'])
    st.session_state[KP+"tokens_file"] = os.path.join(st.session_state[KP+'app_data_home'],
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
    for tag in [KP+'end_chat', KP+'tokens', KP+'llm_return_words', KP+'llm_words_hops']:
        if tag in st.session_state:
            del st.session_state[tag]
    st.session_state[KP+"inputs"] = []
    load_users()


def print_trace_logs():
    for t in st.session_state[KP+"trace_log"]:
        print(t)


def clear_trace_logs():
    st.session_state[KP+"trace_log"] = []


def show_sidebar():
    with st.sidebar:
        if KP+"usernames" not in st.session_state:
            st.session_state[KP+"usernames"] = ["Type your name"]+sorted(st.session_state[KP+"userdetails"].keys())
        st.markdown("# Name")
        st.selectbox("# Name:", st.session_state[KP+"usernames"], key=KP+"new_name", on_change=init,
                     args=(True,), label_visibility="collapsed",
                     index=st.session_state[KP+"usernames"].index(st.session_state[KP+"name"]) if st.session_state[KP+"name"] != "Anonymous" else 0)
        if KP+'end_chat' not in st.session_state:
            if len(st.session_state[KP+'wset']) > 0:
                st.button("New Chat", on_click=chat_new)
            if st.session_state[KP+'name'] != "Anonymous" and len(st.session_state[KP+'wset']) > 0:
                # st.info("Name:"+st.session_state[KP+'name'])
                st.button("End Session", on_click=chat_end)
        # st.divider()
    #     st.markdown("# FAQ")
    #     with st.expander(":green[**What is Now LLM?**]"):
    #         st.success("""
    #  - A Large Language Model like **GPT**
    #  - Built in-house by team Optimus (ATG)
    #  - **CAPABILITIES**:
    #    - Summarizes text
    #    - Answer questions
    #    - Email Writing
    #    - Story Writing
    #    - .... Much more
    # - It **DOES NOT**:
    #     - Have knowledge about ServiceNow and/or its employees
    #     - Its knowledge is limited to wikipedia and its parametric memory
    #     - It does not have knowledge about itself or its creators""")
    #     with st.expander(":yellow[**What is this experience about?**]"):
    #         st.warning("""
    #  - Grab a cup of coffee and chat with NOW-LLM 
    #  - NOW-LLM will use wikipedia to answer your questions
    #  - Ask it about Virat Kohli, the world war and more
    #  - HUMBLE REQUEST: 
    #     - Have meaningful and tricky conversations with NOW-LLM
    #     - Help us improve it and win prizes along the way!!""")
    #     with st.expander(":blue[**Help us and win prizes**]"):
    #         st.info("""
    #  - Help NOW-LLM learn from your feedback
    #  - Chat with it and vote on it's responses
    #  - Each conversation and feedback gives you points
    #  - Top-5 scores win AWESOME PIRZES""")


def setup_word_by_word_display_init():
    idx = len(st.session_state[KP+'wset']) - 1
    st.session_state[KP+'llm_return_words'] = st.session_state[KP+'wset'][idx]['content'].split(' ')
    st.session_state[KP+'wset'][idx]['content'] = ''
    st.session_state[KP+'llm_words_hops'] = 1
    if 0 < CONTENT_HOP_COUNT_FOR_DISPLAY < len(st.session_state[KP+'llm_return_words']):
        st.session_state[KP+'llm_words_hops'] = \
            int(len(st.session_state[KP+'llm_return_words']) / CONTENT_HOP_COUNT_FOR_DISPLAY)


def setup_word_by_word_display_next_word():
    word_display_num = min(st.session_state[KP+'llm_words_hops'], len(st.session_state[KP+'llm_return_words']))
    display_words = st.session_state[KP+'llm_return_words'][:word_display_num]
    st.session_state[KP+'llm_return_words'] = st.session_state[KP+'llm_return_words'][word_display_num:]
    if st.session_state[KP+'wset'][-1]['content']:
        st.session_state[KP+'wset'][-1]['content'] += ' '
    st.session_state[KP+'wset'][-1]['content'] += " ".join(display_words)
    if len(st.session_state[KP+'llm_return_words']) == 0:
        del st.session_state[KP+'llm_return_words']
        del st.session_state[KP+'llm_words_hops']


def update_chat_with_generated_message(turns):
    idx = len(st.session_state[KP+'wset']) - 1
    st.session_state[KP+'wset'][idx]['content'] = turns[-1]["content"]
    if 'docs' in turns[-1] and turns[-1]['docs']:
        if FLAG_SHOW_DOCS:
            st.session_state[KP+'wset'][idx]['docs'] = turns[-1]['docs']
        else:
            if turns[-1]['docs'] != DEFAULT_DOCS:
                st.session_state[KP+'wset'][idx]['docs'] = "Answering using wikipedia"
            else:
                st.session_state[KP+'wset'][idx]['docs'] = "Answering using parametric memory"
        if 'search_query' in turns[-1]:
            st.session_state[KP+'wset'][idx - 1]['docs'] = turns[-1]['search_query']
    if "metadata" in turns[-1]:
        st.session_state[KP + 'wset'][idx]['metadata'] = turns[-1]['metadata']


def add_chat_conversation(user_ask, turns):
    add_chat("user", user_ask)
    add_chat("robot", "llm_output")
    update_chat_with_generated_message(turns)


def rag_chat():
    word_printing = True if KP+'llm_return_words' in st.session_state else False
    init()
    if not word_printing:
        show_sidebar()
        if len(st.session_state[KP+"inputs"]) == 1:
            user_ask = st.session_state[KP+"inputs"][0]
            turns = gen_message(len(st.session_state[KP+'wset']) - 1, user_ask=user_ask)
            if turns is None:
                return
            add_chat_conversation(user_ask, turns)
            # Word by Display
            if CONTENT_HOP_COUNT_FOR_DISPLAY > 0:
                setup_word_by_word_display_init()
                word_printing = True
    if word_printing:
        setup_word_by_word_display_next_word()

    if st.session_state[KP+'wset_changed'] and not word_printing:
        st.session_state[KP+'wset_changed'] = False
        save_chat()
    show_chat()
    if word_printing:
        time.sleep(0.002)
        st.experimental_rerun()


if __name__ == '__main__':
    st.set_page_config(layout="wide")
    st.title("Chat with NOW-LLM")
    rag_chat()
