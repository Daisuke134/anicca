// aitinkerers-apply — fill register form + submit demo proposal
// Verified DOM 2026-05-05. Used by aitinkerers-apply.sh.

const setVal = (el, val) => {
  const proto = el.tagName === 'TEXTAREA'
    ? window.HTMLTextAreaElement.prototype
    : window.HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, val);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('blur', { bubbles: true }));
};

window.AITInkerersApply = {
  // Step 1: submit {{profile.lateness.stakeholders.channel}} to trigger OTP
  submitEmail({{profile.lateness.stakeholders.channel}}) {
    const e = document.getElementById('inline-auth-{{profile.lateness.stakeholders.channel}}-input');
    if (!e) return { err: 'no {{profile.lateness.stakeholders.channel}} input' };
    setVal(e, {{profile.lateness.stakeholders.channel}});
    const btn = document.getElementById('inline-auth-submit-{{profile.lateness.stakeholders.channel}}');
    if (!btn) return { err: 'no submit btn' };
    btn.click();
    return { sent: true };
  },

  // Step 2: enter OTP digits + click verify
  enterOtp(otp4) {
    const digits = String(otp4).split('');
    const names = ['one-time-code', 'inline-auth-code-1', 'inline-auth-code-2', 'inline-auth-code-3'];
    for (let i = 0; i < 4; i++) {
      const el = document.querySelector('input[name="' + names[i] + '"]');
      if (el) setVal(el, digits[i]);
    }
    const verify = document.getElementById('verify-code');
    if (!verify) return { err: 'no verify' };
    const r = verify.getBoundingClientRect();
    return { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
  },

  // Step 3: fill register form fields
  fillRegister({ name, company, jobTitle, linkedin, github, twitter }) {
    const data = {
      ask_for_name_value: name,
      ask_for_company_name_value: company,
      ask_for_job_title_value: jobTitle,
      linkedin: linkedin || '',
      github: github || '',
      twitter: twitter || ''
    };
    const filled = {};
    for (const [id, val] of Object.entries(data)) {
      const el = document.getElementById(id);
      if (el) { setVal(el, val); filled[id] = el.value.length; }
    }
    return filled;
  },

  // Step 4: click Register Now (JS .click() not coords — coords don't fire)
  clickRegister() {
    const b = document.getElementById('rsvp-submit');
    if (!b) return { err: 'no rsvp-submit' };
    b.click();
    return { clicked: true };
  },

  // Step 5: detect post-register state
  isRegistered() {
    const txt = (document.body.innerText || '');
    return /Application submitted|Registration Submitted|Under Review/i.test(txt);
  },

  // Step 6: fill demo proposal form
  fillDemoProposal({ title, description, learn, tech, url1, url2, video }) {
    const data = {
      speaker_title: title,
      speaker_description: description,
      speaker_justification: learn,
      speaker_technologies: tech,
      speaker_url_1: url1 || '',
      speaker_url_2: url2 || '',
      speaker_video: video || ''
    };
    const filled = {};
    for (const [id, val] of Object.entries(data)) {
      const el = document.getElementById(id);
      if (el && val) { setVal(el, val); filled[id] = el.value.length; }
    }
    const cb = document.getElementById('code-agreement');
    if (cb && !cb.checked) cb.click();
    return { filled, agreement: cb ? cb.checked : false };
  },

  // Step 7: submit proposal — MUST use form-scoped query, not text search
  submitProposal() {
    const form = document.querySelector('form');
    if (!form) return { err: 'no form' };
    const btn = form.querySelector('button[type="submit"][name="submit"]');
    if (!btn) return { err: 'no submit btn' };
    btn.click();
    return { clicked: true };
  },

  // Step 8: detect demo proposal submitted state
  isProposalSubmitted() {
    const txt = (document.body.innerText || '');
    return /Pending review by organizers|Thanks for submitting your proposal/i.test(txt);
  }
};
