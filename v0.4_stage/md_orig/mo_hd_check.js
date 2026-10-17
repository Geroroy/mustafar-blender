// 리마스터(HD, F5) 모드 확인: 배경·조각 아틀라스가 오류 없이 그려지는지 스크린샷 한 장. 실행: NODE_PATH=$(npm root -g) node mo_hd_check.js <출력 png>
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const ctx = await chromium.launchPersistentContext(process.env.PW_PROFILE || '/tmp/mo_hd_profile', { args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'], viewport: { width: 1280, height: 720 } });
  const page = ctx.pages()[0] || (await ctx.newPage()); const errs = [];
  page.on('pageerror', (e) => errs.push(String(e))); page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  await page.goto(process.env.STAGE_URL || 'http://localhost:5173/#stage-landing');
  for (let i = 0; i < 400; i++) { if (await page.evaluate(() => window.__ready === true)) break; await page.waitForTimeout(1000); }
  await page.click('#startBtn'); await page.waitForTimeout(1500);
  await page.keyboard.press('F5'); for (let i = 0; i < 240 && !(await page.evaluate(() => !!window.__renderer.hd)); i++) await page.waitForTimeout(1000);
  await page.evaluate(() => { const p = window.__game.player; p.x = 106.3; p.y = 90.5; }); await page.waitForTimeout(1500);
  await page.screenshot({ path: path.resolve(process.argv[2]) });
  console.log('hd', await page.evaluate(() => !!window.__renderer.hd), 'errors', JSON.stringify(errs));
  await ctx.close();
})();
