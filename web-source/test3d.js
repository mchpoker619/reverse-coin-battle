// 無頭 Chromium 測試 3D 頁：規則邏輯、物理、電腦對戰、截圖
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const OUT = process.argv[2] || '/tmp/shots3d';
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1360, height: 820 } });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.route('**/*', route => {
    const u = route.request().url();
    if (u.includes('three.min.js')) return route.fulfill({ path: path.join(__dirname, 'package/build/three.min.js'), contentType: 'application/javascript' });
    if (u.startsWith('file:')) return route.continue();
    return route.abort();
  });
  const target = process.argv[3];
  if (target) { await page.goto('file://' + target); }
  else {
    const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
    const wrapped = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + html + '</body></html>';
    fs.writeFileSync('/tmp/rcb3d.html', wrapped);
    await page.goto('file:///tmp/rcb3d.html');
  }
  await page.waitForTimeout(1500);
  await page.screenshot({ path: OUT + '/01_title.png' });

  // ---- 規則邏輯（端到端：真實出手）
  const res = await page.evaluate(async () => {
    const X = window.__RCB, G = X.G, out = [];
    const run = (name, att, def, flip, hitSpot, expectAlive, expectLog, pow = 0.75) => {
      X.P.FLIP = flip;
      G.players = [X.newPlayer('攻'), X.newPlayer('守')];
      G.players[0].camp = 'X'; G.players[1].camp = 'O';
      G.players[0].team = [att, 'v1x-c-ram', 'v1x-c-ram']; G.players[1].team = [def, 'v1o-c-ker', 'v1o-c-ker'];
      G.firstCamp = 'X'; X.startBattle();
      const S = G.pieces[0], D = G.pieces[3];
      G.pieces.filter(p => p !== S && p !== D).forEach((p, k) => { p.x = -X.W/2 + X.R + 0.2 + k * 2.2 * X.R; p.z = X.H/2 - X.R - 0.2; });
      D.x = 0; D.z = 0; D.angle = hitSpot ? 0 : Math.PI/2; S.x = -10.3; S.z = 0;
      G.selected = S; X.confirmSelect(); G.aim = 0; X.confirmAim(); G.power = pow; X.lockPower(); G.acc = 0; X.lockAcc();
      for (let i = 0; i < 60*30; i++) { X.update(1/60); if (G.phase === 'duel') X.skipDuel(); if (['select','over','place'].includes(G.phase)) break; }
      const log = G.log.map(l => l[0]).filter(s => !s.includes('出手') && !s.includes('擲金幣')).join(' / ');
      out.push([D.alive === expectAlive && log.includes(expectLog), name, log]);
    };
    run('A 攻9000 打守2000（非メタ）落地仍自己色 → 淘汰', 'v4x-br', 'v4o-c-iru', 0, true, false, 'OX 2000 < 9000');
    run('B 守ボーダー白9000/黑3000 被打彈起 → 用翻面 3000 比，3000 ≥ 2000 存活', 'v4x-c-sai', 'v4o-br', 0, true, true, 'OX 3000 ≥ 2000');
    run('C 平手 8000 vs 8000（非メタ）→ 守方存活', 'v1x-rr', 'v1o-rr', 0, true, true, 'OX 8000 ≥ 8000');
    run('D 守カブトルR白7000 彈起 → 翻面 3000 < 9000 淘汰', 'v4x-br', 'v3o-r-kab', 0, true, false, 'OX 3000 < 9000');
    run('E 官方例：守レオウ白8000 被 5000 打彈起 → 翻面 4000 淘汰', 'v1x-r', 'v3o-br', 0, true, false, 'OX 4000 < 5000');
    run('E2 守カイザーク(白4000/黑8000) 站白面被打彈起 → 翻面 8000 強，存活', 'v1x-r', 'v3x-br', 0, true, true, 'OX 8000 ≥ 5000');
    run('F 翻成對方色 → 直接淘汰', 'v4x-c-sai', 'v4o-br', 1, true, false, '翻成對方顏色 → 淘汰');
    run('G 沒打到弱點 → 不比 OX', 'v4x-br', 'v4o-c-iru', 0, false, true, '沒翻面 → 存活');
    // 存活的彈起金幣放回原位
    run('H 守方 OX 存活（留在場內）', 'v1x-r', 'v3x-br', 0, true, true, '存活', 0.42);
    { const D = G.pieces[3]; out.push([D.alive && !D.out && Math.hypot(D.x, D.z) > 0.5, 'H2 存活守方留在停下的位置（判定助手 D6）', [D.x.toFixed(2), D.z.toFixed(2)]]); }
    // isn_ver.1：攻擊方翻成對方色不淘汰
    X.RULES.mode = 'house';
    run('I isn_ver.1 攻擊方翻成對方色不淘汰', 'v4x-br', 'v4o-c-iru', 1, true, false, '攻擊方不淘汰');
    out.push([G.pieces[0].alive, 'I2 攻擊方仍存活（isn_ver.1）', '']);
    // 官方：攻擊方自爆翻色 → OUT
    X.RULES.mode = 'official';
    run('J 官方 攻擊方自爆翻成對方色 → OUT', 'v4x-br', 'v4o-c-iru', 1, true, false, '自爆翻成對方顏色 → 淘汰');
    out.push([!G.pieces[0].alive, 'J2 攻擊方被淘汰（官方）', '']);
    X.RULES.mode = 'house';
    X.P.FLIP = 0.5;
    // 邊框三情形
    const p = G.pieces[0];
    const wall = (v, ang) => { p.alive = true; p.out = false; p.spotSpeed = 0; p.spotSrc = ''; p.angle = ang; p.x = X.W/2 - X.R - 0.02; p.z = 0; p.vx = v; p.vz = 0; G.pieces.forEach(q => { if (q !== p) q.alive = false; }); for (let i = 0; i < 20 && !p.out; i++) X.physics(1/240); return p; };
    let w = wall(12, 0); out.push([!w.out && w.vx < 0 && w.spotSpeed < X.P.UNLOCK, '邊框 慢 → 只反彈', [w.out, w.vx.toFixed(1)]]);
    w = wall(23, 0); out.push([!w.out && w.vx < 0 && w.spotSrc === 'rail', '邊框 弱點朝牆 中速 → 反彈＋翻轉', [w.out, w.spotSpeed.toFixed(1)]]);
    w = wall(23, Math.PI/2); out.push([!w.out && w.spotSpeed < X.P.UNLOCK, '邊框 非弱點朝牆 中速 → 只反彈', w.out]);
    w = wall(X.P.OUT_SPEED * 1.15, 0); out.push([w.out, '邊框 快 → 出界', w.out]);
    // 撞球
    const a = G.pieces[0], b = G.pieces[3]; a.alive = b.alive = true; a.out = b.out = false;
    a.x = -2*X.R + 0.01; a.z = 0; b.x = 0; b.z = 0; a.vx = 36; a.vz = 0; b.vx = b.vz = 0;
    X.collide(a, b); out.push([Math.abs(a.vx) < 2 && b.vx > 34 && a.spin === 0 && b.spin === 0, '正面撞擊 母球停（無旋轉不帶轉）', [a.vx.toFixed(2), b.vx.toFixed(2)]]);
    // 旋轉：母球右旋正面撞 → 目標反向轉＋被帶偏
    a.x = -2*X.R + 0.01; a.z = 0; b.x = 0; b.z = 0; a.vx = 36; a.vz = 0; b.vx = b.vz = 0; a.spin = 20; b.spin = 0;
    X.collide(a, b); out.push([a.spin < 20 && b.spin < 0 && Math.abs(b.vz) > 0.5, '旋轉撞擊 → 對手反向轉（齒輪）＋側向帶偏', [a.spin.toFixed(1), b.spin.toFixed(1), b.vz.toFixed(2)]]);
    // 旋轉撞牆 → 反彈角度改變
    { const wallSpin = sp => { const p = G.pieces[0]; p.alive = true; p.out = false; p.x = X.W/2 - X.R + 0.01; p.z = 0; p.vx = 12; p.vz = 0; p.spin = sp; p.angle = Math.PI/2; p.spotSpeed = 0; X.railBounce(p); return p.vz; };
      const z0 = wallSpin(0), zR = wallSpin(15), zL = wallSpin(-15);
      out.push([Math.abs(z0) < 1e-9 && zR * zL < 0 && Math.abs(zR) > 1, '帶旋轉撞牆 → 反彈角度改變（左右相反）', [z0.toFixed(2), zR.toFixed(2), zL.toFixed(2)]]); }
    // 旋轉衰減＋弧線
    { G.pieces.forEach(p => p.alive = false); const p = G.pieces[0]; p.alive = true; p.out = false; p.x = 0; p.z = 10; p.vx = 0; p.vz = -20; p.spin = 14; p.angle = 0;
      const sh = G.shooter; G.shooter = null;
      for (let i = 0; i < 300; i++) X.physics(1/120);
      out.push([p.spin === 0 && p.x > 0.25 && p.angle > 1, '旋轉會減速到 0、滑行走弧線、金幣有轉動', [p.spin, p.x.toFixed(2), p.angle.toFixed(2)]]);
      G.shooter = sh; G.pieces.forEach(q => q.alive = true); }
    // 精準度最邊緣 70°、出界 > 翻轉、組隊規則
    { X.RULES.mode = 'official'; G.players = [X.newPlayer('攻'), X.newPlayer('守')]; G.players[0].camp = 'X'; G.players[1].camp = 'O';
      G.players[0].team = ['v1x-r']; G.players[1].team = ['v1o-r-nya']; G.firstCamp = 'X'; X.startBattle();
      X.confirmSelect(); G.aim = 0; X.confirmAim(); G.power = 0.5; X.lockPower(); G.acc = 1; X.lockAcc();
      const s = G.selected, a = Math.atan2(s.vz, s.vx) * 180 / Math.PI;
      out.push([Math.abs(a - 70) < 0.5, '精準度最邊緣實際偏 70°', a.toFixed(1)]);
      G.phase = 'over'; }
    { G.spinLvl = 0; const e0 = X.accErr(0.05); G.spinLvl = 3; const e3 = X.accErr(0.05), z3 = X.perfZone(); G.spinLvl = 0;
      out.push([e0 === 0 && e3 !== 0 && Math.abs(z3 - 0.028) < 1e-9, '旋轉越強 PERFECT 區越窄（3 段剩 40%）', [e0, e3.toFixed(3), z3.toFixed(3)]]); }
    { const a = G.pieces[0], b = G.pieces[1]; a.alive = b.alive = true; a.out = b.out = false; X.RULES.spin = false;
      a.x = -2*X.R + 0.01; a.z = 0.6; b.x = 0; b.z = 0; a.vx = 36; a.vz = 0; b.vx = b.vz = 0; a.spin = b.spin = 0;
      X.collide(a, b); const ok1 = a.spin === 0 && b.spin === 0; X.RULES.spin = true;
      out.push([ok1, '旋轉關閉 → 切球也不產生旋轉', [a.spin, b.spin]]); }
    out.push([X.P.OUT_SPEED > X.P.UNLOCK, '出界門檻 > 翻轉門檻', [X.P.OUT_SPEED, X.P.UNLOCK]]);
    { const c = ids => ids.reduce((s, i) => s + X.BY_ID[i].cost, 0);
      out.push([c(['v4x-br','v3x-bbr']) === 13000 && c(['v3o-br']) === 6000 && X.PRESETS.every(([, ids]) => c(ids) <= 15000 && new Set(ids).size === ids.length), '組隊 メタ幣算 M 值、預設隊伍都 ≤15000 且不重複', '']); }
    // 翻轉機率
    let flips = 0, n = 3000;
    for (let i = 0; i < n; i++) { flips += Math.random() < X.P.FLIP ? 1 : 0; }
    out.push([Math.abs(flips/n - 0.5) < 0.03, '翻轉 1/2', (flips/n).toFixed(3)]);
    return out;
  });
  res.forEach(([ok, name, info]) => console.log(ok ? 'PASS' : 'FAIL', name, '→', JSON.stringify(info).slice(0, 160)));

  // ---- 電腦對電腦
  const stats = await page.evaluate(() => {
    const X = window.__RCB, G = X.G; const r = { games: 0, turns: 0, win: {} , stuck: 0};
    for (let gi = 0; gi < 20; gi++) {
      G.players = [X.newPlayer('A', true), X.newPlayer('B', true)];
      G.players[0].camp = 'X'; G.players[1].camp = 'O';
      G.players[0].team = X.PRESETS[gi % 5][1].slice(); G.players[1].team = X.PRESETS[(gi + 1) % 5][1].slice();
      G.firstCamp = 'O'; X.startBattle();
      let turns = 0, lt = G.turn, f = 0;
      while (G.phase !== 'over' && f < 60*60*20) { X.update(1/60); f++; if (G.turn !== lt) { turns++; lt = G.turn; } if (turns > 300) break; }
      if (G.phase !== 'over') r.stuck++;
      r.games++; r.turns += turns; r.win[G.winner] = (r.win[G.winner] || 0) + 1;
    }
    return r;
  });
  console.log('CPU', JSON.stringify(stats));

  // ---- 截圖：真實流程
  await page.evaluate(() => { window.__RCB.UI.show('title'); window.__RCB.UI.hideDuel(); window.__RCB.P.FLIP = 0.5; });
  await page.click('#btnPvP'); await page.waitForTimeout(300);
  await page.click('#presets .btn >> nth=2'); await page.waitForTimeout(100);
  await page.screenshot({ path: OUT + '/03_build.png' });
  await page.click('#btnConfirm'); await page.waitForTimeout(200);
  await page.click('#presets .btn >> nth=2'); await page.click('#btnConfirm'); await page.waitForTimeout(200);
  await page.screenshot({ path: OUT + '/02_rps.png' });
  if (await page.isVisible('#pickO')) await page.click('#pickX');
  await page.click('#btnToBuild');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: OUT + '/04_battle.png' });
  await page.evaluate(() => { const X = window.__RCB, G = X.G; X.confirmSelect(); const s = G.selected; const e = G.pieces.find(p => p.team !== G.turn); G.aim = Math.atan2(e.z - s.z, e.x - s.x) + 0.12; });
  await page.waitForTimeout(800);
  await page.screenshot({ path: OUT + '/05_aim.png' });
  await page.evaluate(() => { const X = window.__RCB; X.GFX.setMode('top'); });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: OUT + '/06_aim_top.png' });
  await page.evaluate(() => { window.__RCB.GFX.setMode('tilt'); }); await page.waitForTimeout(1200);
  await page.screenshot({ path: OUT + '/06b_guide_on.png' });
  await page.keyboard.press('h'); await page.waitForTimeout(300);
  await page.screenshot({ path: OUT + '/06c_guide_off.png' });
  const gtxt = await page.textContent('#camGuide'); console.log('guide button:', gtxt);
  await page.keyboard.press('h');
  await page.evaluate(() => { const X = window.__RCB, G = X.G; X.GFX.setMode('tilt'); X.confirmAim(); G.power = 0.8; X.lockPower(); G.acc = 0; X.lockAcc(); X.P.FLIP = 0; });
  // 等待到彈起
  for (let i = 0; i < 80; i++) { const ph = await page.evaluate(() => window.__RCB.G.phase); if (ph === 'jump') break; await page.waitForTimeout(100); }
  await page.waitForTimeout(450);
  await page.screenshot({ path: OUT + '/07_jump.png' });
  for (let i = 0; i < 40; i++) { const ph = await page.evaluate(() => window.__RCB.G.phase); if (ph === 'duel') break; await page.waitForTimeout(100); }
  await page.waitForTimeout(1300);
  await page.screenshot({ path: OUT + '/08_duel.png' });
  // 強制一場 OX 對決截圖
  await page.evaluate(() => { const X = window.__RCB, G = X.G; X.P.FLIP = 0; G.scene = 'battle';
    const S = G.pieces.find(p => p.team === G.turn && p.alive), D = G.pieces.find(p => p.team !== G.turn && p.alive);
    G.pieces.filter(p => p !== S && p !== D).forEach((p, k) => { p.x = -X.W/2 + X.R + 0.2 + k * 2.3 * X.R; p.z = (k % 2 ? 1 : -1) * (X.H/2 - X.R - 0.2); });
    D.x = 3; D.z = 0; D.angle = 0; S.x = -7; S.z = 0; G.selected = S; G.phase = 'aim'; G.aim = 0; X.confirmAim(); G.power = 0.7; X.lockPower(); G.acc = 0; X.lockAcc(); });
  for (let i = 0; i < 60; i++) { const ph = await page.evaluate(() => window.__RCB.G.phase); if (ph === 'jump') break; await page.waitForTimeout(100); }
  await page.waitForTimeout(500);
  await page.screenshot({ path: OUT + '/07b_jump.png' });
  for (let i = 0; i < 40; i++) { const ph = await page.evaluate(() => window.__RCB.G.phase); if (ph === 'duel') break; await page.waitForTimeout(100); }
  await page.waitForTimeout(1400);
  await page.screenshot({ path: OUT + '/08b_duel.png' });
  // 手機寬度
  await page.setViewportSize({ width: 400, height: 820 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: OUT + '/09_phone.png' });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  console.log('phone horizontal overflow:', overflow);
  console.log('ERRORS:', errors.length ? errors.join('\n') : 'none');
  await browser.close();
})();
