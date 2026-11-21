// Verifies every sign: compiles, aliases resolve, and each hand actually reaches
// the place / contact the sign describes (IK error in cm).
import { SIGNS, SIGNABLE_WORDS, lookupSign, buildSignClip } from './src/sign-dictionary.js';
import { posePhase, restingPose, place } from './src/sign-clip.js';
import { handPoint, anchorPoint } from './src/sign-rig.js';

const only = process.argv.slice(2);
const dist = (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]) * 100;
let problems = [], compiled = 0;

// aliases
for (const w of SIGNABLE_WORDS) if (!lookupSign(w)) problems.push(`alias ${w} -> nothing`);

for (const [name, sign] of Object.entries(SIGNS)) {
	if (only.length && !only.includes(name)) continue;
	try { const c = buildSignClip(name); if (!c.tracks.length) throw new Error('no tracks'); compiled++; }
	catch (e) { problems.push(`${name}: compile failed: ${e.message}`); continue; }
	sign.phases.forEach((phase, i) => {
		const pose = posePhase(phase);
		for (const side of ['Left', 'Right']) {
			const own = phase[side.toLowerCase()];
			const spec = own === 'rest' ? null : phase.both ? { ...phase.both, ...(own ?? {}) } : own;
			if (!spec || typeof spec !== 'object') continue;
			const wrist = pose.worldPos(`${side}Hand`);
			if (spec.at) {
				const target = place(spec.at, side, pose);
				const err = dist(wrist, target);
				if (err > 1.5) problems.push(`${name} phase ${i+1} ${side}: wrist ${err.toFixed(1)} cm from target (out of reach?)`);
			}
			if (spec.touch && !spec.touch.to) {/* hand-to-hand handled below */}
			if (spec.touch) {
				const other = side === 'Left' ? 'Right' : 'Left';
				const t = spec.touch, tg = t.to ?? 'other';
				let target;
				const outward = side === 'Right' ? -1 : 1;
				if (['other','left','right'].includes(tg)) {
					const o = tg === 'other' ? other : tg === 'left' ? 'Left' : 'Right';
					const b = handPoint(pose, o, t.on ?? 'palm');
					target = [b[0] + outward*(t.out??0), b[1] + (t.up??0), b[2] + (t.forward??0)];
				} else target = place({ anchor: tg, out: t.out, up: t.up, forward: t.forward }, side, pose);
				const part = handPoint(pose, side, t.part ?? 'fingertips');
				const err = dist(part, target) - (t.gap ?? 0) * 100;
				if (Math.abs(err) > 1.5) problems.push(`${name} phase ${i+1} ${side}: contact ${t.part} is ${err.toFixed(1)} cm off its ${tg}${t.on ? '.'+t.on : ''} target`);
			}
		}
		// two hands should not occupy the same space
		const L = pose.worldPos('LeftHand'), R = pose.worldPos('RightHand');
		if ((phase.both || (phase.left && phase.right)) && !JSON.stringify(phase).includes('touch') && dist(L, R) < 6)
			problems.push(`${name} phase ${i+1}: wrists only ${dist(L,R).toFixed(1)} cm apart (hands may collide)`);
	});
}
console.log(`compiled ${compiled}/${only.length || Object.keys(SIGNS).length} signs; ${SIGNABLE_WORDS.length} signable words`);
console.log(problems.length ? problems.join('\n') : 'no problems found');
