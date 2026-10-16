// MD_REMAKE_POC01 실제 게임 확인(Playwright, 헤드리스 Chromium). 기존 game_test/play_test.js와 같은 방식(게임 클릭 이동·키 이동, 이벤트 기록).
// 준비: 게임 public/stages/mustafar_landing/에 out_md_poc01을 잠시 복사 → npx vite --port 5173
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
  await page.screenshot({ path: path.join(OUT, '01_start.png') });
  await page.evaluate(() => window.__game.stage.lockExit(true));

  // 1) 판 가장자리(앞 뾰족 끝·−Y 변·+Y 뒤 난간) — 판 안에서 멈춰야 함
  await go('nose tip beyond (stop on deck)', -26, 0, '02_nose.png', (x) => x >= -23.0, [-15, 0]);
  await go('-Y edge beyond (stop on deck)', 0, -17, '03_negy_edge.png', (x, y) => y >= -14.0, [0, -9]);
  await go('+Y back rail beyond (stop before rail)', 0, 17, '04_back_rail.png', (x, y) => y <= 13.9, [0, 9]);
  // 2) 출입구 옆 상자(모드 격자 상자) 안으로 — 밖에 머물러야 함
  await go('click into crate (stay outside)', 12.8, -12.3, '05_crate.png', (x, y) => !(x > 11.1 && x < 14.5 && y > -14.1 && y < -10.6), [7, -12]);
  // 3) 틈: 베이 앞 열린 틈 쪽으로 — 판 끝(X ≤ 14.5)에서 멈춤
  await go('gap toward bay (stop at pad edge)', 17.5, 3.0, '06_gap.png', (x) => x <= 14.55, [9, 3]);
  // 4) 출입구: 다리 → 영화 윤곽 문(폭 2.0 m) 안 → 통로
  await go('bridge in front of door', 16.5, -8.2, '07_bridge.png', (x) => x > 14.5 && x < 19.5, [9, -7.5]);
  await go('through film door into passage', 21.6, -8.2, '08_in_passage.png', (x) => x > 19.8);
  await go('passage -> beside door, behind panel (stay in passage)', 21.0, -10.0, null, (x) => x > 19.8);
  // 진단: 문 옆(통로 안)에서 다리까지 타일 A* 경로가 있는지, 단위 충돌로 막힌 상태인지
  note('diag: A* path beside-door -> bridge', await page.evaluate(([a, b, c, d]) => { const p = window.__game.pathfinder.find(a, b, c, d, 2500); return p ? p.map((q) => [+q.x.toFixed(2), +q.y.toFixed(2)]) : null; }, [...(await pos() && [ (await pos()).x, (await pos()).y ]), ...G(16.5, -8.2)]));
  note('diag: player collides at current pos', await page.evaluate(() => window.__game.player.collides(window.__game.player.x, window.__game.player.y)));
  await go('back out to bridge (direct click from beside door)', 16.5, -8.2, null, (x) => x < 19.5);
  await go('back out via door center (click door, then bridge)', 21.0, -8.2, null, (x) => x > 19.8);
  await go('back out to bridge', 16.5, -8.2, null, (x) => x < 19.5);
  await go('panel wall beside door from outside (stay outside)', 21.0, -10.6, '09_panel_wall.png', (x) => x < 19.5, [16.5, -10.0]);
  // 5) 옆 통로(+Y, 시설 뒤): 시작 → 끝 → 끝 너머 → 틈 쪽
  await go('walkway start', 16.0, 11.5, null, (x, y) => y > 9.0, [8, 11]);
  await go('walkway behind facility (occlusion)', 26.0, 11.5, '10_walkway_occlusion.png', (x, y) => x > 24 && y > 9.0);
  await go('walkway end', 34.5, 11.5, '11_walkway_end.png', (x) => x > 33.5);
  await go('beyond walkway end (stop)', 38.0, 11.5, null, (x) => x <= 35.35);
  await go('walkway -> gap side (stay on walkway)', 22.0, 6.0, null, (x, y) => y >= 8.9, [22, 11.5]);
  await go('walkway back to pad', 5.0, 10.0, null, (x) => x < 14.5, [24, 11.5]);
  // 6) 전투 시작 지점 → 출구(잠금 해제 후 통로 안)
  const t = S.combat.trigger.center; await reach(t[0], t[1], 0.8); note('combat trigger point', await pos());
  await page.evaluate(() => window.__game.stage.lockExit(false));
  await go('door front (unlocked, no exit yet)', 16.5, -8.2, null, (x) => x < 19.5, [9, -7.5]);
  await page.waitForTimeout(500);
  note('no premature exit', !(await page.evaluate(() => window.__events.some((e) => e[0] === 'stage:exit'))));
  const ex = (S.exit.x0 + S.exit.x1) / 2, ey = (S.exit.y0 + S.exit.y1) / 2;
  await reach(ex, ey, 0.25);
  for (let k = 0; k < 6 && !(await page.evaluate(() => window.__events.some((e) => e[0] === 'stage:exit'))); k++) await keyToward(ex, ey, 300);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(OUT, '12_exit.png') });
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
