// MO(Movie Duels 원본 그대로) 실제 게임 확인(Playwright, 헤드리스 Chromium). 기존 game_test/play_test.js와 같은 방식(게임 클릭 이동·키 이동, 이벤트 기록).
// 준비: 게임 public/stages/mustafar_landing/에 out_md_poc01(또는 out_md_poc02)을 잠시 복사 → npx vite --port 5173
// 실행: NODE_PATH=$(npm root -g) node md_play_test.js <출력 폴더>
// 좌표: 게임 타일(1 m). Blender(X, Y) → 게임 gx = 96 − Y, gy = 95.5 − X
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve(process.argv[2] || 'md_play_out');
fs.mkdirSync(OUT, { recursive: true });
const URL = process.env.STAGE_URL || 'http://localhost:5173/#stage-landing';
const log = [];
const note = (k, v) => { log.push({ k, v }); console.log(k, JSON.stringify(v)); };
const G = (X, Y) => [96 - Y, 95.5 - X];          // Blender → 게임
const W = (gx, gy) => [95.5 - gy, 96 - gx];        // 게임 → Blender (X, Y)

(async () => {
  const ctx = await chromium.launchPersistentContext(process.env.PW_PROFILE || path.join(OUT, '..', 'pw_profile'), {
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'],
    viewport: { width: 1280, height: 720 }, recordVideo: { dir: OUT, size: { width: 1280, height: 720 } } });
  const page = ctx.pages()[0] || (await ctx.newPage());
  page.on('console', (m) => { if (m.type() === 'error') note('console.error', m.text()); });
  page.on('pageerror', (e) => note('pageerror', String(e)));
  await page.goto(URL);
  const t0 = Date.now();
  for (;;) {
    const st = await page.evaluate(() => [window.__ready === true, (document.querySelector('#loading .label') || {}).textContent || '']);
    if (st[0]) break;
    if (Date.now() - t0 > 1500000) throw new Error('loading timeout: ' + st[1]);
    await page.waitForTimeout(2000);
  }
  note('ready', true);
  await page.click('#startBtn');
  await page.waitForTimeout(1500);
  await page.evaluate(() => {
    window.__events = [];
    for (const e of ['stage:start', 'stage:combatTrigger', 'stage:combatArea', 'stage:exit', 'stage:exitLocked']) window.__game.on(e, (...a) => window.__events.push([e, a.length ? a[0] : null, +window.__game.time.toFixed(2)]));
  });
  const pos = () => page.evaluate(() => ({ x: +window.__game.player.x.toFixed(2), y: +window.__game.player.y.toFixed(2) }));
  const walk = () => page.evaluate(() => !window.__game.world.isBlocked(window.__game.player.x, window.__game.player.y));
  const toScreen = (x, y) => page.evaluate(([x, y]) => { const r = window.__renderer; return { x: ((x - y) * 20 - r.cam.x) * r.scale, y: ((x + y) * 10 - r.cam.y) * r.scale }; }, [x, y]);
  const clickTo = async (x, y, wait = 4000, tol = 0.6) => {
    for (let hop = 0; hop < 14; hop++) {
      const p = await pos(); const dx = x - p.x, dy = y - p.y, d = Math.hypot(dx, dy);
      if (d < tol) break;
      const k = Math.min(1, 6 / d); const s = await toScreen(p.x + dx * k, p.y + dy * k);
      await page.mouse.click(s.x, s.y); await page.waitForTimeout(Math.min(wait, 900 + d * k * 260));
      const q = await pos(); if (Math.hypot(q.x - p.x, q.y - p.y) < 0.05) break;
    }
  };
  // 키 이동으로 목표 쪽으로(클릭 길찾기가 막힌 칸 옆에서 실패할 때). 화면 방향: W = (−1,−1), S = (+1,+1), D = (+1,−1), A = (−1,+1) (게임 좌표)
  const keyToward = async (gx, gy, ms = 700) => {
    const p = await pos(); const dx = gx - p.x, dy = gy - p.y; const keys = [];
    if (dx + dy > 0.1) keys.push('s'); else if (dx + dy < -0.1) keys.push('w');
    if (dx - dy > 0.1) keys.push('d'); else if (dx - dy < -0.1) keys.push('a');
    for (const k of keys) await page.keyboard.down(k);
    await page.waitForTimeout(ms);
    for (const k of keys) await page.keyboard.up(k);
  };
  const reach = async (gx, gy, tol = 0.6) => {          // 클릭 → 안 되면 키로 조금 → 다시 클릭
    for (let i = 0; i < 4; i++) {
      await clickTo(gx, gy, 6000, tol); const p = await pos();
      if (Math.hypot(gx - p.x, gy - p.y) < tol + 0.2) return;
      await keyToward(gx, gy, 600);
    }
  };
  const home = async (X = 0, Y = 0) => { const [gx, gy] = G(X, Y); await reach(gx, gy, 1.0); };
  const go = async (label, X, Y, shot, check, from) => {
    if (from) await home(from[0], from[1]);
    const p0 = await pos();
    const [gx, gy] = G(X, Y); await clickTo(gx, gy, 6000);
    if (Math.hypot((await pos()).x - p0.x, (await pos()).y - p0.y) < 0.05) await keyToward(gx, gy, 1500);
    const q = await pos(); const [wx, wy] = W(q.x, q.y); const wk = await walk();
    const r = { game: q, world: [+wx.toFixed(2), +wy.toFixed(2)], walkable: wk, moved: +Math.hypot(q.x - p0.x, q.y - p0.y).toFixed(2) };
    if (check) r.pass = check(wx, wy) && wk;
    note(label, r);
    if (shot) await page.screenshot({ path: path.join(OUT, shot) });
    return r;
  };
  const S = await page.evaluate(() => window.__game.stage.data);
  note('spawn', await pos()); note('exit', S.exit); note('combat', S.combat);
  note('spawn walkable', await walk());
  await page.screenshot({ path: path.join(OUT, '01_start.png') });
  await page.evaluate(() => window.__game.stage.lockExit(true));
  const outside = (b) => (x, y) => !(x > b[0] && x < b[1] && y > b[2] && y < b[3]);
  // 1) 판 위 소품(상자·통·우주선 승강 경사) 안으로 클릭 → 밖에 머물러야 함 (원본 형상 막힘)
  const OB = { barrels: [-7.75, -4.0, -3.12, -0.25], crateW: [-9.0, -6.62, -16.75, -14.0], crateE: [10.62, 13.25, -9.62, -6.88], crateS: [5.62, 8.88, -19.62, -15.38], shipRamp: [-2.0, 0.88, -17.75, -14.75] };
  await go('click into barrels', -5.9, -1.7, '02_barrels.png', outside(OB.barrels), [-9.5, 0.5]);
  await go('click into west crate', -7.8, -15.4, '03_crate_w.png', outside(OB.crateW), [-11.5, -11.0]);
  await go('click into east crate', 11.9, -8.2, '04_crate_e.png', outside(OB.crateE), [9.0, -4.5]);
  await go('click into south crate', 7.2, -17.5, '05_crate_s.png', outside(OB.crateS), [4.0, -13.0]);
  await go('click into ship boarding ramp', -0.6, -16.2, '06_ship_ramp.png', outside(OB.shipRamp), [-3.5, -12.0]);
  // 2) 우주선 아래(배 밑면 2.4~2.8 m 위)로 걸어 들어가기 → 지나갈 수 있어야 함 + 가림 확인
  await go('walk under the ship belly', 0.0, -23.0, '07_under_ship.png', (x, y) => y < -21.5, [0, -12]);
  await go('under the ship, further', 0.0, -31.0, '08_under_ship2.png', (x, y) => y < -29.0);
  // 3) 우주선 뒤(깊이상 먼 쪽)·앞에서 가림
  await go('behind the ship (farther from camera)', 4.5, -12.5, '09_behind_ship.png', null, [6, -9]);
  await go('in front of the ship', -8.0, -34.0, '10_front_ship.png', null, [-11, -26]);
  // 4) 판 가장자리 — 판 안에서 멈춤
  await go('west edge beyond (stop on deck)', -20.0, -10.0, '11_edge_w.png', (x) => x >= -14.3, [-10, -10]);
  await go('east edge beyond (stop on deck)', 20.0, -10.0, '12_edge_e.png', (x) => x <= 14.3, [10, -10]);
  await go('far tip beyond (stop on deck)', 0.0, -50.0, '13_tip.png', (x, y) => y >= -38.5, [0, -30]);
  // 5) 시설 정면(베이·입구 오른쪽 문틀)·벽 → 통과 못 함
  await go('click into open bay (stay in front)', -3.0, 8.0, '14_bay.png', (x, y) => y <= 4.6, [-3, -1]);
  await go('click into facility wall left of door', 3.0, 8.0, null, (x, y) => y <= 4.6, [3, -1]);
  // 6) 옆 통로(L자): 시작 → 끝 → 끝 너머 → 시설 벽 쪽
  await go('walkway start', -11.0, 5.0, null, (x, y) => y > 3.0, [-11, -3]);
  await go('walkway end', -11.0, 19.0, '15_walkway_end.png', (x, y) => y > 17.5);
  await go('beyond walkway end (stop)', -11.0, 26.0, null, (x, y) => y <= 21.2);
  await go('walkway -> facility wall (stay outside)', -3.0, 12.0, null, (x) => x <= -7.2, [-11, 12]);
  await go('walkway back to pad', -4.0, -8.0, null, (x, y) => y < 0, [-11, 10]);
  // 7) 전투 시작 지점 → 출구
  const t = S.combat.trigger.center; await reach(t[0], t[1], 0.8); note('combat trigger point', await pos());
  await page.evaluate(() => window.__game.stage.lockExit(false));
  await go('stairs top: door front (no exit yet)', 8.3, 0.8, '16_stairs_front.png', (x, y) => y < 1.7, [8.3, -5]);
  await page.waitForTimeout(500);
  note('no premature exit', !(await page.evaluate(() => window.__events.some((e) => e[0] === 'stage:exit'))));
  await go('stairs: click far down the stairs (stop at the walk limit)', 8.3, 6.0, '17_stairs_limit.png', (x, y) => y <= 3.0, [8.3, -3]);
  const ex = (S.exit.x0 + S.exit.x1) / 2, ey = (S.exit.y0 + S.exit.y1) / 2;
  await reach(ex, ey, 0.25);
  for (let k = 0; k < 6 && !(await page.evaluate(() => window.__events.some((e) => e[0] === 'stage:exit'))); k++) await keyToward(ex, ey, 300);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(OUT, '18_exit.png') });
  note('final pos', await pos());
  note('events', await page.evaluate(() => window.__events));
  const ok = log.filter((l) => l.v && typeof l.v === 'object' && 'pass' in l.v);
  note('summary', { checks: ok.length, passed: ok.filter((l) => l.v.pass).length, failed: ok.filter((l) => !l.v.pass).map((l) => l.k),
                    exit: (await page.evaluate(() => window.__events.some((e) => e[0] === 'stage:exit'))) });
  fs.writeFileSync(path.join(OUT, 'result.json'), JSON.stringify(log, null, 1));
  const vid = page.video();
  await ctx.close();
  if (vid) fs.renameSync(await vid.path(), path.join(OUT, 'play.webm'));
})().catch((e) => { console.error(e); process.exit(1); });
