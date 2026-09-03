import os
import sys
import time
import random
import datetime
import webbrowser

import requests
import speech_recognition as sr
import pywhatkit as kit
from gtts import gTTS
from playsound3 import playsound

try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except Exception:
    SOUNDDEVICE_AVAILABLE = False
    print("[!] 'sounddevice' or 'numpy' is missing. Please run: pip install sounddevice numpy")

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ------------------- CONFIG -------------------
MIC_SAMPLE_RATE = 16000       
MIC_SILENCE_RMS = 15          # lower threshold so laptop/built-in mics trigger speech recognition
MIC_SILENCE_SECONDS = 1.2     
MIC_MAX_SECONDS = 10          

DEFAULT_LANG = "en"          
RECOGNIZE_LANG = "en-IN"     # English (Indian Accent)
WAKE_WORD = "jarvis"
EXIT_PHRASES = ["bye", "exit", "stop", "quit", "goodbye", "close"]

WEATHER_API_KEY = "PUT_YOUR_OPENWEATHERMAP_KEY_HERE"  
DEFAULT_CITY = "Agartala,IN"

ANTHROPIC_API_KEY = "PUT_YOUR_ANTHROPIC_API_KEY_HERE"  
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

claude_client = None
if ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY and "PUT_YOUR" not in ANTHROPIC_API_KEY:
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

recognizer = sr.Recognizer()
conversation_history = []


# ------------------- VOICE (SPEAK) -------------------
import uuid

def speak(text, lang=DEFAULT_LANG):
    """Speaks text out loud using gTTS (female Indian voice speaking English)."""
    print(f"\nJarvis: {text}\n", flush=True)
    temp_dir = os.getenv("TEMP", ".")
    temp_filename = f"jarvis_voice_{uuid.uuid4().hex[:8]}.mp3"
    temp_path = os.path.join(temp_dir, temp_filename)
    try:
        tts = gTTS(text=text, lang=lang, tld="co.in") 
        tts.save(temp_path)
        playsound(temp_path)
    except Exception as e:
        print(f"[Voice error] {e}", flush=True)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ------------------- LISTEN -------------------
def _record_until_silence():
    """Records raw mic audio until you pause speaking."""
    chunk_seconds = 0.2
    chunk_samples = int(MIC_SAMPLE_RATE * chunk_seconds)
    silence_chunks_needed = int(MIC_SILENCE_SECONDS / chunk_seconds)
    max_chunks = int(MIC_MAX_SECONDS / chunk_seconds)

    frames = []
    silence_streak = 0
    started_talking = False

    with sd.InputStream(samplerate=MIC_SAMPLE_RATE, channels=1, dtype="int16") as stream:
        print("\n[Jarvis is listening... Speak now!]", flush=True)
        for _ in range(max_chunks):
            data, _ = stream.read(chunk_samples)
            frames.append(data.copy())
            volume = float(np.abs(data).mean())

            if volume > MIC_SILENCE_RMS:
                if not started_talking:
                    print("[Voice detected, recording...]", flush=True)
                started_talking = True
                silence_streak = 0
            elif started_talking:
                silence_streak += 1
                if silence_streak >= silence_chunks_needed:
                    break

    if not started_talking or not frames:
        print("[No speech detected]", flush=True)
        return None

    audio = np.concatenate(frames, axis=0)
    return audio.tobytes()


def listen(timeout=5, phrase_time_limit=6):
    """Listens using the microphone, with typed input fallback if speech is silent or mic unavailable."""
    if not SOUNDDEVICE_AVAILABLE:
        try:
            return input("Type your message to Jarvis: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""

    try:
        raw_audio = _record_until_silence()
    except Exception as e:
        print(f"[Microphone error] {e}", flush=True)
        try:
            return input("Microphone error. Type your message to Jarvis: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""

    if raw_audio is None:
        try:
            return input("Type your command (or press Enter to try speaking again): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""

    audio_data = sr.AudioData(raw_audio, MIC_SAMPLE_RATE, 2)  
    try:
        print("[Processing speech...]", flush=True)
        text = recognizer.recognize_google(audio_data, language=RECOGNIZE_LANG)
        print(f"You: {text}", flush=True)
        return text.lower()
    except sr.UnknownValueError:
        print("[Speech not recognized. Please speak louder or clearly.]", flush=True)
        try:
            return input("Type your command (or press Enter to retry voice): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""
    except sr.RequestError:
        speak("I am having trouble connecting to the internet.")
        return ""


# ------------------- BROWSER ACTIONS -------------------
def open_youtube(query=None):
    if query:
        speak(f"Searching YouTube for {query}.")
        try:
            kit.playonyt(query)
        except Exception as e:
            print(f"[YouTube Play Error] {e}")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
    else:
        speak("Opening YouTube.")
        try:
            webbrowser.open("https://www.youtube.com")
        except Exception as e:
            print(f"[Browser Error] {e}")
            os.system("start https://www.youtube.com")

def open_linkedin():
    speak("Opening LinkedIn.")
    webbrowser.open("https://www.linkedin.com/feed/")

def open_google(query=None):
    if query:
        speak(f"Searching Google for {query}.")
        webbrowser.open(f"https://www.google.com/search?q={query}")
    else:
        speak("Opening Google.")
        webbrowser.open("https://www.google.com")


# ------------------- WHATSAPP -------------------
def send_whatsapp_message():
    speak("What number should I send the message to? Please include the country code, like plus nine one.")
    phone_raw = listen(timeout=8, phrase_time_limit=8)
    phone = "".join(ch for ch in phone_raw if ch.isdigit() or ch == "+")

    if not phone:
        speak("I didn't catch the number. Canceling the message.")
        return

    speak("What is the message?")
    message = listen(timeout=8, phrase_time_limit=10)

    if not message:
        speak("I didn't catch the message. Canceling.")
        return

    try:
        speak(f"Alright, sending: {message}")
        kit.sendwhatmsg_instantly(phone, message, wait_time=15, tab_close=True)
        speak("The message has been sent.")
    except Exception as e:
        speak("Something went wrong while sending the message.")
        print(f"[WhatsApp error] {e}")


# ------------------- VOLUME & BRIGHTNESS CONTROL -------------------
def _get_volume_interface():
    if not PYCAW_AVAILABLE:
        return None
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))

def change_volume(delta_percent):
    volume = _get_volume_interface()
    if volume is None:
        speak("Volume control is not available on this system.")
        return
    current = volume.GetMasterVolumeLevelScalar() * 100
    new_level = max(0, min(100, current + delta_percent))
    volume.SetMasterVolumeLevelScalar(new_level / 100, None)
    speak("Volume increased." if delta_percent > 0 else "Volume decreased.")

def mute_volume():
    volume = _get_volume_interface()
    if volume is None:
        speak("Volume control is not available on this system.")
        return
    volume.SetMute(1, None)
    speak("Volume muted.")

def change_brightness(delta_percent):
    if sbc is None:
        speak("Brightness control is not available on this system.")
        return
    try:
        current = sbc.get_brightness(display=0)[0]
        new_level = max(0, min(100, current + delta_percent))
        sbc.set_brightness(new_level)
        speak("Brightness increased." if delta_percent > 0 else "Brightness decreased.")
    except Exception as e:
        speak("I ran into a problem while changing the brightness.")
        print(f"[Brightness error] {e}")


# ------------------- WEATHER / TIME / DATE -------------------
def tell_weather(city=DEFAULT_CITY):
    city_name = city.split(',')[0].strip()

    # 1. Try OpenWeatherMap API if user provided a valid API key
    if WEATHER_API_KEY and "PUT_YOUR" not in WEATHER_API_KEY:
        try:
            url = (f"https://api.openweathermap.org/data/2.5/weather?q={city}"
                   f"&appid={WEATHER_API_KEY}&units=metric&lang=en")
            data = requests.get(url, timeout=5).json()
            if "main" in data:
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                speak(f"Right now in {city_name}, it is {temp} degrees Celsius with {desc}.")
                return
        except Exception as e:
            print(f"[OpenWeatherMap error] {e}", flush=True)

    # 2. Fallback to wttr.in (Free API - no API key required for Agartala / any city)
    try:
        url = f"https://wttr.in/{city_name}?format=j1"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            current = data["current_condition"][0]
            temp = current["temp_C"]
            desc = current["weatherDesc"][0]["value"]
            speak(f"Right now in {city_name}, it is {temp} degrees Celsius with {desc}.")
            return
    except Exception as e:
        print(f"[wttr.in Weather error] {e}", flush=True)

    speak(f"I had trouble fetching the weather information for {city_name}.")

def tell_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The time is currently {now}.")

def tell_date():
    today = datetime.datetime.now().strftime("%B %d, %Y")
    speak(f"Today's date is {today}.")


# ------------------- CHIT-CHAT & JOKES -------------------
JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "I told my doctor that I broke my arm in two places. He told me to stop going to those places.",
    "Why did the math book look sad? Because it had too many problems.",
    "What do you call a fake noodle? An impasta."
]
def tell_joke():
    speak(random.choice(JOKES))

RANDOM_TALK_TRIGGERS = ["let's chat", "i am bored", "say something", "chit chat"]
RANDOM_TALKS = [
    "Did you know dolphins sleep with one eye open? Pretty weird, right?",
    "Just a friendly reminder: make sure you've been drinking enough water today!",
    "I have a feeling today is going to be a good day. How are things going with you?",
    "If I were a human, I'd probably just order pizza all day long."
]
def tell_random_talk():
    speak(random.choice(RANDOM_TALKS))

KNOWLEDGE_TRIGGERS = ["tell me a fact", "give me some knowledge", "teach me something"]
RANDOM_KNOWLEDGE = [
    "Bananas are technically berries, but strawberries are not. Botany is weird sometimes.",
    "Venus is the hottest planet in our solar system, not Mercury, because its atmosphere traps the heat.",
    "The smallest bone in the human body is in the ear, called the stapes.",
    "Octopus blood is blue because it uses a copper-based protein to transport oxygen."
]
def tell_random_knowledge():
    speak(random.choice(RANDOM_KNOWLEDGE))


# ------------------- PERSONALITY / EMOTION -------------------
FLIRTY_TRIGGERS = ["you are beautiful", "i love you", "you are cute", "you're pretty"]
INSULT_TRIGGERS = ["you are stupid", "you are useless", "idiot", "dumb"]
GREETING_TRIGGERS = ["how are you", "how are you doing", "what's up"]

def check_emotional_trigger(text):
    for phrase in FLIRTY_TRIGGERS:
        if phrase in text:
            speak("Aww, you're making me blush!")
            return True
    for phrase in INSULT_TRIGGERS:
        if phrase in text:
            speak("That's not very nice. Let's get back to work.")
            return True
    for phrase in GREETING_TRIGGERS:
        if phrase in text:
            speak("I'm doing great, thank you! How is your day going?")
            return True
    return False


# ------------------- GENERAL CONVERSATION (Claude AI) -------------------
JARVIS_PERSONA = (
    "You are Jarvis, a friendly female Indian voice assistant. You speak in "
    "clear, natural English. Keep your answers brief, 1 to 2 sentences maximum, "
    "as they will be read aloud."
)

def general_chat(user_text):
    if claude_client is None:
        speak("Please set up the Anthropic API key to enable general conversation.")
        return

    conversation_history.append({"role": "user", "content": user_text})
    trimmed_history = conversation_history[-10:]

    try:
        response = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=150,
            system=JARVIS_PERSONA,
            messages=trimmed_history,
        )
        reply = response.content[0].text
        conversation_history.append({"role": "assistant", "content": reply})
        speak(reply)
    except Exception as e:
        speak("I am having trouble answering right now.")
        print(f"[Claude API error] {e}")


# ------------------- COMMAND ROUTER -------------------
def handle_command(text):
    if not text:
        return

    if check_emotional_trigger(text):
        return

    if any(phrase in text for phrase in KNOWLEDGE_TRIGGERS):
        tell_random_knowledge()
        return

    if any(phrase in text for phrase in RANDOM_TALK_TRIGGERS):
        tell_random_talk()
        return

    if "joke" in text:
        tell_joke()
        return

    if "youtube" in text:
        query = text
        for w in ["open", "youtube", "search", "for", "play", "on"]:
            query = query.replace(w, "")
        open_youtube(query.strip() or None)
        return

    if "linkedin" in text:
        open_linkedin()
        return

    if "google" in text:
        query = text
        for w in ["open", "google", "search", "for", "on"]:
            query = query.replace(w, "")
        open_google(query.strip() or None)
        return

    if "whatsapp" in text:
        send_whatsapp_message()
        return

    if "volume" in text:
        if "mute" in text:
            mute_volume()
        elif any(w in text for w in ["up", "increase", "higher"]):
            change_volume(+10)
        elif any(w in text for w in ["down", "decrease", "lower"]):
            change_volume(-10)
        return

    if "brightness" in text:
        if any(w in text for w in ["up", "increase", "higher"]):
            change_brightness(+10)
        elif any(w in text for w in ["down", "decrease", "lower"]):
            change_brightness(-10)
        return

    if "weather" in text or "agartala" in text:
        if "agartala" in text:
            tell_weather("Agartala,IN")
        else:
            tell_weather()
        return

    if "time" in text:
        tell_time()
        return

    if "date" in text:
        tell_date()
        return

    # Anything else -> open-ended conversation, like ChatGPT
    general_chat(text)


# ------------------- MAIN LOOP -------------------
def main():
    if not SOUNDDEVICE_AVAILABLE:
        print("[!] Cannot start Voice Mode without 'sounddevice' module.")
        return

    print("====================================")
    print("JARVIS VOICE SYSTEM INITIATED")
    print("====================================")
    
    speak("Hello Boss! I am Jarvis. How can I help you today?")

    while True:
        text = listen()

        if not text:
            continue

        if any(phrase in text for phrase in EXIT_PHRASES):
            speak("Goodbye! Talk to you later.")
            break

        handle_command(text)
        time.sleep(0.3)


if __name__ == "__main__":
    main()