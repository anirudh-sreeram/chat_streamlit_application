import json
import os

import streamlit as st
from streamlit_star_rating import st_star_rating

KP = "now_summary."

# context_data="""
# Task Number
# CS6724800
# State
# Closed
# Short description
# Unable to Update Agent Client Collector Framework Plugin
# Description
# -- We are unable to update the Agent Client Collector Framework Plugin to the latest version 3.1.1
# -- We tried to raise an SR for plugin update, but the change is closed stating that its a store plugin
# Activity
#
#
#
#
# System
# Work notes
# 2023-06-27 16:00:02
# Auto close workflow COMPLETED for the case. Case has now been closed.
#
# Rainer Hedemann
# Work notes
# 2023-06-27 14:58:38
# SAM to inform Allianz about closure.
#
# System
# Work notes
# 2023-06-23 16:00:08
# Auto close final notification sent to the case contact, case will be automatically closed at 2023-06-27 16:00:00 UTC.
#
# System
# Work notes
# 2023-06-21 16:00:14
# Auto close 2nd notification sent to the case contact. Final attempt will be made to at 2023-06-23 16:00:00 UTC.
#
# System
# Additional comments
# 2023-06-19 16:00:06
# This message is to inform you that this case is in a Solution Proposed state and is being monitored by auto-close workflow.
#
# - This case will close in 9 days (US-based and excluding weekends) unless action is taken.
# - Any comment to the case will stop this workflow.
# - Further updates on the auto-close progress will only be sent to the primary contact for this case.
#
# With regards,
# ServiceNow
#
#
#
# Show more
# System
# Work notes
# 2023-06-19 16:00:06
# Auto close 1st notification sent to the case contact. Second attempt will be made to at 2023-06-21 16:00:00 UTC.
#
# System
# Work notes
# 2023-06-15 13:35:42
# Auto-agent: Case moved to automation user based on rules in "Case - Solution Proposed - Start" configuration.
#
# Luana De Luca-Driessen
# Additional comments
# 2023-06-15 07:35:10
# Solution proposed is :
#
# Hello Satish,
#
# I hope you are well.
#
# I am following up with you to see if the issue is solved after you reviewed the information I provided in my last comments.
#
# As I didn't hear from you, for now I have moved this case to a "Solution Proposed " status assuming the issue is solved, but the case will remain open.
#
# If you are comfortable with the information provided and you have no further questions, please consider closing this Case by clicking on Accept Solution.
#
# Should you have further questions on this matter, please just update this case with your comments, I'll be happy to assist.
#
# With kind regards,
# Luana De Luca | Sr Customer Support Rep | Customer Support Administration | Servicenow | Works for you
#
#
# Show more
# Luana De Luca-Driessen
# Work notes
# 2023-06-15 07:35:10
# KB0754177 : Store App Support Info
# KB0754177 - Store App Support Info - Perma Link [Internal]
#
# Luana De Luca-Driessen
# Work notes
# 2023-06-15 07:35:10
# Auto close workflow is TRIGGERED for the case. Case contact will be notified of auto-close process at 2023-06-19 16:00:00 UTC.
#
# Luana De Luca-Driessen
# Additional comments
# 2023-06-12 07:53:33
# Hello Satish,
#
# My name is Luana De Luca and I will be assisting you with your case.
#
# Issue:
#
# You are unable to update Agent Client Collector Framework Plugin to the latest version 3.1.1
# You tried to raise a change to update it, but the change was closed stating that it's a store application
#
# Investigation Summary:
#
# - I found in our records CHG46736284 raised from your end to update Agent Client Collector Framework
# - Confirming this is a Store application: Store link: Agent Client Collector Framework
# - I have verified the status of this app for you in Store and it seems the new app version should already be available for install in your instances. (screenshot attached for reference)
# - I was unable to verify further in your dev instance due to access restrictions.
#
# Next Steps:
#
# - Could you please access your instance and navigate to System Applications > All Available Applications > All
# - Search for Agent Client Collector Framework
# - See if the application is found and if the version 3.1.1 is available. The update button should be enabled and you can proceed with the update.
#
# If you are experiencing any issues, could you please provide details on the issue and grant me (luana.deluca) access to aztechdev instance, I'll be happy to assist further.
#
# I'll be awaiting your response.
#
# ***
#
# As part of the troubleshooting process, I and other ServiceNow personnel may need to access your instance(s) in order to review the service impact to your instance and determine root cause. It may also be necessary to make some changes on a sub-production instance in order to troubleshoot the issue or to test a probable solution. These changes, if any, will be reverted back to the original state. If any change is not reverted a reason will be provided for the same.
#
# I am working in the CET time zone. Please note that my working hours are 08:30 to 17:30 CET.
# Should you need assistance outside of this time frame, another engineer will be available to assist you.
#
# With kind regards,
# Luana De Luca | Customer Support Administration | Servicenow | Works for you
#
#
# Show more
# datacenter_sync
# Work notes
# 2023-06-12 07:32:30
# No AEE Cases Found
# Feedback for AIOps
#
# datacenter_sync
# Work notes
# 2023-06-12 06:28:32
# The Instance aztechdev has SNC Access Control plugin set to enabled
#
# Feedback for AIOps
#
#
# Show more
# datacenter_sync
# Work notes
# 2023-06-12 06:28:29
# No AEE Cases Found
# Feedback for AIOps
#
# extern.kvv_satish-kumar@allianz.de
#
# Additional comments
# 2023-06-12 06:26:16
# Preferred phone number: 8919241533
# Is it ok to contact you on your phone? - Yes
#
# Best time to contact you:
# Morning (8 AM to 12 PM)
#
# Subject: Unable to Update Agent Client Collector Framework Plugin
#
# Description: -- We are unable to update the Agent Client Collector Framework Plugin to the latest version 3.1.1
# -- We tried to raise an SR for plugin update, but the change is closed stating that its a store plugin
#
# Steps to reproduce:
# -- Try to update the Agent Client Collector Framework Plugin to the latest version
# -- It is failing with attached error.
# """
# summary1="""1. Issue:
# The customer reported that they were unable to update the Agent Client Collector Framework Plugin to the latest version 3.1.1
#
# 2. Actions Taken:
# - Notified the requestor that the application is a store application and that the new version should already be available for install in their instances.
# - Informed the requestor that they could access their instance and navigate to System Applications > All Available Applications > All and search for Agent Client Collector Framework to check if the application was found and if the version 3.1.1 was available.
#
# 3. Resolution:
# The resolution for the case is unknown.
# """
# summary2="""1. Issue:
# The customer is unable to update the Agent Client Collector Framework Plugin to the latest version 3.1.1
#
# 2. Actions Taken:
# - Confirmed that the application is a Store application.
# - Informed the customer that the new app version should already be available for install in their instances.
#
# 3. Resolution:
# The resolution for the case is unknown. The customer was informed that the new app version should already be available in their instances.
# """
# summary3="""1. Issue:
# The customer is unable to update the Agent Client Collector Framework Plugin to the latest version 3.1.1
#
# 2. Actions Taken:
# - Confirmed that the application is a Store application: Store link: Agent Client Collector Framework
# - Notified the customer that the new app version should already be available for install in their instances.
# - Instructed the customer to access their instance and navigate to System Applications > All Available Applications > All.
# - Instructed the customer search for Agent Client Collector Framework and check if the version 3.1.1 is available.
#
# 3. Resolution:
# The resolution for the case is unknown. The customer was instructed to access their instance and navigate to System Applications>All Available Applications>All. They were asked to search for Agent Client Collector Framework and check if version 3.1.1 is available for installation.
# """


def show_task_info():
    cols = st.columns(4)
    collabels = ["Task state", "Assigned to", "Project name", "Project number"]
    # colvalues = ["Published1", "Partha Mukherjee", "Summary evaluation", "LBP0001004"]
    colvalues = ["Published1", st.session_state["global.username"].replace('.', ' ').capitalize(), "Summary evaluation", "LBP0001004"]
    for i in range(4):
        cols[i].text(collabels[i])
    for i in range(4):
        cols[i].text(colvalues[i])


def show_band2():
    def move_forward():
        st.session_state[KP+"fileId"] += 1
        if st.session_state[KP+"fileId"] >= len(st.session_state[KP+"files"]):
            st.session_state[KP+"fileId"] = 0
    cols = st.columns([2,6,2])
    cols[0].markdown("[Labelling Guidelines](https://servicenow-my.sharepoint.com/:w:/p/ankit_goel/EQKlszEbW7xJjDRVspT6F9ABPsQm0ZoxnDc9cCfsh33RhA?e=CJsWL5)")
    cols[2].button(":arrow_right: Provide next new feedback", on_click=move_forward)


def show_context():
    st.markdown("Data used for summarization")
    # st.markdown(context_data)
    st.markdown(st.session_state[KP+"file_content"][0]["content"] + "\n\n" + st.session_state[KP+"file_content"][1]["content"])


def show_summaries():
    # summaries = [summary1, summary2, summary3]
    for i in range(3):
        with st.expander("Summary " + str(i+1)):
            st.markdown("Summary " + str(i+1))
            # st.markdown(summaries[i])
            st.markdown(st.session_state[KP+"file_content"][2]["content"])
            st_star_rating("Rate the summary", 5, 5, 20, key=KP+"rating_"+str(i))
            if KP+"rating_"+str(i) in st.session_state and st.session_state[KP+"rating_"+str(i)] is not None and int(st.session_state[KP+"rating_"+str(i)]) < 5:
                st.markdown("Highlight specific issues with generated summary")
                questions = ["The summary missed capturing important details",
                             "The summary contains inaccurate facts",
                             "The summary contains irrelevant facts from within the task/record",
                             "The summary contains irrelevant facts from outside the task/record",
                             "The summary has mixed up attributing who said what (for example, the agent and user)",
                             "The summary has details captured in wrong places/sections"]
                for j in range(len(questions)):
                    st.radio(questions[j], options=["Agree", "Somewhat agree", "Do not agree"], horizontal=True,
                             key=KP+"rating_opinion_"+str(i)+"_"+str(j))
            st.text_area("Comments", key=KP+"rating_comment_"+str(i))


def show_context_and_summaries():
    cols = st.columns(2)
    with cols[0]:
        show_context()
    with cols[1]:
        st.markdown("Step 1 of 2: Rate the generated summaries")
        show_summaries()
        st.markdown("Step 2 of 2: Write your summary")
        st.text_area("User provided summary (Optional)", key=KP+"user_provided_summary")


def now_summary_box():
    # Incident Id
    st.title(st.session_state[KP+"files"][st.session_state[KP+"fileId"]].split('_')[1].split('.')[0])
    show_task_info()
    show_band2()
    show_context_and_summaries()


def now_summary():
    if KP+"files" not in st.session_state:
        st.session_state[KP+"files"] = os.listdir("./data/redventures")
        st.session_state[KP+"fileId"] = 0
    if KP+"file_read" not in st.session_state or st.session_state[KP+"file_read_id"] != st.session_state[KP+"fileId"]:
        fpath = os.path.join("./data/redventures", st.session_state[KP+"files"][st.session_state[KP+"fileId"]])
        with open(fpath) as fh:
            st.session_state[KP+"file_content"] = json.load(fh)
        st.session_state[KP+"file_read_id"] = st.session_state[KP+"fileId"]
    now_summary_box()


if __name__ == '__main__':
    now_summary()
