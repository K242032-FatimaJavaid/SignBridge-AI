// Lexical ASL signs: the vocabulary an avatar signs instead of spelling.
//
// Fingerspelling is a fallback, not a language: a signer spells names and
// loanwords and SIGNS everything else. This module holds the signs themselves,
// written the way ASL is actually described: a handshape, a place on or in
// front of the body, the direction the palm and fingers face, and a movement
// through those places. Both hands are first-class: two-handed signs are the
// normal case in ASL, and writing one is a single `both:` block because places
// and directions are body-relative (src/sign-clip.js), so the non-dominant hand
// mirrors for free.
//
// Every sign compiles through the same solver the alphabet uses: the wrist goes
// to a POINT in signing space and src/sign-rig.js's two-bone IK finds the
// shoulder, elbow, and wrist that put it there. Nothing is hand-tuned in joint
// angles, so a sign holds up on any rigged avatar the retargeter can drive.
//
// Coverage is deliberately a core vocabulary, not a claim to fluency. Words with
// no entry here fingerspell (src/sign-speech.js decides), and this file is meant
// to grow: add an entry, add a test asserting where the hands end up, done.
//
// Grammar note: these are citation-form signs strung together in English word
// order. That is "signed English", not ASL grammar (which reorders, inflects
// verbs spatially, and carries meaning in the face). The page says so plainly;
// we are not pretending otherwise.

import { SignTimeline, mirrorPhase, neutralPose, posePhase, restingPose } from './sign-clip.js';

// Where the non-dominant hand waits when it is a surface for the other hand to
// act on (FALL, HELP, GOOD, STOP): flat, palm up, in front of the chest.
const BASE_PALM = {
	shape: 'FLAT',
	at: { anchor: 'sternum', out: 0.06, up: -0.09, forward: 0.24 },
	fingers: ['forward', 'in'],
	palm: 'up',
};

// Neutral signing space in front of the chest, where most two-handed signs live.
const NEUTRAL = { anchor: 'sternum', out: 0.13, up: -0.02, forward: 0.26 };

/** Shorthand for a place in signing space: an anchor plus metre offsets. */
const pt = (anchor, out = 0, up = 0, forward = 0) => ({ anchor, out, up, forward });

/** A number sign: the digit handshape held up beside the face, palm out. */
function numberSign(shape, gloss) {
	return {
		gloss,
		phases: [{ t: 0.3, right: { shape, at: pt('chin', 0.2, -0.06, 0.22), fingers: 'up', palm: 'forward' }, hold: 0.26 }],
	};
}

/**
 * The vocabulary. Each sign is a list of phases; `t` is the seconds spent moving
 * INTO that phase and `hold` the seconds spent in it. `both` poses both hands
 * from one description, `right`/`left` override or act alone.
 *
 * @type {Record<string, { gloss: string, phases: object[] }>}
 */
export const SIGNS = Object.freeze({
	HELLO: {
		gloss: 'Flat hand salutes out from the temple.',
		phases: [
			{ face: 'pleasant', t: 0.3, right: { shape: 'FLAT', at: { anchor: 'forehead', out: 0.11, up: -0.03, forward: 0.1 }, fingers: ['up', 'in'], palm: ['forward', 'down'] }, head: { nod: 2 }, hold: 0.1 },
			{ face: 'pleasant', t: 0.32, right: { shape: 'FLAT', at: { anchor: 'forehead', out: 0.21, up: -0.07, forward: 0.18 }, fingers: ['up', 'out'], palm: 'forward' }, head: { nod: -2 }, hold: 0.18 },
		],
	},
	THANK: {
		gloss: 'Flat hand moves out and down from the chin.',
		phases: [
			{ face: 'pleasant', t: 0.3, right: { shape: 'FLAT', touch: { to: 'chin', part: 'fingertips', out: 0.02, forward: 0.01 }, fingers: ['up', 'in'], palm: 'back' }, head: { nod: 3 }, hold: 0.12 },
			{ face: 'pleasant', t: 0.34, right: { shape: 'FLAT', at: { anchor: 'chin', out: 0.08, up: -0.16, forward: 0.28 }, fingers: ['forward', 'up'], palm: 'up' }, head: { nod: 6 }, hold: 0.16 },
		],
	},
	PLEASE: {
		gloss: 'Flat hand circles on the chest.',
		phases: [
			{ t: 0.3, right: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.02, up: 0.03, forward: 0.13 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.26, right: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.09, up: -0.02, forward: 0.13 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.26, right: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.02, up: -0.07, forward: 0.13 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.26, right: { shape: 'FLAT', at: { anchor: 'sternum', out: -0.04, up: -0.02, forward: 0.13 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.26, right: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.02, up: 0.03, forward: 0.13 }, fingers: ['up', 'in'], palm: 'back' }, hold: 0.1 },
		],
	},
	SORRY: {
		gloss: 'A-hand circles over the heart.',
		phases: [
			{ face: 'concern', t: 0.3, right: { shape: 'A', at: { anchor: 'sternum', out: 0.03, up: 0.02, forward: 0.14 }, fingers: 'up', palm: 'back' }, head: { nod: 5, tilt: 3 } },
			{ face: 'concern', t: 0.26, right: { shape: 'A', at: { anchor: 'sternum', out: 0.1, up: -0.04, forward: 0.14 }, fingers: 'up', palm: 'back' }, head: { nod: 5, tilt: 3 } },
			{ face: 'concern', t: 0.26, right: { shape: 'A', at: { anchor: 'sternum', out: 0.03, up: -0.09, forward: 0.14 }, fingers: 'up', palm: 'back' }, head: { nod: 5, tilt: 3 } },
			{ face: 'concern', t: 0.26, right: { shape: 'A', at: { anchor: 'sternum', out: 0.03, up: 0.02, forward: 0.14 }, fingers: 'up', palm: 'back' }, head: { nod: 5, tilt: 3 }, hold: 0.12 },
		],
	},
	YES: {
		gloss: 'S-hand nods at the wrist, like a head saying yes.',
		phases: [
			{ face: 'question', t: 0.28, right: { shape: 'S', at: NEUTRAL, fingers: 'up', palm: 'forward' }, head: { nod: 3 } },
			{ face: 'question', t: 0.18, right: { shape: 'S', at: NEUTRAL, fingers: ['forward', 'down'], palm: ['forward', 'down'] }, head: { nod: 7 } },
			{ face: 'question', t: 0.18, right: { shape: 'S', at: NEUTRAL, fingers: 'up', palm: 'forward' }, head: { nod: 2 } },
			{ face: 'question', t: 0.18, right: { shape: 'S', at: NEUTRAL, fingers: ['forward', 'down'], palm: ['forward', 'down'] }, head: { nod: 7 }, hold: 0.12 },
		],
	},
	NO: {
		gloss: 'Index and middle finger snap shut against the thumb.',
		phases: [
			{ face: 'negate', t: 0.28, right: { shape: 'U', at: { anchor: 'chin', out: 0.14, up: -0.1, forward: 0.24 }, fingers: ['forward', 'up'], palm: ['down', 'forward'] }, head: { turn: 4 } },
			{ face: 'negate', t: 0.2, right: { shape: 'FLAT_O', at: { anchor: 'chin', out: 0.14, up: -0.1, forward: 0.24 }, fingers: ['forward', 'up'], palm: ['down', 'forward'] }, head: { turn: -4 }, hold: 0.16 },
		],
	},
	HAPPY: {
		gloss: 'Both flat hands brush up the chest in circles.',
		phases: [
			{ face: 'pleasant', t: 0.3, both: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.14, up: -0.13, forward: 0.16 }, fingers: ['up', 'in'], palm: 'back' }, head: { nod: -2 } },
			{ face: 'pleasant', t: 0.24, both: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.16, up: 0.01, forward: 0.19 }, fingers: ['up', 'in'], palm: ['back', 'down'] }, head: { nod: -4 } },
			{ face: 'pleasant', t: 0.24, both: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.14, up: -0.13, forward: 0.16 }, fingers: ['up', 'in'], palm: 'back' }, head: { nod: -2 } },
			{ face: 'pleasant', t: 0.24, both: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.16, up: 0.01, forward: 0.19 }, fingers: ['up', 'in'], palm: ['back', 'down'] }, head: { nod: -4 }, hold: 0.14 },
		],
	},
	FALL: {
		gloss: 'Two legs stand on the flat palm, then tip over onto their back.',
		phases: [
			{ t: 0.32, left: BASE_PALM, right: { shape: 'V', touch: { part: 'fingertips', on: 'palm' }, fingers: 'down', palm: 'back' }, hold: 0.16 },
			{ t: 0.3, left: BASE_PALM, right: { shape: 'V', touch: { part: 'edge', on: 'palm', out: 0.09, up: 0.02 }, fingers: ['out', 'forward'], palm: 'up' }, head: { turn: -4, tilt: 4 }, hold: 0.2 },
		],
	},
	YALL: {
		gloss: 'Flat palm-up hand sweeps an arc across the group.',
		phases: [
			{ t: 0.3, right: { shape: 'FLAT', at: { anchor: 'sternum', out: -0.08, up: -0.06, forward: 0.28 }, fingers: ['forward', 'in'], palm: 'up' }, head: { turn: 5 } },
			{ t: 0.42, right: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.26, up: -0.04, forward: 0.24 }, fingers: ['forward', 'out'], palm: 'up' }, head: { turn: -6 }, hold: 0.16 },
		],
	},
	YOU: {
		gloss: 'Index finger points at the person addressed.',
		phases: [
			{ t: 0.28, right: { shape: '1', at: { anchor: 'sternum', out: 0.06, up: 0.04, forward: 0.3 }, fingers: 'forward', palm: 'down' }, head: { nod: 2 }, hold: 0.22 },
		],
	},
	ME: {
		gloss: 'Index finger points to the signer’s own chest.',
		phases: [
			{ t: 0.28, right: { shape: '1', at: { anchor: 'sternum', out: 0.05, up: -0.02, forward: 0.14 }, fingers: ['in', 'back'], palm: 'down' }, hold: 0.22 },
		],
	},
	NAME: {
		gloss: 'Two H-hands tap across each other.',
		phases: [
			{ t: 0.3, left: { shape: 'H', at: { anchor: 'sternum', out: 0.05, up: -0.02, forward: 0.25 }, fingers: ['forward', 'in'], palm: ['in', 'down'] }, right: { shape: 'H', at: { anchor: 'sternum', out: 0.05, up: 0.05, forward: 0.25 }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: { shape: 'H', at: { anchor: 'sternum', out: 0.05, up: -0.02, forward: 0.25 }, fingers: ['forward', 'in'], palm: ['in', 'down'] }, right: { shape: 'H', at: { anchor: 'sternum', out: 0.05, up: 0.005, forward: 0.25 }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: { shape: 'H', at: { anchor: 'sternum', out: 0.05, up: -0.02, forward: 0.25 }, fingers: ['forward', 'in'], palm: ['in', 'down'] }, right: { shape: 'H', at: { anchor: 'sternum', out: 0.05, up: 0.05, forward: 0.25 }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: { shape: 'H', at: { anchor: 'sternum', out: 0.05, up: -0.02, forward: 0.25 }, fingers: ['forward', 'in'], palm: ['in', 'down'] }, right: { shape: 'H', at: { anchor: 'sternum', out: 0.05, up: 0.005, forward: 0.25 }, fingers: ['forward', 'in'], palm: 'down' }, hold: 0.14 },
		],
	},
	HELP: {
		gloss: 'A-hand rides the flat palm upward.',
		phases: [
			{ face: 'intense', t: 0.32, left: BASE_PALM, right: { shape: 'A', touch: { part: 'wrist', on: 'palm' }, fingers: 'up', palm: 'in' } },
			{ face: 'intense', t: 0.28, left: { ...BASE_PALM, at: { anchor: 'sternum', out: 0.06, up: 0.02, forward: 0.26 } }, right: { shape: 'A', touch: { part: 'wrist', on: 'palm' }, fingers: 'up', palm: 'in' }, hold: 0.16 },
		],
	},
	GOOD: {
		gloss: 'Flat hand comes down from the chin onto the other palm.',
		phases: [
			{ face: 'pleasant', t: 0.3, right: { shape: 'FLAT', touch: { to: 'chin', part: 'fingertips', out: 0.02, forward: 0.02 }, fingers: ['up', 'in'], palm: 'back' }, left: BASE_PALM, head: { nod: 3 } },
			{ face: 'pleasant', t: 0.3, right: { shape: 'FLAT', touch: { part: 'palm', on: 'palm' }, fingers: ['forward', 'in'], palm: 'up' }, left: BASE_PALM, head: { nod: 5 }, hold: 0.18 },
		],
	},
	BAD: {
		gloss: 'Flat hand leaves the chin and turns palm-down.',
		phases: [
			{ face: 'negate', t: 0.3, right: { shape: 'FLAT', touch: { to: 'chin', part: 'fingertips', out: 0.02, forward: 0.02 }, fingers: ['up', 'in'], palm: 'back' }, head: { nod: 2 } },
			{ face: 'negate', t: 0.3, right: { shape: 'FLAT', at: { anchor: 'chin', out: 0.14, up: -0.2, forward: 0.24 }, fingers: ['forward', 'out'], palm: 'down' }, head: { nod: -3, turn: -5 }, hold: 0.16 },
		],
	},
	LOVE: {
		gloss: 'Both arms cross over the heart.',
		phases: [
			{ face: 'pleasant', t: 0.36, left: { shape: 'S', at: { anchor: 'sternum', out: -0.07, up: 0.02, forward: 0.15 }, fingers: ['up', 'in'], palm: 'back' }, right: { shape: 'S', at: { anchor: 'sternum', out: -0.07, up: -0.05, forward: 0.17 }, fingers: ['up', 'in'], palm: 'back' }, head: { nod: 4, tilt: 3 }, hold: 0.3 },
		],
	},
	LEARN: {
		gloss: 'Fingers lift knowledge off the palm to the forehead.',
		phases: [
			{ t: 0.32, left: BASE_PALM, right: { shape: 'CLAW', touch: { part: 'fingertips', on: 'palm' }, fingers: 'down', palm: 'down' } },
			{ t: 0.2, left: BASE_PALM, right: { shape: 'FLAT_O', at: { anchor: 'sternum', out: 0.04, up: 0.02, forward: 0.26 }, fingers: 'down', palm: 'back' } },
			{ t: 0.32, left: BASE_PALM, right: { shape: 'FLAT_O', touch: { to: 'forehead', part: 'fingertips', out: 0.04, up: -0.04, gap: 0.02 }, fingers: ['up', 'back'], palm: 'down' }, hold: 0.16 },
		],
	},
	KNOW: {
		gloss: 'Fingertips tap the forehead.',
		phases: [
			{ t: 0.3, right: { shape: 'BENT_B', touch: { to: 'forehead', part: 'fingertips', out: 0.07, up: -0.05, gap: 0.03 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.16, right: { shape: 'BENT_B', touch: { to: 'forehead', part: 'fingertips', out: 0.07, up: -0.05 }, fingers: ['up', 'in'], palm: 'back' }, hold: 0.14 },
		],
	},
	THINK: {
		gloss: 'Index finger touches the temple.',
		phases: [
			{ t: 0.3, right: { shape: '1', touch: { to: 'forehead', part: 'indextip', out: 0.08, up: -0.04 }, fingers: ['in', 'up'], palm: 'down' }, head: { tilt: 3 }, hold: 0.24 },
		],
	},
	SEE: {
		gloss: 'V-hand moves out from the eyes.',
		phases: [
			{ t: 0.3, right: { shape: 'V', touch: { to: 'nose', part: 'fingertips', out: 0.05, up: -0.02, forward: 0.05, gap: 0.02 }, fingers: 'up', palm: 'back' } },
			{ t: 0.3, right: { shape: 'V', at: { anchor: 'nose', out: 0.11, up: -0.02, forward: 0.26 }, fingers: 'forward', palm: 'down' }, hold: 0.16 },
		],
	},
	WANT: {
		gloss: 'Both claw hands draw in toward the body.',
		phases: [
			{ face: 'intense', t: 0.32, both: { shape: 'CLAW', at: { anchor: 'sternum', out: 0.11, up: -0.04, forward: 0.32 }, fingers: 'forward', palm: 'up' } },
			{ face: 'intense', t: 0.3, both: { shape: 'CLAW', at: { anchor: 'sternum', out: 0.11, up: -0.08, forward: 0.19 }, fingers: ['forward', 'up'], palm: 'up' }, head: { nod: 3 }, hold: 0.16 },
		],
	},
	MORE: {
		gloss: 'Both flat-O hands tap fingertips together.',
		phases: [
			{ t: 0.3, both: { shape: 'FLAT_O', at: { anchor: 'sternum', out: 0.11, up: 0.0, forward: 0.26 }, fingers: 'in', palm: 'down' } },
			{ t: 0.18, both: { shape: 'FLAT_O', fingers: 'in', palm: 'down' }, left: { at: { anchor: 'sternum', out: 0.05, up: 0.0, forward: 0.26 } }, right: { touch: { part: 'fingertips', on: 'fingertips' } } },
			{ t: 0.18, both: { shape: 'FLAT_O', at: { anchor: 'sternum', out: 0.11, up: 0.0, forward: 0.26 }, fingers: 'in', palm: 'down' } },
			{ t: 0.18, both: { shape: 'FLAT_O', fingers: 'in', palm: 'down' }, left: { at: { anchor: 'sternum', out: 0.05, up: 0.0, forward: 0.26 } }, right: { touch: { part: 'fingertips', on: 'fingertips' } }, hold: 0.14 },
		],
	},
	STOP: {
		gloss: 'Flat hand chops down onto the other palm.',
		phases: [
			{ face: 'intense', t: 0.3, left: { ...BASE_PALM, at: { anchor: 'sternum', out: 0.04, up: -0.06, forward: 0.26 } }, right: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.04, up: 0.09, forward: 0.26 }, fingers: ['forward', 'up'], palm: 'in' } },
			{ face: 'intense', t: 0.2, left: { ...BASE_PALM, at: { anchor: 'sternum', out: 0.04, up: -0.06, forward: 0.26 } }, right: { shape: 'FLAT', touch: { part: 'edge', on: 'palm' }, fingers: 'forward', palm: 'in' }, head: { nod: 3 }, hold: 0.2 },
		],
	},
	WORK: {
		gloss: 'One fist taps the back of the other wrist twice.',
		phases: [
			{ t: 0.32, left: { shape: 'S', at: { anchor: 'sternum', out: 0.02, up: -0.08, forward: 0.26 }, fingers: ['forward', 'in'], palm: 'down' }, right: { shape: 'S', at: { anchor: 'sternum', out: 0.03, up: 0.02, forward: 0.24 }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: { shape: 'S', at: { anchor: 'sternum', out: 0.02, up: -0.08, forward: 0.26 }, fingers: ['forward', 'in'], palm: 'down' }, right: { shape: 'S', touch: { part: 'palm', on: 'back' }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: { shape: 'S', at: { anchor: 'sternum', out: 0.02, up: -0.08, forward: 0.26 }, fingers: ['forward', 'in'], palm: 'down' }, right: { shape: 'S', at: { anchor: 'sternum', out: 0.03, up: 0.02, forward: 0.24 }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: { shape: 'S', at: { anchor: 'sternum', out: 0.02, up: -0.08, forward: 0.26 }, fingers: ['forward', 'in'], palm: 'down' }, right: { shape: 'S', at: { anchor: 'sternum', out: 0.03, up: -0.03, forward: 0.24 }, fingers: ['forward', 'in'], palm: 'down' }, hold: 0.14 },
		],
	},
	FRIEND: {
		gloss: 'Hooked index fingers link, then swap.',
		phases: [
			{ t: 0.32, left: { shape: 'X', at: { anchor: 'sternum', out: 0.05, up: -0.03, forward: 0.26 }, fingers: ['forward', 'in', 'up'], palm: 'up' }, right: { shape: 'X', at: { anchor: 'sternum', out: 0.05, up: 0.03, forward: 0.26 }, fingers: ['forward', 'in', 'down'], palm: 'down' }, hold: 0.14 },
			{ t: 0.26, left: { shape: 'X', at: { anchor: 'sternum', out: 0.05, up: 0.03, forward: 0.26 }, fingers: ['forward', 'in', 'down'], palm: 'down' }, right: { shape: 'X', at: { anchor: 'sternum', out: 0.05, up: -0.03, forward: 0.26 }, fingers: ['forward', 'in', 'up'], palm: 'up' }, hold: 0.16 },
		],
	},
	MEET: {
		gloss: 'Two upright index fingers come together.',
		phases: [
			{ t: 0.3, both: { shape: '1', at: { anchor: 'sternum', out: 0.17, up: 0.02, forward: 0.26 }, fingers: 'up', palm: 'in' } },
			{ t: 0.28, both: { shape: '1', at: { anchor: 'sternum', out: 0.04, up: 0.02, forward: 0.26 }, fingers: 'up', palm: 'in' }, head: { nod: 3 }, hold: 0.18 },
		],
	},
	NICE: {
		gloss: 'Flat hand slides cleanly across the other palm.',
		phases: [
			{ face: 'pleasant', t: 0.32, left: { ...BASE_PALM, fingers: ['forward', 'out'] }, right: { shape: 'FLAT', touch: { part: 'palm', on: 'palm', out: -0.08 }, fingers: ['forward', 'out'], palm: 'down' } },
			{ face: 'pleasant', t: 0.32, left: { ...BASE_PALM, fingers: ['forward', 'out'] }, right: { shape: 'FLAT', touch: { part: 'palm', on: 'palm', out: 0.15 }, fingers: ['forward', 'out'], palm: 'down' }, hold: 0.16 },
		],
	},
	WELCOME: {
		gloss: 'Open palm sweeps in toward the body, inviting.',
		phases: [
			{ face: 'pleasant', t: 0.32, right: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.22, up: -0.04, forward: 0.3 }, fingers: ['forward', 'out'], palm: 'up' }, head: { turn: -4 } },
			{ face: 'pleasant', t: 0.34, right: { shape: 'FLAT', at: { anchor: 'sternum', out: 0.02, up: -0.06, forward: 0.22 }, fingers: ['forward', 'in'], palm: 'up' }, head: { nod: 4 }, hold: 0.18 },
		],
	},
	WHAT: {
		gloss: 'Both palms turn up and shake, with a questioning brow.',
		phases: [
			{ face: 'wh', t: 0.3, both: { shape: '5', at: { anchor: 'sternum', out: 0.15, up: -0.08, forward: 0.26 }, fingers: ['forward', 'out'], palm: 'up' }, head: { tilt: 3, nod: -3 } },
			{ face: 'wh', t: 0.16, both: { shape: '5', at: { anchor: 'sternum', out: 0.18, up: -0.06, forward: 0.26 }, fingers: ['forward', 'out'], palm: 'up' }, head: { tilt: 3, nod: -3 } },
			{ face: 'wh', t: 0.16, both: { shape: '5', at: { anchor: 'sternum', out: 0.15, up: -0.08, forward: 0.26 }, fingers: ['forward', 'out'], palm: 'up' }, head: { tilt: 3, nod: -3 }, hold: 0.16 },
		],
	},
	FINISH: {
		gloss: 'Both open hands flick out and down: done.',
		phases: [
			{ t: 0.3, both: { shape: '5', at: { anchor: 'sternum', out: 0.1, up: 0.04, forward: 0.24 }, fingers: 'up', palm: 'back' } },
			{ t: 0.24, both: { shape: '5', at: { anchor: 'sternum', out: 0.2, up: -0.08, forward: 0.26 }, fingers: ['forward', 'out'], palm: 'down' }, head: { nod: 4 }, hold: 0.18 },
		],
	},
	AGAIN: {
		gloss: 'Bent hand arcs over and taps into the flat palm.',
		phases: [
			{ t: 0.32, left: BASE_PALM, right: { shape: 'BENT_B', at: { anchor: 'sternum', out: 0.2, up: 0.02, forward: 0.24 }, fingers: ['up', 'out'], palm: 'up' } },
			{ t: 0.3, left: BASE_PALM, right: { shape: 'BENT_B', touch: { part: 'fingertips', on: 'palm' }, fingers: ['down', 'in'], palm: 'down' }, hold: 0.16 },
		],
	},
	THREE: {
		gloss: 'The number three, held up clearly.',
		phases: [
			{ t: 0.3, right: { shape: '3', at: { anchor: 'chin', out: 0.2, up: -0.06, forward: 0.22 }, fingers: 'up', palm: 'forward' }, hold: 0.26 },
		],
	},

	// ═══ Expanded vocabulary ═══════════════════════════════════════════════
	// Everything below is written with the same handshape / place / direction
	// vocabulary as the signs above and compiles through the same IK solver.

	// ── Greetings and courtesy ──────────────────────────────────────────────
	GOODBYE: {
		gloss: 'Open hand waves goodbye.',
		phases: [
			{ face: 'pleasant', t: 0.3, right: { shape: '5', at: pt('chin', 0.2, -0.02, 0.22), fingers: 'up', palm: 'forward' } },
			{ face: 'pleasant', t: 0.16, right: { shape: '5', at: pt('chin', 0.2, -0.02, 0.22), fingers: ['up', 'out'], palm: 'forward' } },
			{ face: 'pleasant', t: 0.16, right: { shape: '5', at: pt('chin', 0.2, -0.02, 0.22), fingers: ['up', 'in'], palm: 'forward' } },
			{ face: 'pleasant', t: 0.16, right: { shape: '5', at: pt('chin', 0.2, -0.02, 0.22), fingers: ['up', 'out'], palm: 'forward' } },
			{ face: 'pleasant', t: 0.16, right: { shape: '5', at: pt('chin', 0.2, -0.02, 0.22), fingers: 'up', palm: 'forward' }, hold: 0.1 },
		],
	},
	ILOVEYOU: {
		gloss: 'The I-love-you handshape: pinky, index, and thumb extended.',
		phases: [
			{ face: 'pleasant', t: 0.32, right: { shape: 'ILY', at: pt('chin', 0.2, -0.04, 0.2), fingers: 'up', palm: 'forward' }, head: { tilt: 3 } },
			{ face: 'pleasant', t: 0.24, right: { shape: 'ILY', at: pt('chin', 0.2, -0.04, 0.27), fingers: 'up', palm: 'forward' }, head: { tilt: 3, nod: 3 }, hold: 0.34 },
		],
	},
	EXCUSE: {
		gloss: 'Fingertips brush across the other palm.',
		phases: [
			{ t: 0.3, left: BASE_PALM, right: { shape: 'FLAT', touch: { part: 'fingertips', on: 'palm', forward: -0.06 }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.2, left: BASE_PALM, right: { shape: 'FLAT', touch: { part: 'fingertips', on: 'palm', forward: 0.04 }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: BASE_PALM, right: { shape: 'FLAT', touch: { part: 'fingertips', on: 'palm', forward: -0.06 }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.2, left: BASE_PALM, right: { shape: 'FLAT', touch: { part: 'fingertips', on: 'palm', forward: 0.04 }, fingers: ['forward', 'in'], palm: 'down' }, hold: 0.12 },
		],
	},
	MORNING: {
		gloss: 'One arm is the horizon; the other hand rises like the sun.',
		phases: [
			{ t: 0.32, left: { shape: 'FLAT', at: pt('belly', 0.04, 0.04, 0.24), fingers: ['forward', 'in'], palm: 'back' }, right: { shape: 'FLAT', at: pt('belly', 0.06, 0.06, 0.28), fingers: ['forward', 'in'], palm: 'up' } },
			{ face: 'pleasant', t: 0.4, left: { shape: 'FLAT', at: pt('belly', 0.04, 0.04, 0.24), fingers: ['forward', 'in'], palm: 'back' }, right: { shape: 'FLAT', at: pt('sternum', 0.06, 0.1, 0.3), fingers: ['forward', 'up'], palm: ['up', 'in'] }, head: { nod: -2 }, hold: 0.2 },
		],
	},
	NIGHT: {
		gloss: 'A bent hand arcs over and rests on the other wrist: the sun sets.',
		phases: [
			{ t: 0.32, left: { shape: 'FLAT', at: pt('sternum', 0.06, -0.04, 0.26), fingers: ['forward', 'in'], palm: 'down' }, right: { shape: 'BENT_B', at: pt('sternum', 0.2, 0.1, 0.26), fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.34, left: { shape: 'FLAT', at: pt('sternum', 0.06, -0.04, 0.26), fingers: ['forward', 'in'], palm: 'down' }, right: { shape: 'BENT_B', touch: { to: 'left', on: 'back', part: 'fingertips', forward: -0.04 }, fingers: ['forward', 'in'], palm: 'down' }, head: { nod: 3 }, hold: 0.2 },
		],
	},

	// ── Questions (the brows carry the grammar) ─────────────────────────────
	WHERE: {
		gloss: 'Index finger wags side to side.',
		phases: [
			{ face: 'wh', t: 0.3, right: { shape: '1', at: pt('sternum', 0.16, 0.0, 0.27), fingers: ['up', 'out'], palm: 'forward' }, head: { tilt: 2 } },
			{ face: 'wh', t: 0.2, right: { shape: '1', at: pt('sternum', 0.16, 0.0, 0.27), fingers: ['up', 'in'], palm: 'forward' }, head: { tilt: 2 } },
			{ face: 'wh', t: 0.2, right: { shape: '1', at: pt('sternum', 0.16, 0.0, 0.27), fingers: ['up', 'out'], palm: 'forward' }, head: { tilt: 2 } },
			{ face: 'wh', t: 0.2, right: { shape: '1', at: pt('sternum', 0.16, 0.0, 0.27), fingers: ['up', 'in'], palm: 'forward' }, head: { tilt: 2 }, hold: 0.1 },
		],
	},
	WHO: {
		gloss: 'Index finger circles at the lips.',
		phases: [
			{ face: 'wh', t: 0.3, right: { shape: '1', at: pt('mouth', 0.02, 0.04, 0.14), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'wh', t: 0.2, right: { shape: '1', at: pt('mouth', 0.07, 0.0, 0.14), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'wh', t: 0.2, right: { shape: '1', at: pt('mouth', 0.02, -0.04, 0.14), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'wh', t: 0.2, right: { shape: '1', at: pt('mouth', -0.03, 0.0, 0.14), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'wh', t: 0.2, right: { shape: '1', at: pt('mouth', 0.02, 0.04, 0.14), fingers: ['up', 'in'], palm: 'back' }, hold: 0.1 },
		],
	},
	WHY: {
		gloss: 'Fingertips leave the forehead and pull out into a Y-hand.',
		phases: [
			{ face: 'wh', t: 0.3, right: { shape: 'BENT_B', touch: { to: 'forehead', part: 'fingertips', out: 0.07, up: -0.05, gap: 0.03 }, fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'wh', t: 0.32, right: { shape: 'Y', at: pt('forehead', 0.14, -0.04, 0.24), fingers: 'up', palm: 'back' }, head: { tilt: 3 }, hold: 0.16 },
		],
	},
	HOW: {
		gloss: 'Two fists roll forward and open, palms up.',
		phases: [
			{ face: 'wh', t: 0.3, both: { shape: 'S', at: pt('sternum', 0.06, -0.02, 0.24), fingers: 'forward', palm: 'down' } },
			{ face: 'wh', t: 0.34, both: { shape: '5', at: pt('sternum', 0.12, 0.0, 0.32), fingers: 'forward', palm: 'up' }, head: { tilt: 2 }, hold: 0.16 },
		],
	},

	// ── Pronouns ────────────────────────────────────────────────────────────
	MY: {
		gloss: 'Flat hand rests on the chest.',
		phases: [
			{ t: 0.3, right: { shape: 'FLAT', at: pt('sternum', 0.02, 0.0, 0.13), fingers: ['up', 'in'], palm: 'back' }, hold: 0.24 },
		],
	},
	YOUR: {
		gloss: 'Flat hand pushes toward the person addressed.',
		phases: [
			{ t: 0.3, right: { shape: 'FLAT', at: pt('sternum', 0.06, 0.04, 0.2), fingers: 'up', palm: 'forward' } },
			{ t: 0.22, right: { shape: 'FLAT', at: pt('sternum', 0.06, 0.04, 0.32), fingers: 'up', palm: 'forward' }, hold: 0.2 },
		],
	},
	HE: {
		gloss: 'Index finger points to the side, at the person.',
		phases: [
			{ t: 0.3, right: { shape: '1', at: pt('sternum', 0.27, -0.02, 0.26), fingers: ['forward', 'out'], palm: 'down' }, head: { turn: -3 }, hold: 0.22 },
		],
	},
	THEY: {
		gloss: 'Index finger sweeps across the group.',
		phases: [
			{ t: 0.3, right: { shape: '1', at: pt('sternum', 0.1, -0.02, 0.28), fingers: 'forward', palm: 'down' } },
			{ t: 0.34, right: { shape: '1', at: pt('sternum', 0.32, -0.02, 0.24), fingers: ['forward', 'out'], palm: 'down' }, head: { turn: -5 }, hold: 0.16 },
		],
	},
	WE: {
		gloss: 'Index finger touches one side of the chest and arcs to the other.',
		phases: [
			{ t: 0.3, right: { shape: '1', at: pt('sternum', 0.17, 0.02, 0.15), fingers: ['in', 'back'], palm: 'down' } },
			{ t: 0.34, right: { shape: '1', at: pt('sternum', -0.14, 0.02, 0.17), fingers: ['in', 'back'], palm: 'down' }, head: { nod: 2 }, hold: 0.16 },
		],
	},

	// ── Needs: food, water, rest, health ────────────────────────────────────
	WATER: {
		gloss: 'W-hand taps the chin.',
		phases: [
			{ t: 0.3, right: { shape: 'W', touch: { to: 'chin', part: 'indextip', out: 0.02, forward: 0.0, gap: 0.04 }, fingers: ['up', 'in'], palm: 'forward' } },
			{ t: 0.14, right: { shape: 'W', touch: { to: 'chin', part: 'indextip', out: 0.02, forward: 0.0 }, fingers: ['up', 'in'], palm: 'forward' } },
			{ t: 0.14, right: { shape: 'W', touch: { to: 'chin', part: 'indextip', out: 0.02, forward: 0.0, gap: 0.04 }, fingers: ['up', 'in'], palm: 'forward' } },
			{ t: 0.14, right: { shape: 'W', touch: { to: 'chin', part: 'indextip', out: 0.02, forward: 0.0 }, fingers: ['up', 'in'], palm: 'forward' }, hold: 0.12 },
		],
	},
	FOOD: {
		gloss: 'Fingertips tap the lips, like putting food in the mouth.',
		phases: [
			{ t: 0.3, right: { shape: 'FLAT_O', touch: { to: 'mouth', part: 'fingertips', out: 0.01, gap: 0.05 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.14, right: { shape: 'FLAT_O', touch: { to: 'mouth', part: 'fingertips', out: 0.01 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.14, right: { shape: 'FLAT_O', touch: { to: 'mouth', part: 'fingertips', out: 0.01, gap: 0.05 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.14, right: { shape: 'FLAT_O', touch: { to: 'mouth', part: 'fingertips', out: 0.01 }, fingers: ['up', 'in'], palm: 'back' }, hold: 0.12 },
		],
	},
	DRINK: {
		gloss: 'C-hand tips toward the mouth, like a cup.',
		phases: [
			{ t: 0.3, right: { shape: 'C', at: pt('mouth', 0.03, -0.03, 0.14), fingers: ['up', 'in'], palm: 'in' } },
			{ t: 0.3, right: { shape: 'C', at: pt('mouth', 0.03, -0.01, 0.14), fingers: ['up', 'back', 'in'], palm: ['in', 'up'] }, head: { nod: -4 }, hold: 0.16 },
		],
	},
	HUNGRY: {
		gloss: 'C-hand slides down the chest, an empty stomach.',
		phases: [
			{ t: 0.3, right: { shape: 'C', at: pt('sternum', 0.0, 0.07, 0.15), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'concern', t: 0.34, right: { shape: 'C', at: pt('sternum', 0.0, -0.1, 0.15), fingers: ['up', 'in'], palm: 'back' }, head: { nod: 3 }, hold: 0.18 },
		],
	},
	THIRSTY: {
		gloss: 'Index finger traces down the throat.',
		phases: [
			{ t: 0.3, right: { shape: '1', at: pt('chin', 0.01, 0.0, 0.13), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'concern', t: 0.34, right: { shape: '1', at: pt('neck', 0.01, -0.08, 0.13), fingers: ['up', 'in'], palm: 'back' }, head: { nod: -3 }, hold: 0.18 },
		],
	},
	TIRED: {
		gloss: 'Bent hands rest on the chest and sag.',
		phases: [
			{ t: 0.3, both: { shape: 'BENT_B', at: pt('sternum', 0.17, 0.04, 0.13), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'concern', t: 0.4, both: { shape: 'BENT_B', at: pt('sternum', 0.2, -0.07, 0.15), fingers: ['forward', 'in', 'up'], palm: 'back' }, head: { nod: 6, tilt: 4 }, hold: 0.22 },
		],
	},
	SICK: {
		gloss: 'Middle fingers touch the forehead and the stomach.',
		phases: [
			{ face: 'concern', t: 0.34, left: { shape: 'OPEN_8', at: pt('belly', 0.03, 0.03, 0.15), fingers: ['up', 'in'], palm: 'back' }, right: { shape: 'OPEN_8', touch: { to: 'forehead', part: 'middletip', out: 0.05, up: -0.05, gap: 0.02 }, fingers: ['up', 'in'], palm: 'back' }, head: { tilt: 4, nod: 3 }, hold: 0.3 },
		],
	},
	PAIN: {
		gloss: 'Index fingers jab toward each other.',
		phases: [
			{ face: 'concern', t: 0.3, both: { shape: '1', at: pt('sternum', 0.2, 0.0, 0.26), fingers: 'in', palm: 'down' } },
			{ face: 'concern', t: 0.16, both: { shape: '1', at: pt('sternum', 0.15, 0.0, 0.26), fingers: 'in', palm: 'down' } },
			{ face: 'concern', t: 0.16, both: { shape: '1', at: pt('sternum', 0.2, 0.0, 0.26), fingers: 'in', palm: 'down' } },
			{ face: 'concern', t: 0.16, both: { shape: '1', at: pt('sternum', 0.15, 0.0, 0.26), fingers: 'in', palm: 'down' }, hold: 0.14 },
		],
	},
	DOCTOR: {
		gloss: 'D-hand taps the wrist, taking a pulse.',
		phases: [
			{ t: 0.3, left: BASE_PALM, right: { shape: 'D', touch: { to: 'left', on: 'wrist', part: 'indextip', gap: 0.04 }, fingers: ['in', 'forward'], palm: 'down' } },
			{ t: 0.14, left: BASE_PALM, right: { shape: 'D', touch: { to: 'left', on: 'wrist', part: 'indextip' }, fingers: ['in', 'forward'], palm: 'down' } },
			{ t: 0.14, left: BASE_PALM, right: { shape: 'D', touch: { to: 'left', on: 'wrist', part: 'indextip', gap: 0.04 }, fingers: ['in', 'forward'], palm: 'down' } },
			{ t: 0.14, left: BASE_PALM, right: { shape: 'D', touch: { to: 'left', on: 'wrist', part: 'indextip' }, fingers: ['in', 'forward'], palm: 'down' }, hold: 0.12 },
		],
	},
	EMERGENCY: {
		gloss: 'E-hand shakes urgently.',
		phases: [
			{ face: 'intense', t: 0.28, right: { shape: 'E', at: pt('chin', 0.2, -0.03, 0.22), fingers: ['up', 'out'], palm: 'forward' } },
			{ face: 'intense', t: 0.12, right: { shape: 'E', at: pt('chin', 0.2, -0.03, 0.22), fingers: ['up', 'in'], palm: 'forward' } },
			{ face: 'intense', t: 0.12, right: { shape: 'E', at: pt('chin', 0.2, -0.03, 0.22), fingers: ['up', 'out'], palm: 'forward' } },
			{ face: 'intense', t: 0.12, right: { shape: 'E', at: pt('chin', 0.2, -0.03, 0.22), fingers: ['up', 'in'], palm: 'forward' } },
			{ face: 'intense', t: 0.12, right: { shape: 'E', at: pt('chin', 0.2, -0.03, 0.22), fingers: ['up', 'out'], palm: 'forward' }, hold: 0.14 },
		],
	},
	BATHROOM: {
		gloss: 'T-hand shakes side to side.',
		phases: [
			{ t: 0.3, right: { shape: 'T', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'out'], palm: 'forward' } },
			{ t: 0.14, right: { shape: 'T', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'in'], palm: 'forward' } },
			{ t: 0.14, right: { shape: 'T', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'out'], palm: 'forward' } },
			{ t: 0.14, right: { shape: 'T', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'in'], palm: 'forward' }, hold: 0.14 },
		],
	},
	SLEEP: {
		gloss: 'Open hand closes down over the face as the head tilts.',
		phases: [
			{ t: 0.3, right: { shape: '5', at: pt('nose', 0.03, 0.03, 0.15), fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.4, right: { shape: 'FLAT_O', at: pt('chin', 0.03, -0.02, 0.13), fingers: ['up', 'in'], palm: 'back' }, head: { nod: 4, tilt: 6 }, hold: 0.24 },
		],
	},

	// ── Feelings ────────────────────────────────────────────────────────────
	SAD: {
		gloss: 'Open hands drop down in front of the face.',
		phases: [
			{ face: 'concern', t: 0.3, both: { shape: '5', at: pt('nose', 0.08, 0.0, 0.15), fingers: 'up', palm: 'back' } },
			{ face: 'concern', t: 0.42, both: { shape: '5', at: pt('chin', 0.1, -0.2, 0.17), fingers: 'up', palm: 'back' }, head: { nod: 7 }, hold: 0.24 },
		],
	},
	ANGRY: {
		gloss: 'Claw hand pulls away from the face, tense.',
		phases: [
			{ face: { negate: 1.4, intense: 0.6 }, t: 0.3, right: { shape: 'CLAW', at: pt('nose', 0.0, -0.02, 0.15), fingers: 'up', palm: 'back' }, head: { nod: 2 } },
			{ face: { negate: 1.4, intense: 0.6 }, t: 0.26, right: { shape: 'CLAW', at: pt('nose', 0.04, 0.0, 0.27), fingers: 'up', palm: 'back' }, head: { nod: 2 }, hold: 0.2 },
		],
	},
	SCARED: {
		gloss: 'Fists spring open at the chest, trembling.',
		phases: [
			{ face: { concern: 1.6 }, t: 0.3, both: { shape: 'S', at: pt('sternum', 0.12, 0.0, 0.16), fingers: ['up', 'in'], palm: 'back' }, head: { tilt: 3 } },
			{ face: { concern: 1.6 }, t: 0.16, both: { shape: '5', at: pt('sternum', 0.14, 0.0, 0.18), fingers: ['up', 'in'], palm: 'back' }, head: { tilt: -3 } },
			{ face: { concern: 1.6 }, t: 0.14, both: { shape: '5', at: pt('sternum', 0.11, 0.0, 0.18), fingers: ['up', 'in'], palm: 'back' }, head: { tilt: 3 } },
			{ face: { concern: 1.6 }, t: 0.14, both: { shape: '5', at: pt('sternum', 0.14, 0.0, 0.18), fingers: ['up', 'in'], palm: 'back' }, head: { tilt: -3 }, hold: 0.14 },
		],
	},
	LIKE: {
		gloss: 'Hand draws out from the chest and pinches closed.',
		phases: [
			{ face: 'pleasant', t: 0.3, right: { shape: 'OPEN_8', at: pt('sternum', 0.02, 0.0, 0.13), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'pleasant', t: 0.3, right: { shape: 'FLAT_O', at: pt('sternum', 0.02, 0.0, 0.26), fingers: ['forward', 'up'], palm: 'back' }, head: { nod: 3 }, hold: 0.16 },
		],
	},
	FINE: {
		gloss: 'Open hand with the thumb tapping the chest.',
		phases: [
			{ face: 'pleasant', t: 0.3, right: { shape: '5', at: pt('sternum', 0.05, 0.03, 0.17), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'pleasant', t: 0.14, right: { shape: '5', at: pt('sternum', 0.05, 0.03, 0.12), fingers: ['up', 'in'], palm: 'back' }, head: { nod: 3 } },
			{ face: 'pleasant', t: 0.14, right: { shape: '5', at: pt('sternum', 0.05, 0.03, 0.17), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'pleasant', t: 0.14, right: { shape: '5', at: pt('sternum', 0.05, 0.03, 0.12), fingers: ['up', 'in'], palm: 'back' }, head: { nod: 3 }, hold: 0.14 },
		],
	},

	// ── Family and places ───────────────────────────────────────────────────
	MOTHER: {
		gloss: 'Open hand, thumb taps the chin.',
		phases: [
			{ t: 0.3, right: { shape: '5', touch: { to: 'chin', part: 'thumbtip', out: 0.02, gap: 0.04 }, fingers: 'up', palm: 'in' } },
			{ t: 0.14, right: { shape: '5', touch: { to: 'chin', part: 'thumbtip', out: 0.02 }, fingers: 'up', palm: 'in' } },
			{ t: 0.14, right: { shape: '5', touch: { to: 'chin', part: 'thumbtip', out: 0.02, gap: 0.04 }, fingers: 'up', palm: 'in' } },
			{ t: 0.14, right: { shape: '5', touch: { to: 'chin', part: 'thumbtip', out: 0.02 }, fingers: 'up', palm: 'in' }, hold: 0.12 },
		],
	},
	FATHER: {
		gloss: 'Open hand, thumb taps the forehead.',
		phases: [
			{ t: 0.3, right: { shape: '5', touch: { to: 'forehead', part: 'thumbtip', out: 0.03, up: -0.04, gap: 0.04 }, fingers: 'up', palm: 'in' } },
			{ t: 0.14, right: { shape: '5', touch: { to: 'forehead', part: 'thumbtip', out: 0.03, up: -0.04 }, fingers: 'up', palm: 'in' } },
			{ t: 0.14, right: { shape: '5', touch: { to: 'forehead', part: 'thumbtip', out: 0.03, up: -0.04, gap: 0.04 }, fingers: 'up', palm: 'in' } },
			{ t: 0.14, right: { shape: '5', touch: { to: 'forehead', part: 'thumbtip', out: 0.03, up: -0.04 }, fingers: 'up', palm: 'in' }, hold: 0.12 },
		],
	},
	FAMILY: {
		gloss: 'Two F-hands circle outward and meet: a group.',
		phases: [
			{ t: 0.3, both: { shape: 'F', at: pt('sternum', 0.06, -0.02, 0.26), fingers: 'forward', palm: 'out' } },
			{ face: 'pleasant', t: 0.36, both: { shape: 'F', at: pt('sternum', 0.22, -0.04, 0.3), fingers: 'forward', palm: 'in' }, hold: 0.18 },
		],
	},
	BABY: {
		gloss: 'Arms cradle and rock a baby.',
		phases: [
			{ face: 'pleasant', t: 0.32, left: { shape: 'FLAT', at: pt('sternum', 0.1, -0.13, 0.24), fingers: ['forward', 'in'], palm: 'up' }, right: { shape: 'FLAT', at: pt('sternum', -0.1, -0.07, 0.27), fingers: ['forward', 'in'], palm: 'up' }, head: { tilt: 3 } },
			{ face: 'pleasant', t: 0.36, left: { shape: 'FLAT', at: pt('sternum', 0.16, -0.13, 0.24), fingers: ['forward', 'in'], palm: 'up' }, right: { shape: 'FLAT', at: pt('sternum', -0.04, -0.07, 0.27), fingers: ['forward', 'in'], palm: 'up' }, head: { tilt: -3 } },
			{ face: 'pleasant', t: 0.36, left: { shape: 'FLAT', at: pt('sternum', 0.1, -0.13, 0.24), fingers: ['forward', 'in'], palm: 'up' }, right: { shape: 'FLAT', at: pt('sternum', -0.1, -0.07, 0.27), fingers: ['forward', 'in'], palm: 'up' }, head: { tilt: 3 }, hold: 0.14 },
		],
	},
	HOME: {
		gloss: 'Fingertips touch the mouth, then the cheek: where you eat and sleep.',
		phases: [
			{ t: 0.3, right: { shape: 'FLAT_O', touch: { to: 'mouth', part: 'fingertips', out: 0.01, gap: 0.02 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.3, right: { shape: 'FLAT_O', touch: { to: 'nose', part: 'fingertips', out: 0.07, up: -0.06, gap: 0.02 }, fingers: ['up', 'in'], palm: 'back' }, head: { nod: 2 }, hold: 0.18 },
		],
	},
	SCHOOL: {
		gloss: 'Flat hands clap twice.',
		phases: [
			{ t: 0.3, left: BASE_PALM, right: { shape: 'FLAT', at: pt('sternum', 0.06, 0.12, 0.26), fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: BASE_PALM, right: { shape: 'FLAT', touch: { part: 'palm', on: 'palm' }, fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: BASE_PALM, right: { shape: 'FLAT', at: pt('sternum', 0.06, 0.12, 0.26), fingers: ['forward', 'in'], palm: 'down' } },
			{ t: 0.16, left: BASE_PALM, right: { shape: 'FLAT', touch: { part: 'palm', on: 'palm' }, fingers: ['forward', 'in'], palm: 'down' }, hold: 0.14 },
		],
	},

	// ── Time ────────────────────────────────────────────────────────────────
	NOW: {
		gloss: 'Both palms drop down: right here, right now.',
		phases: [
			{ t: 0.3, both: { shape: 'BENT_B', at: pt('sternum', 0.13, 0.0, 0.26), fingers: 'forward', palm: 'up' } },
			{ t: 0.22, both: { shape: 'BENT_B', at: pt('sternum', 0.13, -0.08, 0.26), fingers: 'forward', palm: 'up' }, head: { nod: 3 }, hold: 0.18 },
		],
	},
	TOMORROW: {
		gloss: 'A-hand thumb leaves the cheek and moves forward.',
		phases: [
			{ t: 0.3, right: { shape: 'A', touch: { to: 'nose', part: 'thumbtip', out: 0.07, up: -0.06, gap: 0.02 }, fingers: 'up', palm: 'in' } },
			{ t: 0.34, right: { shape: 'A', at: pt('nose', 0.08, -0.06, 0.3), fingers: ['up', 'forward'], palm: 'in' }, head: { nod: 2 }, hold: 0.16 },
		],
	},
	YESTERDAY: {
		gloss: 'A-hand thumb moves back from the cheek toward the ear.',
		phases: [
			{ t: 0.3, right: { shape: 'A', touch: { to: 'nose', part: 'thumbtip', out: 0.07, up: -0.06, gap: 0.02 }, fingers: 'up', palm: 'in' } },
			{ t: 0.3, right: { shape: 'A', touch: { to: 'head', part: 'thumbtip', out: 0.11, up: -0.04, forward: 0.0, gap: 0.02 }, fingers: 'up', palm: 'in' }, head: { nod: -2 }, hold: 0.16 },
		],
	},
	TIME: {
		gloss: 'Index finger taps the wrist, where a watch would be.',
		phases: [
			{ t: 0.3, left: { shape: 'FLAT', at: pt('sternum', 0.05, -0.06, 0.24), fingers: ['forward', 'in'], palm: 'down' }, right: { shape: '1', touch: { to: 'left', on: 'back', part: 'indextip', forward: -0.05, gap: 0.04 }, fingers: ['down', 'in'], palm: 'in' } },
			{ t: 0.14, left: { shape: 'FLAT', at: pt('sternum', 0.05, -0.06, 0.24), fingers: ['forward', 'in'], palm: 'down' }, right: { shape: '1', touch: { to: 'left', on: 'back', part: 'indextip', forward: -0.05 }, fingers: ['down', 'in'], palm: 'in' } },
			{ t: 0.14, left: { shape: 'FLAT', at: pt('sternum', 0.05, -0.06, 0.24), fingers: ['forward', 'in'], palm: 'down' }, right: { shape: '1', touch: { to: 'left', on: 'back', part: 'indextip', forward: -0.05, gap: 0.04 }, fingers: ['down', 'in'], palm: 'in' } },
			{ t: 0.14, left: { shape: 'FLAT', at: pt('sternum', 0.05, -0.06, 0.24), fingers: ['forward', 'in'], palm: 'down' }, right: { shape: '1', touch: { to: 'left', on: 'back', part: 'indextip', forward: -0.05 }, fingers: ['down', 'in'], palm: 'in' }, hold: 0.12 },
		],
	},
	WAIT: {
		gloss: 'Open hands, palms up, fingers wiggling.',
		phases: [
			{ face: 'intense', t: 0.3, both: { shape: '5', at: pt('sternum', 0.14, -0.04, 0.28), fingers: 'forward', palm: 'up' }, head: { tilt: 3 } },
			{ face: 'intense', t: 0.14, both: { shape: 'CLAW', at: pt('sternum', 0.14, -0.04, 0.28), fingers: 'forward', palm: 'up' }, head: { tilt: 3 } },
			{ face: 'intense', t: 0.14, both: { shape: '5', at: pt('sternum', 0.14, -0.04, 0.28), fingers: 'forward', palm: 'up' }, head: { tilt: 3 } },
			{ face: 'intense', t: 0.14, both: { shape: 'CLAW', at: pt('sternum', 0.14, -0.04, 0.28), fingers: 'forward', palm: 'up' }, head: { tilt: 3 }, hold: 0.14 },
		],
	},

	// ── Numbers ─────────────────────────────────────────────────────────────
	ZERO: numberSign('0', 'The number zero: an O-hand.'),
	ONE: numberSign('1', 'The number one.'),
	TWO: numberSign('2', 'The number two.'),
	FOUR: numberSign('4', 'The number four.'),
	FIVE: numberSign('5', 'The number five.'),
	SIX: numberSign('6', 'The number six.'),
	SEVEN: numberSign('7', 'The number seven.'),
	EIGHT: numberSign('8', 'The number eight.'),
	NINE: numberSign('9', 'The number nine.'),

	// ── Common verbs ────────────────────────────────────────────────────────
	GO: {
		gloss: 'Index fingers swing forward and point away.',
		phases: [
			{ t: 0.3, both: { shape: '1', at: pt('sternum', 0.1, 0.0, 0.2), fingers: ['up', 'in'], palm: 'in' } },
			{ t: 0.3, both: { shape: '1', at: pt('sternum', 0.12, -0.02, 0.34), fingers: 'forward', palm: 'down' }, head: { nod: 2 }, hold: 0.16 },
		],
	},
	COME: {
		gloss: 'Index finger beckons toward the body.',
		phases: [
			{ t: 0.3, right: { shape: '1', at: pt('sternum', 0.12, -0.04, 0.34), fingers: 'forward', palm: 'up' } },
			{ t: 0.3, right: { shape: '1', at: pt('sternum', 0.1, -0.04, 0.18), fingers: ['up', 'forward'], palm: 'up' }, head: { nod: 3 }, hold: 0.16 },
		],
	},
	GIVE: {
		gloss: 'Both hands offer something forward.',
		phases: [
			{ t: 0.3, both: { shape: 'FLAT_O', at: pt('sternum', 0.12, -0.06, 0.16), fingers: 'forward', palm: 'up' } },
			{ t: 0.3, both: { shape: 'FLAT', at: pt('sternum', 0.14, -0.04, 0.34), fingers: 'forward', palm: 'up' }, head: { nod: 3 }, hold: 0.16 },
		],
	},
	PLAY: {
		gloss: 'Y-hands shake loosely.',
		phases: [
			{ face: 'pleasant', t: 0.3, both: { shape: 'Y', at: pt('sternum', 0.2, 0.0, 0.22), fingers: ['up', 'out'], palm: 'back' } },
			{ face: 'pleasant', t: 0.14, both: { shape: 'Y', at: pt('sternum', 0.2, 0.0, 0.22), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'pleasant', t: 0.14, both: { shape: 'Y', at: pt('sternum', 0.2, 0.0, 0.22), fingers: ['up', 'out'], palm: 'back' } },
			{ face: 'pleasant', t: 0.14, both: { shape: 'Y', at: pt('sternum', 0.2, 0.0, 0.22), fingers: ['up', 'in'], palm: 'back' }, hold: 0.14 },
		],
	},
	CALL: {
		gloss: 'Y-hand held at the ear like a phone.',
		phases: [
			{ t: 0.34, right: { shape: 'Y', at: pt('head', 0.15, -0.03, 0.04), fingers: ['up', 'in'], palm: 'in' }, head: { tilt: 4 }, hold: 0.34 },
		],
	},
	UNDERSTAND: {
		gloss: 'Fist at the temple flicks the index finger up.',
		phases: [
			{ t: 0.3, right: { shape: 'S', at: pt('forehead', 0.07, -0.04, 0.13), fingers: ['up', 'in'], palm: 'back' } },
			{ face: 'pleasant', t: 0.16, right: { shape: '1', at: pt('forehead', 0.07, -0.04, 0.13), fingers: 'up', palm: 'back' }, head: { nod: 4 }, hold: 0.24 },
		],
	},
	HEAR: {
		gloss: 'Index finger points to the ear.',
		phases: [
			{ t: 0.3, right: { shape: '1', at: pt('head', 0.15, -0.01, 0.03), fingers: 'in', palm: 'down' }, head: { turn: 3 }, hold: 0.28 },
		],
	},
	DEAF: {
		gloss: 'Index finger touches the ear, then the mouth.',
		phases: [
			{ t: 0.3, right: { shape: '1', at: pt('head', 0.15, -0.01, 0.03), fingers: 'in', palm: 'down' }, hold: 0.18 },
			{ t: 0.3, right: { shape: '1', at: pt('mouth', 0.1, 0.0, 0.1), fingers: 'in', palm: 'down' }, hold: 0.22 },
		],
	},
	HAVE: {
		gloss: 'Bent hands pull in toward the chest.',
		phases: [
			{ t: 0.3, both: { shape: 'BENT_B', at: pt('sternum', 0.1, -0.02, 0.24), fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.24, both: { shape: 'BENT_B', at: pt('sternum', 0.1, -0.02, 0.13), fingers: ['up', 'in'], palm: 'back' }, head: { nod: 3 }, hold: 0.18 },
		],
	},
	MAYBE: {
		gloss: 'Flat hands weigh up and down like scales.',
		phases: [
			{ face: 'question', t: 0.3, left: { shape: 'FLAT', at: pt('sternum', 0.1, -0.1, 0.27), fingers: 'forward', palm: 'up' }, right: { shape: 'FLAT', at: pt('sternum', 0.1, 0.0, 0.27), fingers: 'forward', palm: 'up' }, head: { tilt: 4 } },
			{ face: 'question', t: 0.3, left: { shape: 'FLAT', at: pt('sternum', 0.1, 0.0, 0.27), fingers: 'forward', palm: 'up' }, right: { shape: 'FLAT', at: pt('sternum', 0.1, -0.1, 0.27), fingers: 'forward', palm: 'up' }, head: { tilt: -4 } },
			{ face: 'question', t: 0.3, left: { shape: 'FLAT', at: pt('sternum', 0.1, -0.1, 0.27), fingers: 'forward', palm: 'up' }, right: { shape: 'FLAT', at: pt('sternum', 0.1, 0.0, 0.27), fingers: 'forward', palm: 'up' }, head: { tilt: 4 }, hold: 0.14 },
		],
	},
	NEED: {
		gloss: 'Hooked index finger nods down, twice.',
		phases: [
			{ face: 'intense', t: 0.3, right: { shape: 'X', at: NEUTRAL, fingers: 'forward', palm: 'down' } },
			{ face: 'intense', t: 0.18, right: { shape: 'X', at: NEUTRAL, fingers: ['forward', 'down'], palm: 'down' }, head: { nod: 5 } },
			{ face: 'intense', t: 0.18, right: { shape: 'X', at: NEUTRAL, fingers: 'forward', palm: 'down' } },
			{ face: 'intense', t: 0.18, right: { shape: 'X', at: NEUTRAL, fingers: ['forward', 'down'], palm: 'down' }, head: { nod: 5 }, hold: 0.14 },
		],
	},
	CAN: {
		gloss: 'Both fists move firmly down.',
		phases: [
			{ t: 0.3, both: { shape: 'S', at: pt('sternum', 0.13, 0.0, 0.26), fingers: 'forward', palm: 'down' } },
			{ t: 0.22, both: { shape: 'S', at: pt('sternum', 0.13, -0.1, 0.26), fingers: 'forward', palm: 'down' }, head: { nod: 4 }, hold: 0.18 },
		],
	},

	// ── Colors ──────────────────────────────────────────────────────────────
	RED: {
		gloss: 'Index finger brushes down over the lips.',
		phases: [
			{ t: 0.3, right: { shape: '1', touch: { to: 'mouth', part: 'indextip', out: 0.01, up: 0.01, gap: 0.01 }, fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.24, right: { shape: '1', touch: { to: 'mouth', part: 'indextip', out: 0.01, up: -0.05, gap: 0.01 }, fingers: ['up', 'in'], palm: 'back' }, hold: 0.2 },
		],
	},
	BLUE: {
		gloss: 'B-hand twists back and forth.',
		phases: [
			{ t: 0.3, right: { shape: 'B', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'out'], palm: 'forward' } },
			{ t: 0.16, right: { shape: 'B', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'in'], palm: 'forward' } },
			{ t: 0.16, right: { shape: 'B', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'out'], palm: 'forward' }, hold: 0.14 },
		],
	},
	GREEN: {
		gloss: 'G-hand twists back and forth.',
		phases: [
			{ t: 0.3, right: { shape: 'G', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['forward', 'out'], palm: 'in' } },
			{ t: 0.16, right: { shape: 'G', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['forward', 'in'], palm: 'in' } },
			{ t: 0.16, right: { shape: 'G', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['forward', 'out'], palm: 'in' }, hold: 0.14 },
		],
	},
	YELLOW: {
		gloss: 'Y-hand twists back and forth.',
		phases: [
			{ t: 0.3, right: { shape: 'Y', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'out'], palm: 'forward' } },
			{ t: 0.16, right: { shape: 'Y', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'in'], palm: 'forward' } },
			{ t: 0.16, right: { shape: 'Y', at: pt('sternum', 0.2, 0.0, 0.24), fingers: ['up', 'out'], palm: 'forward' }, hold: 0.14 },
		],
	},
	ORANGE: {
		gloss: 'C-hand at the mouth squeezes shut, like squeezing an orange.',
		phases: [
			{ t: 0.3, right: { shape: 'C', at: pt('mouth', 0.03, -0.02, 0.14), fingers: ['up', 'in'], palm: 'in' } },
			{ t: 0.14, right: { shape: 'S', at: pt('mouth', 0.03, -0.02, 0.14), fingers: ['up', 'in'], palm: 'in' } },
			{ t: 0.14, right: { shape: 'C', at: pt('mouth', 0.03, -0.02, 0.14), fingers: ['up', 'in'], palm: 'in' } },
			{ t: 0.14, right: { shape: 'S', at: pt('mouth', 0.03, -0.02, 0.14), fingers: ['up', 'in'], palm: 'in' }, hold: 0.14 },
		],
	},
	BLACK: {
		gloss: 'Index finger draws across the brow.',
		phases: [
			{ t: 0.3, right: { shape: '1', touch: { to: 'forehead', part: 'indextip', out: -0.06, up: -0.02, gap: 0.015 }, fingers: 'in', palm: 'down' } },
			{ t: 0.3, right: { shape: '1', touch: { to: 'forehead', part: 'indextip', out: 0.08, up: -0.02, gap: 0.015 }, fingers: 'in', palm: 'down' }, hold: 0.18 },
		],
	},
	WHITE: {
		gloss: 'Open hand on the chest pulls out and closes.',
		phases: [
			{ t: 0.3, right: { shape: '5', at: pt('sternum', 0.04, 0.02, 0.13), fingers: ['up', 'in'], palm: 'back' } },
			{ t: 0.3, right: { shape: 'FLAT_O', at: pt('sternum', 0.04, 0.02, 0.26), fingers: ['forward', 'up'], palm: 'back' }, hold: 0.16 },
		],
	},
});

// Everyday words that map onto a sign already in the table. Kept separate so the
// vocabulary itself stays one entry per sign.
const ALIASES = Object.freeze({
	HI: 'HELLO',
	HEY: 'HELLO',
	THANKS: 'THANK',
	THANKYOU: 'THANK',
	YEAH: 'YES',
	YEP: 'YES',
	OK: 'YES',
	NOPE: 'NO',
	GLAD: 'HAPPY',
	FELL: 'FALL',
	FALLS: 'FALL',
	YOURE: 'YOU',
	MINE: 'MY',
	I: 'ME',
	IM: 'ME',
	WANTS: 'WANT',
	GREAT: 'GOOD',
	NICELY: 'NICE',
	KNOWS: 'KNOW',
	THINKS: 'THINK',
	LOOK: 'SEE',
	WATCH: 'SEE',
	MEETS: 'MEET',
	WORKS: 'WORK',
	WORKING: 'WORK',
	DONE: 'FINISH',
	FINISHED: 'FINISH',
	AGAIN: 'AGAIN',
	REPEAT: 'AGAIN',
	FRIENDS: 'FRIEND',
	HELPS: 'HELP',
	HELPING: 'HELP',
	LEARNING: 'LEARN',
	NAMED: 'NAME',
	EVERYONE: 'YALL',
	EVERYBODY: 'YALL',
	YALL: 'YALL',
	SORRYY: 'SORRY',

	// ── Expanded vocabulary: inflections and synonyms ──
	BYE: 'GOODBYE',
	BYEBYE: 'GOODBYE',
	FAREWELL: 'GOODBYE',
	CHEERIO: 'GOODBYE',
	ILY: 'ILOVEYOU',
	PARDON: 'EXCUSE',
	APOLOGIZE: 'SORRY',
	APOLOGY: 'SORRY',
	WHATS: 'WHAT',
	WHERES: 'WHERE',
	WHOS: 'WHO',
	WHOM: 'WHO',
	HOWS: 'HOW',
	WHYS: 'WHY',
	HES: 'HE',
	SHE: 'HE',
	SHES: 'HE',
	HIM: 'HE',
	HER: 'HE',
	HIS: 'HE',
	THEM: 'THEY',
	THEIR: 'THEY',
	THEIRS: 'THEY',
	THEYRE: 'THEY',
	US: 'WE',
	OUR: 'WE',
	OURS: 'WE',
	WERE: 'WE',
	LETS: 'WE',
	YOURS: 'YOUR',
	EAT: 'FOOD',
	EATS: 'FOOD',
	EATING: 'FOOD',
	ATE: 'FOOD',
	MEAL: 'FOOD',
	LUNCH: 'FOOD',
	DINNER: 'FOOD',
	BREAKFAST: 'FOOD',
	DRINKS: 'DRINK',
	DRINKING: 'DRINK',
	DRANK: 'DRINK',
	BEVERAGE: 'DRINK',
	STARVING: 'HUNGRY',
	EXHAUSTED: 'TIRED',
	SLEEPY: 'TIRED',
	FATIGUED: 'TIRED',
	ILL: 'SICK',
	UNWELL: 'SICK',
	HURT: 'PAIN',
	HURTS: 'PAIN',
	ACHE: 'PAIN',
	PAINFUL: 'PAIN',
	SORE: 'PAIN',
	DOCTORS: 'DOCTOR',
	DR: 'DOCTOR',
	PHYSICIAN: 'DOCTOR',
	EMERGENCIES: 'EMERGENCY',
	URGENT: 'EMERGENCY',
	TOILET: 'BATHROOM',
	RESTROOM: 'BATHROOM',
	WASHROOM: 'BATHROOM',
	LAVATORY: 'BATHROOM',
	LOO: 'BATHROOM',
	SLEEPS: 'SLEEP',
	SLEEPING: 'SLEEP',
	SLEPT: 'SLEEP',
	MOM: 'MOTHER',
	MOMMY: 'MOTHER',
	MAMA: 'MOTHER',
	MUM: 'MOTHER',
	MOTHERS: 'MOTHER',
	DAD: 'FATHER',
	DADDY: 'FATHER',
	PAPA: 'FATHER',
	FATHERS: 'FATHER',
	FAMILIES: 'FAMILY',
	BABIES: 'BABY',
	INFANT: 'BABY',
	HOUSE: 'HOME',
	HOMES: 'HOME',
	SCHOOLS: 'SCHOOL',
	UNHAPPY: 'SAD',
	DEPRESSED: 'SAD',
	UPSET: 'SAD',
	MAD: 'ANGRY',
	FURIOUS: 'ANGRY',
	ANNOYED: 'ANGRY',
	AFRAID: 'SCARED',
	FRIGHTENED: 'SCARED',
	FEAR: 'SCARED',
	FEARFUL: 'SCARED',
	LOVES: 'LOVE',
	LOVED: 'LOVE',
	LIKES: 'LIKE',
	LIKED: 'LIKE',
	ENJOY: 'LIKE',
	OKAY: 'FINE',
	CURRENTLY: 'NOW',
	TIMES: 'TIME',
	CALLS: 'CALL',
	CALLED: 'CALL',
	CALLING: 'CALL',
	PHONE: 'CALL',
	TELEPHONE: 'CALL',
	UNDERSTANDS: 'UNDERSTAND',
	UNDERSTOOD: 'UNDERSTAND',
	HEARS: 'HEAR',
	LISTEN: 'HEAR',
	LISTENS: 'HEAR',
	HAS: 'HAVE',
	HAD: 'HAVE',
	HAVING: 'HAVE',
	COMES: 'COME',
	CAME: 'COME',
	COMING: 'COME',
	GOES: 'GO',
	WENT: 'GO',
	GOING: 'GO',
	GIVES: 'GIVE',
	GAVE: 'GIVE',
	GIVING: 'GIVE',
	PLAYS: 'PLAY',
	PLAYING: 'PLAY',
	PLAYED: 'PLAY',
	WAITS: 'WAIT',
	WAITING: 'WAIT',
	WAITED: 'WAIT',
	NEEDS: 'NEED',
	NEEDED: 'NEED',
	PERHAPS: 'MAYBE',
	POSSIBLY: 'MAYBE',
	NOT: 'NO',
	DONT: 'NO',
	DOESNT: 'NO',
	DIDNT: 'NO',
	ISNT: 'NO',
	ARENT: 'NO',
	WONT: 'NO',
	YUP: 'YES',
	SURE: 'YES',
	WELCOMES: 'WELCOME',
	HAPPILY: 'HAPPY',
	CHEERFUL: 'HAPPY',
});

/** Every word this dictionary can sign, including aliases. */
export const SIGNABLE_WORDS = Object.freeze([...Object.keys(SIGNS), ...Object.keys(ALIASES)].sort());

/**
 * Resolve a normalized word to its sign entry, or null when it must be spelled.
 * @param {string} word  already uppercased/normalized
 * @returns {{ name: string, sign: object }|null}
 */
export function lookupSign(word) {
	const key = String(word ?? '').toUpperCase();
	const name = SIGNS[key] ? key : ALIASES[key];
	return name && SIGNS[name] ? { name, sign: SIGNS[name] } : null;
}

export const DEFAULT_SIGN_TIMING = Object.freeze({
	leadSeconds: 0.3,
	tailSeconds: 0.38,
	/** Scales every authored phase duration: the tempo control for chat. */
	rate: 1,
});

/**
 * Build the AnimationClip document for one lexical sign.
 *
 * @param {string} word
 * @param {{ name?: string, base?: import('./sign-rig.js').Pose, settle?: boolean, rate?: number }} [opts]
 * @returns {object|null} clip document, or null when the word has no sign
 */
export function buildSignClip(word, opts = {}) {
	const found = lookupSign(word);
	if (!found) return null;
	const timing = { ...DEFAULT_SIGN_TIMING, ...opts };
	const rate = timing.rate > 0 ? timing.rate : 1;
	const base = opts.base ?? restingPose();
	const lead = opts.lead !== false;
	// Mid-utterance the hands are already up, so the sign opens from the neutral
	// signing stance rather than from the arms hanging at the sides.
	const tl = new SignTimeline({ base, open: lead ? base : neutralPose(base) });

	const dominant = opts.dominant === 'Left' ? 'Left' : 'Right';
	found.sign.phases.forEach((phase, i) => {
		const seconds = ((phase.t ?? 0.3) + (i === 0 && lead ? timing.leadSeconds : 0)) / rate;
		const shaped = dominant === 'Left' ? mirrorPhase(phase) : phase;
		tl.to(posePhase(shaped, base), seconds, { ease: phase.ease ?? (i === 0 ? 'out' : 'smooth') });
		if (phase.hold) tl.hold(phase.hold / rate);
	});

	if (opts.settle !== false) tl.settle(timing.tailSeconds / rate);

	return tl.build({
		name: opts.name ?? `sign-${found.name.toLowerCase()}`,
		seed: `sign:${found.name}:${rate}:${lead}:${opts.settle !== false}:${dominant}`,
	});
}

/**
 * A lookup function shaped for {@link import('./sign-speech.js').compileUtterance}:
 * pass it as `signs` and every word with an entry is SIGNED, the rest spelled.
 *
 * @param {{ base?: import('./sign-rig.js').Pose, rate?: number }} [opts]
 * @returns {(word: string) => object|null}
 */
export function signLookup(opts = {}) {
	const cache = new Map();
	return (word, position = {}) => {
		const lead = position.first !== false;
		const settle = position.last !== false;
		const key = `${word}|${lead}|${settle}|${opts.dominant ?? 'Right'}`;
		if (!cache.has(key)) cache.set(key, buildSignClip(word, { ...opts, lead, settle }));
		return cache.get(key);
	};
}

/** Human-readable description of a sign, for the vocabulary UI. */
export function signGloss(word) {
	return lookupSign(word)?.sign.gloss ?? null;
}
