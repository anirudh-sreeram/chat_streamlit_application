import os
from src.predict import predict
import langchain
from langchain.utilities import WikipediaAPIWrapper
import requests
import json
import getpass
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig, GenerationConfig
import transformers
import torch
import pandas as pd
from tqdm.auto import tqdm
import re
tqdm.pandas()
KP = "now_llm_qa."

QA_PROMPT = """Answer based on information provided in the above DOCUMENTS only.  If the answer is not in the above DOCUMENTS, say 'I dont know'."""
WIKI_NO_ARTICLE = "No good Wikipedia Search Result was found"
DEFAULT_DOCS = "No documents were found for the search query.  Defaulting to parametric memory."

class QA:
    def __init__(self):
        self.wiki_api = WikipediaAPIWrapper()
        self.prefix_dict = {"robot": "", "user": "", "context": "", "end": ""}
        
    def clean_wiki_articles(self, wiki_articles):
        res = []
        articles = wiki_articles.split("Page:")
        for article in articles:
            if len(article.strip()) == 0:
                continue
            article = article.strip()
            article_split = article.split("\n")
            title = article_split[0].replace("Articles:", "").strip()
            context = (" ".join(article_split[1:])).replace("Articles:", "").replace("Summary:", "").strip()
            res.append(context)
        return res

    def get_wiki_articles(self, search_query):
        try:
            wiki_articles = self.wiki_api.run(search_query)
            if wiki_articles == WIKI_NO_ARTICLE:
                return None
            else:
                # preprocessing
                wiki_articles = self.clean_wiki_articles(wiki_articles)
                wiki_articles = wiki_articles

            return wiki_articles
        except Exception as e:
            return None
        
    def get_AI_search_documents(self, search_query,usr, pwd):
        try:
            # Set the request parameters
            url = 'https://sndart0000687.service-now.com/api/now/aisa/search'
            #print('URL: ' + url)

            # Eg. Should be username and password to log in to DART instance
            # user = input('Username: ')
            # pwd = getpass.getpass('Password: ')

            # Set proper headers
            headers = {"Content-Type":"application/json","Accept":"application/json"}

            # Do the HTTP request
            data_search = "{\"searchContextConfigId\":\"7e695ec91be3f51038cd8444604bcb54\",\"searchTerm\":\"{search_query}\",\"rpSysId\":\"00731b9d5b231010d9a5ce1a8581c7dd\"}".format(search_query=search_query)
            response = requests.post(url, auth=(user, pwd), headers=headers ,data=data_search)

            # Check for HTTP codes other than 200
            if response.status_code != 200: 
                print('Status:', response.status_code, 'Headers:', response.headers, 'Error Response:',response.json())
                return None

            # Decode the JSON response into a dictionary and use the data
            data = response.json()
            return data
        except Exception as e:
            return None
    
    def get_search_query(self, conversation_stack, search_query_model="NOW_LLM_V0.2_15.5B_CHAT"):
        pseudo_prompt = conversation_stack + "{}Let me think about a topic for your question.{}{}Topic:".format(self.prefix_dict["robot"], self.prefix_dict["end"], self.prefix_dict["robot"])
        search_query = predict(
            search_query_model,
            pseudo_prompt,
            max_new_tokens=20, 
            temperature=0.3, 
            num_beams=1, 
            no_repeat_ngram_size=30, 
            do_sample=True, 
            chat=True
        )
        search_query = search_query.split("\n")[0].strip().replace(self.prefix_dict["end"], "")
        
        return search_query
    
    def format_stack(self, qa_stack):
        inp = ""
        for i, s in enumerate(qa_stack[-7:]):  # 3 * 2 previous and 1 for current question
            if i % 2 == 0:
                if i+1 < len(qa_stack) and qa_stack[i+1] == "Sorry, there is not sufficient information to answer this question.":
                    continue
                inp += "{}{}{}".format(self.prefix_dict["user"], s, self.prefix_dict["end"])
            else:
                if s == "Sorry, there is not sufficient information to answer this question.":
                    continue
                inp += "{}{}{}".format(self.prefix_dict["robot"], s, self.prefix_dict["end"])
        return inp

    def check_greeting(self, query, greeting_model="UL2"):
        # greeting_prompt_str = f"""<|system|>Is '{query}?' considered a greeting?  Answer yes or no.<|endoftext|><|agent|>"""
        greeting_prompt_str = f"""Is '{query}' considered a greeting?  Answer yes or no."""

        greeting_prediction = predict(
            model=greeting_model,
            prompt=greeting_prompt_str,
            max_new_tokens=5,
            temperature=1,
            num_beams=4,
            no_repeat_ngram_size=30,
            do_sample=False,
            chat=True
        )
        greeting_flg = True if "yes" in greeting_prediction.lower() else False
        return greeting_flg
    
    def check_doc_relevancy(self, query, wiki_articles, doc_relevancy_model="UL2"):
        # doc_relevancy_prompt_str = f"""{wiki_articles}\n\nCan the question '{query}' be answered from the above documents?  Answer yes or no."""
        doc_relevancy_prompt_str = f"""{wiki_articles}\n\nWhat is the answer to '{query}' based only on the above document?\nIf it can't be answered using the given information, say 'I don't know'."""

        doc_relevancy_prediction = predict(
            model=doc_relevancy_model,
            prompt=doc_relevancy_prompt_str,
            max_new_tokens=5,
            temperature=1,
            num_beams=4,
            no_repeat_ngram_size=30,
            do_sample=False,
            chat=True
        )
        # print("Doc Relevancy Prediction:", doc_relevancy_prediction)
        doc_relevancy_flg = True
        for i in ["MAINT: ", "i don't know"]:
            if i in doc_relevancy_prediction.lower():
                doc_relevancy_flg = False
        # print("Doc Relevancy :", "True" if doc_relevancy_flg else "False")
        return doc_relevancy_flg


    def get_prediction(self, model, qa_stack,search_type="wiki"):
        metadata = {"relevance": []}

        # check greeting
        greeting_flg = self.check_greeting(qa_stack[-1], model)
        metadata["greeting_flg"] = greeting_flg
        print("Greeting Flag: ", greeting_flg)
        search_query, docs = "", DEFAULT_DOCS
        
        if greeting_flg:
            prompt = self.prefix_dict["user"] + qa_stack[-1] + self.prefix_dict["end"]
        else:
            # get conversation stack
            conversation_stack = self.format_stack(qa_stack)
            
            # get search query
            search_query = self.get_search_query(conversation_stack, model)
            # print("Search Query: ", search_query + "\n")
            
            if search_type == 'wiki':
                # get wiki_articles
                wiki_articles = self.get_wiki_articles(search_query)
                if wiki_articles is None:
                    # No wiki articles, answer from parametric memory!
                    # print("PARAMETRIC MEMORY NO ARTICLES")
                    prompt = conversation_stack + self.prefix_dict["robot"]
                else:
                    # Check relevancy of wiki articles
                    for wiki_article in wiki_articles:
                        doc_relevancy_flg = self.check_doc_relevancy(qa_stack[-1], wiki_article, model)
                        metadata["relevance"].append({
                            "relevant": doc_relevancy_flg,
                            "document": wiki_article
                        })
                        if doc_relevancy_flg:
                            if docs == DEFAULT_DOCS:
                                docs = ""
                            docs += wiki_article + "\n\n"     
                    docs = docs.strip()
                    if len(docs) > 0:
                        # print("IN-CONTEXT PREDICTION")
                        prompt = "{}{}\n\n{}{}{}{}".format(self.prefix_dict["context"], docs, QA_PROMPT, self.prefix_dict["end"], conversation_stack, self.prefix_dict["robot"] )
                    else:
                        # Not relevant, answer from parametric memory!
                        # print("PARAMETRIC MEMORY NOT RELEVANT")
                        prompt = conversation_stack + self.prefix_dict["robot"] 
            else:
                # get AI search documents
                user = input('Username: ')
                pwd = getpass.getpass('Password: ')
                ai_search_documents = self.get_AI_search_documents(search_query, user, pwd)
                if ai_search_documents is not None:
                    prompt = conversation_stack + self.prefix_dict["robot"]
                else:
                    for doc in ai_search_documents:
                        doc_relevancy_flg = self.check_doc_relevancy(qa_stack[-1], doc, model)
                        metadata["relevance"].append({
                            "relevant": doc_relevancy_flg,
                            "document": doc
                        })
                        if doc_relevancy_flg:
                            if docs == DEFAULT_DOCS:
                                docs = ""
                            docs += doc + "\n\n"   
                    docs = docs.strip()
                    if len(docs) > 0:
                        prompt = "{}{}\n\n{}{}{}{}".format(self.prefix_dict["context"], docs, QA_PROMPT, self.prefix_dict["end"], conversation_stack, self.prefix_dict["robot"] )
                    else:
                        prompt = conversation_stack + self.prefix_dict["robot"]
        
                
        # print("Prompt: ", prompt + "\n")
        # print("MODEL = =====================", model)
        res = predict(
            model, 
            prompt, 
            max_new_tokens=500, 
            temperature=0.3, 
            num_beams=1, 
            no_repeat_ngram_size=30, 
            do_sample=True, 
            chat=True
        )
        # print("Response: ", res + "\n")
        
        # print("#################")
        
        res = res.replace(self.prefix_dict["robot"], "").replace(self.prefix_dict["user"], "").replace(self.prefix_dict["context"], "").replace(self.prefix_dict["end"].strip(), "")
        if len(docs.strip()) != 0 and docs != DEFAULT_DOCS:
            docs = "Below are some relevant documents that we found.\n\n" + docs
        # print("Docs at end of Predict:", docs)
        return res, search_query, docs, metadata
