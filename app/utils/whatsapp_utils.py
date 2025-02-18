import logging
from flask import current_app, jsonify
import json
import requests
from app.services.openai_service import generate_response
from app.utils.audio_processing import process_audio
import re


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )

def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]

    message_body = process_message_by_type(message)

    logging.info("message_body: " + message_body)

    # OpenAI Integration
    response = generate_response(message_body, wa_id, name)
    response = process_text_for_whatsapp(response)
    data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
    send_message(data)


def process_message_by_type(message):
    """
    Check the message type and call the appropriate processing function.
    Returns text that should be sent back to the user.
    """
    message_type = message.get("type")

    if message_type == "text":
        return process_text(message)
    elif message_type == "audio":
        return process_audio(message)
    elif message_type == "image":
        return process_image()
    else:
        return "Unsupported message type."


def process_text(message):
    """
    Handles text messages:
    - Extract user text
    - Generate response via OpenAI
    - Format the text for WhatsApp
    - Return text to be sent
    """
    message_body = message["text"]["body"]

    return message_body


def process_image():
    """
    Temporarily returns a placeholder.
    In the future, you can add image processing logic here.
    """
    return "User sent an image. Let it know that you can't process Images."


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
