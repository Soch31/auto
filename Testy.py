# Importing required packages
import streamlit as st
import openai
import uuid
import time
import pandas as pd
import io
import os
from openai import OpenAI
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from yaml.dumper import SafeDumper
from streamlit_authenticator import Hasher
import hashlib

# Initialize OpenAI client
client = OpenAI()

# Your chosen model
MODEL = "gpt-3.5-turbo-1106"

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

st.set_page_config(page_title="Auto specialist")

# Set up the page
st.sidebar.image('TS.png',use_column_width=True)
st.sidebar.title("Bob expert auto")
st.sidebar.divider()

# Select Assistant
st.session_state.selected_assistant = "asst_so6ra1jPtNThyYeebycqfsLr"
st.sidebar.markdown(" Avez-vous des questions spécifiques sur le marché de l'industrie automobile, les perspectives d'emploi ou les évolutions des compétences dans ce secteur ? Je suis là pour vous répondre !")
st.sidebar.divider()

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
                    message_content = content_part.text
                    annotations = message_content.annotations
                    # Iterate over the annotations and add footnotes
                    for index, annotation in enumerate(annotations):
                        # Replace the text with a footnote
                        message_content.value = message_content.value.replace(annotation.text, f' [{index}]')
                    
                        # Gather citations based on annotation attributes
                        if (file_citation := getattr(annotation, 'file_citation', None)):
                            cited_file = client.files.retrieve(file_citation.file_id)
                            citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
                        elif (file_path := getattr(annotation, 'file_path', None)):
                            cited_file = client.files.retrieve(file_path.file_id)
                            citations.append(f'[{index}] Click <here> to download {cited_file.filename}')
                            # Note: File download functionality not implemented above for brevity
                    
                    # Add footnotes to the end of the message before displaying to user
                    message_content.value += '\n' + '\n'.join(citations)
                    st.markdown(message_content)

# Chat input and message creation with file ID
if prompt := st.chat_input(""):
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

