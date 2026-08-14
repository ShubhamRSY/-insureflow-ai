(function () {
  'use strict';

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- Active nav link (by path) ---- */
  var pathname = window.location.pathname.replace(/\/+$/, '') || '/';
  document.querySelectorAll('a[data-nav]').forEach(function (a) {
    if (a.getAttribute('href') === pathname) a.classList.add('active');
  });

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
    var dur = 1400, start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased) + suffix;
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
      el.textContent = el.getAttribute('data-target') + (el.getAttribute('data-suffix') || '');
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
    '.feature-card, .agent-card, .audience-card, .bento-card, .testimonial-card, .lob-card, .zta-step'
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
      tag: 'Stage 1 · Triage',
      title: 'Qualify the submission in seconds',
      desc: 'Before a human opens a single document, deterministic rules qualify the file against your live underwriting guide.',
      items: [
        'Appetite filters fire first — product line, state, class code, and revenue checks against your UW guide',
        'Impact and exposure scored from loss runs — exposure types, revenue limits, and limits / SIR',
        'New-renewal and policy characteristics (first-party, third-party, employment practices) verified',
        'Auto-routed to the right lane — or to a REFER queue — before an underwriter ever sees it'
      ]
    },
    {
      tag: 'Stage 2 · Risk & Price',
      title: 'Verify, analyze, and price with evidence',
      desc: 'Documents are parsed, reconciled, and scored. Risk is verified against live oracles, then priced with filing-grade rate manuals.',
      items: [
        'Documents parsed, provenance tracked, reconciled, and deduplicated — gaps flagged, never guessed',
        'Loss history via live oracles — CLUE, A-PLUS, NCCI, CAT — no fake clean data when keys are missing',
        'COPE graded — construction, occupancy, protection, exposure',
        'ZTA pipeline: deterministic rules, then trained ML, then LLM only where needed — every token accounted in zta_report',
        'Rating engines and rate manuals (ISO / AAIS / NCCI) build the indicated premium'
      ]
    },
    {
      tag: 'Stage 3 · Decision',
      title: 'Bind-ready memo with licensed sign-off',
      desc: 'A clear recommendation with reasons, premium, and audit trail — and bind only after a licensed UW signs off.',
      items: [
        'ACCEPT / CONDITIONAL_ACCEPT / REFER / DECLINE with reasons and subjectivities',
        'Deep dive re-runs oracles, portfolio, reinsurance, and fraud ML on demand',
        'UW memo with quoted premium presented for licensed sign-off — AI proposes, humans decide',
        'Encrypted audit bundle exported as a SHA-256 manifest ZIP, examiner-ready'
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
  var catLabel = { oracles: 'Oracles', policy: 'Policy & CRM', ops: 'Enterprise ops', sources: 'Doc sources' };
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
    { q: 'How is Rytera different from a document-extraction tool?', a: 'Extraction stops at text. Rytera runs an end-to-end pipeline — triage, risk verification, rating, and a decision with audit trail — so underwriters review a bind-ready memo instead of a pile of parsed PDFs.' },
    { q: 'What is Zero Token Architecture (ZTA)?', a: 'ZTA means deterministic code and trained ML solve everything they can before any LLM is invoked. Most stages run at zero tokens. When an LLM is truly needed, it is budgeted per job, tracked per stage, and reported in each job\'s zta_report.' },
    { q: 'Can we pilot in shadow mode before binding anything?', a: 'Yes. Shadow mode runs the full pipeline on real submissions with bind off, so your team can measure accuracy and steer the book before any live decision or policy admin integration is enabled.' },
    { q: 'Does Rytera work with our policy administration system?', a: 'Desk+ bind posts the full quote, coverages, filing ID, and subjectivities into Guidewire PolicyCenter, BriteCore, or Duck Creek after licensed UW sign-off. Simulated PAS is refused on paid plans so UW does not re-key. Pilot keeps bind off in shadow.' },
    { q: 'How do you handle PII and security?', a: 'Named insureds, SSNs, EINs, DOBs, and other PII are stripped before we touch a file with any LLM API — every insurance section, mortgage, and lending. Deterministic underwriting still sees the original locally. Every job is org-scoped, and every decision ships in an encrypted SHA-256 manifest audit bundle.' },
    { q: 'Can we choose which insurance company a file is for?', a: 'Yes. Every insurance run has a writing-company picker from your appointed panel. Add Meridian Mutual, Harbor Casualty, or any carrier you actually appoint. Rytera does not invent a live market appointment. The chosen company is stamped on the job and the audit trail; rating still uses the rate book you loaded.' },
    { q: 'What if an oracle or data feed is unavailable?', a: 'Pilot may use simulated oracles. Desk+ fail-closes: missing live CLUE / NCCI / A+ / CAT keys become a critical finding instead of a fake clean history. Auto mode never invents loss runs.' },
    { q: 'How does UW sign-off work?', a: 'The pipeline proposes ACCEPT, CONDITIONAL_ACCEPT, REFER, or DECLINE. A licensed underwriter reviews within their authority matrix tier and either signs off or overrides — every override is traceable in the audit trail.' },
    { q: 'Which verticals and lines are supported?', a: '12 insurance sections on one workbench — life (term live), health (filed HLTH-2026-01), general/non-life, commercial, specialty, provider type, engineering, aviation, fidelity & burglary, catastrophe, niche liability, and warranty / financial / emerging — plus mortgage and commercial lending. General/non-life and unfiled specialty leaves stay catalog-only until a filed general book is loaded; we do not invent a premium.' },
    { q: 'How is Rytera priced?', a: 'Per bind-ready memo. Pilot $0/mo (5 memos, then $95). Desk $799/mo (25, then $55) — live oracles + your SERFF book required. Book $2,490/mo (80, then $38) with live Guidewire bind, no re-key. Enterprise from $6,500/mo. Simulated oracles, pilot manuals, or simulated PAS are not sold at Desk+ prices.' },
    { q: 'Is rating from our filed rates or a demo book?', a: 'Pilot uses the InsureFlow demo book. Desk+ will not quote until you import your SERFF / carrier filings via POST /rating/carrier-book or CARRIER_BOOK_PATH. Pilot manuals are never silently used as your book.' }
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
})();
