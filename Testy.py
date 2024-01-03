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

def load_config(config_path='config.yaml'):
    with open(config_path, 'r') as file:
        return yaml.load(file, Loader=SafeLoader)

def save_config(config, config_path='config.yaml'):
    with open(config_path, 'w') as file:
        yaml.dump(config, file, Dumper=SafeDumper)

def hash_secret_key(secret_key):
    return hashlib.sha256(secret_key.encode()).hexdigest()

def verify_secret_key(input_secret_key, stored_hashed_secret_key):
    input_hashed = hash_secret_key(input_secret_key)
    return input_hashed == stored_hashed_secret_key

st.set_page_config(
    page_title="Talent Solutions",
    page_icon="🧊",
    layout='wide',
)

config = load_config()

if 'registration_form' not in st.session_state:
    st.session_state['registration_form'] = False

if 'reset_password_form' not in st.session_state:
    st.session_state['reset_password_form'] = False

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

name, authentication_status, username = authenticator.login('Login', 'main')

if not authentication_status:
    if st.button('Create Account'):
        st.session_state['registration_form'] = True

    if st.session_state['registration_form']:
        new_username = st.text_input("Username", key="new_username")
        new_name = st.text_input("Full Name", key="new_name")
        new_email = st.text_input("Email", key="new_email")
        new_password = st.text_input("Password", type="password", key="new_password")
        secret_key = st.text_input("Secret Key", type="password", key="secret_key")

        if st.button('Register', key='register_button'):
        # Vérifiez si tous les champs sont remplis
            if new_username and new_name and new_email and new_password and secret_key:
                hashed_password = Hasher([new_password]).generate()[0]
                hashed_secret_key = hash_secret_key(secret_key)

                config['credentials']['usernames'][new_username] = {
                    'name': new_name,
                    'email': new_email,
                    'password': hashed_password,
                    'secret_key': hashed_secret_key
                }

                save_config(config)
                st.success('User registered successfully')
                st.session_state['registration_form'] = False
            else:
                st.error("Please fill in all fields")

    if st.button('Forgot Password'):
        st.session_state['reset_password_form'] = True
    if st.session_state['reset_password_form']:
        fp_username = st.text_input("Enter your username", key="fp_username")
        fp_secret_key = st.text_input("Enter your secret key", type="password", key="fp_secret_key")
    
        if st.button('Verify Secret Key', key='verify_key'):
            user_info = config['credentials']['usernames'].get(fp_username)
            if user_info and verify_secret_key(fp_secret_key, user_info.get('secret_key')):
                st.success("Secret key verified. You can now reset your password.")
                st.session_state['verified_secret_key'] = True
            else:
                st.error("Invalid secret key or username")
    
    if st.session_state.get('verified_secret_key', False):
        new_password2 = st.text_input("Enter your new password", type="password", key="new_password2")
        if st.button('Confirm New Password', key='conf_password'):
            hashed_password2 = stauth.Hasher([new_password2]).generate()[0]
            #print("New hashed password:", hashed_password2)  # For debugging
            config['credentials']['usernames'][fp_username]['password'] = hashed_password2
            save_config(config)
            st.success("Password reset successfully")
            st.session_state['reset_password_form'] = False
            st.session_state['verified_secret_key'] = False  # Reset l'état
    
    

elif authentication_status:
    st.write(f'Welcome {name}')
    if authenticator.logout('Logout', 'main', key='unique_key'):
        st.write("You have been logged out!")

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
    
    # Set up the page
    st.sidebar.image('TS.png',use_column_width=True)
    st.sidebar.title("SAM l'expert emploi")
    st.sidebar.divider()
    
    # Select Assistant
    st.session_state.selected_assistant = "asst_OmqTkgUMqoPEOX4boQ7EGxbz"
    st.sidebar.markdown("Je m’appelle Sam, je suis expert.e emploi en France. Je suis une intelligence artificielle au service de l’accompagnement Activ’Projet. Je suis là pour vous donner des idées et ouvrir des pistes de réflexion")
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
                        st.markdown(message_text)
    
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
elif authentication_status == False:
    st.error('Username/password is incorrect')

elif authentication_status == None:
    st.warning('Please enter your username and password')

