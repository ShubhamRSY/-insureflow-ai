(function () {
  'use strict';

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- Location-time day/night theme (automatic — no user toggle) ---- */
  var themeGeo = { lat: null, lng: null };

  function sunTimes(lat, lng, date) {
    var rad = Math.PI / 180;
    var start = new Date(date.getFullYear(), 0, 0);
    var day = Math.floor((date - start) / 86400000);
    var lngHour = lng / 15;
    var t = day + ((6 - lngHour) / 24);
    var M = (357.5291 + 0.98560028 * t) % 360;
    var C = 1.9148 * Math.sin(M * rad) + 0.02 * Math.sin(2 * M * rad);
    var lambda = (M + 102.9372 + C + 180) % 360;
    var Jtransit = 2451545 + t + 0.0053 * Math.sin(M * rad) - 0.0069 * Math.sin(2 * lambda * rad);
    var sinDec = Math.sin(lambda * rad) * Math.sin(23.4397 * rad);
    var cosDec = Math.cos(Math.asin(sinDec));
    var zenith = 90.833 * rad;
    var cosH = (Math.cos(zenith) - Math.sin(lat * rad) * sinDec) / (Math.cos(lat * rad) * cosDec);
    if (cosH > 1 || cosH < -1) return null;
    var H = Math.acos(cosH) / rad;
    function jdToLocal(jd) {
      return new Date((jd - 2440587.5) * 86400000 - date.getTimezoneOffset() * 60000);
    }
    return { sunrise: jdToLocal(Jtransit - H / 360), sunset: jdToLocal(Jtransit + H / 360) };
  }

  function isDaytime(now) {
    if (themeGeo.lat != null && themeGeo.lng != null) {
      var st = sunTimes(themeGeo.lat, themeGeo.lng, now);
      if (st) return now >= st.sunrise && now < st.sunset;
    }
    var h = now.getHours() + now.getMinutes() / 60;
    return h >= 6.5 && h < 19.5;
  }

  function applyLocationTheme() {
    document.documentElement.setAttribute('data-theme', isDaytime(new Date()) ? 'day' : 'night');
  }

  applyLocationTheme();
  setInterval(applyLocationTheme, 60000);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) applyLocationTheme();
  });

  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        themeGeo.lat = pos.coords.latitude;
        themeGeo.lng = pos.coords.longitude;
        applyLocationTheme();
      },
      function () {},
      { timeout: 8000, maximumAge: 3600000, enableHighAccuracy: false }
    );
  }

  window.__ryteraTheme = { apply: applyLocationTheme, geo: themeGeo };

  /* ---- Active nav link (by path) ---- */
  var pathname = window.location.pathname.replace(/\/+$/, '') || '/';
  document.querySelectorAll('a[data-nav]').forEach(function (a) {
    if (a.getAttribute('href') === pathname) a.classList.add('active');
  });

  /* ---- Desktop dropdowns (tap on coarse pointers) ---- */
  document.querySelectorAll('.nav-item').forEach(function (item) {
    var trigger = item.querySelector(':scope > a');
    if (!trigger) return;
    trigger.addEventListener('click', function (e) {
      if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
      e.preventDefault();
      var open = item.classList.contains('open');
      document.querySelectorAll('.nav-item.open').forEach(function (el) { el.classList.remove('open'); });
      if (!open) item.classList.add('open');
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.nav-item')) {
      document.querySelectorAll('.nav-item.open').forEach(function (el) { el.classList.remove('open'); });
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.nav-item.open').forEach(function (el) { el.classList.remove('open'); });
    }
  });

  /* ---- Reveal on scroll ---- */
  var revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !prefersReduced) {
    var ro = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('visible'); ro.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(function (el) { ro.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('visible'); });
  }

  /* ---- Animated counters ---- */
  function animateCounter(el) {
    var target = parseFloat(el.getAttribute('data-target'));
    if (isNaN(target)) return;
    var suffix = el.getAttribute('data-suffix') || '';
    var decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
    var shown = (el.textContent || '').replace(suffix, '').trim();
    if (shown !== '0' && shown !== '') {
      el.textContent = (decimals > 0 ? target.toFixed(decimals) : Math.round(target)) + suffix;
      return;
    }
    var dur = 1400, start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      var current = target * eased;
      el.textContent = (decimals > 0 ? current.toFixed(decimals) : Math.round(current)) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  var counters = document.querySelectorAll('.num[data-target]');
  if ('IntersectionObserver' in window && !prefersReduced) {
    var co = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { animateCounter(en.target); co.unobserve(en.target); }
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { co.observe(el); });
  } else {
    counters.forEach(function (el) {
      var target = parseFloat(el.getAttribute('data-target'));
      var decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
      var suffix = el.getAttribute('data-suffix') || '';
      el.textContent = (decimals > 0 && !isNaN(target) ? target.toFixed(decimals) : el.getAttribute('data-target')) + suffix;
    });
  }

  /* ---- Sticky header + scroll progress ---- */
  var header = document.getElementById('header');
  var progress = document.getElementById('scroll-progress');
  function onScroll() {
    if (header) {
      if (window.scrollY > 24) { header.classList.add('scrolled'); }
      else { header.classList.remove('scrolled'); }
    }
    if (progress) {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var p = max > 0 ? Math.min(window.scrollY / max, 1) : 0;
      progress.style.transform = 'scaleX(' + p + ')';
    }
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---- Cursor spotlight on cards ---- */
  var spotEls = document.querySelectorAll(
    '.feature-card, .agent-card, .audience-card, .bento-card, .testimonial-card, .zta-step'
  );
  if (!prefersReduced) {
    spotEls.forEach(function (el) {
      el.addEventListener('mousemove', function (e) {
        var r = el.getBoundingClientRect();
        el.style.setProperty('--mx', (e.clientX - r.left) + 'px');
        el.style.setProperty('--my', (e.clientY - r.top) + 'px');
      });
    });
  }

  /* ---- Mobile nav ---- */
  var menuBtn = document.getElementById('menu-btn');
  var mobileNav = document.getElementById('mobile-nav');
  if (menuBtn && mobileNav) {
    menuBtn.addEventListener('click', function () {
      var open = mobileNav.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
    mobileNav.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        mobileNav.classList.remove('open');
        menuBtn.setAttribute('aria-expanded', 'false');
        menuBtn.setAttribute('aria-label', 'Open menu');
      });
    });
  }

  /* ---- Vertical tabs ---- */
  var tabs = document.querySelectorAll('.tab');
  var panels = document.querySelectorAll('.tab-panel');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
      panels.forEach(function (p) { p.classList.remove('active'); });
      tab.classList.add('active');
      tab.setAttribute('aria-selected', 'true');
      var panel = document.getElementById('tab-' + tab.getAttribute('data-tab'));
      if (panel) panel.classList.add('active');
    });
  });

  /* ---- Pipeline (how it works) ---- */
  var pipeline = [
    {
      tag: 'Stage 1 · Sort the queue',
      title: 'Which files need you first',
      desc: 'Triage means sorting the pile before a human opens a document. Ordinary rules check the file against what you will write.',
      items: [
        'What you will write fires first — product, state, class, and size against your underwriting guide',
        'How much is at risk is scored from claim history — limits, deductibles, and what sits on the page',
        'New vs renewal, and whether the cover is first-party or third-party, is checked',
        'Routed to the right lane — or to a human referral queue — before an underwriter ever sees it'
      ]
    },
    {
      tag: 'Stage 2 · Check & price',
      title: 'Verify the file, then price from your rates',
      desc: 'Documents are read and the numbers matched. Risk is checked against real outside data (when connected), then priced from the rates you filed with the state.',
      items: [
        'Documents read, sources tracked, numbers matched, duplicates removed — gaps flagged, never guessed',
        'Claim history from live outside data — prior claims, workers-comp, catastrophe — no fake clean history when accounts are missing',
        'How the building is built (COPE): construction, occupancy, protection, exposure',
        'Ordinary rules first, then trained scorers, then a language model only where needed — every AI cost counted',
        'Your filed rate manuals build the indicated premium. We do not invent a price'
      ]
    },
    {
      tag: 'Stage 3 · You decide',
      title: 'A memo you can sign',
      desc: 'A clear recommendation with reasons, a premium, and a paper trail. The policy issues only after a licensed underwriter signs.',
      items: [
        'Accept, accept with conditions, refer, or decline — with reasons and any conditions that must be true first',
        'A deeper pass can re-check outside data, the rest of the book, reinsurance, and fraud flags when you ask',
        'The memo with the quoted premium waits for licensed sign-off — AI proposes, humans decide',
        'A sealed pack an examiner can open. Nobody can quietly rewrite the record'
      ]
    }
  ];
  var panelEl = document.getElementById('pipeline-panel');
  var stepBtns = document.querySelectorAll('.pipeline-step');
  function renderStep(i) {
    var d = pipeline[i];
    var ul = '<ul class="panel-list">' + d.items.map(function (it) { return '<li>' + it + '</li>'; }).join('') + '</ul>';
    panelEl.innerHTML = '<p class="panel-tag"><svg class="ico" aria-hidden="true"><use href="#i-workflow"/></svg>' + d.tag + '</p><h3 class="panel-title">' + d.title + '</h3><p class="panel-desc">' + d.desc + '</p>' + ul;
    stepBtns.forEach(function (b) {
      var active = Number(b.getAttribute('data-step')) === i;
      b.classList.toggle('active', active);
      b.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }
  if (panelEl) {
    stepBtns.forEach(function (b) {
      b.addEventListener('click', function () { renderStep(Number(b.getAttribute('data-step'))); });
    });
    renderStep(0);
  }

  /* ---- ZTA interactive ladder ---- */
  var ztaSteps = document.querySelectorAll('.zta-ladder.zta-interactive .zta-step');
  var ztaDetail = document.getElementById('zta-detail-panel');
  var ztaDetails = [
    {
      kicker: 'Layer 1 · ~90% of pipeline',
      title: 'Ordinary rules run first',
      desc: 'Document readers, cross-field math, COPE checks, your rate engine, and statutory compliance gates execute in deterministic code. Same inputs, same output — zero AI tokens billed.'
    },
    {
      kicker: 'Layer 2 · trained scorers',
      title: 'Eight models, no prompts',
      desc: 'Loss, fraud, churn, premium, book risk, and default scorers behave like calculators — fixed weights, repeatable scores. Still zero token cost on typical jobs.'
    },
    {
      kicker: 'Layer 3 · language model last',
      title: 'Judgment only when code cannot decide',
      desc: 'Free-text synthesis and narrative memo drafting run inside a per-job budget. Every token is counted, reported on the job, and never used to invent a fact the rules already know.'
    }
  ];
  function renderZta(i) {
    if (!ztaDetail || !ztaDetails[i]) return;
    var d = ztaDetails[i];
    ztaDetail.innerHTML = '<p class="zta-detail-kicker">' + d.kicker + '</p><h4>' + d.title + '</h4><p>' + d.desc + '</p>';
    ztaSteps.forEach(function (step, idx) {
      step.classList.toggle('active', idx === i);
      step.setAttribute('aria-selected', idx === i ? 'true' : 'false');
    });
  }
  if (ztaSteps.length && ztaDetail) {
    ztaSteps.forEach(function (step, i) {
      step.setAttribute('role', 'tab');
      step.setAttribute('tabindex', '0');
      step.addEventListener('click', function () { renderZta(i); });
      step.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); renderZta(i); }
      });
    });
    renderZta(0);
  }

  /* ---- Integrations ---- */
  var integrations = [
    { n: 'CLUE Auto', c: 'oracles' },
    { n: 'CLUE Property', c: 'oracles' },
    { n: 'A-PLUS Loss History', c: 'oracles' },
    { n: 'NCCI eSummit', c: 'oracles' },
    { n: 'LexisNexis Risk', c: 'oracles' },
    { n: 'ISO ClaimSearch', c: 'oracles' },
    { n: 'NOAA / FEMA CAT', c: 'oracles' },
    { n: 'Guidewire PolicyCenter', c: 'policy' },
    { n: 'Duck Creek Policy', c: 'policy' },
    { n: 'Applied Epic', c: 'policy' },
    { n: 'Vertafore AMS360', c: 'policy' },
    { n: 'Salesforce', c: 'policy' },
    { n: 'HubSpot', c: 'policy' },
    { n: 'DocuSign', c: 'policy' },
    { n: 'Jira Service Mgmt', c: 'ops' },
    { n: 'Slack', c: 'ops' },
    { n: 'Box', c: 'ops' },
    { n: 'Dropbox', c: 'ops' },
    { n: 'Google Drive', c: 'ops' },
    { n: 'Email — IMAP / Exchange', c: 'sources' },
    { n: 'AWS S3', c: 'sources' },
    { n: 'SharePoint', c: 'sources' },
    { n: 'Azure Blob', c: 'sources' },
    { n: 'SFTP', c: 'sources' }
  ];
  var catLabel = { oracles: 'Outside data', policy: 'Policy & CRM', ops: 'Enterprise ops', sources: 'Doc sources' };
  var grid = document.getElementById('integration-grid');
  function renderGrid(filter) {
    if (!grid) return;
    grid.innerHTML = integrations.map(function (it) {
      return '<div class="integration-tile' + (filter && it.c !== filter ? ' hidden' : '') + '" data-cat="' + it.c + '"><svg class="ico" aria-hidden="true"><use href="#i-cable"/></svg>' + it.n + '<span class="cat">' + catLabel[it.c] + '</span></div>';
    }).join('');
  }
  renderGrid(null);
  document.querySelectorAll('.filter-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.filter-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      var f = btn.getAttribute('data-filter');
      renderGrid(f === 'all' ? null : f);
    });
  });

  /* ---- FAQ ---- */
  var faqs = [
    { q: 'How is Rytera different from a document-extraction tool?', a: 'Extraction stops at text. Rytera sorts the queue, checks the risk, prices from your rates, and hands you a memo you can sign — with a paper trail. You review a recommendation, not a pile of parsed PDFs.' },
    { q: 'What is Zero Token Architecture (ZTA)?', a: 'Most steps are ordinary software (no AI bill). A language model is the last resort, counted, and never used to invent a fact. That is Zero Token Architecture, said simply: we do not pay an AI to do what a rule already can.' },
    { q: 'Can we try it without issuing a policy?', a: 'Yes. Practice mode (sometimes called shadow) runs on real files without issuing a policy. Prove it on your book. Go live when you say so.' },
    { q: 'Does Rytera work with our policy administration system?', a: 'After a licensed underwriter signs, Desk and above can send the full quote — coverages, filing ID, and conditions — into Guidewire, BriteCore, or Duck Creek so you do not re-type it. A pretend connection is refused on paid plans. Pilot keeps issue-off in practice mode.' },
    { q: 'How do you handle names and private details?', a: 'The person or company on the policy (the named insured) and private details like Social Security numbers come off before any language model sees the page. Your underwriter still sees the real file. The AI does not. Every decision ships in a sealed pack an examiner can open.' },
    { q: 'What if an outside data feed is unavailable?', a: 'Pilot may use honest demo data, labeled as demo. Desk and above stop: missing real claim-history or catastrophe accounts become a finding, not a fake clean history. We never invent a loss run.' },
    { q: 'How does underwriter sign-off work?', a: 'The software proposes accept, accept with conditions, refer, or decline. A licensed underwriter reviews within who is allowed to sign what size of risk, then signs or changes it. Every change is recorded.' },
    { q: 'Which lines are supported?', a: 'Insurance companies, mortgage lenders, and commercial lenders share one workbench — commercial liability, property, auto, workers’ comp, professional liability, cyber, excess & surplus, marine, plus homeowners, auto, term life, mortgage, and consumer / commercial lending.' },
    { q: 'How is Rytera priced?', a: 'Per memo you can sign. Pilot $0/mo (5 memos, then $95). Desk $799/mo (25, then $55) — live outside data plus your filed rates required. Book $2,490/mo (80, then $38) with live Guidewire bind and no re-key. Enterprise from $6,500/mo. Demo data, demo rate books, or a pretend policy-system connection are not sold at Desk prices.' },
    { q: 'Is the price from our filed rates or a demo book?', a: 'Pilot uses a demo book, honestly labeled. Desk and above will not quote until you load the rates you filed with the state. A demo book is never silently used as yours.' },
    { q: 'Do you detect photoshopped photos, fraud rings, and live telematics?', a: 'Yes, and only as far as the code goes. Photos: we read EXIF editor tags and JPEG recompress scars, then ask for the original camera file — we do not claim a crime lab. Rings: a graph net links files that share a phone, email, tax ID, address, or IP. Connected-car and cyber-scan feeds compare the questionnaire to the car or domain only when that account is live. Simulated never invents a clean driving or security score.' },
    { q: 'How do you stop the memo from inventing a fact?', a: 'Hard zero-hallucination gate: uncited limits, totals, and dollar figures are stripped and the file is referred. Max allowed hallucinations is 0. Citation gate, Self-RAG/HyDE, multi-read self-consistency, and a capped Extractor↔Auditor loop all run before bind. The glass box UI lets you click a value and see the page highlight.' }
  ];
  var faqList = document.getElementById('faq-list');
  function renderFaqs(filter) {
    if (!faqList) return;
    var q = (filter || '').toLowerCase();
    faqList.innerHTML = faqs.map(function (f) {
      var hidden = q && (f.q + ' ' + f.a).toLowerCase().indexOf(q) === -1;
      return '<div class="faq-item' + (hidden ? ' hidden' : '') + '">' +
        '<button type="button" class="faq-q" aria-expanded="false"><span>' + f.q + '</span>' +
        '<span class="chev"><svg class="ico" aria-hidden="true"><use href="#i-chevron-down"/></svg></span></button>' +
        '<div class="faq-a"><div class="faq-a-inner"><p>' + f.a + '</p></div></div></div>';
    }).join('');
    faqList.querySelectorAll('.faq-q').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var item = btn.closest('.faq-item');
        var isOpen = item.classList.contains('open');
        faqList.querySelectorAll('.faq-item.open').forEach(function (o) {
          o.classList.remove('open');
          o.querySelector('.faq-q').setAttribute('aria-expanded', 'false');
        });
        if (!isOpen) {
          item.classList.add('open');
          btn.setAttribute('aria-expanded', 'true');
        }
      });
    });
  }
  renderFaqs('');
  var faqSearch = document.getElementById('faq-search');
  if (faqSearch) {
    faqSearch.addEventListener('input', function () { renderFaqs(faqSearch.value); });
  }

  /* ---- Marquee (seamless loop) ---- */
  var track = document.querySelector('.marquee-track');
  if (track) {
    var systems = [
      { n: 'Guidewire', i: 'i-building' },
      { n: 'Applied Epic', i: 'i-layers' },
      { n: 'Duck Creek', i: 'i-server' },
      { n: 'Salesforce', i: 'i-globe' },
      { n: 'AMS360', i: 'i-workflow' },
      { n: 'SharePoint', i: 'i-package' },
      { n: 'AWS S3', i: 'i-database' },
      { n: 'Azure Blob', i: 'i-database' },
      { n: 'SFTP', i: 'i-cable' },
      { n: 'CLUE', i: 'i-shield-check' },
      { n: 'A-PLUS', i: 'i-shield-check' },
      { n: 'NCCI', i: 'i-chart' },
      { n: 'ISO', i: 'i-book' },
      { n: 'LexisNexis', i: 'i-search' },
      { n: 'DocuSign', i: 'i-file-check' },
      { n: 'Slack', i: 'i-mail' },
      { n: 'Google Drive', i: 'i-layers' },
      { n: 'OneDrive', i: 'i-package' },
      { n: 'HubSpot', i: 'i-users' },
      { n: 'ServiceNow', i: 'i-workflow' }
    ];
    var tile = systems.map(function (s) {
      return '<span class="marquee-item"><svg class="ico" aria-hidden="true"><use href="#' + s.i + '"/></svg> ' + s.n + '</span>';
    }).join('');
    track.innerHTML = tile + tile;
  }

  /* ---- Demo modal ---- */
  var modal = document.getElementById('demo-modal');
  var modalWrap = document.getElementById('modal-form-wrap');
  var modalSuccess = document.getElementById('modal-success');
  var form = document.getElementById('demo-form');
  var status = document.getElementById('form-status');
  function openModal() {
    if (!modal) return;
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
  document.querySelectorAll('#open-demo-nav, #open-demo-hero, #open-demo-mobile, #open-demo-contact, [data-open-demo]').forEach(function (btn) {
    btn.addEventListener('click', openModal);
  });
  var closeBtn = document.getElementById('close-demo');
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (modal) {
    modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeModal(); });
  }
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = form.name.value.trim();
      var email = form.email.value.trim();
      var company = form.company.value.trim();
      status.textContent = '';
      if (!name || !email || !company) {
        status.textContent = 'Please fill in your name, email, and company.';
        return;
      }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        status.textContent = 'Please enter a valid work email.';
        return;
      }
      var submitBtn = document.getElementById('demo-submit');
      if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Sending…'; }
      fetch('/api/contact/demo-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          email: email,
          company: company,
          message: form.message.value.trim(),
          vertical: form.vertical.value
        })
      }).then(function (res) {
        if (!res.ok) throw new Error('Request failed (' + res.status + ')');
        form.style.display = 'none';
        modalWrap.style.display = 'none';
        modalSuccess.classList.add('show');
      }).catch(function () {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Send request'; }
        status.textContent = 'Something went wrong — please email hello@ryterainc.com or try again.';
      });
    });
  }

  /* ---- Glossary Interactive Reference ---- */
  var glossaryTerms = [
    { t: 'Underwriter', c: 'underwriting', d: 'The licensed person who decides yes, no, or not yet on a risk. Rytera drafts. They still sign.' },
    { t: 'Carrier / MGA', c: 'underwriting', d: 'Carrier = the insurance company that takes the risk. MGA = a specialist team allowed to underwrite on a carrier’s behalf.' },
    { t: 'Submission', c: 'underwriting', d: 'The pile a broker sends when they want a quote: PDFs, spreadsheets, emails, photos.' },
    { t: 'The Rytera Memo', c: 'underwriting', d: 'The decision-ready recommendation artifact you can read and sign: a completed, auditable file summary with every figure cited to its source page and filed rate — not a pile of notes you still have to rewrite.' },
    { t: 'Practice mode (shadow)', c: 'underwriting', d: 'Run Rytera on real files without issuing a policy. Prove it on your book. Go live when you say so.' },
    { t: 'Appetite', c: 'underwriting', d: 'What your company is willing to write. Files that don’t fit get referred out before they eat a day.' },
    { t: 'Triage', c: 'underwriting', d: 'Sorting the queue so the files that need a human rise first, and the obvious no’s don’t steal the morning.' },
    { t: 'Loss run / SOV / ACORD', c: 'underwriting', d: 'Loss run = history of claims. SOV (schedule of values) = the list of buildings and what they’re worth. ACORD = a standard insurance form brokers already use.' },
    { t: 'Limit, deductible, exposure', c: 'underwriting', d: 'Limit = the most the policy would pay. Deductible = what the customer pays first. Exposure = how much is actually at risk.' },
    { t: 'COPE', c: 'underwriting', d: 'Construction, Occupancy, Protection, Exposure — the four things a property underwriter always checks (how it’s built, who uses it, fire protection, what sits next door).' },
    { t: 'Rate book / SERFF / filing', c: 'compliance', d: 'Your official prices, as filed with the state. SERFF is the system states use to receive those filings. We will not quote off a demo book and call it yours.' },
    { t: 'Policy admin / Guidewire / PAS', c: 'data', d: 'The system that actually issues the policy. Bind without re-key means the quote lands there in full — you should not have to type it again.' },
    { t: 'IMAP, S3, SFTP', c: 'data', d: 'How files already arrive: email (IMAP), a cloud folder (S3), or a secure drop (SFTP). We meet the file where it lives.' },
    { t: 'AI / LLM', c: 'ai', d: 'A language model — software that can read and write. We use it only where judgment is needed. It never issues a policy. Names come off first.' },
    { t: 'Zero Token Architecture', c: 'ai', d: 'Most steps are ordinary rules and checks (no AI bill). AI is the last resort, counted, and never used to invent a fact.' },
    { t: 'Human-in-the-loop', c: 'compliance', d: 'A person stays in charge. Software proposes. A licensed underwriter disposes. Every change they make is recorded.' },
    { t: 'Paper trail / exam pack', c: 'compliance', d: 'A sealed record of what was read, checked, and signed. When a regulator asks why this file, you hand them that — not a story from three shared drives.' },
    { t: 'PII / de-identification', c: 'compliance', d: 'Private details: names, Social Security numbers, tax IDs, dates of birth. Stripping them before AI sees the page is de-identification.' },
    { t: 'Catalog vs live', c: 'lines', d: 'Catalog = we show the product, but we will not pretend we can price or bind it yet. Live = your real rates and connections are in, so a quote is honest.' },
    { t: 'Line desk vs staff desk', c: 'underwriting', d: 'Line underwriters work the files in the branch. Staff underwriters at home office set the rules the line desk follows.' },
    { t: 'Filing-grade', c: 'compliance', d: 'Priced from your official, state-filed rates — not a demo book, not a guess.' },
    { t: 'Tokens', c: 'ai', d: 'The unit an AI vendor bills. “Zero token” means that step used ordinary software, so there is no AI bill and the answer is repeatable.' },
    { t: 'Locked files / who can see what', c: 'compliance', d: 'Fernet = files stored locked. JWT / RBAC = only the right people in your company can open them. SHA-256 = a seal so nobody can quietly change the record.' },
    { t: 'Fail-closed', c: 'compliance', d: 'If a real data feed is missing, we stop or refer the file. We do not invent a clean history so the screen looks pretty.' },
    { t: 'Re-key', c: 'data', d: 'Typing the same quote into another system by hand. Bind without re-key means the policy system receives the full quote.' },
    { t: 'Subjectivities', c: 'underwriting', d: 'Conditions that must be true before the policy can go live (an inspection, a missing form, a signed warranty).' },
    { t: 'Authority matrix', c: 'compliance', d: 'Who is allowed to sign what size of risk. A junior underwriter cannot silently bind a jumbo account.' },
    { t: 'IVANS / SharePoint / Drive', c: 'data', d: 'Industry mailboxes and cloud folders where files already live. We connect when you contract them; until then we do not pretend they are live.' },
    { t: 'GL, WC, D&O, E&O', c: 'lines', d: 'General liability, workers’ compensation, directors & officers, errors & omissions — common commercial covers. We say the long name first.' },
    { t: 'UL, OPD, CI, UBI', c: 'lines', d: 'Universal life, outpatient (day-to-day doctor visits), critical illness, usage-based insurance (price from how you drive). Catalog until we can honestly price them.' },
    { t: 'ISO / AAIS / NCCI', c: 'compliance', d: 'Industry groups that publish standard rates and class codes. Carriers start there, then add their own expenses and profit.' },
    { t: 'E&S (excess & surplus)', c: 'lines', d: 'Risks the regular market will not write. A specialist market can, with extra checks on who is allowed to bind.' },
    { t: 'TRID, Reg Z, HMDA / ECOA, Reg B', c: 'compliance', d: 'Mortgage and lending fairness rules: clear closing costs, honest credit pricing, equal treatment, and a written reason if we say no.' },
    { t: 'MVR / CLUE / HO-3', c: 'data', d: 'MVR = driving record. CLUE = prior home/auto claims. HO-3 = a common homeowners policy form.' },
    { t: 'Replacement cost', c: 'underwriting', d: 'What it would cost to rebuild, not what the building would sell for. A small house cannot claim a warehouse rebuild number.' },
    { t: 'Cross-field check', c: 'underwriting', d: 'Two facts on the same file have to be able to be true together. Payroll needs people. A license cannot be issued after the policy starts.' },
    { t: 'EXIF / ELA', c: 'ai', d: 'EXIF = the camera tag on a photo (who saved it, when). ELA = JPEG error-level analysis — a local paste often leaves a hotter recompress scar than an original shot.' },
    { t: 'Fraud ring / graph net', c: 'ai', d: 'Files linked by the same phone, address, tax ID, or IP. A small neural net on that graph scores whether the cluster looks like a ring — not a guess from a single file.' },
    { t: 'Telematics / cyber scan', c: 'data', d: 'Telematics = what the car actually did (miles, hard brakes). Cyber scan = an outside look at a domain. We compare those to the questionnaire only when the feed is live.' },
    { t: 'Citation gate', c: 'ai', d: 'A critical number without a page, box, or source ref is not a fact. It fails straight-through processing and stays off the memo until grounded.' },
    { t: 'Self-RAG / HyDE', c: 'ai', d: 'Self-RAG = retrieve, ask if the context is enough, retrieve again if not. HyDE = search with a hypothetical guideline paragraph when the desk question is too short for vector match.' },
    { t: 'Glass box', c: 'ai', d: 'Click a value, see the page highlight. Warm color means low confidence. Approve still needs a licensed person.' },
    { t: 'Zero-hallucination gate', c: 'ai', d: 'Target: zero uncited money, limits, or totals on a Rytera Memo. Anything invented is stripped and the file is referred. We do not rubber-stamp a pretty number.' },
    { t: 'Oracles (CLUE, NCCI, A+, CAT)', c: 'data', d: 'Outside data checks: prior claims, workers-comp history, catastrophe risk. We only treat them as real when your accounts are connected. We never fake a clean history.' },
    { t: 'Verbatim Source Attribution', c: 'ai', d: 'Every extracted data point, financial metric, or policy clause links directly to its original document bounding box and page number.' },
    { t: 'Chain-of-Thought Auditing', c: 'ai', d: 'A step-by-step audit trail showing how the multi-agent system reached a conclusion (e.g. why a risk score was elevated based on loss runs).' },
    { t: 'Field-Level Confidence Scores', c: 'ai', d: 'Individual confidence scores per field rather than a single global score. Low-confidence extractions automatically route to human review.' },
    { t: 'Frictionless Overrides', c: 'underwriting', d: 'Single-click override controls allowing an underwriter to modify AI recommendations with mandatory drop-down reason logging.' },
    { t: 'Deterministic Guardrails (UWGs)', c: 'compliance', d: 'Hard-coded underwriting guidelines (minimum credit, class exclusions, maximum limits) executed via deterministic code, not LLM guesswork.' },
    { t: 'Multi-Year Reproducibility', c: 'compliance', d: 'The ability to reconstruct the exact data state, prompts, and reasoning trail for state market-conduct exams 3+ years later.' },
    { t: 'Graceful Degradation / Fail-Closed', c: 'compliance', d: 'If a scan is blurry or an API times out, the system cleanly halts and requests human intervention rather than hallucinating missing figures.' },
    { t: 'Insufficient Data ("I Don\'t Know")', c: 'ai', d: 'Agents explicitly output "Insufficient Data" when information is absent from a submission, with zero financial interpolation or synthetic guessing.' }
  ];

  var catNames = {
    all: 'All Terms',
    underwriting: 'Underwriting',
    ai: 'AI & Architecture',
    data: 'Data & Oracles',
    compliance: 'Compliance',
    lines: 'Lines & Desks'
  };

  var glossaryModal = document.getElementById('glossary-modal');
  var glossaryList = document.getElementById('glossary-modal-list');
  var glossaryInput = document.getElementById('glossary-modal-input');
  var currentCat = 'all';
  var currentQuery = '';

  function renderGlossary() {
    if (!glossaryList) return;
    var q = (currentQuery || '').toLowerCase().trim();
    var filtered = glossaryTerms.filter(function (item) {
      var matchesCat = (currentCat === 'all' || item.c === currentCat);
      var matchesQuery = !q || (item.t.toLowerCase().indexOf(q) !== -1 || item.d.toLowerCase().indexOf(q) !== -1);
      return matchesCat && matchesQuery;
    });

    if (filtered.length === 0) {
      glossaryList.innerHTML = '<div class="glossary-empty"><p>No definitions found for "<strong>' + currentQuery + '</strong>".</p><button type="button" class="btn btn-ghost btn-sm" id="reset-glossary-btn" style="margin-top:.8rem">Show all terms</button></div>';
      var rBtn = document.getElementById('reset-glossary-btn');
      if (rBtn) {
        rBtn.addEventListener('click', function () {
          currentQuery = '';
          currentCat = 'all';
          if (glossaryInput) glossaryInput.value = '';
          document.querySelectorAll('.glossary-filter-chip').forEach(function (c) {
            c.classList.toggle('active', c.getAttribute('data-cat') === 'all');
          });
          renderGlossary();
        });
      }
      return;
    }

    glossaryList.innerHTML = '<div class="glossary-grid">' + filtered.map(function (item) {
      return '<div class="glossary-card" data-cat="' + item.c + '">' +
        '<div class="glossary-card-top">' +
          '<span class="glossary-term">' + item.t + '</span>' +
          '<span class="glossary-category-tag">' + (catNames[item.c] || item.c) + '</span>' +
        '</div>' +
        '<p class="glossary-def">' + item.d + '</p>' +
      '</div>';
    }).join('') + '</div>';
  }

  function openGlossary(initialQuery, initialCat) {
    if (!glossaryModal) return;
    if (typeof initialQuery === 'string') {
      currentQuery = initialQuery;
      if (glossaryInput) glossaryInput.value = initialQuery;
    }
    if (typeof initialCat === 'string') {
      currentCat = initialCat;
      document.querySelectorAll('.glossary-filter-chip').forEach(function (c) {
        c.classList.toggle('active', c.getAttribute('data-cat') === initialCat);
      });
    }
    renderGlossary();
    glossaryModal.classList.add('open');
    document.body.style.overflow = 'hidden';
    if (glossaryInput) setTimeout(function () { glossaryInput.focus(); }, 100);
  }

  function closeGlossary() {
    if (!glossaryModal) return;
    glossaryModal.classList.remove('open');
    document.body.style.overflow = '';
  }

  document.querySelectorAll('#open-glossary-nav, #open-glossary-hero, #open-glossary-mobile, #open-glossary-footer, #open-glossary-full, [data-open-glossary]').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      openGlossary('', 'all');
    });
  });

  // Intercept any <a href="#plain"> links so they open the interactive glossary modal
  document.querySelectorAll('a[href="#plain"]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      openGlossary('', 'all');
    });
  });

  // Featured terms click in preview box
  document.querySelectorAll('.glossary-featured-grid .plain-term').forEach(function (card) {
    card.style.cursor = 'pointer';
    card.addEventListener('click', function () {
      var term = card.getAttribute('data-term') || card.querySelector('dt').textContent;
      openGlossary(term, 'all');
    });
  });

  var previewInp = document.getElementById('preview-glossary-search');
  var previewBtn = document.getElementById('preview-search-btn');
  if (previewBtn && previewInp) {
    previewBtn.addEventListener('click', function () {
      openGlossary(previewInp.value);
    });
    previewInp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') openGlossary(previewInp.value);
    });
  }

  var closeGlossaryBtn = document.getElementById('close-glossary');
  if (closeGlossaryBtn) closeGlossaryBtn.addEventListener('click', closeGlossary);

  if (glossaryModal) {
    glossaryModal.addEventListener('click', function (e) {
      if (e.target === glossaryModal) closeGlossary();
    });
  }

  if (glossaryInput) {
    glossaryInput.addEventListener('input', function () {
      currentQuery = glossaryInput.value;
      renderGlossary();
    });
  }

  var clearBtn = document.getElementById('clear-glossary-search');
  if (clearBtn && glossaryInput) {
    clearBtn.addEventListener('click', function () {
      glossaryInput.value = '';
      currentQuery = '';
      renderGlossary();
      glossaryInput.focus();
    });
  }

  document.querySelectorAll('.glossary-filter-chip').forEach(function (chip) {
    chip.addEventListener('click', function () {
      document.querySelectorAll('.glossary-filter-chip').forEach(function (c) { c.classList.remove('active'); });
      chip.classList.add('active');
      currentCat = chip.getAttribute('data-cat') || 'all';
      renderGlossary();
    });
  });

  /* =====================================================================
     2026 MODERN UI ENHANCEMENTS
     ===================================================================== */

  /* ---- Glow Mouse Follower ---- */
  if (!prefersReduced) {
    var glowEl = document.querySelector('.glow-follower');
    if (glowEl) {
      var glowX = 0, glowY = 0, glowCurX = 0, glowCurY = 0;
      document.addEventListener('mousemove', function (e) {
        glowX = e.clientX;
        glowY = e.clientY;
        glowEl.classList.add('active');
      });
      document.addEventListener('mouseleave', function () {
        glowEl.classList.remove('active');
      });
      function animateGlow() {
        glowCurX += (glowX - glowCurX) * 0.08;
        glowCurY += (glowY - glowCurY) * 0.08;
        glowEl.style.left = glowCurX + 'px';
        glowEl.style.top = glowCurY + 'px';
        requestAnimationFrame(animateGlow);
      }
      animateGlow();
    }
  }

  /* ---- 3D Card Tilt ---- */
  if (!prefersReduced) {
    var tiltCards = document.querySelectorAll('.feature-card, .audience-card, .agent-card, .bento-card, .testimonial-card');
    tiltCards.forEach(function (card) {
      card.classList.add('tilt-card');
      card.addEventListener('mousemove', function (e) {
        var r = card.getBoundingClientRect();
        var cx = r.left + r.width / 2;
        var cy = r.top + r.height / 2;
        var dx = (e.clientX - cx) / (r.width / 2);
        var dy = (e.clientY - cy) / (r.height / 2);
        var tiltX = dy * -4;
        var tiltY = dx * 4;
        card.style.transform = 'perspective(800px) rotateX(' + tiltX + 'deg) rotateY(' + tiltY + 'deg) translateY(-5px)';
      });
      card.addEventListener('mouseleave', function () {
        card.style.transform = '';
      });
    });
  }

  /* ---- Magnetic Buttons ---- */
  if (!prefersReduced) {
    document.querySelectorAll('.btn-primary').forEach(function (btn) {
      btn.addEventListener('mousemove', function (e) {
        var r = btn.getBoundingClientRect();
        var x = e.clientX - r.left - r.width / 2;
        var y = e.clientY - r.top - r.height / 2;
        btn.style.transform = 'translate(' + (x * 0.15) + 'px, ' + (y * 0.15) + 'px)';
      });
      btn.addEventListener('mouseleave', function () {
        btn.style.transform = '';
      });
    });
  }

  /* ---- Button Ripple Effect ---- */
  document.querySelectorAll('.btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      if (prefersReduced) return;
      var r = btn.getBoundingClientRect();
      var circle = document.createElement('span');
      circle.classList.add('ripple-circle');
      var size = Math.max(r.width, r.height);
      circle.style.width = circle.style.height = size + 'px';
      circle.style.left = (e.clientX - r.left - size / 2) + 'px';
      circle.style.top = (e.clientY - r.top - size / 2) + 'px';
      btn.appendChild(circle);
      setTimeout(function () { circle.remove(); }, 650);
    });
  });

  /* ---- Staggered Reveal ---- */
  if ('IntersectionObserver' in window && !prefersReduced) {
    var staggerEls = document.querySelectorAll('.stagger-reveal');
    var staggerObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('visible'); staggerObs.unobserve(en.target); }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -30px 0px' });
    staggerEls.forEach(function (el) { staggerObs.observe(el); });
  } else {
    document.querySelectorAll('.stagger-reveal').forEach(function (el) { el.classList.add('visible'); });
  }

  /* ---- Text Scramble Hero ---- */
  if (!prefersReduced) {
    var scrambleEls = document.querySelectorAll('.scramble-text');
    scrambleEls.forEach(function (el) {
      var text = el.getAttribute('data-text') || el.textContent;
      el.textContent = '';
      el.setAttribute('aria-label', text);
      var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%&*';
      var len = text.length;
      var revealed = 0;
      function step() {
        if (revealed >= len) {
          el.textContent = text;
          return;
        }
        var display = '';
        for (var i = 0; i < len; i++) {
          if (i < revealed) {
            display += text[i];
          } else if (text[i] === ' ' || text[i] === '\n') {
            display += text[i];
          } else {
            display += chars[Math.floor(Math.random() * chars.length)];
          }
        }
        el.textContent = display;
        revealed += 1;
        setTimeout(step, 25 + Math.random() * 15);
      }
      var scrambleObs = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) {
            step();
            scrambleObs.unobserve(en.target);
          }
        });
      }, { threshold: 0.5 });
      scrambleObs.observe(el);
    });
  }

  /* ---- Stat Ring Animation ---- */
  if ('IntersectionObserver' in window && !prefersReduced) {
    var rings = document.querySelectorAll('.stat-ring');
    var ringObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('visible'); ringObs.unobserve(en.target); }
      });
    }, { threshold: 0.5 });
    rings.forEach(function (el) { ringObs.observe(el); });
  } else {
    document.querySelectorAll('.stat-ring').forEach(function (el) { el.classList.add('visible'); });
  }

  /* ---- Parallax Scroll ---- */
  if (!prefersReduced) {
    var parallaxLayers = document.querySelectorAll('.parallax-layer');
    if (parallaxLayers.length) {
      var lastScroll = 0;
      function updateParallax() {
        var sy = window.scrollY;
        if (Math.abs(sy - lastScroll) < 1) {
          requestAnimationFrame(updateParallax);
          return;
        }
        lastScroll = sy;
        parallaxLayers.forEach(function (layer) {
          var speed = parseFloat(layer.getAttribute('data-speed')) || 0.3;
          var rect = layer.parentElement.getBoundingClientRect();
          var offset = (rect.top + rect.height / 2 - window.innerHeight / 2) * speed;
          layer.style.transform = 'translateY(' + offset + 'px)';
        });
        requestAnimationFrame(updateParallax);
      }
      requestAnimationFrame(updateParallax);
    }
  }

  /* ---- Floating Particles ---- */
  if (!prefersReduced) {
    var particleFields = document.querySelectorAll('.particle-field');
    particleFields.forEach(function (field) {
      for (var i = 0; i < 18; i++) {
        var p = document.createElement('div');
        p.classList.add('particle');
        p.style.left = Math.random() * 100 + '%';
        p.style.bottom = '-10px';
        p.style.animationDuration = (8 + Math.random() * 14) + 's';
        p.style.animationDelay = (Math.random() * 10) + 's';
        p.style.width = p.style.height = (2 + Math.random() * 3) + 'px';
        p.style.opacity = 0.15 + Math.random() * 0.35;
        field.appendChild(p);
      }
    });
  }

})();
