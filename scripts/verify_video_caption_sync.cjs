const { chromium } = require('playwright');

async function verifyVideoSync() {
  console.log('=== LIVE VIDEO CAPTION SYNCHRONIZATION AUDIT ===');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  await page.goto('http://localhost:3000/', { waitUntil: 'networkidle' });

  const videoHandle = await page.$('video');
  if (!videoHandle) {
    console.error('No video element found!');
    process.exit(1);
  }

  // Inspect cues directly from textTrack
  const allCues = await page.evaluate(async (v) => {
    // Wait for track to load
    const track = v.textTracks[0];
    if (track) {
      track.mode = 'showing';
    }
    // Wait up to 1s for cues to be populated
    for (let i = 0; i < 10; i++) {
      if (track && track.cues && track.cues.length > 0) break;
      await new Promise(r => setTimeout(r, 100));
    }

    const cues = [];
    if (track && track.cues) {
      for (let i = 0; i < track.cues.length; i++) {
        const c = track.cues[i];
        cues.push({
          id: c.id || (i + 1),
          startTime: c.startTime,
          endTime: c.endTime,
          text: c.text
        });
      }
    }
    return {
      duration: v.duration,
      cues: cues
    };
  }, videoHandle);

  console.log(`Video total duration: ${allCues.duration.toFixed(2)}s`);
  console.log(`Total parsed text cues in browser: ${allCues.cues.length}`);
  allCues.cues.forEach(c => {
    console.log(`  Cue ${c.id} [${c.startTime.toFixed(2)}s - ${c.endTime.toFixed(2)}s]: "${c.text.slice(0, 50)}..."`);
  });

  // Now perform actual seek and test active cues
  const testPoints = [4.0, 20.0, 48.0];
  console.log('\n--- Active Cue Checks at Key Timestamps ---');
  for (const t of testPoints) {
    const result = await page.evaluate(async ({ v, time }) => {
      return new Promise((resolve) => {
        const onSeeked = () => {
          v.removeEventListener('seeked', onSeeked);
          const track = v.textTracks[0];
          const active = track && track.activeCues && track.activeCues.length > 0
            ? { start: track.activeCues[0].startTime, end: track.activeCues[0].endTime, text: track.activeCues[0].text }
            : null;
          resolve(active);
        };
        v.addEventListener('seeked', onSeeked);
        v.currentTime = time;
      });
    }, { v: videoHandle, time: t });

    console.log(`Timestamp ${t.toFixed(1)}s:`);
    if (result) {
      console.log(`  Active Cue: [${result.start}s - ${result.end}s] -> "${result.text}"`);
    } else {
      console.log(`  No active cue!`);
    }
  }

  await browser.close();
}

verifyVideoSync().catch(console.error);
