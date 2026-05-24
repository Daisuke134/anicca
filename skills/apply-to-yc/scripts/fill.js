// apply-to-yc — fill all 20 YC application text fields via React-aware native value setter.
// Read by apply.sh, injected into Chrome 9223 via {{profile.lateness.stakeholders.channel}}-harness CDP Runtime.evaluate.
//
// USAGE inside {{profile.lateness.stakeholders.channel}}-harness:
//   const PAYLOAD = JSON.parse(decodeURIComponent("__PAYLOAD__"))
//   then evaluate the body of fillAll(PAYLOAD)
//
// Field map verified against apply.ycombinator.com/apps/<id>/edit (2026-05-05).

(function fillAll(payload) {
  const setVal = (el, val) => {
    const proto = el.tagName === 'TEXTAREA'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(el, val);
    el.dispatchEvent(new Event('input',  { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur',   { bubbles: true }));
  };

  const byName = (n) => document.querySelector(`[name="${n}"]`);

  const filled = [];
  const missing = [];

  for (const [name, val] of Object.entries(payload)) {
    const el = byName(name);
    if (!el) { missing.push(name); continue; }
    setVal(el, val);
    filled.push(name);
  }

  return JSON.stringify({ filled, missing, totalFilled: filled.length });
})(__PAYLOAD__);
