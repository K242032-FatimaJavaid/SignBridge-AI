import { compileUtterance, signLookup } from "./dist/sign-language.mjs";

const result = compileUtterance("happy to meet you", {
    signs: signLookup()
});

console.log(JSON.stringify({
    signed: result.signed,
    spelled: result.spelled,
    duration: result.clip?.duration,
    tracks: result.clip?.tracks?.length
}, null, 2));
