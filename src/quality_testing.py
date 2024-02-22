import os
import json
import time
import re
import streamlit as st
import src.predict as predict

KP = "quality_testing."

QE_PROMPT_CATEGORIES = [
    "intent_classification",
    "closed_qa",
    "open_qa",
    "chat_summarization",
    "document_summarization"
]


doc_fields = {
    "doc_type": "Document Type",
    "num_paragraphs": "Number of Paragraphs",
    "prompt_input_features": "Prompt input features",
    "prompt_category": "Prompt Category",
    "high_level_guidelines": "High level guidelines",
    "prompt_input": "Keywords"
}

doc_values = {
    "doc_type": ["Any", "KB", "EMAIL", "STORY", "POEM", "ARTICLE"],
    "num_paragraphs": ['Any', '0', '1', '2', '3', '4', '5', '>5'],
    "prompt_input_features": ["Tables", "JSON", "CSV", "TSV", "Bulleted Lists", "Numbered Lists",
                              "Single paragraph", "Multi paragraph", "Conversations"],
    "prompt_category": ["Context_Based_QA", "Open_ended_QA", "Open_ended_QA - Brainstorming",
                        "Open_ended_QA - Advice", "Generative_QA", "Meta_QA", "Reasoning_QA", "Adversarial_QA",
                        "Summarization", "Aspect - Summarization", "Classification", "Extraction"],
    "high_level_guidelines": ["Do not answer if no info", "Answer in brief", "Answer in detail",
                              "Be as verbose as possible.", "Keep your answer short.", "Give details while answering.",
                              "Answer based on the context only.", "Say 'I do not know' if you cannot answer.",
                              "If you do not have sufficient information to answer, say 'Unanswerable'."]
}
text_fields = ["prompt_input"]
one_select_fields = ["doc_type", "num_paragraphs"]
multi_select_fields = ["prompt_input_features", "prompt_category", "high_level_guidelines"]
set_fields = one_select_fields + multi_select_fields


def display_session_state_vars(location):
    print('+' * 50, location)
    for key in sorted(st.session_state.keys()):
        if key in [KP + "contexts", "predict.MODELS"]:
            continue
        print(key, "=", st.session_state[key])
    print('+' * 50)


def save_sample():
    # display_session_state_vars("save_sample")
    if KP + "display_data_set" in st.session_state:
        sample_path = st.session_state[KP + "display_data_set_key"]
    else:
        persist_folder = st.session_state[KP + "prompt_folder"].split(',')[0]
        sample_dir = os.path.join(st.session_state["global.data_home"], persist_folder)
        os.makedirs(sample_dir, exist_ok=True)
        sample_path = os.path.join("", sample_dir, str(time.time()) + ".json")

    temp_dict = {
        "doc_type": st.session_state[KP + "main_box.doc_type"],
        "num_paragraphs": st.session_state[KP + "main_box.num_paragraphs"],
        "prompt_input_features": st.session_state[KP + "main_box.prompt_input_features"],
        "prompt_category": st.session_state[KP + "main_box.prompt_category"],
        "high_level_guidelines": st.session_state[KP + "main_box.high_level_guidelines"],
        "prompt_input": st.session_state[KP + "main_box.prompt_input"]
    }
    f = open(sample_path, "w")
    f.write(json.dumps(temp_dict, indent=4))
    f.close()
    st.session_state[KP + "prompt_data"][sample_path] = temp_dict
    st.info("Sample {} saved".format(sample_path))


def sidebar_display_model_parameter_box():
    with st.sidebar.expander(':guitar: Parameters'):
        models = predict.get_models()
        # Set model name
        st.multiselect("model", models.keys(), default=list(models.keys())[0], key=KP + "model_name")
        # Set parameters for the editor
        st.slider("max_new_tokens", min_value=1, max_value=1000, value=128, key=KP + "max_new_tokens", step=1)
        # Set model temperature
        st.slider("temperature", min_value=0.01, max_value=1.0, value=0.3, key=KP + "temperature", step=0.01)
        # Enter num beams
        st.slider("num_beams", min_value=1, max_value=6, value=1, key=KP + "num_beams", step=1)
        # Enter no repeat n-gram size
        st.slider("no_repeat_ngram_size", min_value=1, max_value=100, value=25, key=KP + "no_repeat_ngram_size", step=1)
        # Enter do sample
        st.selectbox("do_sample", [True, False], key=KP + "do_sample")


def load_datasets():
    dataset_dir = st.session_state[KP + "prompt_folder"].split(',')
    st.session_state[KP + "prompt_data"] = {}
    for dataset in dataset_dir:
        dataset_dir_path = os.path.join(st.session_state["global.data_home"], dataset)
        for file in os.listdir(dataset_dir_path):
            if file.endswith(".json"):
                fpath = os.path.join(dataset_dir_path, file)
                st.session_state[KP + "prompt_data"][fpath] = json.loads(open(fpath, "r").read())


def filter_datasets():
    st.session_state[KP + "prompt_data_filtered"] = {}
    # Run the filter through all the data
    for jkey in st.session_state[KP + "prompt_data"].keys():
        pass_filter = True
        for attr in set_fields:
            key = KP + "filter_box." + attr
            if key in st.session_state and st.session_state[key]:
                if attr not in st.session_state[KP + "prompt_data"][jkey]:
                    pass_filter = False

                if attr in one_select_fields:
                    if st.session_state[key] != 'Any':
                        if str(st.session_state[KP + "prompt_data"][jkey][attr]) != str(st.session_state[key]):
                            pass_filter = False
                else:
                    if len(st.session_state[key]) > 0:
                        if len([i for i in st.session_state[key] if i in st.session_state[KP + "prompt_data"][jkey][attr]]) < 1:
                            # print("Not adding", jkey)
                            pass_filter = False
            if not pass_filter:
                break
        if not pass_filter:
            continue
        for tf in text_fields:
            # quality_testing.filter_box.prompt_input
            key = KP + "filter_box." + tf
            if key in st.session_state and st.session_state[key]:
                # print("Checking:", st.session_state[key], "in", st.session_state[KP + "prompt_data"][jkey][tf])
                if not re.search(st.session_state[key], st.session_state[KP + "prompt_data"][jkey][tf],
                                 re.IGNORECASE):
                    pass_filter = False
        if pass_filter:
            st.session_state[KP + "prompt_data_filtered"][jkey] = st.session_state[KP + "prompt_data"][jkey]


def load_dataset():
    if st.session_state[KP + "selected_dataset"] is None:
        return
    for jkey in st.session_state[KP + "prompt_data"].keys():
        if jkey.endswith(st.session_state[KP + "selected_dataset"]):
            st.session_state[KP + "display_data_set"] = st.session_state[KP + "prompt_data"][jkey]
            st.session_state[KP + "display_data_set_key"] = jkey
            return
    st.info("System Error: Key[%s] not found in dataset" % st.session_state[KP + "selected_dataset"])


def save_dataset():
    # Update the Original Dataset with changes values
    jkey = st.session_state[KP + "display_data_set_key"]
    for attr in list(doc_fields.keys()):
        if KP + "load" + attr in st.session_state:
            st.session_state[KP + "prompt_data"][jkey][attr] = st.session_state[KP + "load" + attr]
    with open(jkey, "w") as fh:
        json.dump(st.session_state[KP + "prompt_data"][jkey], fh)


def sidebar_display_filter_box():
    # Filter Box Header
    with st.sidebar.expander(':saxophone: Filter & Load'):
        if KP + "prompt_folder" in st.session_state:
            dataset = st.session_state[KP + "prompt_data"]
            if KP + "prompt_data_filtered" in st.session_state:
                dataset = st.session_state[KP + "prompt_data_filtered"]
            # create_dataset_features(dataset)
            # st.markdown('#### Folder: '+st.session_state[KP+"prompt_folder"])
            for one_select in one_select_fields:
                display_select_box("filter_box.", one_select, "")
            for multi_select in multi_select_fields:
                display_multiselect_box("filter_box.", multi_select, "")
            for tf in text_fields:
                st.text_input(doc_fields[tf], key=KP + "filter_box." + tf,
                              value=st.session_state[KP + "filter_box." + tf] if KP + "filter_box." + tf in st.session_state else "")
            st.button("Filter", key=KP+"filter_box.filter", on_click=filter_datasets)
            st.selectbox("Prompts [%s]:" % len(dataset.keys()),
                         options=sorted(list([os.path.basename(p) for p in dataset.keys()])),
                         key=KP + "selected_dataset")
            st.button("Load", key=KP + "load", on_click=load_dataset)
        else:
            st.markdown(':red[#### Filter not possible. `prompt_folder` not defined]')


def init():
    if KP + "init" not in st.session_state:
        load_datasets()
        st.session_state[KP + "init"] = True


def main_display_dataset():
    for attr in set_fields:
        if attr in st.session_state[KP + "display_data_set"]:
            options = doc_values[attr]
            default = st.session_state[KP + "display_data_set"][attr]
            if not isinstance(default, list):
                default = [default]
            if len(default) > 0:
                options += default
            if len(options) > 1:
                st.multiselect(doc_fields[attr], options=options, key=KP + "load" + attr,
                               default=st.session_state[KP + "display_data_set"][attr])
        else:
            st.multiselect(doc_fields[attr], options=doc_values[attr], key=KP + "load" + attr)
    st.text_area(label="prompt_input", value=st.session_state[KP + "display_data_set"]["prompt_input"], height=200,
                 key=KP + "load" + "prompt_input")
    st.button("Save", key=KP + "save", on_click=save_dataset)


def display_select_box(key_prefix, key, data_tag):
    # print("display_select_box", key_prefix, key, data_tag)
    label = doc_fields[key]
    options = doc_values[key]
    default = options[0]

    if data_tag and KP + data_tag in st.session_state:
        default = st.session_state[KP + data_tag][key]
    if isinstance(default, list):
        default = default[0]
    if isinstance(default, int):
        default = str(default)
    if default == "None":
        default = "Any"
    st.selectbox(label, options=options, key=KP + key_prefix + key, index=options.index(default))


def display_multiselect_box(key_prefix, key, data_tag):
    label = doc_fields[key]
    options = doc_values[key]
    default = None
    if KP + data_tag in st.session_state:
        # print("Before Default:", key, st.session_state[KP + data_tag][key])
        # print("Options:", doc_values[key])
        default = []
        for x in st.session_state[KP + data_tag][key]:
            if x == "None":
                continue
            elif x not in options:
                for o in options:
                    if o.lower() == x.lower():
                        default.append(o)
            else:
                default.append(x)
        # print("After Default:", key, default)
    st.multiselect(label, options=options, key=KP + key_prefix + key, default=default)


def clear_form():
    if KP + "display_data_set" in st.session_state:
        del st.session_state[KP + "display_data_set"]
        del st.session_state[KP + "display_data_set_key"]
    if KP + "main_box.prompt_input" in st.session_state:
        del st.session_state[KP + "main_box.prompt_input"]


def gen_prediction():
    st.session_state[KP + "Responses"] = []
    for model in st.session_state[KP + "model_name"]:
        try:
            prefix_dict = predict.get_model_prompt_tags(model)
            output = predict.predict(
                model=model,
                prompt=st.session_state[KP + "main_box.prompt_input"] + prefix_dict["end"],
                max_new_tokens=int(st.session_state[KP + "max_new_tokens"]),
                temperature=float(st.session_state[KP + "temperature"]),
                num_beams=int(st.session_state[KP + "num_beams"]),
                no_repeat_ngram_size=int(st.session_state[KP + "no_repeat_ngram_size"]),
                do_sample=st.session_state[KP + "do_sample"]
            )
            output = output.replace(prefix_dict["robot"].strip(), "").replace(prefix_dict["end"].strip(), "").strip()
            st.session_state[KP+"Responses"].append({"model": model, "content": output})
        except Exception as e:
            st.session_state[KP + "Responses"].append({"model": model, "content": "Model Error"})


def main_display_default():
    st.title('QE Sample creator')
    if KP + "display_data_set" in st.session_state:
        st.markdown(os.path.basename(st.session_state[KP + "display_data_set_key"]))
    display_session_state_vars("main_display_default")
    with st.form("my_form", clear_on_submit=True):
        if KP + "display_data_set" in st.session_state and st.session_state[KP + "display_data_set"]:
            st.session_state[KP + "main_box.prompt_input"] = st.session_state[KP + "display_data_set"]["prompt_input"]
        # display_session_state_vars("main_display_default")
        for one_select in one_select_fields:
            display_select_box("main_box.", one_select, "display_data_set")
        for multi_select in multi_select_fields:
            display_multiselect_box("main_box.", multi_select, "display_data_set")
        st.text_area("Your prompt here", height=300, key=KP + "main_box.prompt_input")
        but1, but2, but3 = st.columns([1,6,1])
        but1.form_submit_button('Submit', on_click=save_sample)
        but2.form_submit_button("Generate", on_click=gen_prediction)
        but3.form_submit_button("Clear", on_click=clear_form)
        if KP+"Responses" in st.session_state:
            # print(st.session_state[KP+"Responses"])
            for response in st.session_state[KP+"Responses"]:
                st.text_area(label=response["model"], value=response["content"], height=200)


def sidebar_display_default():
    sidebar_display_filter_box()
    sidebar_display_model_parameter_box()


def quality_testing():
    init()
    sidebar_display_default()
    main_display_default()


if __name__ == '__main__':
    quality_testing()
