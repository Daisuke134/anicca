// apply-to-yc/progress — fill /edit/progress page.
// usernums + 6 monthly USD$ + revenuesource + growthrate + click Yes divs.

(function progress(payload) {
  const setVal = (el, val) => {
    const proto = el.tagName === 'TEXTAREA'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(el, String(val));
    el.dispatchEvent(new Event('input',  { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur',   { bubbles: true }));
  };

  const byName = (n) => document.querySelector(`[name="${n}"]`);
  const out = { filled: [], clicked: [], missing: [] };

  // 1. usernums (textarea)
  const u = byName('usernums');
  if (u) { setVal(u, payload.usernums); out.filled.push('usernums'); }
  else out.missing.push('usernums');

  // 2. revenuesource (textarea)
  const rs = byName('revenuesource');
  if (rs) { setVal(rs, payload.revenuesource); out.filled.push('revenuesource'); }
  else out.missing.push('revenuesource');

  // 3. growthrate (textarea)
  const gr = byName('growthrate');
  if (gr) { setVal(gr, payload.growthrate); out.filled.push('growthrate'); }
  else out.missing.push('growthrate');

  // 4. 6 monthly USD$ inputs (placeholder="USD$") in document order
  const monthly = Array.from(document.querySelectorAll('input[placeholder="USD$"]'));
  payload.monthly_revenue.slice(0, 6).forEach((v, i) => {
    if (monthly[i]) { setVal(monthly[i], v); out.filled.push(`monthly[${i}]=${v}`); }
  });

  // 5. Yes divs (CSS-only fake radios). Find by text content of cursor-pointer divs.
  // "Are people using your product?" Yes  &  "Do you have revenue?" Yes
  const yesDivs = Array.from(document.querySelectorAll('div.cursor-pointer, div[role="radio"]'))
    .filter(d => /\bYes\b/i.test(d.textContent.trim()) && d.textContent.trim().length < 6);
  yesDivs.forEach(d => { d.click(); out.clicked.push('Yes'); });

  return JSON.stringify(out);
})(__PAYLOAD__);
