import openai
import shelve
from dotenv import load_dotenv
import os
import time
import logging

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

# Initialize OpenAI client with v2 header
client = openai.OpenAI(api_key=OPENAI_API_KEY, default_headers={'OpenAI-Beta': 'assistants=v2'})


def check_if_thread_exists(wa_id):
    """ Check if a thread exists for the given WhatsApp ID """
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)


def store_thread(wa_id, thread_id):
    """ Store a new thread ID for a WhatsApp user """
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id


def run_assistant(thread_id, name):
    """ Run the assistant and wait for a response """
    # Start the assistant's response
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=OPENAI_ASSISTANT_ID,
    )

    # Wait for the assistant to complete the response
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status == "completed":
            break
        time.sleep(0.5)

    # Retrieve the last message
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    new_message = messages.data[0].content[0].text.value
    logging.info(f"Generated message: {new_message}")

    return new_message


def generate_response(message_body, wa_id, name):

    # Check if an existing thread is available
    thread_id = check_if_thread_exists(wa_id)

    # Create a new thread if none exists
    if thread_id is None:
        logging.info(f"Creating new thread for {name} with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id)
        thread_id = thread.id
    else:
        logging.info(f"Retrieving existing thread for {name} with wa_id {wa_id}")

    # Add user's message to the thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    # Run the assistant and return its response
    return run_assistant(thread_id, name)

