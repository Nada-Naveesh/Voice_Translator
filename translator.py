import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import noisereduce as nr
import speech_recognition as sr
from deep_translator import GoogleTranslator
from gtts import gTTS
import pygame
import tempfile
import time
import os
import tkinter as tk
from tkinter import messagebox
from threading import Thread
from PIL import Image, ImageTk
import requests
from io import BytesIO

# Try to import Whisper for offline, high-accuracy speech recognition
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Configuration
fs = 16000  # Sample rate
duration = 5  # seconds
recognizer = sr.Recognizer()
audio_file = "cleaned_audio.wav"

# Initialize pygame mixer
pygame.mixer.init()

# --- Audio Recording and Noise Reduction ---
def record_with_noise_reduction(status_label=None):
    if status_label:
        status_label.config(text="🎙 Recording...", fg="#d35400")
        status_label.update()
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    if status_label:
        status_label.config(text="🔇 Reducing background noise...", fg="#2980b9")
        status_label.update()
    audio_np = audio.flatten()
    reduced_audio = nr.reduce_noise(y=audio_np, sr=fs)
    reduced_audio = reduced_audio.astype(np.int16).reshape(-1, 1)
    wav.write(audio_file, fs, reduced_audio)
    if status_label:
        status_label.config(text="✅ Cleaned audio saved.", fg="#27ae60")
        status_label.update()

# --- Speech Recognition ---
def speech_to_text_from_clean_audio(language="en", status_label=None):
    # Try Whisper first
    if WHISPER_AVAILABLE:
        if status_label:
            status_label.config(text="🔍 Recognizing speech (Whisper)...", fg="#2980b9")
            status_label.update()
        try:
            model = whisper.load_model("base")
            result = model.transcribe(audio_file, language=language)
            return result['text']
        except Exception as e:
            print("Whisper failed:", e)
            if status_label:
                status_label.config(text="⚠ Whisper failed, using Google...", fg="#c0392b")
                status_label.update()
    # Fallback to Google
    with sr.AudioFile(audio_file) as source:
        audio_data = recognizer.record(source)
        try:
            if status_label:
                status_label.config(text="🔍 Recognizing speech (Google)...", fg="#2980b9")
                status_label.update()
            text = recognizer.recognize_google(audio_data, language=language)
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            return ""

# --- Translation ---
def translate_text(text, source_lang="en", target_lang="te"):
    if not text.strip():
        return ""
    try:
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        return translated
    except Exception as e:
        print("Translation error:", e)
        return "[Translation Error]"

# --- Text-to-Speech ---
def speak_text(text, lang="te"):
    if not text.strip():
        return
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
        temp_filename = fp.name
    tts = gTTS(text=text, lang=lang)
    tts.save(temp_filename)
    try:
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    finally:
        try:
            os.unlink(temp_filename)
        except:
            pass

# --- Main Translation Workflow ---
def live_voice_translate(source_lang='en', target_lang='te', status_label=None, text_var=None, confirm_btn=None, re_record_btn=None):
    record_with_noise_reduction(status_label)
    recognized_text = speech_to_text_from_clean_audio(language=source_lang, status_label=status_label)
    if text_var is not None:
        text_var.set(recognized_text)
    if confirm_btn is not None and re_record_btn is not None:
        confirm_btn.config(state='normal')
        re_record_btn.config(state='normal')
    if status_label:
        status_label.config(text="📝 Please confirm or re-record.", fg="#8e44ad")
        status_label.update()

def do_translation_and_speak(source_lang, target_lang, status_label, text_var):
    input_text = text_var.get()
    if not input_text.strip():
        if status_label:
            status_label.config(text="❌ No text to translate.", fg="#c0392b")
        return
    if status_label:
        status_label.config(text="🌍 Translating...", fg="#8e44ad")
        status_label.update()
    translated_text = translate_text(input_text, source_lang, target_lang)
    if status_label:
        status_label.config(text="🔊 Speaking...", fg="#16a085")
        status_label.update()
    speak_text(translated_text, lang=target_lang)
    if status_label:
        status_label.config(text="✅ Done!", fg="#27ae60")
        status_label.update()

# --- Utility: Load Images from URL ---
def get_image_from_url(url, size):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content)).convert('RGB')
        img = img.resize(size, Image.ANTIALIAS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Could not load image from {url}: {e}")
        return None

# --- GUI ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Indian Government Voice Translator")
    root.state('zoomed')  # Fullscreen

    # Get screen size
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # URLs for public domain/official images
    railway_url = "https://upload.wikimedia.org/wikipedia/commons/6/6b/Indian_Railways_logo.png"
    busstand_url = "https://upload.wikimedia.org/wikipedia/commons/2/2e/APSRTC_Bus_Stand%2C_Anantapur.jpg"
    gov_bg_url = "https://upload.wikimedia.org/wikipedia/commons/4/4e/Flag_of_India.svg"

    # Try to load a beautiful collage background
    bg_img = Image.new('RGB', (screen_width, screen_height), "#f5f6fa")
    try:
        # Load and paste bus stand image
        bus_img = requests.get(busstand_url)
        bus_img = Image.open(BytesIO(bus_img.content)).convert('RGB')
        bus_img = bus_img.resize((int(screen_width*0.6), int(screen_height*0.6)), Image.ANTIALIAS)
        bg_img.paste(bus_img, (int(screen_width*0.2), int(screen_height*0.25)))
    except Exception as e:
        print("Could not load bus stand image:", e)
    try:
        # Load and paste Indian Railways logo
        rail_img = requests.get(railway_url)
        rail_img = Image.open(BytesIO(rail_img.content)).convert('RGBA')
        rail_img = rail_img.resize((200, 200), Image.ANTIALIAS)
        bg_img.paste(rail_img, (40, 40), rail_img)
    except Exception as e:
        print("Could not load railway logo:", e)
    try:
        # Load and paste Indian flag (as a faded overlay)
        flag_img = requests.get(gov_bg_url)
        flag_img = Image.open(BytesIO(flag_img.content)).convert('RGBA')
        flag_img = flag_img.resize((int(screen_width*0.25), int(screen_height*0.15)), Image.ANTIALIAS)
        flag_img.putalpha(80)
        bg_img.paste(flag_img, (screen_width-flag_img.width-40, 40), flag_img)
    except Exception as e:
        print("Could not load flag image:", e)

    bg_photo = ImageTk.PhotoImage(bg_img)
    bg_label = tk.Label(root, image=bg_photo)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    # Header frame
    header = tk.Frame(root, bg="#273c75", height=80)
    header.place(relx=0, rely=0, relwidth=1, height=80)

    title = tk.Label(header, text="Indian Railways & Bus Stand Voice Translator",
                     font=("Verdana", 24, "bold"), fg="white", bg="#273c75")
    title.pack(pady=20)

    # Main content frame
    main = tk.Frame(root, bg="#f5f6fa")
    main.place(relx=0.5, rely=0.18, anchor='n', relwidth=0.5, relheight=0.7)

    # Language selection
    lang_frame = tk.Frame(main, bg="#f5f6fa")
    lang_frame.pack(pady=10)
    lang_var = tk.StringVar(value='en-te')
    tk.Radiobutton(lang_frame, text="English to Telugu", variable=lang_var, value='en-te',
                   font=("Arial", 12), bg="#f5f6fa").pack(side='left', padx=10)
    tk.Radiobutton(lang_frame, text="Hindi to Telugu", variable=lang_var, value='hi-te',
                   font=("Arial", 12), bg="#f5f6fa").pack(side='left', padx=10)

    # Recognized text display
    text_var = tk.StringVar()
    text_label = tk.Label(main, text="Recognized Text:", font=("Arial", 12, "bold"), bg="#f5f6fa")
    text_label.pack(pady=(20, 5))
    text_entry = tk.Entry(main, textvariable=text_var, font=("Arial", 14), width=40, state='readonly', justify='center')
    text_entry.pack(pady=5)

    status_label = tk.Label(main, text="", font=("Arial", 12, "bold"), fg="#273c75", bg="#f5f6fa")
    status_label.pack(pady=10)

    # Buttons
    btn_frame = tk.Frame(main, bg="#f5f6fa")
    btn_frame.pack(pady=10)

    def start_recording():
        # Disable buttons during recording
        confirm_btn.config(state='disabled')
        re_record_btn.config(state='disabled')
        text_var.set("")
        source, target = lang_var.get().split('-')
        Thread(target=live_voice_translate, args=(source, target, status_label, text_var, confirm_btn, re_record_btn), daemon=True).start()

    def confirm_translation():
        source, target = lang_var.get().split('-')
        confirm_btn.config(state='disabled')
        re_record_btn.config(state='disabled')
        Thread(target=do_translation_and_speak, args=(source, target, status_label, text_var), daemon=True).start()

    def re_record():
        start_recording()

    record_btn = tk.Button(btn_frame, text="🎤 Record", font=("Arial", 14, "bold"), width=12,
                           bg="#e67e22", fg="white", activebackground="#d35400", command=start_recording)
    record_btn.pack(side='left', padx=10)

    confirm_btn = tk.Button(btn_frame, text="✅ Confirm", font=("Arial", 14, "bold"), width=12,
                            bg="#27ae60", fg="white", activebackground="#229954", command=confirm_translation, state='disabled')
    confirm_btn.pack(side='left', padx=10)

    re_record_btn = tk.Button(btn_frame, text="🔄 Re-record", font=("Arial", 14, "bold"), width=12,
                              bg="#2980b9", fg="white", activebackground="#2471a3", command=re_record, state='disabled')
    re_record_btn.pack(side='left', padx=10)

    info = tk.Label(main, text="Speak after clicking 'Record'.\nCheck console for details.",
                    font=("Arial", 10), fg="#636e72", bg="#f5f6fa")
    info.pack(pady=5)

    # Accessibility: Keyboard shortcuts
    root.bind('<F5>', lambda e: start_recording())
    root.bind('<Return>', lambda e: confirm_translation())

    root.mainloop()