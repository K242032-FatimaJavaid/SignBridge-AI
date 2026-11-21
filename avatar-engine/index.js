export {
  SignSpeaker,
  compileUtterance,
  estimateDuration,
  utteranceWords,
  CHAT_TIMING
} from "./src/sign-speech.js";

export {
  LETTER_SHAPES,
  DEFAULT_TIMING,
  buildFingerspellingClip,
  letterPose,
  normalizeWord
} from "./src/fingerspelling.js";

export {
  SIGNS,
  SIGNABLE_WORDS,
  DEFAULT_SIGN_TIMING,
  buildSignClip,
  lookupSign,
  signGloss,
  signLookup
} from "./src/sign-dictionary.js";

export {
  HANDSHAPES,
  HANDSHAPE_NAMES,
  applyHandshape,
  handshapeLocals
} from "./src/sign-handshapes.js";

export * from "./src/sign-clip.js";
export * from "./src/sign-rig.js";
