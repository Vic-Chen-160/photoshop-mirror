// Render scene.html into docs/demo.mp4 and docs/demo.gif.
//
//   npm install && npm run render            full video + GIF
//   node render.mjs --stills 3,5.4,9.5       a few PNG stills into frames/ for checking
//
// Needs Google Chrome and ffmpeg (brew install ffmpeg).
import puppeteer from "puppeteer-core";
import { spawn } from "node:child_process";
import { mkdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DOCS = path.join(HERE, "..");
const FPS = 30;
const DPR = 1.5;                        // 1280×800 scene → 1920×1200 frames
const CHROME = process.env.CHROME ||
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const arg = process.argv.indexOf("--stills");
const stills = arg > 0 ? process.argv[arg + 1].split(",").map(Number) : null;

if (!existsSync(CHROME)) { console.error(`Chrome not found at ${CHROME} (set CHROME=…)`); process.exit(1); }

const browser = await puppeteer.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 800, deviceScaleFactor: DPR });
await page.goto("file://" + path.join(HERE, "scene.html"));
await page.evaluate(() => document.fonts.ready);
const duration = await page.evaluate(() => window.DURATION);

const shot = async t => {
  await page.evaluate(t => window.render(t), t);
  return page.screenshot({ type: "png", captureBeyondViewport: false });
};

if (stills) {
  mkdirSync(path.join(HERE, "frames"), { recursive: true });
  for (const t of stills) {
    const file = path.join(HERE, "frames", `t${t.toFixed(2)}.png`);
    await page.evaluate(t => window.render(t), t);
    await page.screenshot({ path: file });
    console.log(file);
  }
  await browser.close();
  process.exit(0);
}

const run = (args, feed) => new Promise((ok, fail) => {
  const p = spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...args],
                  { stdio: [feed ? "pipe" : "ignore", "inherit", "inherit"] });
  p.on("exit", c => c ? fail(new Error("ffmpeg exited " + c)) : ok());
  if (feed) feed(p.stdin);
});

const mp4 = path.join(DOCS, "demo.mp4");
const gif = path.join(DOCS, "demo.gif");
const frames = Math.round(duration * FPS);

await run(["-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", mp4],
  async stdin => {
    for (let i = 0; i < frames; i++) {
      const buf = await shot(i / FPS);
      if (!stdin.write(buf)) await new Promise(r => stdin.once("drain", r));
      if (i % FPS === 0) process.stdout.write(`\r  frame ${i}/${frames}`);
    }
    stdin.end();
    process.stdout.write(`\r  frame ${frames}/${frames}\n`);
  });
await browser.close();

// GIF: smaller and slower frame rate, with a palette built from the video itself
await run(["-i", mp4, "-vf",
  "fps=15,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=192:stats_mode=diff[p];" +
  "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle", gif]);

console.log("  " + mp4 + "\n  " + gif);
