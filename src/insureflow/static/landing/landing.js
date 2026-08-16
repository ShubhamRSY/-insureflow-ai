(function () {
  'use strict';

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- Active nav link (by path) ---- */
  var pathname = window.location.pathname.replace(/\/+$/, '') || '/';
  document.querySelectorAll('a[data-nav]').forEach(function (a) {
    if (a.getAttribute('href') === pathname) a.classList.add('active');
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
    var shown = (el.textContent || '').replace(suffix, '').trim();
    if (shown !== '0' && shown !== '') {
      el.textContent = Math.round(target) + suffix;
      return;
    }
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
})();
