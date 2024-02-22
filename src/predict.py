
import copy
import os
import json
import requests
import streamlit as st

KP = "predict."

round_robin_idx = 0


def get_models():
    load_model_endpoints()
    models = copy.copy(st.session_state[KP + "MODELS"])
    return models


def get_model_names():
    return list(get_models().keys())


def get_default_model(default_attr):
    load_model_endpoints()
    for model in st.session_state[KP + "MODELS"]:
        if default_attr in st.session_state[KP + "MODELS"][model] and \
                st.session_state[KP + "MODELS"][model][default_attr]:
            return model
    models = list(st.session_state[KP + "MODELS"].keys())
    return models[0]


def get_default_chat_model():
    return get_default_model("model_chat_default")


def get_default_summarization_model():
    return get_default_model("model_summarize_default")


def get_model_prompt_tags(model):
    load_model_endpoints()
    if model in st.session_state[KP + "MODELS"]:
        if "prompt_tags" in st.session_state[KP + "MODELS"][model]:
            return st.session_state[KP + "MODELS"][model]["prompt_tags"]
    return {"user": "<|customer|>", "context": "<|system|>", "robot": "<|agent|>", "end":  "<|endoftext|>"}


def huggingface_server(model, prompt, max_new_tokens, temperature, num_beams, no_repeat_ngram_size, do_sample,
                       chat=False):
    global round_robin_idx
    url_lst = st.session_state[KP+"MODELS"][model]['url']
    if isinstance(url_lst, list):
        num_urls = len(url_lst)
        url_lst = url_lst[round_robin_idx % num_urls:] + url_lst[:round_robin_idx % num_urls]
        round_robin_idx += 1
    else:
        url_lst = [url_lst]
    
    if chat:
        inp = globals()[st.session_state[KP+"MODELS"][model]['chat_formatter']](prompt)
    else:
        inp = globals()[st.session_state[KP+"MODELS"][model]['formatter']](prompt)
    
    for url in url_lst:
        # print("Round Robin Idx: ", round_robin_idx)
        # print("Url Hit: ", url)
        payload = json.dumps({
            "inputs": inp,
            "parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "do_sample": do_sample,
                "num_beams": num_beams,
                "no_repeat_ngram_size": no_repeat_ngram_size,
                "stop": ["<|end|>", "<|endoftext|>"]
            }
        })

        headers = {
            'Authorization': st.session_state[KP+"MODELS"][model]['Authorization'],
            'Content-Type': st.session_state[KP+"MODELS"][model]['Content-Type']
        }
        try:
            response = requests.request("POST", url, headers=headers, data=payload,
                                            timeout=st.session_state[KP+"MODELS"][model]['timeout'])
        except Exception as e:
            print("Exception:", str(e))
        
        json_response = json.loads(response.text)
                
        if 'error' not in json_response:
            if "open assistant" in json_response['generated_text'].lower() or "laion" in json_response['generated_text'].lower():
                return "I'm NOW Assistant, trained by ServiceNow. I can answer questions using my knowledge or wikipedi! I can also write emails, summarization documents and so on."
            else:
                return json_response['generated_text']
        else:
            print("Response Error:", response.text)
    return "MAINT: I'm having lunch, will be back soon."
    

def nemo_server(model, prompt, max_new_tokens, temperature, num_beams, no_repeat_ngram_size, do_sample, chat=False):
    """
    NeMo generation params documentation - https://github.com/NVIDIA/NeMo/blob/2db352a67c38425062cea936d0623e405ae07bb1/nemo/collections/nlp/modules/common/text_generation_utils.py#L462
    """

    url = st.session_state[KP+"MODELS"][model]['url']

    if chat:
        inp = globals()[st.session_state[KP+"MODELS"][model]['chat_formatter']](prompt)
    else:
        inp = globals()[st.session_state[KP+"MODELS"][model]['formatter']](prompt)

    data = {
        "sentences": [inp],
        "tokens_to_generate": max_new_tokens,
        "greedy": do_sample,
        "add_BOS": False,
        "temperature": temperature,
        "min_tokens_to_generate": 1,
    }

    headers = {
        'Authorization': st.session_state[KP+"MODELS"][model]['Authorization'],
        'Content-Type': st.session_state[KP+"MODELS"][model]['Content-Type']
    }

    resp = requests.put(
        url,
        data=json.dumps(data),
        headers=headers,
        timeout=st.session_state[KP + "MODELS"][model]['timeout']
    )

    sentences = resp.json()['sentences']

    return sentences[0][len(inp):]


def aide_server(model, prompt, max_new_tokens, temperature, num_beams, no_repeat_ngram_size, do_sample, chat=False):
    options = json.dumps({"max_new_tokens": max_new_tokens,
                          "temperature": temperature,
                          "do_sample": do_sample,
                          "num_beams": num_beams,
                          "use_peft": "none",
                          "no_repeat_ngram_size": no_repeat_ngram_size,
                          "stop_token": "<|customer|>"
                          })
    daaslet_url = "https://mlexp-daas010.bwi100.service-now.com:8080/api/v1/predict"
    headers = {'X-Daaslet-Token': "d8aaf51b-a3ba-4069-8797-64984bb598ba"}
    request = {"model": model, "prompt": prompt, "options": options,  "environment": None}
    if "capability" in st.session_state[KP+"MODELS"][model]:
        request["capability"] = st.session_state[KP+"MODELS"][model]["capability"]
    try:
        response = requests.post(daaslet_url, headers=headers, data=json.dumps(request), verify=False)
    except Exception as e:
        print("Exception:", str(e))

    json_response = json.loads(response.text)
    if "outputs" in json_response:
        if "<|customer|>" in json_response["outputs"][0]["data"][0]:
            return json_response["outputs"][0]["data"][0].split("<|customer|>")[0]
        return json_response["outputs"][0]["data"][0]
    return "MAINT: I'm having lunch, will be back soon."


PREDICT_ROUTER = {
    "huggingface_server": huggingface_server,
    "nemo_server": nemo_server,
    "aide_server": aide_server
}


def now_gpt_formatter(prompt):
    return prompt + "<|endoftext|>"


def dummy_formatter(prompt):
    return prompt


def oasst_formatter(prompt):
    return "<|prompter|>" + prompt + "<|endoftext|><|assistant|>"


def nemo_formatter(prompt):
    return "User:\n{}\n\nAssistant:\n".format(prompt)


def load_model_endpoints():
    # if KP + "MODELS" not in st.session_state:
    st.session_state[KP + "MODELS"] = json.loads(open(st.session_state["global.model_endpoints"], "r").read())


def predict(model, prompt, max_new_tokens, temperature, num_beams, no_repeat_ngram_size, do_sample, chat=False):
    load_model_endpoints()
    print("SERVER ==== ", st.session_state[KP+"MODELS"][model])
    return PREDICT_ROUTER[st.session_state[KP+"MODELS"][model]['server']](model, prompt, max_new_tokens, temperature,
                                                                          num_beams, no_repeat_ngram_size, do_sample,
                                                                          chat)
