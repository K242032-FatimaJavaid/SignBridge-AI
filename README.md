# SignBridge AI
### An AI-Powered Bidirectional Sign Language Communication System with a 3D Animated Avatar and Intelligent Assistant

**FAST National University of Computer and Emerging Sciences — Karachi Campus**  
**Course:** Artificial Intelligence Laboratory (Fall 2026)  
**Project Type:** Semester Lab Project

## 1. Project Overview

SignBridge AI is a web-based communication prototype designed to support interaction between American Sign Language (ASL) users and individuals who communicate through spoken or written English.

The application combines computer vision, machine learning, speech processing, a 3D animated avatar, and Google Gemini to provide three interconnected communication capabilities:

1. **ASL to Text and Speech:** Recognizes supported hand signs through a webcam and converts them into English text and spoken audio.
2. **Speech/Text to ASL:** Maps supported English words and expressions to gesture animations performed by a 3D human avatar.
3. **AI Assistant:** Provides conversational responses through Google Gemini, with text and speech output.

The system focuses on a limited vocabulary of supported signs rather than attempting unrestricted, grammatically complete ASL translation.

## 2. Key Features

### ASL Recognition and Speech Generation

- Live webcam-based recognition using MediaPipe Hands.
- Recognition of 25 word-level signs.
- Fingerspelling support for 26 alphabet letters.
- Recognition of digits 0–9.
- Automatic switching to alphabet or number recognition in supported contexts.
- Sentence formation from recognized gestures.
- Text-to-speech output for completed sentences.
- Confidence-based prediction filtering and repeated-sign confirmation.
- Automatic and precise sign-recognition workflows.

### Speech and Text to ASL Avatar

- Speech-to-text processing for spoken English input.
- Support for typed English input.
- Animated 3D human avatar.
- Mapping of supported words and expressions to avatar gestures.
- Browser-based avatar rendering and animation.
- Support for fingerspelling animations where implemented.

The avatar uses animated 3D gestures rather than relying on prerecorded videos as its primary translation mechanism.

### Gemini AI Assistant

- Conversational text generation using Google Gemini.
- Text-based interaction.
- Speech output for assistant responses.
- Integration with the application's communication workflows.

Gemini requires an internet connection and a valid API key. Local sign recognition and trained-model inference do not require Gemini.

## 3. Supported Vocabulary

The word-level recognition model supports the following 25 signs:

`AGE`, `FOOD`, `HELLO`, `HELP`, `I`, `IS`, `MY`, `NAME`, `NEED`, `NO`, `PLEASE`, `QUIET`, `SHUT_UP`, `THANK_YOU`, `TO`, `WANT`, `WATER`, `YES`, `YOU`, `GOODBYE`, `STOP`, `YOU_ARE_WELCOME`, `WHAT`, `FRIEND`, `CLAP`.

Additional recognition capabilities include:

- **Alphabet:** A–Z (26 letters)
- **Numbers:** 0–9 (10 digits)

Together, these provide **61 supported recognition labels** across the word, alphabet, and number systems, excluding the word model's `OTHER` rejection class.

Recognition accuracy varies across signs, lighting conditions, signing styles, and camera viewpoints.

## 4. System Architecture

### ASL to Speech

```text
Webcam
   |
   v
OpenCV + MediaPipe Hands
   |
   v
Hand Landmark Extraction
   |
   v
Temporal Feature Processing
   |
   v
Trained SVM Classifier
   |
   v
Prediction Filtering
   |
   v
Recognized Signs
   |
   v
Sentence Formation
   |
   v
English Text + Speech Output
```

### Speech/Text to ASL

```text
Microphone / Typed Text
          |
          v
   Speech Recognition
          |
          v
   English Text Input
          |
          v
   Supported Gesture Mapping
          |
          v
     3D Avatar Engine
          |
          v
   Animated ASL Gestures
```

### Gemini Assistant

```text
Text / Supported Communication Input
                  |
                  v
          Gemini AI Assistant
                  |
                  v
           Generated Response
                  |
           +------+------+
           |             |
           v             v
      Text Output    Speech Output
```

## 5. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.11 |
| Web application | Streamlit |
| Webcam streaming | Streamlit-WebRTC |
| Computer vision | OpenCV |
| Hand landmark detection | MediaPipe Hands |
| Machine learning | scikit-learn |
| Primary classifier | Support Vector Machine (SVM) |
| Comparison models | Random Forest and k-Nearest Neighbors |
| Numerical processing | NumPy |
| Model serialization | Joblib |
| Evaluation and visualization | Matplotlib |
| AI assistant | Google Gemini |
| Text-to-speech | Python speech-processing tools |
| 3D avatar | Three.js-based browser animation system |
| Avatar development tools | JavaScript, Node.js, Vite |

## 6. Machine Learning Methodology

### Dataset Collection

A custom webcam-based dataset was collected for supported signs in multiple recording sessions.

MediaPipe extracts hand landmarks, which are normalized and converted into feature vectors. Temporal information is included to capture changes in hand position and movement during gestures.

For the word-level classifier:

- Sequence length: 24 frames
- Approximate sampling rate: 12 FPS
- Feature extraction: Hand landmarks, position, and motion information
- Primary classification algorithm: SVM with an RBF kernel

### Dataset and Evaluation Split

| Description | Value |
|---|---:|
| Total recorded sequences | 1,432 |
| Training samples | 984 |
| Testing samples | 448 |
| Classes evaluated | 26 (25 words + OTHER) |
| Training sessions | S2, S3 |
| Evaluation session | S1 |

Complete recording sessions were separated during evaluation to avoid mixing frames from the same sequence between training and testing.

### Classifier Comparison

Three machine learning algorithms were evaluated using the same training and testing split. Two baseline methods were also included.

| Model | Accuracy | Macro F1-score |
|---|---:|---:|
| **Random Forest** | **87.95%** | **0.875** |
| Support Vector Machine (SVM) | 86.38% | 0.864 |
| k-Nearest Neighbors (k-NN) | 77.68% | 0.773 |
| Random Baseline | 4.02% | 0.042 |
| Majority-Class Baseline | 4.46% | 0.003 |

Random Forest achieved the highest recorded evaluation accuracy, outperforming SVM by 1.57 percentage points.

**SVM was retained as the primary real-time recognition model** because its existing recognition pipeline had already been configured, integrated, and tested within the application.

The comparison evaluates the word-level classifier, not the separate alphabet and digit recognition models.

### Model Comparison Graph

![Model Comparison](evaluation/01_model_comparison.png)

### SVM Confusion Matrix

![SVM Confusion Matrix](evaluation/02_svm_confusion_matrix.png)

The confusion matrix shows that performance varies across classes. Some visually similar signs, including HELP and STOP, remain challenging to distinguish consistently.

### Evaluation Limitations

Although S1 recordings were excluded from model training, S1 results were used repeatedly during development to guide improvements. Therefore, these results should be interpreted as development-stage held-out-session results rather than performance on a completely untouched final test set.

A separate unseen-signer evaluation has not been established.

## 7. Response-Time Evaluation

The three principal communication workflows were tested through manually timed trials.

| Module | Average Response Time |
|---|---:|
| ASL to Speech | 7.352 seconds |
| Speech to 3D Avatar | 0.587 seconds |
| Gemini Assistant | 1.425 seconds |

![Response Time Comparison](evaluation/03_response_time.png)

Each workflow was measured over three trials. Measurements include interaction and manual timing delays and should be treated as approximate end-to-end response times.

ASL-to-Speech currently has the highest delay. This is an area for future optimization, particularly gesture confirmation, sentence completion, and streaming responsiveness.

## 8. Project Structure

```text
SignBridge-AI/
|
|-- app.py
|-- recognition/
|-- assistant/
|-- speech/
|-- avatar-engine/
|   |-- src/
|   |-- public/
|   |-- package.json
|   |-- package-lock.json
|
|-- models/
|   |-- sequence_extended_v1.joblib
|   |-- alnum_alphabet_v1.joblib
|   |-- alnum_numbers_v1.joblib
|   |-- alphabet_uv_specialist_v1.joblib
|
|-- assets/
|-- evaluation/
|   |-- 01_model_comparison.png
|   |-- 02_svm_confusion_matrix.png
|   |-- 03_response_time.png
|   |-- model_comparison.csv
|   |-- latency_results.csv
|   |-- svm_classification_report.txt
|
|-- sequence_extended.py
|-- evaluate_models.py
|-- measure_latency.py
|-- requirements.txt
|-- run_signbridge.bat
|-- README.md
```

The repository includes additional training, testing, and development scripts. Raw recording datasets and local environments may be maintained separately from the public repository.

## 9. Installation and Setup

### Requirements

- Windows 10 or Windows 11
- Python 3.11
- Webcam and microphone
- Google Chrome or another compatible browser
- Internet connection for Gemini
- A Gemini API key for online assistant functionality
- Node.js and npm for developing or rebuilding the 3D avatar frontend

### Step 1 — Clone the Repository

```powershell
git clone https://github.com/K242032-FatimaJavaid/SignBridge-AI.git
cd SignBridge-AI
```

### Step 2 — Create a Python Virtual Environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Then activate the environment again.

### Step 3 — Install Python Dependencies

Install all required Python packages using the provided `requirements.txt` file:

```powershell
python -m pip install -r requirements.txt
```

After installation, verify that all package dependencies are compatible:

```powershell
python -m pip check
```

If the installation is successful, the expected output is:

```text
No broken requirements found.
```

The `requirements.txt` file contains the tested package versions required to run SignBridge AI, including Streamlit, MediaPipe, OpenCV, NumPy, and Google GenAI.

### Step 4 — Configure Gemini

The Gemini AI Assistant requires a valid Google Gemini API key.

Create a `.streamlit` folder in the project root and add a `secrets.toml` file containing:

`GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"`

Replace the placeholder with your own API key. The key must be stored locally and must never be committed to GitHub.

Alternatively, the `GEMINI_API_KEY` environment variable can be used when no Streamlit secrets file is present.

ASL recognition, sentence formation, and speech translation can work without a Gemini API key. Only the Gemini AI Assistant requires it.

### Step 5 — Launch SignBridge AI

From the project root:

```powershell
python -m streamlit run app.py --server.address 127.0.0.1
```

Open the application in Chrome:

```text
http://127.0.0.1:8501
```

Grant camera and microphone access when prompted.

### Optional — Avatar Development

The Three.js avatar source code is stored in `avatar-engine/`. If the avatar development frontend needs to be run or rebuilt separately, use Node.js and the scripts defined in its `package.json`.

```powershell
cd avatar-engine
npm install
npm run dev
```

The development server will display its local address in the terminal.

Return to the project root before launching the Streamlit application.

## 10. Using the Application

### ASL to Speech

1. Launch SignBridge AI.
2. Open the ASL recognition interface.
3. Select the webcam and start recognition.
4. Perform a supported sign in front of the camera.
5. Review recognized words in the sentence panel.
6. Complete the sentence to generate spoken output.

The system also supports alphabet and digit recognition for supported fingerspelling and number-entry contexts.

### Speech to ASL

1. Open the speech-to-ASL interface.
2. Provide spoken or typed English.
3. Submit the expression.
4. View supported gestures through the animated 3D avatar.

Only expressions supported by the avatar's gesture library can be animated correctly.

### Gemini Assistant

1. Open the AI assistant.
2. Enter a message using the available supported input method.
3. Submit the message.
4. Read or listen to the generated response.

Gemini responses require an active internet connection.

## 11. Challenges and Limitations

The current prototype has several limitations:

- Confusion between visually similar hand signs.
- Sensitivity to signing speed, hand position, and camera viewpoint.
- Variation in recognition performance across different vocabulary classes.
- Increased ASL-to-Speech response time due to sequence processing and sentence confirmation.
- Limited support for full ASL grammar and nonmanual expressions.
- Avatar animation limited to supported gestures.
- Internet dependency for Gemini responses.
- Limited evaluation across independent signers and environments.

SignBridge AI is an academic prototype and should not be treated as a certified sign-language interpreting system.

## 12. Future Improvements

Potential future improvements include:

- Reducing webcam streaming and end-to-end recognition latency.
- Increasing dataset diversity across multiple signers.
- Evaluating models on a completely independent recording session.
- Improving recognition of similar gestures.
- Expanding supported vocabulary after validating existing signs.
- Improving sentence handling and contextual interpretation.
- Expanding the 3D avatar gesture library.
- Improving support for continuous communication.
- Strengthening offline assistance and application robustness.

## 13. Project Team

| Team Member | Roll Number | Contribution |
|---|---|---|
| **Fatima Javaid (Team Leader)** | 24K-2032 | Project coordination, dataset collection, ASL recognition, model training and evaluation, sign-to-speech |
| **Sidratun Muntaha** | 24K-2007 | 3D avatar, gesture animation, phrase mapping and avatar integration |
| **Abeeha Shaikh** | 24K-2031 | AI assistant, speech processing, application interface, backend and integration |

## 14. Academic Information

**Institution:** FAST National University of Computer and Emerging Sciences, Karachi Campus  
**Course:** Artificial Intelligence Laboratory (Fall 2026)  
**Project:** SignBridge AI — An AI-Powered Bidirectional Sign Language Communication System with a 3D Animated Avatar and Intelligent Assistant

---

**SignBridge AI — Bridging Communication Through Artificial Intelligence.**
