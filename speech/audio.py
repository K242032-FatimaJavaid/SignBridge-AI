"""Optional speech recognition and local text-to-speech."""

def speak(text):
    import pyttsx3
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def recognize_microphone():
    import speech_recognition as sr
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source, timeout=7, phrase_time_limit=8)
    # Google Web Speech requires network; optional microphone workflow.
    return r.recognize_google(audio)
