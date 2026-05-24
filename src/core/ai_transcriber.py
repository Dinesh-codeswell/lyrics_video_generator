import requests
import time
import os
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch API Key from environment
API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

BASE_URL = "https://api.assemblyai.com/v2"
HEADERS = {"authorization": API_KEY}

def transcribe_audio(audio_path: Path) -> List[Dict[str, Any]]:
    """
    Sends audio to AssemblyAI, polls for result, and returns word-level timestamps.
    """
    # 1. Upload the file
    print(f"Uploading {audio_path.name} to AssemblyAI...")
    with open(audio_path, "rb") as f:
        response = requests.post(f"{BASE_URL}/upload", headers=HEADERS, data=f)
    
    upload_url = response.json()["upload_url"]

    # 2. Request transcription
    print("Requesting transcription...")
    data = {
        "audio_url": upload_url,
        "word_boost": ["verse", "chorus"], # Subtle boost for music structure
        "filter_profanity": False,
    }
    response = requests.post(f"{BASE_URL}/transcript", headers=HEADERS, json=data)
    transcript_id = response.json()["id"]

    # 3. Polling for results
    print("AI is analyzing audio (polling)...")
    while True:
        status_response = requests.get(f"{BASE_URL}/transcript/{transcript_id}", headers=HEADERS)
        result = status_response.json()

        if result["status"] == "completed":
            print("Transcription complete!")
            return result["words"]
        elif result["status"] == "error":
            raise Exception(f"AI Transcription failed: {result['error']}")
        
        time.sleep(3) # Wait before polling again

def group_words_into_lines(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    The 'Smart Grouper' algorithm.
    Groups individual words into readable lyric lines based on:
    - Punctuation
    - Gaps > 1.0 second
    - Line length (max 8-10 words)
    """
    if not words:
        return []

    lines = []
    current_line_words = []
    
    for i, word_data in enumerate(words):
        text = word_data["text"]
        start = word_data["start"] / 1000.0 # API returns ms, we use seconds
        end = word_data["end"] / 1000.0
        
        current_line_words.append({
            "text": text,
            "start": start,
            "end": end
        })

        # Logic to decide if we should cut the line here
        should_cut = False
        
        # 1. Punctuation cut
        if text.endswith((".", "?", "!", ",")):
            should_cut = True
            
        # 2. Time gap cut (Gap to next word > 1s)
        if i < len(words) - 1:
            next_start = words[i+1]["start"] / 1000.0
            if (next_start - end) > 1.0:
                should_cut = True
        
        # 3. Max length cut (8 words for readability)
        if len(current_line_words) >= 8:
            should_cut = True

        if should_cut or i == len(words) - 1:
            line_text = " ".join([w["text"] for w in current_line_words])
            line_start = current_line_words[0]["start"]
            
            lines.append({
                "time": line_start,
                "text": line_text
            })
            current_line_words = []

    return lines

def generate_ai_lyrics(audio_path: Path, song_title: str, artist: str = "Unknown Artist") -> Dict[str, Any]:
    """
    Main entry point: Transcribes -> Groups -> Returns project-ready JSON.
    """
    try:
        raw_words = transcribe_audio(audio_path)
        lyric_lines = group_words_into_lines(raw_words)
        
        return {
            "title": song_title,
            "artist": artist,
            "lyrics": lyric_lines
        }
    except Exception as e:
        print(f"Error in generate_ai_lyrics: {e}")
        raise
