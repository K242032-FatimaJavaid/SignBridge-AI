# SignBridge AI

**An AI-Powered Bidirectional Sign Language Communication System with a
3D Animated Avatar and Intelligent Assistant**

SignBridge AI is a proposed web-based communication platform for
reducing communication barriers between American Sign Language (ASL)
users and people who primarily communicate through spoken or written
English. The project combines ASL recognition, speech/text-to-ASL
gesture animation, and an intelligent conversational assistant.

> **Project status:** Semester lab project proposal (Fall 2026). This
> README describes the planned system and scope; it does not claim that
> all proposed features have already been implemented.

## Project Information

  ----------------------------------------------------------------------------------------------------
  Item                                Details
  ----------------------------------- ----------------------------------------------------------------
  University                          FAST --- National University of Computer and Emerging Sciences,
                                      Karachi Campus

  Course                              AL-2002 Artificial Intelligence (Laboratory)

  Semester                            Fall 2026

  Project category                    Applied / Data

  Team leader                         Fatima Javaid --- 24K-2032

  Team member                         Sidratun Muntaha --- 24K-2007

  Team member                         Abeeha Shaikh --- 24K-2031

  Repository                          [SignBridge AI on
                                      GitHub](https://github.com/K242032-FatimaJavaid/SignBridge-AI)
  ----------------------------------------------------------------------------------------------------

## Project Overview

The proposed system has three connected communication modes:

1.  **ASL-to-Speech Recognition:** A webcam captures selected ASL signs.
    A machine learning model classifies the signs, displays their
    English equivalents, and converts the recognized text into audible
    speech.
2.  **Speech/Text-to-ASL Gestures:** A user speaks or types English
    words or supported expressions. The system identifies supported
    content and triggers the corresponding gesture animation on a rigged
    3D human avatar.
3.  **Intelligent AI Assistant:** Users interact with an assistant
    through supported ASL signs, speech, or typed text. The assistant
    generates contextual responses, displays them as text, and provides
    speech output. Supported expressions may also be performed by the
    avatar.

The avatar is intended to use reusable animations and controlled hand,
finger, arm, and body movements rather than prerecorded sign-language
videos.

## Problem and Motivation

ASL users may encounter communication barriers in educational
institutions, workplaces, public settings, and everyday situations when
an interpreter is unavailable. Writing messages or relying on another
person can interrupt natural communication.

Automatic sign recognition is challenging because signs can vary in hand
shape, orientation, movement, signing speed, camera angle, lighting, and
signer characteristics. SignBridge AI proposes combining landmark-based
computer vision and supervised machine learning with speech processing,
gesture mapping, 3D animation, and conversational AI to support
communication in both directions.

## Main Features in the Proposed Scope

-   Real-time recognition of approximately **5--10 selected ASL signs**.
-   Conversion of recognized signs into English text and speech.
-   Spoken and typed English input.
-   Mapping of supported English words and expressions to ASL gesture
    animations.
-   A rigged 3D human avatar that performs supported gestures.
-   An AI assistant with text and speech responses.
-   Avatar signing for supported assistant responses.
-   A unified web interface integrating the communication modules.
-   Evaluation and comparison of the sign-recognition models.

The initial vocabulary is intentionally limited. Expansion may be
considered if time permits.

## Proposed System Workflow

### 1. ASL-to-Speech

1.  Capture webcam frames.
2.  Detect hands and extract hand landmarks using MediaPipe.
3.  Normalize and prepare the landmark features.
4.  Classify the gesture using a trained machine learning model.
5.  Display the recognized English label.
6.  Convert the recognized text into speech.

### 2. Speech/Text-to-ASL

1.  Receive spoken or typed English input.
2.  Convert speech to text when the input is spoken.
3.  Normalize the text and identify supported words or expressions.
4.  Map the supported content to gesture animations.
5.  Send the animation sequence to the 3D avatar controller.
6.  Play the corresponding avatar gestures.

### 3. Intelligent Assistant

1.  Receive supported sign input, speech, or typed text.
2.  Pass the message to the assistant service.
3.  Generate a contextual response using the Gemini API.
4.  Display the response as text and convert it into speech.
5.  Extract supported expressions from the response for avatar output.

Avatar signing is limited to expressions available in the
gesture-mapping library.

## Proposed AI and Technical Approach

  -----------------------------------------------------------------------
  Component               Planned role            Proposed tools /
                                                  approach
  ----------------------- ----------------------- -----------------------
  Hand landmark           Detect hands and        MediaPipe, OpenCV
  extraction              extract structured      
                          landmark coordinates    

  Sign classification     Recognize selected ASL  Scikit-learn: Random
                          signs from labeled      Forest, Support Vector
                          landmark features       Machine (SVM),
                                                  k-Nearest Neighbors
                                                  (k-NN)

  Speech recognition      Convert spoken English  SpeechRecognition or
                          into text               Whisper

  Text-to-speech          Produce audible output  Local engine such as
                          from text               `pyttsx3`

  Text-to-ASL mapping     Match supported English Custom gesture-mapping
                          expressions to gesture  library
                          animations              

  Conversational          Generate contextual     Google Gemini API
  assistant               responses               

  3D gesture animation    Animate a rigged human  Blender, Three.js,
                          avatar                  custom animation
                                                  controller

  Backend and interface   Integrate the modules   Planned FastAPI backend
                          through a web           and web interface
                          application             
  -----------------------------------------------------------------------

### Landmark Representation

MediaPipe can provide 21 three-dimensional landmarks for each detected
hand:

-   One hand: `21 × 3 = 63` coordinate features per frame.
-   Two hands: `2 × 21 × 3 = 126` coordinate features per frame.
-   A proposed window of 30 frames for two hands contains
    `30 × 126 = 3,780` coordinate features.

Coordinates will be normalized relative to hand position and scale.
Missing-hand information will be handled consistently. Temporal features
may be flattened or summarized into fixed-length vectors for the
selected classifiers.

### Planned Software Classes

-   **`LandmarkExtractor`** --- extracts and normalizes hand landmarks
    from webcam frames.
-   **`SignClassifier`** --- trains, predicts, evaluates, saves, and
    loads sign-recognition models.
-   **`SpeechService`** --- handles speech recognition and
    text-to-speech.
-   **`GestureMapper`** --- normalizes text and maps supported
    expressions to avatar animations.
-   **`AvatarController`** --- loads the avatar and manages gesture
    playback and animation queues.
-   **`AssistantService`** --- generates conversational responses and
    identifies expressions supported by the avatar.
-   **`ApplicationController`** --- integrates the modules through the
    backend and web interface.

The proposal identifies the planned backend endpoints as `/recognize`,
`/translate`, and `/chat`.

## Dataset

The project plans to use a **self-collected dataset** of webcam
recordings for selected ASL signs. The WLASL dataset will be used as a
reference for ASL vocabulary and gesture examples.

-   Reference dataset: [WLASL](https://github.com/dxli94/WLASL)
-   Planned initial vocabulary: 5--10 selected signs.
-   Target collection: approximately 100 or more samples per sign (about
    500--1,000 labeled samples initially).
-   Preprocessing: landmark extraction, coordinate normalization,
    fixed-length feature preparation, consistent handling of missing
    landmarks, class labeling, and train/test splitting.
-   Public reference material will be used according to its published
    licensing and usage terms. Reference videos will not be
    redistributed without appropriate permission.

## Model Evaluation Plan

The proposed classifiers are:

1.  Random Forest
2.  Support Vector Machine (SVM)
3.  k-Nearest Neighbors (k-NN)

The models will be compared with two baseline predictors:

-   **Random guessing:** for a balanced dataset with `N` classes,
    expected accuracy is approximately `1/N`.
-   **Majority-class baseline:** always predicts the most frequent class
    in the training data.

### Evaluation Metrics

-   Accuracy
-   Precision
-   Recall
-   F1-score
-   Confusion matrix
-   Recognition and response time
-   Manual evaluation of avatar gesture correctness against reliable ASL
    references

The proposal suggests an approximately 80/20 train/test split, grouping
samples by recording session or signer where possible to reduce data
leakage. If enough recordings are available, an additional test using a
signer excluded from training will be conducted.

A fixed random seed of 42 is planned for reproducibility. Where
applicable, experiments may be repeated with seeds 42, 43, 44, 45, and
46, with mean and standard deviation reported.

### Planned Results Visualizations

1.  Confusion matrix for the best-performing recognition model.
2.  Bar chart comparing accuracy and F1-score across the classifiers and
    baselines.
3.  Bar chart comparing recognition or response times across evaluated
    methods and system modules.

## Scope and Limitations

### In Scope

-   Recognition of 5--10 selected ASL signs.
-   ASL-to-English text and speech conversion.
-   Spoken and typed English input.
-   3D avatar animation for supported ASL gestures.
-   Text-to-ASL gesture mapping.
-   AI assistant with text and speech responses.
-   Avatar signing of supported assistant responses.
-   Unified web interface and model evaluation.

### Out of Scope

-   Unrestricted continuous ASL sentence recognition.
-   Complete English-to-ASL grammatical translation.
-   Unlimited ASL vocabulary.
-   Generative creation of new ASL gestures.
-   Full facial-expression and nonmanual grammatical modeling.
-   Mobile application development.
-   Training large-scale deep learning models from scratch.
-   Support for multiple sign languages.
-   Fully offline generative conversational AI.

**Important limitation:** The proposed gesture mapping supports only a
predefined vocabulary and expression library. Word-by-word animation may
not fully represent ASL grammar. The project does not claim to provide
unrestricted or complete ASL translation.

## Offline Availability

The proposal plans to store the trained recognition model,
gesture-mapping library, and 3D avatar assets locally. Text-to-speech is
intended to use a local engine such as `pyttsx3`. If local Whisper is
used, its required model files will be downloaded and cached in advance.

The Gemini assistant requires internet connectivity and an API key,
subject to service availability and usage limits. When offline, the
assistant is intended to fall back to a limited set of predefined
responses. The main recognition and avatar features are intended to
remain usable offline after required dependencies and model files have
been installed.

## Team Responsibilities

  ------------------------------------------------------------------------
  Team member           Primary                          Approximate share
                        responsibilities      
  --------------------- --------------------- ----------------------------
  Fatima Javaid (Team   Project coordination,                          33%
  Leader)               ASL recognition,      
                        dataset collection,   
                        preprocessing,        
                        MediaPipe feature     
                        extraction, model     
                        training and          
                        evaluation,           
                        ASL-to-text and       
                        speech                

  Sidratun Muntaha      3D avatar                                      33%
                        development, gesture  
                        animations,           
                        text-to-ASL mapping,  
                        avatar animation      
                        engine, gesture       
                        validation,           
                        documentation support 

  Abeeha Shaikh         AI assistant, speech                           34%
                        recognition, user     
                        interface, backend    
                        API, module           
                        integration,          
                        application testing   
  ------------------------------------------------------------------------

All team members will participate in planning, progress reviews,
integration testing, debugging, final-report preparation, performance
evaluation, and the final demonstration.

## Proposed Timeline

The proposal allocates four weeks to the project:

  -----------------------------------------------------------------------
  Period                  Planned work            Owners
  ----------------------- ----------------------- -----------------------
  Week 1 --- Foundation   Set up webcam landmark  Fatima, Sidratun
                          extraction, finalize    
                          the selected ASL        
                          vocabulary, prepare the 
                          initial dataset, and    
                          establish the rigged 3D 
                          avatar                  

  Week 2 --- AI Model and Train and evaluate      Fatima, Sidratun
  Avatar                  classifiers, implement  
                          real-time predictions,  
                          prepare gesture         
                          animations, and connect 
                          typed English input to  
                          avatar playback         

  Week 3 --- Speech and   Integrate speech        Abeeha, Sidratun
  AI Integration          recognition, assistant  
                          responses, and          
                          voice-controlled avatar 
                          gestures                

  End of Week 3           Integrate all three     Abeeha, all members
                          communication modules   
                          into one web interface  

  Week 4 --- Evaluation   Compare models,         All members
  and Finalization        validate gestures,      
                          measure performance,    
                          fix bugs, and complete  
                          documentation and       
                          demonstration           
  -----------------------------------------------------------------------

## Risks and Mitigation

  -----------------------------------------------------------------------
  Potential risk                      Proposed mitigation
  ----------------------------------- -----------------------------------
  Low ASL recognition accuracy due to Collect additional samples,
  lighting, camera angle, occlusion,  normalize landmark features,
  or signer variation                 compare classifiers, and keep the
                                      initial vocabulary focused

  Complexity of 3D avatar animation   Use a ready-rigged avatar, create
                                      reusable animations, and prioritize
                                      essential gestures

  Incorrect ASL gesture               Validate animations against
  representation                      reliable ASL references, use
                                      complete phrase animations where
                                      appropriate, and avoid claims of
                                      unrestricted translation

  Module integration issues           Test modules independently, define
                                      clear interfaces, and begin
                                      integration before the final week

  Internet or API availability        Keep core recognition and avatar
                                      assets local and provide predefined
                                      assistant responses as an offline
                                      fallback
  -----------------------------------------------------------------------

## Repository

<https://github.com/K242032-FatimaJavaid/SignBridge-AI>

Implementation-specific installation instructions, dependency versions,
configuration steps, and usage examples should be added here once the
corresponding application setup is finalized.

------------------------------------------------------------------------

*Prepared from the SignBridge AI project proposal for AL-2002 Artificial
Intelligence Laboratory, Fall 2026.*
