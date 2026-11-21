import { writeFileSync } from "node:fs";
import { compileUtterance, signLookup } from "./dist/sign-language.mjs";

const result = compileUtterance("happy to meet you", {
    signs: signLookup()
});

writeFileSync(
    "./test-clip.json",
    JSON.stringify(result, null, 2),
    "utf8"
);

console.log("Clip saved: test-clip.json");
console.log("Clip properties:", Object.keys(result.clip));
console.log("First animation track:");
console.log(JSON.stringify(result.clip.tracks[0], null, 2));
