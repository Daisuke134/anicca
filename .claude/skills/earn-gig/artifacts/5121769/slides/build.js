const pptxgen = require('pptxgenjs');
const path = require('path');
const html2pptx = require(path.join(process.env.HOME, '.claude/skills/pptx/scripts/html2pptx.js'));

(async () => {
  const dir = path.join(process.env.HOME, '.claude/skills/earn-gig/artifacts/5121769/slides');
  const out = path.join(process.env.HOME, '.claude/skills/earn-gig/artifacts/5121769/ppt_sample.pptx');
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'Daisuke';
  pptx.title = '授業スライド テンプレート — 比例と反比例';

  // Logical kit order: 表紙 -> 目次 -> セクション扉 -> 本文+グラフ -> 比較 -> 表 -> まとめ
  await html2pptx(path.join(dir, 'slide1.html'), pptx);  // 表紙
  await html2pptx(path.join(dir, 'slide5.html'), pptx);  // 目次
  await html2pptx(path.join(dir, 'slide6.html'), pptx);  // セクション扉

  const { slide: s2, placeholders } = await html2pptx(path.join(dir, 'slide2.html'), pptx);  // 本文+グラフ
  if (placeholders.length) {
    s2.addChart(pptx.charts.LINE, [{
      name: 'y = 80x',
      labels: ['0', '1', '2', '3', '4', '5'],
      values: [0, 80, 160, 240, 320, 400]
    }], {
      ...placeholders[0],
      lineSize: 3, lineSmooth: false,
      showLegend: false,
      showCatAxisTitle: true, catAxisTitle: 'x（個数）',
      showValAxisTitle: true, valAxisTitle: 'y（円）',
      valAxisMinVal: 0, valAxisMaxVal: 400, valAxisMajorUnit: 100,
      lineDataSymbol: 'circle', lineDataSymbolSize: 6,
      chartColors: ['1B4965'],
      catAxisLabelColor: '23303A', valAxisLabelColor: '23303A'
    });
  }

  await html2pptx(path.join(dir, 'slide3.html'), pptx);  // 比較

  const { slide: s7, placeholders: ph7 } = await html2pptx(path.join(dir, 'slide7.html'), pptx);  // 表
  if (ph7.length) {
    const hdr = { fill: { color: '1B4965' }, color: 'FFFFFF', bold: true };
    s7.addTable([
      [{ text: 'x （個）', options: hdr }, { text: '0', options: hdr }, { text: '1', options: hdr }, { text: '2', options: hdr }, { text: '3', options: hdr }, { text: '4', options: hdr }, { text: '5', options: hdr }],
      [{ text: 'y （円）', options: { fill: { color: 'EAF1F8' }, color: '1B4965', bold: true } }, '0', '80', '160', '240', '320', '400']
    ], {
      ...ph7[0],
      colW: (() => { const first = 1.05, n = 6, rest = (ph7[0].w - first) / n; return [first, rest, rest, rest, rest, rest, rest]; })(),
      border: { pt: 1, color: 'CFE0EA' },
      align: 'center', valign: 'middle', fontSize: 14, color: '23303A',
      rowH: [0.9, 0.9], fill: { color: 'FFFFFF' }
    });
  }

  await html2pptx(path.join(dir, 'slide4.html'), pptx);  // まとめ

  await pptx.writeFile({ fileName: out });
  console.log('saved', out);
})().catch(e => { console.error(e); process.exit(1); });
