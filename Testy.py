 # Importing required packages
import streamlit as st
import openai
import uuid
import time
import pandas as pd
import io
import os
from openai import OpenAI

os.environ["OPENAI_ASSISTANT"] = "asst_aPtDiweLeWDH8hNd3jAOrb4I"

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

# Set up the page
st.set_page_config(page_title="Enter title here")
st.sidebar.title("Genius ROME")
st.sidebar.divider()
st.sidebar.markdown(" ", unsafe_allow_html=True)
st.sidebar.markdown("Je suis spécialiste des sujets de compétences, en charge des questions liées aux compétences professionnelles et aux certifications nécessaires pour divers métiers. Avec mon attitude franchement peu aimable, je peux vous fournir des informations telles que la liste des compétences d'un métier spécifique, ainsi que les certifications requises, à partir des fichiers ROME que j'ai à ma disposition. Ces fichiers couvrent les familles de métiers, les métiers eux-mêmes et les compétences associées. Allez, crachez le morceau, de quoi avez-vous besoin ?")
st.sidebar.divider()

# Initialize OpenAI assistant
if "assistant" not in st.session_state:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    st.session_state.assistant = openai.beta.assistants.retrieve(os.environ["OPENAI_ASSISTANT"])
    st.session_state.thread = client.beta.threads.create(
        metadata={'session_id': st.session_state.session_id}
    )

# Display chat messages
elif hasattr(st.session_state.run, 'status') and st.session_state.run.status == "completed":
    st.session_state.messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread.id
    )

# Extract the message content
message_content = message.content[0].text
annotations = message_content.annotations
citations = []

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

# display to user
for message in reversed(st.session_state.messages.data):
   if message.role in ["user", "assistant"]:
      with st.chat_message(message.role):
          for content_part in message.content:
              message_text = content_part.text.value
              st.markdown(message_text)

# Chat input and message creation with file ID
if prompt := st.chat_input("Comment puis-je vous aider ?"):
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
        assistant_id=st.session_state.assistant.id,
    )
    if st.session_state.retry_error < 3:
        time.sleep(1)
        st.rerun()

# Extract the message content
message_content = message.content[0].text
annotations = message_content.annotations
citations = []
