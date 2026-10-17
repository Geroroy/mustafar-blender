// MO(Movie Duels 원본 그대로) 실제 게임 확인 2 — 게임 자체 충돌 함수로 한 이동 연결 검사 + 키 이동 걷기. 시작 위치는 순간이동으로 맞춤(검사 준비)(Playwright, 헤드리스 Chromium). 기존 game_test/play_test.js와 같은 방식(게임 클릭 이동·키 이동, 이벤트 기록).
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
  note('spawn', await pos()); note('exit', S.exit);
  await page.evaluate(() => window.__game.stage.lockExit(true));
  const tele = async (X, Y) => { const [gx, gy] = G(X, Y); await page.evaluate(([x, y]) => { const p = window.__game.player; p.x = x; p.y = y; p.path = null; p.action = null; }, [gx, gy]); await page.waitForTimeout(300); };
  // ---- A) 게임 자신의 단위 충돌(player.collides)로 0.125 m 걸음 BFS: 시작점에서 걸어서 닿는 곳
  const nav = await page.evaluate(([sx, sy]) => {
    const g = window.__game, p = g.player, st = 0.125, C = g.world.col;
    const gx0 = C.gx0, gy0 = C.gy0, W = Math.round(C.cols), H = Math.round(C.rows);
    const free = new Uint8Array(W * H);
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) free[j * W + i] = p.collides(gx0 + (i + 0.5) * st, gy0 + (j + 0.5) * st) ? 0 : 1;
    const idx = (x, y) => [Math.floor((x - gx0) / st), Math.floor((y - gy0) / st)];
    const seen = new Uint8Array(W * H); const [si, sj] = idx(sx, sy); const q = [sj * W + si]; seen[q[0]] = 1; let n = 0;
    for (let h = 0; h < q.length; h++) {
      const k = q[h]; const i = k % W, j = (k - i) / W; n++;
      for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
        const a = i + di, b = j + dj; if (a < 0 || b < 0 || a >= W || b >= H) continue; const kk = b * W + a;
        if (!seen[kk] && free[kk]) { seen[kk] = 1; q.push(kk); }
      }
    }
    window.__nav = { seen, W, H, gx0, gy0, st };
    return { free: free.reduce((s, v) => s + v, 0), reach: n };
  }, [S.spawn[0], S.spawn[1]]);
  note('nav: unit-collision cells free / reachable from spawn', nav);
  const nreach = async (label, X, Y, want) => {
    const [gx, gy] = G(X, Y);
    const r = await page.evaluate(([x, y]) => { const n = window.__nav; const i = Math.floor((x - n.gx0) / n.st), j = Math.floor((y - n.gy0) / n.st); return !!n.seen[j * n.W + i]; }, [gx, gy]);
    const path = await page.evaluate(([a, b, c, d]) => { const p = window.__game.pathfinder.find(a, b, c, d, 4000); return p ? p.length : null; }, [S.spawn[0], S.spawn[1], gx, gy]);
    note(label, { world: [X, Y], reachable_by_walking: r, astar_waypoints: path, pass: r === want });
  };
  await nreach('nav: pad open floor near crates', 8.0, -12.0, true);
  await nreach('nav: far pad corner (−X,−Y side)', -12.5, -22.0, true);
  await nreach('nav: far pad tip', 0.0, -35.0, true);
  await nreach('nav: under the ship belly (center)', 0.0, -23.0, true);
  await nreach('nav: under the ship, further', 0.0, -31.0, true);
  await nreach('nav: east side beyond ship ramp', 2.0, -16.0, true);
  await nreach('nav: walkway start', -11.0, 3.0, true);
  await nreach('nav: walkway end', -11.0, 20.0, true);
  await nreach('nav: stairs top (exit zone)', 8.3, 2.35, true);
  await nreach('nav: stairs lower than walk limit (corridor)', 8.3, 7.0, false);
  await nreach('nav: inside barrels', -5.9, -1.7, false);
  await nreach('nav: inside west crate', -7.8, -15.4, false);
  await nreach('nav: inside ship boarding ramp', -0.6, -16.2, false);
  await nreach('nav: inside the open bay', -3.0, 8.0, false);
  await nreach('nav: past the pad edge', -20.0, -10.0, false);
  // ---- B) 게임 자신의 이동 코드(player.navigate = 클릭 이동, player.move = 키 이동과 같은 충돌·미끄러짐)를 고정 시간 간격으로 돌려 본다
  const sim = (from, to, mode, speed = 4.0) => page.evaluate(([f, t, mode, speed]) => {
    const g = window.__game, p = g.player; p.x = f[0]; p.y = f[1]; p.path = null; p.pathGoal = null;
    let steps = 0, arrived = false; const dt = 1 / 30;
    for (; steps < 2400; steps++) {
      if (mode === 'nav') { arrived = p.navigate(t[0], t[1], speed, dt, 0.15); if (arrived) break; }
      else { const d = Math.hypot(t[0] - p.x, t[1] - p.y); const x0 = p.x, y0 = p.y; p.moveToward(t[0], t[1], speed, dt); if (Math.hypot(p.x - x0, p.y - y0) < 1e-4 && steps > 5) break; if (d < 0.05) break; }
      g.stage.update(dt);
    }
    return { x: +p.x.toFixed(2), y: +p.y.toFixed(2), steps, arrived };
  }, [from, to, mode, speed]);
  const simTest = async (label, fromW, toW, mode, check, shot) => {
    const f = G(...fromW), t = G(...toW); const r = await sim(f, t, mode); const [X, Y] = W(r.x, r.y);
    const res = { from: fromW, goal: toW, mode, end_world: [+X.toFixed(2), +Y.toFixed(2)], steps: r.steps, arrived: r.arrived };
    res.pass = check(X, Y, r) && await walk(); note(label, res);
    if (shot) { await page.waitForTimeout(400); await page.screenshot({ path: path.join(OUT, shot) }); }
  };
  const near = (cx, cy, r) => (x, y) => Math.hypot(x - cx, y - cy) < r;
  await simTest('walk (click-move) spawn → under the ship belly', [4.13, -5.99], [0.0, -23.0], 'nav', near(0, -23, 0.5), 's01_under_ship.png');
  await simTest('walk (click-move) → far under the ship', [4.13, -5.99], [0.0, -31.0], 'nav', near(0, -31, 0.5), 's02_under_ship_far.png');
  await simTest('walk (click-move) → far pad tip', [0.0, -23.0], [0.0, -35.0], 'nav', near(0, -35, 0.5));
  await simTest('walk (click-move) → east of the ship ramp', [4.13, -5.99], [2.0, -16.0], 'nav', near(2, -16, 0.5));
  await simTest('walk (click-move) → walkway start → end', [4.13, -5.99], [-11.0, 20.0], 'nav', near(-11, 20, 0.5), 's03_walkway_end.png');
  await simTest('walk (click-move) walkway end → back to the pad', [-11.0, 20.0], [-6.0, -5.0], 'nav', near(-6, -5, 0.5));
  await simTest('straight move into barrels (stop short)', [-9.5, -1.7], [-2.0, -1.7], 'move', (x, y) => x < -7.6 && x > -9.6, 's04_barrels.png');
  await simTest('straight move into west crate (stop short)', [-11.5, -15.4], [-4.0, -15.4], 'move', (x) => x < -7.8, 's05_crate_w.png');
  await simTest('straight move into east crate (stop short)', [8.0, -8.2], [16.0, -8.2], 'move', (x) => x < 11.9 && x > 8.0);
  await simTest('straight move into south crate (stop short)', [7.2, -12.0], [7.2, -24.0], 'move', (x, y) => y > -15.4 && y < -12.0);
  await simTest('straight move into the boarding ramp (stop short)', [-0.6, -12.0], [-0.6, -24.0], 'move', (x, y) => y > -16.2, 's06_ramp.png');
  await simTest('straight move −X off the pad (stop on deck)', [-11.0, -6.0], [-22.0, -6.0], 'move', (x) => x >= -14.45 && x < -13.0, 's07_edge_w.png');
  await simTest('straight move +X off the pad (stop on deck)', [10.0, -10.0], [22.0, -10.0], 'move', (x) => x <= 14.45 && x > 13.0);
  await simTest('straight move −Y off the pad tip (stop on deck)', [0.0, -30.0], [0.0, -50.0], 'move', (x, y) => y > -38.5 && y < -35.0);
  await simTest('straight move +Y past the walkway end (stop)', [-11.0, 14.0], [-11.0, 30.0], 'move', (x, y) => y > 19.0 && y <= 21.3);
  await simTest('straight move +X into the facility wall at the walkway (stop outside)', [-10.0, 12.0], [0.0, 12.0], 'move', (x) => x < -7.1);
  await simTest('straight move +Y toward the open bay (stop at the pad edge)', [-3.0, -3.0], [-3.0, 12.0], 'move', (x, y) => y < 0.5 && y > -3.0, 's08_bay.png');
  await page.evaluate(() => window.__game.stage.lockExit(false));
  await simTest('straight move +Y down the entrance stairs (stop at the walk limit; stage ends)', [8.3, -3.0], [8.3, 9.0], 'move', (x, y) => y > 1.8 && y <= 3.0);
  await page.waitForTimeout(2500);
  note('exit event fired', { pass: await page.evaluate(() => window.__events.some((e) => e[0] === 'stage:exit')) });
  await page.screenshot({ path: path.join(OUT, 's09_exit.png') });
  note('events', await page.evaluate(() => window.__events));
  const ok = log.filter((l) => l.v && typeof l.v === 'object' && 'pass' in l.v);
  note('summary', { checks: ok.length, passed: ok.filter((l) => l.v.pass).length, failed: ok.filter((l) => !l.v.pass).map((l) => l.k) });
  fs.writeFileSync(path.join(OUT, 'result2.json'), JSON.stringify(log, null, 1));
  const vid = page.video();
  await ctx.close();
  if (vid) fs.renameSync(await vid.path(), path.join(OUT, 'play2.webm'));
})().catch((e) => { console.error(e); process.exit(1); });
