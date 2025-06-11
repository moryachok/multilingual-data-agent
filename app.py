import streamlit as st
from utils import FabricLakehousePlugin, handle_intermediate_steps
import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread, AzureAIAgentSettings
from dotenv import load_dotenv
import logging
import nest_asyncio
import yaml

load_dotenv()
nest_asyncio.apply()

file_handler = logging.FileHandler("logs/streamlit_agent_chat.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))
logger = logging.getLogger("streamlit-agent-chat")
logger.addHandler(file_handler)
logger.setLevel(logging.DEBUG)

with open("config/config.yml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
page_title = config.get("streamlit", {}).get("page_title")
chat_input_placeholder = config.get("streamlit", {}).get("chat_input_placeholder")
sidebar_header = config.get("streamlit", {}).get("sidebar", {}).get("header")
sidebar_subheader = config.get("streamlit", {}).get("sidebar", {}).get("subheader")
st.set_page_config(page_title=page_title, layout="centered")

# Inject RTL and Hebrew font support
st.markdown(
    """
    <style>
    body, .stApp, .stTextInput, .stChatMessage, .stMarkdown, .stButton, .stTitle {
        direction: rtl;
        text-align: right;
        font-family: 'Arial', 'Noto Sans Hebrew', 'sans-serif';
    }
    .stChatMessage {
        background-color: #f0f0f5;
        border-radius: 12px;
        margin-bottom: 8px;
        padding: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title(page_title)

# Add sidebar with thread ID information
with st.sidebar:
    st.header(sidebar_header)
    st.markdown("""
    **Thread ID:**
      <span style='direction:ltr;display:inline-block;font-family:monospace;background:#eee;padding:2px 6px;border-radius:4px;'>%s</span>
    """ % (st.session_state.get("agent_thread_id", "EMPTY")), unsafe_allow_html=True)
    st.subheader(sidebar_subheader)
    sample_questions = config.get("streamlit", {}).get("sample_questions", [])
    if sample_questions:
        st.markdown("\n".join(f"- {q}" for q in sample_questions), unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

async def ask_agent(user_input):
    logger.info(f"ask_agent() called with user_input: {user_input}")
    thread_id = st.session_state.get("agent_thread_id", None)
    response_text = ""
    async with DefaultAzureCredential() as creds:
        async with AzureAIAgent.create_client(credential=creds, endpoint=os.getenv("AI_FOUNDRY_ENDPOINT")) as client:
            agent_definition = await client.agents.get_agent(agent_id="asst_nhJVNQtc0TCrVIGuMtZ7LBo6")
            agent = AzureAIAgent(
                client=client,
                definition=agent_definition,
                plugins=[FabricLakehousePlugin(database="insurance")],
            )
            async for response in agent.invoke(
                messages=user_input,
                thread_id=thread_id,
                on_intermediate_message=handle_intermediate_steps,
            ):
                logger.debug(f"Agent response: {response}")
                response_text = str(response)
                st.session_state.agent_thread_id = response.thread.id if response.thread else None
    logger.info(f"ask_agent() returning response: {response_text}")
    return response_text

# React to user input
if prompt := st.chat_input(chat_input_placeholder):
    logger.info(f"User input: {prompt}")
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Call the agent and get the response
    response = asyncio.get_event_loop().run_until_complete(ask_agent(prompt))
    logger.info(f"Agent response (raw): {response}")
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
