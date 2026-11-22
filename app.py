"""SignBridge AI — glassmorphism dashboard, preserving existing integrations."""
from pathlib import Path
import re
import html
import streamlit as st

# Set the main project folder
ROOT = Path(__file__).resolve().parent

# Set the folder where sign videos are stored
VIDEO_DIR = ROOT / 'assets' / 'asl_videos'

# List of signs that have demonstration videos
SUPPORTED_SIGNS = {
    'HELLO': 'HELLO.mp4', 'YES': 'YES.mp4', 'NO': 'NO.mp4',
    'HELP': 'HELP.mp4', 'THANK_YOU': 'THANK_YOU.mp4',
}

# List of signs the model has been trained to recognize
TRAINED_SIGNS = ['AGE', 'FOOD', 'HELLO', 'HELP', 'I', 'IS', 'MY', 'NAME', 'NEED', 'NO', 'PLEASE', 'QUIET', 'SHUT_UP', 'THANK_YOU', 'TO', 'WANT', 'WATER', 'YES', 'YOU', 'GOODBYE', 'STOP', 'YOU_ARE_WELCOME', 'WHAT', 'FRIEND', 'CLAP']

# Count the letters and numbers included in the vocabulary
# SIGNBRIDGE_VOCABULARY_COUNT_V2
ALPHABET_COUNT = 26
NUMBER_COUNT = 10

# Calculate the total vocabulary
TOTAL_VOCABULARY = len(TRAINED_SIGNS) + ALPHABET_COUNT + NUMBER_COUNT

# Set the basic Streamlit page settings
st.set_page_config(page_title='SignBridge AI | Communication Reimagined', page_icon='🤟', layout='wide', initial_sidebar_state='expanded')

# Add the CSS styling for the dashboard
st.markdown('''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
:root {color-scheme:dark;}
html,body,[class*="css"],.stApp {font-family:'Inter',sans-serif;}
.stApp {
 color:#eaf4ff;
 background:radial-gradient(ellipse at 12% 7%,rgba(50,177,202,.19),transparent 34%),
 radial-gradient(ellipse at 92% 18%,rgba(137,99,242,.18),transparent 35%),
 radial-gradient(ellipse at 52% 93%,rgba(23,92,165,.16),transparent 46%),#080f1f;
 background-attachment:fixed;
}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {
 background:rgba(13,25,45,.77);backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);
 border-right:1px solid rgba(182,218,255,.13);
}
[data-testid="stSidebar"] > div:first-child {padding-top:1.8rem;}
.block-container {max-width:1420px;padding-top:2.1rem;padding-bottom:3rem;}
h1,h2,h3,h4 {font-family:'Plus Jakarta Sans',sans-serif!important;letter-spacing:-.035em;color:#f5fbff!important;}
h1 {font-size:clamp(2rem,3.1vw,3rem)!important;font-weight:800!important;}
h2 {font-weight:750!important;} h3 {font-weight:700!important;}
p,li,label {color:#c8d8e9;}
[data-testid="stCaptionContainer"],small {color:#a5b9d0!important;}
.glass {background:rgba(24,42,69,.55);border:1px solid rgba(195,228,255,.16);
 box-shadow:0 18px 50px rgba(0,0,0,.17),inset 0 1px 0 rgba(255,255,255,.045);
 backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-radius:22px;padding:26px;}
.hero {padding:clamp(26px,4vw,52px);background:linear-gradient(120deg,rgba(29,74,99,.66),rgba(30,34,76,.64));
 border:1px solid rgba(168,233,243,.21);border-radius:26px;box-shadow:0 22px 60px rgba(0,0,0,.2);margin-bottom:22px;}
.eyebrow {font-size:.72rem;letter-spacing:.19em;color:#85e6dc;font-weight:800;text-transform:uppercase;margin-bottom:12px;}
.hero-title {font-family:'Plus Jakarta Sans',sans-serif;font-weight:800;font-size:clamp(2rem,4vw,3.7rem);
 line-height:1.14;letter-spacing:-.055em;color:#fff;max-width:790px;margin:0 0 17px;}
.hero-desc {color:#c6d9e8;max-width:690px;font-size:1rem;line-height:1.8;margin:0;}
.gradient-word {background:linear-gradient(100deg,#89f2e2,#9bc8ff,#c4b5fd);background-clip:text;-webkit-background-clip:text;color:transparent;}
.stat {background:rgba(25,45,72,.57);border:1px solid rgba(187,220,250,.14);border-radius:19px;
 padding:23px 24px;min-height:128px;backdrop-filter:blur(18px);}
.stat-num {font-family:'Plus Jakarta Sans',sans-serif;font-size:2rem;font-weight:800;color:#9ff4e6;letter-spacing:-.045em;}
.stat-label {color:#adbed1;font-size:.82rem;margin-top:4px;}
.feature {background:rgba(24,43,69,.57);border:1px solid rgba(190,225,250,.14);border-radius:21px;
 padding:26px;min-height:224px;backdrop-filter:blur(18px);transition:border-color .2s,transform .2s;}
.feature:hover {border-color:rgba(139,235,222,.5);transform:translateY(-3px);}
.feature-icon {font-size:1.8rem;margin-bottom:18px;}
.feature-title {font-family:'Plus Jakarta Sans',sans-serif;color:#fff;font-weight:750;font-size:1.08rem;margin-bottom:9px;}
.feature-desc {color:#b8cadd;line-height:1.65;font-size:.88rem;}
.section-label {font-family:'Plus Jakarta Sans',sans-serif;color:#f2f8ff;font-weight:750;font-size:1.28rem;margin:28px 0 17px;}
.sidebar-brand {font-family:'Plus Jakarta Sans',sans-serif;color:#fff;font-size:1.55rem;font-weight:800;letter-spacing:-.04em;}
.sidebar-sub {color:#9fb9cf;font-size:.78rem;line-height:1.6;margin:5px 0 16px;}
.pill {display:inline-block;background:rgba(91,219,202,.1);border:1px solid rgba(123,238,218,.25);
 color:#a6f7e9;border-radius:99px;padding:6px 12px;font-size:.74rem;font-weight:650;}
[data-testid="stRadio"] label {padding:8px 7px;border-radius:12px;}
[data-testid="stRadio"] label:hover {background:rgba(156,207,255,.07);}
div.stButton > button {border-radius:13px!important;background:linear-gradient(105deg,#31c5bb,#388dc5)!important;
 border:1px solid rgba(170,251,241,.25)!important;color:#071525!important;font-weight:750!important;
 min-height:43px;box-shadow:0 6px 23px rgba(41,183,186,.16);transition:filter .2s,transform .2s;}
div.stButton > button:hover {filter:brightness(1.13);transform:translateY(-1px);}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stChatInput"] textarea {
 background:rgba(13,27,46,.8)!important;color:#f4fbff!important;border:1px solid rgba(173,214,250,.2)!important;border-radius:12px!important;}
[data-testid="stVerticalBlockBorderWrapper"] > div {background:rgba(24,42,68,.45);border-color:rgba(186,221,255,.15)!important;
 backdrop-filter:blur(15px);border-radius:20px!important;}
[data-testid="stChatMessage"] {background:rgba(28,47,75,.45);border:1px solid rgba(178,216,250,.12);border-radius:16px;}
[data-testid="stAlert"] {border-radius:15px;background:rgba(23,50,71,.7);}
[data-testid="stVideo"] {border-radius:16px;overflow:hidden;}
[data-testid="stSidebar"] hr,hr {border-color:rgba(178,217,255,.14)!important;}
.footer {color:#8fa7bf;font-size:.77rem;margin-top:40px;padding-top:16px;border-top:1px solid rgba(180,220,255,.12);}
@media(max-width:700px){.block-container{padding-top:1rem}.hero{padding:25px}.feature{min-height:unset}}
</style>
''', unsafe_allow_html=True)


# Find the signs that match the words in the given text
def find_signs(text):
    """Preserve word order and repetitions for the available video vocabulary."""

    # Convert the text into a list of lowercase words
    words = re.findall(r'[a-z]+', text.lower())
    found = []
    i = 0

    # Go through each word in the text
    while i < len(words):

        # Treat "thank you" as one sign
        if words[i:i+2] == ['thank','you']:
            sign = 'THANK_YOU'
            i += 2
        else:
            # Convert the word to uppercase
            sign = words[i].upper()
            i += 1

        # Add the sign if a video is available for it
        if sign in SUPPORTED_SIGNS:
            found.append(sign)

    return found


# Display the video for each matching sign
def show_sign_videos(text):
    signs = find_signs(text)

    # Show a warning if no matching sign was found
    if not signs:
        st.warning('No matching demonstration video available for this phrase.')
        return

    # Show how many matching videos were found
    st.caption(f'{len(signs)} matching sign demonstration(s) • In sequence')

    # Display each matching sign video
    for index, sign in enumerate(signs, start=1):
        path = VIDEO_DIR / SUPPORTED_SIGNS[sign]
        st.markdown(f'**{index:02d}  ·  {sign.replace("_", " ")}**')

        # Check if the video file exists
        if path.is_file():
            st.video(str(path))
        else:
            st.warning(f'Video not found: {path.name}')

    st.caption('Individual sign demonstrations only; this is not full ASL grammar translation.')


# Create the sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-brand">✧ SignBridge AI</div><div class="sidebar-sub">An intelligent bridge between gestures and communication.</div>', unsafe_allow_html=True)
    st.markdown('<span class="pill">● AI prototype</span>', unsafe_allow_html=True)
    st.divider()

    # Let the user choose which part of the application to use
    page = st.radio('WORKSPACE', ['⌂  Dashboard', '◉  ASL → Speech', '◈  Speech → ASL', '✦  AI Assistant'], label_visibility='visible')

    st.divider()
    st.markdown('**Recognition vocabulary**')

    # Show the number of supported signs, letters, numbers, and videos
    st.caption(f'{len(TRAINED_SIGNS)} words ? {ALPHABET_COUNT} letters ? {NUMBER_COUNT} digits ? {len(SUPPORTED_SIGNS)} demonstration videos')

    # Show the list of supported signs
    with st.expander('View supported signs'):
        st.write(' · '.join(sign.replace('_',' ') for sign in TRAINED_SIGNS))

    st.divider()
    st.caption('University AI project · Limited-vocabulary educational prototype')


# Show the dashboard page
if page.startswith('⌂'):
    st.markdown('''<div class="hero"><div class="eyebrow">WELCOME TO SIGNBRIDGE AI</div>
      <div class="hero-title">Every gesture<br>deserves <span class="gradient-word">a voice.</span></div>
      <p class="hero-desc">Explore real-time sign recognition, spoken communication, sign demonstrations, and intelligent assistance — brought together in one accessible experience.</p>
    </div>''', unsafe_allow_html=True)

    # Create three statistics cards
    a,b,c = st.columns(3, gap='medium')

    with a:
        st.markdown(f'<div class="stat"><div class="stat-num">{TOTAL_VOCABULARY}</div><div class="stat-label">Recognizable signs & characters</div></div>', unsafe_allow_html=True)

    with b:
        st.markdown('<div class="stat"><div class="stat-num">2-way</div><div class="stat-label">Communication tools</div></div>', unsafe_allow_html=True)

    with c:
        st.markdown('<div class="stat"><div class="stat-num">AI</div><div class="stat-label">Gemini-powered assistant</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Explore your workspace</div>', unsafe_allow_html=True)

    # Create the feature cards shown on the dashboard
    cards = [
        ('📷','ASL to Speech','Use your webcam to recognize supported signs and build spoken sentences.'),
        ('🎙️','Speech to ASL','Type or record English and view matching sign demonstration videos.'),
        ('✦','AI Assistant','Ask questions and get helpful responses from Gemini AI.'),
    ]

    # Display the feature cards
    cols = st.columns(3, gap='medium')
    for col,(ico,title,desc) in zip(cols,cards):
        with col:
            st.markdown(f'<div class="feature"><div class="feature-icon">{ico}</div><div class="feature-title">{title}</div><div class="feature-desc">{desc}</div></div>', unsafe_allow_html=True)

    st.info('Start with ASL → Speech to test live sign recognition. The webcam feature continues to use your existing model and sentence-speaking logic.')


# Show the ASL to Speech page
elif 'ASL → Speech' in page:
    st.markdown('<div class="eyebrow">LIVE RECOGNITION STUDIO</div>', unsafe_allow_html=True)
    st.title('ASL to Speech')
    st.caption('Recognize signs in real time, interpret short sequences, and speak the result.')

    # Import and start the webcam recognition feature
    from recognition.webcam_streamlit import show_webcam
    show_webcam()


# Show the Speech to ASL page
elif 'Speech → ASL' in page:

    st.markdown(
        '<div class="eyebrow">REVERSE TRANSLATION STUDIO</div>',
        unsafe_allow_html=True
    )

    st.title('Speech to ASL')

    st.caption(
        'Convert typed or spoken English into '
        '3D sign language animations.'
    )

    # Import and start the avatar feature
    from speech_to_asl_avatar import show_avatar_studio

    show_avatar_studio()


# Show the AI Assistant page
else:
    from assistant.gemini_chat import ask_gemini

    st.markdown('<div class="eyebrow">YOUR INTELLIGENT COMPANION</div>', unsafe_allow_html=True)
    st.title('Gemini AI Assistant')
    st.caption('Explore questions, get explanations, and discover relevant signs.')

    # Create the chat history if it does not already exist
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # Clear the previous conversation
    if st.button('Clear conversation'):
        st.session_state.chat_history = []
        st.rerun()

    # Display the previous messages
    for message in st.session_state.chat_history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    # Get a new question from the user
    question = st.chat_input('Ask SignBridge AI anything…')

    if question:
        # Add the user's question to the chat history
        st.session_state.chat_history.append({'role':'user','content':question})

        try:
            # Get the last few messages to send to Gemini
            recent = st.session_state.chat_history[-10:]
            conversation = '\n'.join(f"{m['role']}: {m['content']}" for m in recent)

            # Ask Gemini for a response
            with st.spinner('Thinking…'):
                answer = ask_gemini(conversation)

            # Add Gemini's response to the chat history
            st.session_state.chat_history.append({'role':'assistant','content':answer})

        except Exception as exc:
            # Remove the question if there was an error
            st.session_state.chat_history.pop()

            # Show the error message
            st.error(f'Gemini error: {exc}')

        else:
            # Refresh the page to show the new response
            st.rerun()

    # Show actions if Gemini has given a response
    if st.session_state.chat_history and st.session_state.chat_history[-1]['role']=='assistant':
        answer = st.session_state.chat_history[-1]['content']
        st.markdown('### Response actions')

        # Speak the Gemini response
        if st.button('🔊 Speak response'):
            try:
                from speech.audio import speak
                speak(answer)
                st.success('Response spoken.')
            except Exception as exc:
                st.error(f'Speech error: {exc}')

        # Show matching ASL sign videos
        with st.expander('🤟 View matching ASL signs'):
            show_sign_videos(answer)


# Show the footer at the bottom of the page
st.markdown('<div class="footer">SignBridge AI · Educational prototype · Not a full ASL translator. Online speech transcription sends microphone audio to an external service.</div>', unsafe_allow_html=True)
