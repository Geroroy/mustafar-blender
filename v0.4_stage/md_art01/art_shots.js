// ART01 전후 비교 촬영 — 실제 게임에서 같은 캐릭터 위치·같은 카메라·같은 배율로 5곳을 찍는다(Playwright, 헤드리스 Chromium).
// 전(MO 데이터)·후(ART01 데이터)를 같은 스크립트로 각각 찍어 화면을 1:1로 맞춘다. 게임 코드는 바꾸지 않는다(디버그 전역 __game/__renderer만 사용).
// 준비: 게임 public/stages/mustafar_landing/에 비교할 데이터 → npx vite --port 5173
// 실행: NODE_PATH=$(npm root -g) node art_shots.js <출력 폴더> [remaster,original]
// 좌표: Blender(X, Y) m → 게임 gx = 96 − Y, gy = 95.5 − X. 캐릭터 위치(아래 SPOTS)는 걷는 칸 위의 자리라 렌더 구역(art_regions.json, 이음선 검사용)과 다르다. 입구는 출구 칸에 들어가지 않게 계단 앞.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve(process.argv[2] || 'art_shots');
fs.mkdirSync(OUT, { recursive: true });
const URL = process.env.STAGE_URL || 'http://localhost:5173/#stage-landing';
const G = (X, Y) => [96 - Y, 95.5 - X];
const SPOTS = [
  ['start', 4.13, -5.99], ['ship_front', -7.0, -30.0], ['ship_back', 7.0, -22.0], ['entrance', 8.3, 0.4], ['walkway', -11.0, 12.0],
];
const log = [];

async function run(mode) {
  const ctx = await chromium.launchPersistentContext(path.join(OUT, `_profile_${mode}`), {
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'],
    viewport: { width: 1280, height: 720 } });
  const page = ctx.pages()[0] || (await ctx.newPage());
  const errs = [];
  page.on('pageerror', (e) => errs.push(String(e))); page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  await page.addInitScript((m) => { try { localStorage.setItem('cw.gfx', m); localStorage.setItem('cw.zoom.desktop', '1'); } catch (e) {} }, mode);
  await page.goto(URL);
  for (let i = 0; i < 900; i++) { if (await page.evaluate(() => window.__ready === true)) break; await page.waitForTimeout(1000); }
  await page.click('#startBtn'); await page.waitForTimeout(10000);          // 지역 이름 띠(무스타파 · 착륙장)가 사라질 때까지 — 전후 화면에 같은 UI만 남게
  const hd = await page.evaluate(() => !!window.__renderer.hd);
  for (const [name, X, Y] of SPOTS) {
    const [gx, gy] = G(X, Y);
    // 걷는 칸인지 게임 충돌 함수로 확인하고, 막혀 있으면 가장 가까운 걷는 칸(0.25 m 간격, 3 m 안)으로
    const p = await page.evaluate(([gx, gy]) => {
      const w = window.__game.world; let best = null;
      search: for (let r = 0; r <= 3; r += 0.25) for (let a = 0; a < (r === 0 ? 1 : 16); a++) {
        const x = gx + r * Math.cos(a * Math.PI / 8), y = gy + r * Math.sin(a * Math.PI / 8);
        if (!w.isBlocked(x, y)) { best = [x, y]; break search; }
      }
      const pl = window.__game.player; pl.scripted = true; pl.x = best[0]; pl.y = best[1]; pl.vx = 0; pl.vy = 0;
      return best;
    }, [gx, gy]);
    for (const z of [1, 2]) {
      await page.evaluate((z) => window.__renderer.setZoom(z), z);
      await page.waitForTimeout(1200);
      await page.screenshot({ path: path.join(OUT, `${mode}_z${z}_${name}.png`) });
    }
    await page.evaluate(() => window.__renderer.setZoom(1));
    log.push({ mode, hd, spot: name, world_target: [X, Y], game: p.map((v) => +v.toFixed(2)) });
  }
  log.push({ mode, errors: errs });
  await ctx.close();
}

(async () => {
  const modes = (process.argv[3] || 'remaster,original').split(',');
  for (const m of modes) await run(m);
  fs.writeFileSync(path.join(OUT, `shots_${modes.join('_')}.json`), JSON.stringify(log, null, 1));
  console.log(JSON.stringify(log));
})();
