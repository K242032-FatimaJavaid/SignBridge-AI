
import sounddevice as sd
import speech_recognition as sr

SAMPLE_RATE = 16000
DURATION = 5

print("Get ready to speak...")
input("Press Enter to start recording.")

print("Recording for 5 seconds...")

recording = sd.rec(
    int(DURATION * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype="int16",
    device=1
)

sd.wait()

print("Recording finished. Recognizing speech...")

recognizer = sr.Recognizer()

audio = sr.AudioData(
    recording.tobytes(),
    SAMPLE_RATE,
    2
)

try:
    text = recognizer.recognize_google(audio)
    print("You said:", text)

except sr.UnknownValueError:
    print("Could not understand your speech.")

except sr.RequestError as error:
    print("Speech recognition service error:", error)
