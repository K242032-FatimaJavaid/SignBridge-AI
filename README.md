# SignBridge AI — 4-week university prototype

A **starter implementation**, not a finished natural-ASL translator. Includes a Streamlit three-mode UI, webcam data collection, MediaPipe landmark features, a scikit-learn Random Forest baseline, live sign prediction, optional speech recognition and text-to-speech, a phrase-to-video lookup, and a rule-based assistant. No trained weights, recorded ASL videos, or LLM credentials are included.

## Requirements
- Python 3.11 recommended; webcam and microphone; Windows or Linux desktop.
- MediaPipe classic `mp.solutions.hands` API is used. If a newer release removes this API, pin a compatible MediaPipe release or migrate to Hand Landmarker Tasks.
- Internet is needed to install packages and for the optional Google Web Speech recognizer.
- On Ubuntu, microphone capture may require `sudo apt install portaudio19-dev python3-dev` then `pip install pyaudio`. Text-to-speech may need `sudo apt install espeak-ng`.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Member 1 — recognition pipeline
1. Verify webcam: `python -m recognition.collect --label HELLO --count 150`
2. Press SPACE to start/pause collection, Q to stop; record distinct examples and varied angles, not only near-identical adjacent frames.
3. Repeat for another sign, e.g. `python -m recognition.collect --label THANK_YOU --count 150`. **Check sign correctness with an ASL reference and fluent signer.**
4. Train: `python -m recognition.train`
5. Run: `python -m recognition.live` (press Q to exit).

**Limitation:** This baseline classifies *individual frames*, so it cannot correctly model dynamic signs that depend on motion. It is an engineering scaffold, not validated ASL recognition. For dynamic signs, capture short frame sequences and train an LSTM/GRU or temporal model. A random frame split overstates performance; evaluate with independent participants and sessions.

## Member 2 — speech and signing output
- Use the **Speech → ASL** tab. Type a phrase or try the optional microphone button.
- Add your own **licensed, verified** ASL MP4 clips in `assets/asl_videos/` using lowercase underscores, e.g. `thank_you.mp4`, `hello.mp4`.
- The application will explicitly report unsupported phrases. Do not substitute English fingerspelling and claim full ASL translation.

## Member 3 — UI and assistant
- `streamlit run app.py` shows three modes.
- `assistant/logic.py` provides transparent offline canned responses; replace with an LLM API later if approved. Current assistant is **not** an LLM.
- Streamlit app and webcam recognition are separate windows in this starter. Integrating continuous video into the UI requires a streaming component (e.g. streamlit-webrtc) and concurrency handling.

## Suggested 4-week delivery
- Week 1: install, camera/mic tests, interface, sign vocabulary agreement.
- Week 2: data collection, baseline model, licensed videos, assistant logic.
- Week 3: integrate model output with audio, add ASL videos, test all modes.
- Week 4: unseen-signer testing, failure analysis, demo/report.

## Testing
```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

## Ethics & evaluation
ASL is a natural language, not English on the hands. Accurate signing requires motion, nonmanual markers, and ASL grammar. Obtain consent for recording. Avoid claiming accessibility-grade translation until tested with Deaf ASL users. Report unseen-signer accuracy, confusion matrix, latency, phrase coverage, and limitations.
