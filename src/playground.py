import os
import json
import time
import streamlit as st
import src.predict as predict
import lib.common as common
import pandas as pd

# Key Prefix
KP = "playground."

def read_json_file(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

def read_excel_file(file_path):
    df = pd.read_excel(file_path,sheet_name="ITSM - VA Hand Off - v5.3")
    return df
    
def load_config():
    if KP + "config_loaded_checksum" in st.session_state and common.get_file_checksum(
            st.session_state[KP + "config"]) == st.session_state[KP + "config_loaded_checksum"]:
        return
    st.session_state[KP + "config_loaded"] = common.get_config_as_dict(st.session_state[KP + "config"])
    st.session_state[KP + "config_loaded_checksum"] = common.get_file_checksum(st.session_state[KP + "config"])
    load_global_config()

    
def load_global_config():
    for key in st.session_state[KP + "config_loaded"]["GLOBAL"]:
        st.session_state[KP + key] = st.session_state[KP + "config_loaded"]["GLOBAL"][key]

def add_transcript_to_prompt(ekey):
        idx = st.session_state[KP+ 'read_chat_transcript_data'].index[st.session_state[KP+ 'read_chat_transcript_data']['Task Number (DO NOT EDIT)'] == st.session_state[ekey]].tolist()
        st.session_state[KP+"prompt"] = st.session_state[KP+ 'read_chat_transcript_data']['Hand off Chat extracted'][idx[0]]
        # for element in st.session_state[KP+ 'read_chat_transcript_data']:
        #     if st.session_state[ekey] == element['chat_label']:
        #         st.session_state[KP+"prompt"] =  element['chat_transcript']
        #         break

def log_sample():
    for model in st.session_state[KP+"model_name"]:
        temp_dict = st.session_state[KP+"feedback_dictionary"][model]

        sample_dir = os.path.join(
            "",
            st.session_state[KP+"DATA_HOME"],
            st.session_state[KP+"test_{}".format(model)],
            model
        )

        os.makedirs(sample_dir, exist_ok=True)

        sample_path = os.path.join("", sample_dir, str(time.time()) + ".json")

        f = open(sample_path, "w")
        f.write(json.dumps(temp_dict, indent=4))
        f.close()

def load_chats():
    if KP+'chat_transcript_name' not in st.session_state:
        # st.session_state[KP+'chat_transcript_name'] = []
        st.session_state[KP+ 'read_chat_transcript_data'] = read_excel_file(st.session_state[KP + "config_loaded"]['GLOBAL']['chat_transcript_path'])
        st.session_state[KP+'chat_transcript_name'] = list(st.session_state[KP+ 'read_chat_transcript_data']['Task Number (DO NOT EDIT)'])
        # for element in st.session_state[KP+ 'read_chat_transcript_data']:
        #     st.session_state[KP+'chat_transcript_name'].append(element['chat_label'])
    if KP+"user_prompt_data" not in st.session_state:
        st.session_state[KP+"user_prompt_data"] = read_json_file(st.session_state[KP + "config_loaded"]['GLOBAL']['user_prompt_path'])
    if KP+"sprompt_data" not in st.session_state:
        st.session_state[KP+"sprompt_data"] = read_json_file(st.session_state[KP + "config_loaded"]['GLOBAL']['system_prompt_path'])


def playground():
    load_config()
    load_chats()

    # Heading for the sidebar
    st.sidebar.markdown('## Choose Models')

    models = predict.get_models()
    st.sidebar.multiselect("model", models.keys(), default=list(models.keys())[4], key=KP+"model_name")
    # st.sidebar.slider("max_new_tokens", min_value=1, max_value=1000, value=500, key=KP+"max_new_tokens", step=1,disabled=True)
    # st.sidebar.slider("temperature", min_value=0.01, max_value=1.0, value=0.2, key=KP+"temperature", step=0.01,disabled=True)
    # st.sidebar.slider("num_beams", min_value=1, max_value=6, value=1, key=KP+"num_beams", step=1,disabled=True)
    # st.sidebar.slider("no_repeat_ngram_size", min_value=1, max_value=100, value=10, key=KP+"no_repeat_ngram_size", step=1,disabled=True)
    # st.sidebar.selectbox("do_sample", [True, False], key=KP+"do_sample",disabled=True)
    # st.session_state[KP+"feedback_dictionary"] = {}

    # Name the app
    st.title('LLM Playground')
    st.divider()
    
    st.selectbox("select system prompt",["None"] + st.session_state[KP+"sprompt_data"], key=KP+"sp")
    if st.session_state[KP+"sp"] != "None":
       system_prompt = st.text_area("System prompt", st.session_state[KP+"sp"], key=KP+"system_prompt")
    c1, c2 = st.columns([1, 1])
    c1.selectbox("select chat transcript",["None"] + st.session_state[KP+'chat_transcript_name'] , key=KP+"chat_transcript",on_change=add_transcript_to_prompt,args=(KP+"chat_transcript",))
    st.write("Chat transcript")
    prompt_input = st.text_area("Prompt", "", height=500, key=KP+"prompt", label_visibility="collapsed")
    s1,s2 = st.columns([1,1])
    user_prompt = s1.selectbox("User prompt", st.session_state[KP+"user_prompt_data"], key=KP+"user_prompt")
    if user_prompt != "None":
        u_prompt = st.text_input("", user_prompt, key=KP+"user_prompt_display")

    submit_button = st.button(label='Submit')

    if (submit_button):

        #with st.form("my_form"):

        for model in st.session_state[KP+"model_name"]:
            output = predict.predict(
                model=model,
                prompt=system_prompt+'\n\n'+prompt_input+'\n\n'+u_prompt,
                max_new_tokens=128, #int(st.session_state[KP+"max_new_tokens"]),
                temperature=0.2, #float(st.session_state[KP+"temperature"]),
                num_beams=1, #int(st.session_state[KP+"num_beams"]),
                no_repeat_ngram_size=10, #int(st.session_state[KP+"no_repeat_ngram_size"]),
                do_sample=True #st.session_state[KP+"do_sample"]
                )

            content = ""

            logtxtbox = st.empty()

            logtxtbox.text_area(label=model, value=content, height=200)

            output_list = output.split(" ")

            for word in output_list:
                time.sleep(0.05)
                content += word + " "
                logtxtbox.text_area(label=model, value=content, height=200)

                # st.radio("Feedback", ["Pass", "Fail"], horizontal=True, key=KP+"test_{}".format(model))

                # st.session_state[KP+"feedback_dictionary"][model] = {
                #     "prompt": prompt_input,
                #     "output": output,
                #     "model": model,
                #     "max_new_tokens": int(st.session_state[KP+"max_new_tokens"]),
                #     "temperature": float(st.session_state[KP+"temperature"]),
                #     "num_beams": int(st.session_state[KP+"num_beams"]),
                #     "no_repeat_ngram_size": int(st.session_state[KP+"no_repeat_ngram_size"]),
                #     "do_sample": st.session_state[KP+"do_sample"],
                #     "test": "pass"
                # }

            # st.form_submit_button("Submit", on_click=log_sample)


if __name__ == '__main__':
    playground()
