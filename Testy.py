# Importing required packages
import streamlit as st
import openai
import uuid
import time
import pandas as pd
import io
import os
from openai import OpenAI


# Initialize OpenAI client
client = OpenAI()

# Your chosen model
MODEL = "gpt-4-1106-preview"

# Initialize session state variables
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "run" not in st.session_state:
    st.session_state.run = {"status": None}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "retry_error" not in st.session_state:
    st.session_state.retry_error = 0

if "selected_assistant" not in st.session_state:
    st.session_state.selected_assistant = "name"

st.set_page_config(page_title="Enter title here")

# Select Assistant
user_select=st.selectbox("Sélectionner votre assistant",("ROME V1", "ROME V2"))
st.write('You selected:', user_select)

if user_select == "ROME V1":
    st.session_state.selected_assistant = "asst_aPtDiweLeWDH8hNd3jAOrb4I"
elif user_select == "ROME V2":
    st.session_state.selected_assistant = "asst_4bWW6Rb0sM1CTYMqHQs2NpcD"

# Set up the page
st.sidebar.title("Genius ROME")
st.sidebar.divider()
st.sidebar.markdown(" ", unsafe_allow_html=True)
st.sidebar.markdown("Je suis spécialiste des sujets de compétences, en charge des questions liées aux compétences professionnelles et aux certifications nécessaires pour divers métiers. Je peux vous fournir des informations telles que la liste des compétences d'un métier spécifique, ainsi que les certifications requises, à partir des fichiers ROME que j'ai à ma disposition. Ces fichiers couvrent les familles de métiers, les métiers eux-mêmes et les compétences associées. De quoi avez-vous besoin ?")
st.sidebar.divider()
st.sidebar.markdown("Si vous voulez me demander quelque chose, soyez polis et surtout concis !")
st.sidebar.divider()
st.sidebar.write("Assistant sélectionné",user_select,st.session_state.selected_assistant)

# Initialize OpenAI assistant
if "assistant" not in st.session_state:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    st.session_state.assistant = openai.beta.assistants.retrieve(st.session_state.selected_assistant)
    st.session_state.thread = client.beta.threads.create(
        metadata={'session_id': st.session_state.session_id}
    )

# Display chat messages
elif hasattr(st.session_state.run, 'status') and st.session_state.run.status == "completed":
    st.session_state.messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread.id
    )
    for message in reversed(st.session_state.messages.data):
        if message.role in ["user", "assistant"]:
            with st.chat_message(message.role):
                for content_part in message.content:
                    message_text = content_part.text.value
                    st.markdown(message_text)

# Chat input and message creation with file ID
if prompt := st.chat_input("Crachez le morceau !"):
    with st.chat_message('user'):
        st.write(prompt)

    message_data = {
        "thread_id": st.session_state.thread.id,
        "role": "user",
        "content": prompt
    }

    # Include file ID in the request if available
    if "file_id" in st.session_state:
        message_data["file_ids"] = [st.session_state.file_id]

    st.session_state.messages = client.beta.threads.messages.create(**message_data)

    st.session_state.run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread.id,
        assistant_id=st.session_state.selected_assistant,
    )
    if st.session_state.retry_error < 3:
        time.sleep(1)
        st.rerun()

# Handle run status
if hasattr(st.session_state.run, 'status'):
    if st.session_state.run.status == "running":
        with st.chat_message('assistant'):
            st.write("Thinking ......")
        if st.session_state.retry_error < 3:
            time.sleep(1)
            st.rerun()

    elif st.session_state.run.status == "failed":
        st.session_state.retry_error += 1
        with st.chat_message('assistant'):
            if st.session_state.retry_error < 3:
                st.write("Run failed, retrying ......")
                time.sleep(3)
                st.rerun()
            else:
                st.error("FAILED: The OpenAI API is currently processing too many requests. Please try again later ......")

    elif st.session_state.run.status != "completed":
        st.session_state.run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread.id,
            run_id=st.session_state.run.id,
        )
        if st.session_state.retry_error < 3:
            time.sleep(3)
            st.rerun()
