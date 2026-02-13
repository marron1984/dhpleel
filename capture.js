const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const path = require('path');
const fs = require('fs');

const PORT = 8795;
const FPS = 30;
const WIDTH = 1080;
const HEIGHT = 1920;

const SCENE_DURATIONS = [3000, 4500, 4000, 3500, 4000, 4000, 4000, 4500, 3500, 5000];

const IMAGE_MAP = {
  'https://github.com/user-attachments/assets/26f975ed-b6d0-4796-83f1-a3a18aa36a61': '/output/images/wanmono.jpg',
  'https://github.com/user-attachments/assets/bb591483-6e62-4606-b122-2b5bff559be7': '/output/images/zensai.jpg',
  'https://github.com/user-attachments/assets/53efd776-9e27-4267-817d-3945c0ae9f09': '/output/images/tsukuri.jpg',
  'https://github.com/user-attachments/assets/d1e0f425-072b-467c-a53b-a01e826704ce': '/output/images/yakimono.jpg',
  'https://github.com/user-attachments/assets/410caabd-4fb0-4d4e-8126-7a9d26ab55ab': '/output/images/takimono.jpg',
  'https://github.com/user-attachments/assets/5085807d-85e8-4bd2-86b8-2e6291c9e5b2': '/output/images/shiage.jpg',
  'https://github.com/user-attachments/assets/148e92af-7c36-4a14-9158-f53f3de600db': '/output/images/taimeshi.jpg',
  'https://github.com/user-attachments/assets/f304adcd-7ace-4840-b1b4-b85a17259f50': '/output/images/kanmi.jpg'
};

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process'] });
  const page = await browser.newPage({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 2 });

  // Route GitHub image URLs to local files
  await page.route('https://github.com/user-attachments/assets/**', async (route) => {
    const url = route.request().url();
    const localPath = IMAGE_MAP[url];
    if (localPath) {
      const fullPath = path.join(__dirname, localPath);
      if (fs.existsSync(fullPath)) {
        const body = fs.readFileSync(fullPath);
        await route.fulfill({ status: 200, contentType: 'image/jpeg', body });
        return;
      }
    }
    await route.abort();
  });

  await page.goto(`http://localhost:${PORT}/reels-video-souden-v2.html`, { waitUntil: 'networkidle' });

  // Strip phone frame, scale to 1080x1920
  await page.evaluate(() => {
    document.body.style.margin = '0';
    document.body.style.padding = '0';
    document.body.style.background = '#000';
    document.body.style.overflow = 'hidden';
    document.body.style.display = 'block';

    // Hide non-video elements
    document.querySelector('.page-title').style.display = 'none';
    document.querySelector('.controls').style.display = 'none';
    document.querySelector('.scene-indicator').style.display = 'none';
    document.querySelector('.menu-preview').style.display = 'none';
    document.querySelector('.export-hint').style.display = 'none';
    document.querySelector('.play-overlay').style.display = 'none';
    document.querySelector('.tap-area').style.display = 'none';

    // Strip phone frame, fill viewport
    const pw = document.querySelector('.phone-wrapper');
    pw.style.width = '100vw';
    pw.style.height = '100vh';
    pw.style.borderRadius = '0';
    pw.style.boxShadow = 'none';

    const rc = document.querySelector('.reels-container');
    rc.style.borderRadius = '0';

    const notch = document.querySelector('.phone-notch');
    if (notch) notch.style.display = 'none';

    // Scale up fonts for 1080 output
    const styleEl = document.createElement('style');
    styleEl.textContent = `
      .t-restaurant { font-size: 42px !important; letter-spacing: 14px !important; }
      .t-subtitle { font-size: 18px !important; letter-spacing: 7px !important; }
      .t-michelin { font-size: 14px !important; letter-spacing: 3px !important; padding: 6px 20px !important; }
      .t-course { font-size: 22px !important; letter-spacing: 11px !important; }
      .t-course-en { font-size: 16px !important; letter-spacing: 4px !important; }
      .t-num { font-size: 72px !important; }
      .t-dish-jp { font-size: 33px !important; letter-spacing: 9px !important; }
      .t-dish-desc { font-size: 16px !important; letter-spacing: 2px !important; }
      .t-cta-lead { font-size: 19px !important; letter-spacing: 4px !important; }
      .t-phone { font-size: 45px !important; letter-spacing: 4px !important; }
      .t-address { font-size: 15px !important; letter-spacing: 3px !important; }
      .t-price { font-size: 24px !important; padding: 9px 30px !important; }
      .t-store-block { font-size: 16px !important; letter-spacing: 2px !important; line-height: 2.2 !important; margin-top: 20px !important; }
      .text-bottom { bottom: 84px !important; left: 42px !important; right: 42px !important; }
      .text-center { left: 36px !important; right: 36px !important; }
      .letterbox-top, .letterbox-bottom { height: 0 !important; }
      .scene.active .letterbox-top, .scene.active .letterbox-bottom { animation: letterboxIn1080 1s ease 0.3s forwards !important; }
      @keyframes letterboxIn1080 { to { height: 42px; } }
      .gold-accent { height: 1.5px !important; }
      .t-gold-rule { height: 1.5px !important; }
    `;
    document.head.appendChild(styleEl);
  });

  // Wait for fonts and images
  await page.waitForTimeout(2000);

  const framesDir = path.join(__dirname, 'output', 'frames');
  let frameNum = 0;

  for (let sceneIdx = 0; sceneIdx < SCENE_DURATIONS.length; sceneIdx++) {
    const dur = SCENE_DURATIONS[sceneIdx];
    const totalFrames = Math.round((dur / 1000) * FPS);

    // Activate scene
    await page.evaluate((idx) => {
      document.querySelectorAll('.scene').forEach(s => {
        s.classList.remove('active', 'exiting');
        s.style.opacity = '0';
        s.style.zIndex = '1';
      });
      const el = document.getElementById('scene-' + idx);
      el.style.opacity = '';
      el.style.zIndex = '10';
      el.offsetWidth; // force reflow
      el.classList.add('active');
    }, sceneIdx);

    // Small wait for scene setup
    await page.waitForTimeout(100);

    // Pause all animations
    await page.evaluate((idx) => {
      const el = document.getElementById('scene-' + idx);
      el.getAnimations({ subtree: true }).forEach(a => a.pause());
    }, sceneIdx);

    // Capture each frame
    for (let f = 0; f < totalFrames; f++) {
      const localTimeMs = (f / FPS) * 1000;

      await page.evaluate(({ idx, t }) => {
        const el = document.getElementById('scene-' + idx);
        el.getAnimations({ subtree: true }).forEach(a => {
          a.currentTime = t;
        });
      }, { idx: sceneIdx, t: localTimeMs });

      const padded = String(frameNum).padStart(5, '0');
      await page.screenshot({ path: path.join(framesDir, `frame_${padded}.png`), type: 'png' });
      frameNum++;

      if (frameNum % 100 === 0) console.log(`Frame ${frameNum}...`);
    }

    console.log(`Scene ${sceneIdx} done (${totalFrames} frames)`);
  }

  await browser.close();
  console.log('Done: ' + frameNum);
})();
