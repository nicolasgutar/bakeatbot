import os
import requests
import logging
import base64
from flask import current_app

def download_audio(media_id):
    """
    Download the audio file from WhatsApp servers.
    """
    metadata_url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{media_id}"
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }
    metadata_response = requests.get(metadata_url, headers=headers)

    if metadata_response.status_code != 200:
        logging.error("Failed to get metadata from WhatsApp.")
        return None

    try:
        metadata_json = metadata_response.json()
        audio_url = metadata_json.get("url")
        if not audio_url:
            logging.error("No audio URL found in metadata.")
            return None
    except ValueError:
        logging.error("Failed to parse metadata JSON.")
        return None
    audio_response = requests.get(audio_url, headers=headers)

    if audio_response.status_code == 200:
        with open("debug_audio.ogg", "wb") as f:
            f.write(audio_response.content)
        return audio_response.content
    else:
        logging.error("Failed to download audio file.")
        return None

def convert_audio_to_base64(audio_bytes):
    """
    Convert the raw audio bytes directly to base64 for Google STT API.
    """
    return base64.b64encode(audio_bytes).decode("utf-8")

def transcribe_audio(audio_base64):
    """
    Send Base64-encoded audio to Google STT API using API Key.
    """
    GOOGLE_CLOUD_API_KEY = os.getenv("GOOGLE_CLOUD_API_KEY")

    if not GOOGLE_CLOUD_API_KEY:
        logging.error("Google Cloud API Key is missing.")
        return "Google Cloud API Key is not set."

    url = f"https://speech.googleapis.com/v1/speech:recognize?key={GOOGLE_CLOUD_API_KEY}"

    payload = {
        "config": {
            "encoding": "OGG_OPUS",
            "sampleRateHertz": 48000,
            "languageCode": "es-ES",
            "enableAutomaticPunctuation": True
        },
        "audio": {
            "content": audio_base64
        }
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        response_json = response.json()
        if "results" in response_json and response_json["results"]:
            return response_json["results"][0]["alternatives"][0]["transcript"]
        else:
            return "Could not transcribe the audio."
    else:
        logging.error(f"Google STT API Error: {response.text}")
        return "Error processing audio."

def process_audio(message):
    """
    Process an audio message:
    1. Download the file from WhatsApp.
    2. Convert it to Base64.
    3. Transcribe it using Google STT.
    4. Send transcribed text to OpenAI.
    5. Return AI-generated response.
    """
    media_id = message["audio"]["id"]

    # Step 1: Download audio
    audio_bytes = download_audio(media_id)
    if not audio_bytes:
        return "Error retrieving the audio file."

    # Step 2: Convert directly to Base64 (no intermediate WAV file)
    audio_base64 = convert_audio_to_base64(audio_bytes)

    # Step 3: Transcribe audio
    transcribed_text = transcribe_audio(audio_base64)

    return transcribed_text
