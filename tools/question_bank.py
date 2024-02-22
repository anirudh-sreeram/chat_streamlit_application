import streamlit as st
import pandas as pd
import json

# Function to read question bank data from JSON file
def read_question_bank():
    try:
        with open("qb.json", "r") as file:
            question_bank = json.load(file)
    except FileNotFoundError:
        question_bank = []
    return question_bank


# Function to write question bank data to JSON file
def write_question_bank(question_bank):
    with open("qb.json", "w") as file:
        json.dump(question_bank, file, indent=2)


def search_question_bank():
     # Read question bank data
    question_bank = read_question_bank()
    
    # Search for a question
    search_query = st.text_input("Search for a question:")
    if search_query:
        # remove exceeding and trailing spaces
        search_query = search_query.strip()
        
        #check for matching questions
        matching_questions = [q for q in question_bank['question_bank'] if search_query.lower() in q.lower()]

        if matching_questions:
            # Display warning if question already exists in the question bank
            for i, question in enumerate(matching_questions):
                st.warning('Warning (This question already exists in the Question bank)', icon="⚠️")
        else:
            # Display success message if question does not exist in the question bank and add it to the question bank
            st.radio("Do you want to add this question to the question bank?", ("Yes", "No"),key="add_question",index=1)
            if st.session_state["add_question"] == "Yes":
                question_bank['question_bank'].append(search_query)
                write_question_bank(question_bank)
                st.success('Successfully added the question to the bank', icon="✅")


if __name__ == "__main__":
    search_question_bank()