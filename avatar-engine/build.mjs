import { build } from "esbuild";
import { mkdirSync } from "node:fs";

mkdirSync("dist", { recursive: true });

await build({
  entryPoints: ["index.js"],
  outfile: "dist/sign-language.mjs",
  bundle: true,
  format: "esm",
  platform: "neutral",
  target: "es2020",
  logLevel: "info"
});

console.log("ASL signing engine built successfully.");
