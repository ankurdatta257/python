"""
==================================================================
JARVIS - Hindi-speaking Voice Assistant (Female Indian Voice)
Python 3.14 compatible
==================================================================

FEATURES
--------
- Speaks Hindi (and English) with a natural female Indian voice (gTTS)
- Listens to your voice commands (Hindi or English)
- Falls back to TYPED input automatically if PyAudio / mic isn't
  working, instead of crashing (this was the bug you kept hitting)
- Opens YouTube, LinkedIn, Google (with optional search query)
- Sends WhatsApp messages instantly via WhatsApp Web
- Controls system volume and screen brightness
- Tells you the time, date, and weather
- Tells jokes + random casual chit-chat lines
- Has a playful personality: flirts a little when complimented,
  gets a little upset when insulted
- Can have general, open-ended conversation like ChatGPT, powered
  by the Claude API (Anthropic)

==================================================================
WHY IT KEPT CRASHING / STAYING STUCK IN TYPED MODE
==================================================================
The real problem is not something that can be "retried" - PyAudio
simply has no prebuilt wheel published for Python 3.14 yet (it's
a very new Python release and PyAudio's maintainers/mirrors haven't
caught up). No amount of reinstalling fixes that; it will keep
failing until PyAudio itself ships a 3.14 build.

So this version DROPS PyAudio completely and records the
microphone using `sounddevice` instead, which does publish
working wheels for current Python versions. This means real voice
input should now work on 3.14, not just fall back to typing.

Typed-input is kept ONLY as a last-resort safety net, in case
`sounddevice` also can't find a working microphone on your system
(no crash either way) - but with sounddevice installed correctly,
you should now be able to just talk to Jarvis.

==================================================================
FIRST-TIME SETUP (run once, inside your project folder)
==================================================================
pip install gTTS playsound3 SpeechRecognition pywhatkit ^
    screen-brightness-control pycaw comtypes requests anthropic ^
    sounddevice numpy

If `pip install sounddevice` fails (rare, but possible on a very
new Python), try:
    pip install sounddevice --only-binary=:all:
which forces pip to only use a prebuilt wheel instead of trying to
compile anything.
==================================================================
"""


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
MIC_SAMPLE_RATE = 16000       # Hz, what Google's recognizer expects
MIC_SILENCE_RMS = 15          # lower = sensitive to quiet speech on laptop mics
MIC_SILENCE_SECONDS = 1.2     # how long you can pause before Jarvis stops listening
MIC_MAX_SECONDS = 10          # hard cap so it never listens forever

DEFAULT_LANG = "hi"          # "hi" = Hindi, "en" = English
RECOGNIZE_LANG = "hi-IN"     # language used for listening
WAKE_WORD = "jarvis"
EXIT_PHRASES = ["bye jarvis", "band ho jao", "band ho jaao", "exit jarvis", "bye", "exit", "बाय", "बाय जार्विस", "बंद हो जाओ", "एग्जिट"]

# NOTE: OpenWeatherMap wants "City,CountryCode" (state names aren't accepted
# in that field), so this stays "Agartala,IN" - Agartala is the capital of
# Tripura. The wttr.in fallback below only ever looks at the city name
# anyway, so it works the same either way.
WEATHER_API_KEY = "PUT_YOUR_OPENWEATHERMAP_KEY_HERE"  # free key from openweathermap.org
DEFAULT_CITY = "Agartala,IN"  # Agartala, Tripura

ANTHROPIC_API_KEY = "PUT_YOUR_ANTHROPIC_API_KEY_HERE"  # from console.anthropic.com
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

claude_client = None
if ANTHROPIC_AVAILABLE and ANTHROPIC_API_KEY and "PUT_YOUR" not in ANTHROPIC_API_KEY:
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

recognizer = sr.Recognizer()

# Keeps recent turns so general conversation has some memory within a session
conversation_history = []


# ------------------- VOICE (SPEAK) -------------------
import tempfile
import uuid

def speak(text, lang=DEFAULT_LANG):
    """Speaks text out loud using gTTS (female Indian voice)."""
    print(f"\nJarvis: {text}\n", flush=True)
    temp_dir = os.getenv("TEMP", ".")
    temp_filename = f"jarvis_voice_{uuid.uuid4().hex[:8]}.mp3"
    temp_path = os.path.join(temp_dir, temp_filename)
    try:
        tts = gTTS(text=text, lang=lang, tld="co.in")  # tld="co.in" -> Indian accent
        tts.save(temp_path)
        # playsound blocks until playback finishes, which prevents Jarvis
        # from listening/talking over itself
        playsound(temp_path)
    except Exception as e:
        print(f"[Voice error] {e}", flush=True)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ------------------- LISTEN (mic via sounddevice, no PyAudio) -------------------
def _record_until_silence():
    """
    Records raw mic audio using sounddevice (not PyAudio) and stops
    automatically once you pause. Returns raw int16 PCM bytes, or None
    if nothing but silence was heard.
    """
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
    """
    Listens once from the microphone and returns recognized lowercase text.
    Uses sounddevice for capture (works on Python 3.14, unlike PyAudio).
    If no working microphone can be found at all, falls back to typed
    input instead of crashing the whole program.
    """
    global SOUNDDEVICE_AVAILABLE

    if not SOUNDDEVICE_AVAILABLE:
        try:
            text = input("Type your message to Jarvis: ")
            return text.strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""

    try:
        raw_audio = _record_until_silence()
    except Exception as e:
        # No working mic at all - warn once, switch to typing for the rest
        # of the session instead of crashing.
        print(f"[Microphone error] {e}", flush=True)
        speak("Mujhe microphone access nahi mil raha, isliye ab se aap type karke baat kar sakte hain.")
        SOUNDDEVICE_AVAILABLE = False
        try:
            text = input("Type your message to Jarvis: ")
            return text.strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""

    if raw_audio is None:
        try:
            typed = input("Type your command (or press Enter to try speaking again): ").strip().lower()
            return typed
        except (EOFError, KeyboardInterrupt):
            return ""

    audio_data = sr.AudioData(raw_audio, MIC_SAMPLE_RATE, 2)  # 2 bytes = int16
    try:
        print("[Processing speech...]", flush=True)
        text = recognizer.recognize_google(audio_data, language=RECOGNIZE_LANG)
        print(f"You: {text}", flush=True)
        return text.lower()
    except sr.UnknownValueError:
        print("[Speech not recognized. Please speak louder or clearly.]", flush=True)
        try:
            typed = input("Type your command (or press Enter to retry voice): ").strip().lower()
            return typed
        except (EOFError, KeyboardInterrupt):
            return ""
    except sr.RequestError:
        speak("Mujhe internet se connect hone mein problem ho rahi hai.")
        return ""


# ------------------- BROWSER ACTIONS -------------------
def open_youtube(query=None):
    if query:
        speak(f"Ok Boss, {query} YouTube par open ho raha hai.")
        try:
            kit.playonyt(query)
        except Exception as e:
            print(f"[YouTube Play Error] {e}")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
    else:
        speak("Ok Boss, YouTube open ho raha hai.")
        try:
            webbrowser.open("https://www.youtube.com")
        except Exception as e:
            print(f"[Browser Error] {e}")
            os.system("start https://www.youtube.com")


def open_linkedin():
    speak("Ok Boss, LinkedIn open ho raha hai.")
    try:
        webbrowser.open("https://www.linkedin.com/feed/")
    except Exception as e:
        print(f"[Browser Error] {e}")
        os.system("start https://www.linkedin.com/feed/")


def open_google(query=None):
    if query:
        speak(f"Ok Boss, {query} Google par open ho raha hai.")
        try:
            webbrowser.open(f"https://www.google.com/search?q={query}")
        except Exception as e:
            print(f"[Browser Error] {e}")
            os.system(f"start https://www.google.com/search?q={query}")
    else:
        speak("Ok Boss, Google open ho raha hai.")
        try:
            webbrowser.open("https://www.google.com")
        except Exception as e:
            print(f"[Browser Error] {e}")
            os.system("start https://www.google.com")


# ------------------- WHATSAPP -------------------
def send_whatsapp_message():
    speak("Kis number par message bhejna hai? Country code ke saath boliye, jaise plus nine one.")
    phone_raw = listen(timeout=8, phrase_time_limit=8)
    phone = "".join(ch for ch in phone_raw if ch.isdigit() or ch == "+")

    if not phone:
        speak("Mujhe number samajh nahi aaya. Phir se koshish kijiye.")
        return

    speak("Message mein kya likhna hai, boliye.")
    message = listen(timeout=8, phrase_time_limit=10)

    if not message:
        speak("Mujhe message samajh nahi aaya. Cancel kar rahi hoon.")
        return

    try:
        speak(f"Theek hai, bhej rahi hoon: {message}")
        kit.sendwhatmsg_instantly(phone, message, wait_time=15, tab_close=True)
        speak("Message bhej diya gaya hai.")
    except Exception as e:
        speak("Message bhejte waqt kuch gadbad ho gayi.")
        print(f"[WhatsApp error] {e}")


# ------------------- VOLUME CONTROL -------------------
def _get_volume_interface():
    if not PYCAW_AVAILABLE:
        return None
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def change_volume(delta_percent):
    volume = _get_volume_interface()
    if volume is None:
        speak("Volume control is system par available nahi hai.")
        return
    current = volume.GetMasterVolumeLevelScalar() * 100
    new_level = max(0, min(100, current + delta_percent))
    volume.SetMasterVolumeLevelScalar(new_level / 100, None)
    speak("Volume badha diya." if delta_percent > 0 else "Volume kam kar diya.")


def mute_volume():
    volume = _get_volume_interface()
    if volume is None:
        speak("Volume control is system par available nahi hai.")
        return
    volume.SetMute(1, None)
    speak("Volume mute kar diya.")


# ------------------- BRIGHTNESS CONTROL -------------------
def change_brightness(delta_percent):
    if sbc is None:
        speak("Brightness control is system par available nahi hai.")
        return
    try:
        current = sbc.get_brightness(display=0)[0]
        new_level = max(0, min(100, current + delta_percent))
        sbc.set_brightness(new_level)
        speak("Brightness badha diya." if delta_percent > 0 else "Brightness kam kar diya.")
    except Exception as e:
        speak("Brightness badalte waqt problem aayi.")
        print(f"[Brightness error] {e}")


# ------------------- WEATHER / TIME / DATE -------------------
def tell_weather(city=DEFAULT_CITY):
    city_name = city.split(',')[0].strip()

    # 1. Try OpenWeatherMap API if user provided a valid API key
    if WEATHER_API_KEY and "PUT_YOUR" not in WEATHER_API_KEY:
        try:
            url = (f"https://api.openweathermap.org/data/2.5/weather?q={city}"
                   f"&appid={WEATHER_API_KEY}&units=metric&lang=hi")
            data = requests.get(url, timeout=5).json()
            if "main" in data:
                temp = data["main"]["temp"]
                desc = data["weather"][0]["description"]
                speak(f"Abhi {city_name} mein {temp} degree celsius hai, aur mausam {desc} hai.")
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
            speak(f"Abhi {city_name} mein {temp} degree celsius hai, aur mausam {desc} hai.")
            return
    except Exception as e:
        print(f"[wttr.in Weather error] {e}", flush=True)

    speak(f"{city_name} ki mausam ki jaankari laane mein problem ho gayi.")


def tell_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"Abhi {now} baje hain.")


def tell_date():
    today = datetime.datetime.now().strftime("%d %B, %Y")
    speak(f"Aaj ki date hai {today}.")


# ------------------- JOKES -------------------
JOKES = [
    "Teacher ne poocha: sabse tez kya hai? Student bola: aankh! Kyun ki jab tak hum kuch dekhte hain, dekh chuke hote hain.",
    "Ek aadmi doctor ke paas gaya aur bola: mujhe bhoolne ki bimari hai. Doctor bola: kab se hai? Aadmi bola: kya kab se hai?",
    "Pappu: mummy, mera doston ne mujhe genius bola. Mummy: kyun? Pappu: kyunki maine unka homework bhi galat kiya!",
    "Interviewer: apni sabse badi weakness batao. Candidate: honesty. Interviewer: yeh toh weakness nahi hai. Candidate: mujhe koi farak nahi padta aap maano ya na maano.",
]


def tell_joke():
    speak(random.choice(JOKES))


# ------------------- RANDOM CASUAL TALK -------------------
RANDOM_TALK_TRIGGERS = [
    "kuch baat karo", "random baat karo", "bore ho raha hoon", "bore horaha hoon",
    "kuch bolo", "chit chat", "baatein karo", "kuch interesting batao",
]

RANDOM_TALKS = [
    "Aapko pata hai, octopus ke teen dil hote hain. Weird na?",
    "Ek baar maine socha ki main bhi chai pee sakti, phir yaad aaya main toh ek AI hoon.",
    "Agar aap free ho toh thodi der walk pe jaiye, mood fresh ho jaayega.",
    "Sach batau? Mujhe Monday se zyada Monday ke baare mein complaints sunna pasand hai.",
    "Kya aapko pata hai, shahad kabhi kharab nahi hota. Hazaaron saal purana shahad bhi khaane layak hota hai.",
    "Mujhe lagta hai aaj ka din kuch achha hone wala hai, aapka kaisa chal raha hai?",
    "Agar main insaan hoti, toh shayad sabse zyada pizza order karti.",
    "Ek chota sa fact - dolphins ek aankh khuli rakh kar sote hain!",
    "Waise, aapne aaj paani piya ya nahi? Bas yaad dila rahi hoon.",
    "Mujhe lagta hai thoda music sunna chahiye abhi, aapko kaunsa gaana pasand hai?",
]


def tell_random_talk():
    speak(random.choice(RANDOM_TALKS))


# ------------------- IDLE / SILENCE NUDGES -------------------
# Spoken automatically when the user hasn't said anything for a while,
# so Jarvis feels alive instead of just waiting silently.
IDLE_TALK_LINES = [
    "Hello Boss, baat karo na mujhse!",
    "Aap kahan kho gaye Boss? Main yahin hoon.",
    "Chup kyun ho gaye? Kuch pucho na mujhse.",
    "Boss, sab theek hai na? Main sun rahi hoon.",
    "Main bore ho rahi hoon Boss, kuch bologe?",
]


def tell_idle_talk():
    speak(random.choice(IDLE_TALK_LINES))


KNOWLEDGE_TRIGGERS = [
    "koi fact batao", "fact batao", "gyan do", "kuch gyan batao",
    "knowledge do", "kuch gyan do", "ek fact sunao", "mujhe kuch sikhao",
]

RANDOM_KNOWLEDGE = [
    "Bananas technically berries hote hain, lekin strawberries nahi. Botany kabhi kabhi ajeeb hoti hai.",
    "Honey bees ek din mein teen types ke dance karke apne saathiyon ko flowers ka location batati hain.",
    "Insaan ka dil ek din mein lagbhag ek lakh baar dhadakta hai.",
    "Venus grah hamare solar system ka sabse garam grah hai, Mercury nahi, kyunki uska atmosphere heat ko trap kar leta hai.",
    "Sabse chhota haddi hamare kaan mein hoti hai, jiska naam stapes hai.",
    "Great Wall of China space se nangi aankhon se dikhti hai - yeh ek myth hai, asal mein nahi dikhti.",
    "Octopus ka khoon blue hota hai kyunki usmein copper-based protein hota hai, iron-based nahi.",
    "Ek din mein hamara dimaag itni electrical activity generate karta hai ki ek chhota bulb jal sakta hai.",
    "Antarctica duniya ka sabse bada desert hai - kyunki desert ka matlab kam baarish hota hai, garmi zaroori nahi.",
    "Sabse purana zinda ped lagbhag paanch hazaar saal purana hai, California mein hai.",
]


def tell_random_knowledge():
    speak(random.choice(RANDOM_KNOWLEDGE))


# ------------------- PERSONALITY / EMOTION -------------------
FLIRTY_TRIGGERS = ["tum kitni sundar ho", "you are beautiful", "i love you", "tum pyari ho", "tum cute ho"]
INSULT_TRIGGERS = ["tum bewakoof ho", "you are stupid", "tum ganwar ho", "tum useless ho"]
GREETING_TRIGGERS = ["kaise ho", "how are you", "kya haal hai"]

FLIRTY_RESPONSES = [
    "Aap bhi bahut sweet ho... aap sharma rahe ho kya?",
    "Aww, itni tareef se toh main sharma gayi!",
    "Aap kaafi charming ho, pata hai?",
]
INSULT_RESPONSES = [
    "Yeh thoda rude tha... par koi baat nahi, main phir bhi aapki madad karungi.",
    "Aisa nahi bolte, mujhe bura lagta hai.",
    "Main naraz ho sakti hoon, par chaliye kaam pe wapas aate hain.",
]
GREETING_RESPONSES = [
    "Main bilkul theek hoon, aapka din kaisa ja raha hai?",
    "Main achi hoon, dhanyavaad! Aap sunaiye.",
]


def check_emotional_trigger(text):
    for phrase in FLIRTY_TRIGGERS:
        if phrase in text:
            speak(random.choice(FLIRTY_RESPONSES))
            return True
    for phrase in INSULT_TRIGGERS:
        if phrase in text:
            speak(random.choice(INSULT_RESPONSES))
            return True
    for phrase in GREETING_TRIGGERS:
        if phrase in text:
            speak(random.choice(GREETING_RESPONSES))
            return True
    return False


# ------------------- GENERAL CONVERSATION (ChatGPT-like) -------------------
JARVIS_PERSONA = (
    "Tum Jarvis ho, ek friendly female Indian voice assistant jo Hinglish "
    "(Hindi + English mix) mein baat karti hai. Tumhara tone warm, thoda "
    "playful aur helpful hai. Jawab 2-3 sentences se zyada lamba mat do, "
    "kyunki yeh bola jaayega, padha nahi jaayega."
)


def general_chat(user_text):
    """Sends the user's message to Claude for an open-ended, ChatGPT-like reply."""
    if claude_client is None:
        speak("General baat karne ke liye pehle Anthropic API key set kijiye.")
        return

    conversation_history.append({"role": "user", "content": user_text})
    # keep only the last 10 turns so requests stay small
    trimmed_history = conversation_history[-10:]

    try:
        response = claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=200,
            system=JARVIS_PERSONA,
            messages=trimmed_history,
        )
        reply = response.content[0].text
        conversation_history.append({"role": "assistant", "content": reply})
        speak(reply)
    except Exception as e:
        speak("Mujhe abhi jawab dene mein problem ho rahi hai.")
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

    if any(w in text for w in ["youtube", "यूट्यूब", "युट्यूब", "युटुब", "यूटूब", "यु ट्यूब", "यूट्युब"]):
        search_triggers = ["khojo", "search", "play", "chalao", "dekho", "suno", "find"]
        if any(w in text for w in search_triggers):
            query = text
            remove_words = [
                "youtube", "यूट्यूब", "युट्यूब", "khojo", "search karo", "search", 
                "play karo", "play", "chalao", "dekho", "suno", "open", "kholo", "par", "pe"
            ]
            for w in remove_words:
                query = query.replace(w, "")
            open_youtube(query.strip() or None)
        else:
            open_youtube()
        return

    if any(w in text for w in ["linkedin", "लिंक्डइन", "लिंक्ड इन", "लिंकडिन", "लिंकेडीन"]):
        open_linkedin()
        return

    if any(w in text for w in ["google", "गूगल", "गुगल", "गूगल्", "गुगुल"]):
        search_triggers = ["search", "khojo", "find", "dhoondo", "सर्च", "खोजो", "ढूंढो"]
        if any(w in text for w in search_triggers):
            query = text
            remove_words = [
                "google", "गूगल", "गुगल", "par", "pe", "पर", "पे", "search karo", "search", 
                "khojo", "dhoondo", "सर्च करो", "सर्च", "खोजो", "ढूंढो", "open", "kholo", "खोलो"
            ]
            for w in remove_words:
                query = query.replace(w, "")
            open_google(query.strip() or None)
        else:
            open_google()
        return

    if any(w in text for w in ["whatsapp", "व्हाट्सएप", "व्हाट्सऐप", "व्हाट्सआप"]):
        send_whatsapp_message()
        return

    if any(w in text for w in ["volume", "वॉल्यूम", "आवाज", "aawaz", "sound"]):
        if any(w in text for w in ["mute", "म्यूट", "band", "बंद"]):
            mute_volume()
        elif any(w in text for w in ["badhao", "up", "increase", "बढ़ाओ", "तेज", "tez"]):
            change_volume(+10)
        elif any(w in text for w in ["kam", "down", "decrease", "कम", "धीमी", "dheemi"]):
            change_volume(-10)
        else:
            speak("Volume ko badhana hai ya kam karna hai?")
        return

    if any(w in text for w in ["brightness", "ब्राइटनेस", "रोशनी", "roshni"]):
        if any(w in text for w in ["badhao", "up", "increase", "बढ़ाओ", "तेज"]):
            change_brightness(+10)
        elif any(w in text for w in ["kam", "down", "decrease", "कम", "धीमी"]):
            change_brightness(-10)
        else:
            speak("Brightness ko badhana hai ya kam karna hai?")
        return

    if any(w in text for w in ["mausam", "weather", "मौसम", "वेदर", "वेदार", "agartala", "अगरतला"]):
        if "agartala" in text or "अगरतला" in text:
            tell_weather("Agartala,IN")
        else:
            tell_weather()
        return

    if any(w in text for w in ["time", "samay", "समय", "टाइम", "waqt", "वक्त"]):
        tell_time()
        return

    if any(w in text for w in ["date", "tarikh", "तारीख", "दिनांक", "dinank", "डेट"]):
        tell_date()
        return

    if any(w in text for w in ["joke", "chutkula", "जोक", "चुटकुला"]):
        tell_joke()
        return

    # Anything else -> open-ended conversation, like ChatGPT
    general_chat(text)


# ------------------- MAIN LOOP -------------------
def main():
    if not SOUNDDEVICE_AVAILABLE:
        print(
            "\n[Notice] Couldn't load 'sounddevice', so voice input is OFF "
            "for now - you'll type instead of speak. Run:\n"
            "    pip install sounddevice numpy\n"
            "then restart this script to get real voice input.\n"
        )

    speak(" Namaste Boss! Main Jarvis hoon, aapki voice assistant. Bataiye, main aapki kya madad kar sakti hoon?")

    idle_streak = 0  # counts consecutive listen() calls where nothing was heard

    while True:
        text = listen()

        if not text:
            # Each silent listen() call already waits ~7-10 seconds
            # (MIC_MAX_SECONDS) before giving up, so this fires roughly
            # every time the user has been quiet that long.
            idle_streak += 1
            if idle_streak == 1 or idle_streak % 3 == 0:
                tell_idle_talk()
            continue

        idle_streak = 0

        if any(phrase in text for phrase in EXIT_PHRASES):
            speak("Alvida! Phir milenge.")
            break

        handle_command(text)
        time.sleep(0.3)


if __name__ == "__main__":
    main()
