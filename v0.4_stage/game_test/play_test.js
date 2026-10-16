// 착륙장 스테이지 실제 게임 확인(Playwright, 헤드리스 Chromium).
// 게임 개발 서버(npx vite --port 5173)를 띄운 뒤: NODE_PATH=$(npm root -g) node play_test.js <출력 폴더>
// 하는 일: #stage-landing 열기 → 시작 → 클릭 이동(게임 자체 길찾기)과 WASD 이동 → 상자 충돌·가림 확인 → 가장자리 확인 → 출입구 도착(stage:exit 이벤트)
// 결과: 스크린샷, 플레이 영상(webm), result.json
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve(process.argv[2] || 'game_test_out');
fs.mkdirSync(OUT, { recursive: true });
const URL = process.env.STAGE_URL || 'http://localhost:5173/#stage-landing';
const log = [];
const note = (k, v) => { log.push({ k, v }); console.log(k, JSON.stringify(v)); };

(async () => {
  // 지속 프로필: 구운 스프라이트(IndexedDB)를 다음 실행에 다시 씀
  const ctx = await chromium.launchPersistentContext(process.env.PW_PROFILE || path.join(OUT, '..', 'pw_profile'), {
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'],
    viewport: { width: 1280, height: 720 }, recordVideo: { dir: OUT, size: { width: 1280, height: 720 } } });
  const browser = { close: async () => {} };
  const page = ctx.pages()[0] || (await ctx.newPage());
  page.on('console', (m) => { if (m.type() === 'error') note('console.error', m.text()); });
  page.on('pageerror', (e) => note('pageerror', String(e)));
  await page.goto(URL);
  const t0 = Date.now();
  for (;;) {
    const st = await page.evaluate(() => [window.__ready === true, (document.querySelector('#loading .label') || {}).textContent || '']);
    if (st[0]) break;
    if (Date.now() - t0 > 1500000) throw new Error('loading timeout: ' + st[1]);
    if (((Date.now() - t0) / 1000) % 30 < 2) console.log('loading', Math.round((Date.now() - t0) / 1000), st[1]);
    await page.waitForTimeout(2000);
  }
  note('ready', true);
  await page.screenshot({ path: path.join(OUT, '00_title.png') });
  await page.click('#startBtn');
  await page.waitForTimeout(1500);
  await page.evaluate(() => {
    window.__events = [];
    for (const e of ['stage:start', 'stage:combatTrigger', 'stage:combatArea', 'stage:exit', 'stage:exitLocked']) window.__game.on(e, (...a) => window.__events.push([e, a.length ? a[0] : null, +window.__game.time.toFixed(2)]));
  });
  const pos = () => page.evaluate(() => ({ x: +window.__game.player.x.toFixed(2), y: +window.__game.player.y.toFixed(2) }));
  // world tile → CSS px on screen (renderer camera)
  const toScreen = (x, y) => page.evaluate(([x, y]) => {
    const r = window.__renderer; const sx = (x - y) * 20; const sy = (x + y) * 10;
    return { x: (sx - r.cam.x) * r.scale, y: (sy - r.cam.y) * r.scale };
  }, [x, y]);
  // 화면 안에 보이는 거리(최대 6 타일)씩 클릭해 다가감 — 게임의 클릭 이동(길찾기)을 그대로 씀
  const clickTo = async (x, y, wait = 4000) => {
    for (let hop = 0; hop < 12; hop++) {
      const p = await pos();
      const dx = x - p.x, dy = y - p.y, d = Math.hypot(dx, dy);
      if (d < 0.6) break;
      const k = Math.min(1, 6 / d);
      const s = await toScreen(p.x + dx * k, p.y + dy * k);
      await page.mouse.click(s.x, s.y);
      await page.waitForTimeout(Math.min(wait, 900 + d * k * 260));
      const q = await pos();
      if (Math.hypot(q.x - p.x, q.y - p.y) < 0.05) break; // 더 못 감(막힘)
    }
  };
  const holdKey = async (k, ms) => { await page.keyboard.down(k); await page.waitForTimeout(ms); await page.keyboard.up(k); };
  note('spawn', await pos());
  await page.screenshot({ path: path.join(OUT, '01_start.png') });

  // 1) WASD: 화면 기준 이동
  await holdKey('d', 1200); note('after D', await pos());
  await holdKey('s', 1200); note('after S', await pos());
  await page.screenshot({ path: path.join(OUT, '02_wasd.png') });

  // 2) 낮은 상자 쪽으로 클릭 이동 → 상자 옆(긴 면) 지나가기, 상자 뒤(가림) 확인
  const S = await page.evaluate(() => window.__game.stage.data);
  note('exit', S.exit); note('combat', S.combat);
  // 상자: 게임 x 108.5~115.6, y 81.0~85.0 근처 (A3b). 긴 면 앞(y 86)으로
  await clickTo(108, 86.5, 5000); note('box side', await pos());
  await page.screenshot({ path: path.join(OUT, '03_box_side.png') });
  // 상자 뒤쪽 끝(+Y 끝 = 게임 x 작은 쪽)으로 돌아가 상자 너머(가림) 위치 시도
  await clickTo(106.6, 82.5, 5000); note('box back end', await pos());
  await page.screenshot({ path: path.join(OUT, '04_behind_box.png') });
  // 상자 안으로 클릭(막혀야 함)
  await clickTo(112, 83, 3000); note('click into box (should stay outside)', await pos());
  const inBox = await page.evaluate(() => { const p = window.__game.player; return p.x > 108.6 && p.x < 115 && p.y > 81.1 && p.y < 84.8; });
  note('player inside box footprint', inBox);

  // 3) 가장자리: 앞 가장자리 밖(용암)으로 클릭 → 판 안에 남아야 함
  await clickTo(100, 114, 6000); note('edge (should stop at deck edge)', await pos());
  await page.screenshot({ path: path.join(OUT, '05_edge.png') });
  const onDeck = await page.evaluate(() => !window.__game.world.isBlocked(window.__game.player.x, window.__game.player.y));
  note('player on walkable cell', onDeck);

  // 4) 전투 자리 확인 → 출입구로
  const t = S.combat.trigger.center; await clickTo(t[0], t[1], 5000); note('combat trigger point', await pos());
  await clickTo(118, 86, 7000); note('toward door approach', await pos());
  await page.screenshot({ path: path.join(OUT, '06_door_approach.png') });
  const ex = (S.exit.x0 + S.exit.x1) / 2, ey = (S.exit.y0 + S.exit.y1) / 2;
  await clickTo(ex, ey, 6000); note('exit attempt', await pos());
  let ev = await page.evaluate(() => window.__events.map((e) => e[0]));
  if (!ev.includes('stage:exit')) {
    // 좁은 문턱 앞: 키로 마저 붙기
    for (let k = 0; k < 6 && !ev.includes('stage:exit'); k++) {
      const p = await pos();
      const dx = ex - p.x, dy = ey - p.y;
      // 화면 방향: W = (−1,−1), S = (+1,+1), D = (+1,−1), A = (−1,+1) (게임 좌표)
      const keys = [];
      if (dx + dy > 0.05) keys.push('s'); else if (dx + dy < -0.05) keys.push('w');
      if (dx - dy > 0.05) keys.push('d'); else if (dx - dy < -0.05) keys.push('a');
      for (const kk of keys) await page.keyboard.down(kk);
      await page.waitForTimeout(250);
      for (const kk of keys) await page.keyboard.up(kk);
      await page.waitForTimeout(300);
      ev = await page.evaluate(() => window.__events.map((e) => e[0]));
    }
  }
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(OUT, '07_exit.png') });
  note('final pos', await pos());
  note('events', await page.evaluate(() => window.__events));
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify(log, null, 1));
  const vid = page.video();
  await ctx.close();
  if (vid) fs.renameSync(await vid.path(), path.join(OUT, 'play.webm'));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
