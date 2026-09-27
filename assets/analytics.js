(function () {
  'use strict';
  var measurementId = 'G-H5VHR2H1ZK';
  var key = 'bp-analytics-consent';
  var consent = null;
  var started = false;
  var production = /^(www\.)?bestpicksreviews\.com$/.test(location.hostname);
  try { consent = localStorage.getItem(key); } catch (_) {}
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  window['ga-disable-' + measurementId] = consent !== 'granted';

  function start() {
    if (started || !production || consent !== 'granted') return;
    started = true;
    window['ga-disable-' + measurementId] = false;
    window.gtag('consent', 'default', { analytics_storage: 'granted', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' });
    window.gtag('js', new Date());
    window.gtag('config', measurementId, {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      page_location: location.origin + location.pathname
    });
    var script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
    document.head.appendChild(script);
  }

  function choose(value) {
    consent = value;
    try { localStorage.setItem(key, value); } catch (_) {}
    window['ga-disable-' + measurementId] = value !== 'granted';
    if (started) window.gtag('consent', 'update', { analytics_storage: value === 'granted' ? 'granted' : 'denied' });
    start();
    var panel = document.getElementById('bp-privacy-panel');
    if (panel) panel.remove();
    var control = document.getElementById('bp-privacy-settings');
    if (control) control.focus({ preventScroll: true });
  }

  function showSettings() {
    if (document.getElementById('bp-privacy-panel')) return;
    var panel = document.createElement('section');
    panel.id = 'bp-privacy-panel';
    panel.setAttribute('aria-label', 'Analytics privacy choices');
    panel.innerHTML = '<p><strong>Your privacy choices</strong><br>Allow optional Google Analytics to help us understand which guides and shop links are useful? You can change your choice any time. <a href="/privacy.html">Privacy details</a></p><div><button type="button" data-bp-consent="denied">No thanks</button><button type="button" data-bp-consent="granted">Allow analytics</button></div>';
    panel.querySelectorAll('button').forEach(function (button) {
      button.addEventListener('click', function () { choose(button.dataset.bpConsent); });
    });
    document.body.appendChild(panel);
  }

  function trackClick(event) {
    if (consent !== 'granted' || !production || (event.type === 'auxclick' && event.button !== 1)) return;
    var link = event.target.closest && event.target.closest('a[href]');
    if (!link) return;
    var url;
    try { url = new URL(link.href); } catch (_) { return; }
    var awin = /(^|\.)awin1\.com$/.test(url.hostname);
    var amazon = /(^|\.)amazon\.com$/.test(url.hostname) && url.searchParams.has('tag');
    if (!awin && !amazon) return;
    window.gtag('event', 'affiliate_click', {
      affiliate_network: awin ? 'awin' : 'amazon',
      advertiser_id: awin ? (url.searchParams.get('awinmid') || '') : 'amazon',
      article_slug: location.pathname.replace(/^\/+|\/+$/g, '') || 'home',
      clickref: url.searchParams.get('clickref') || '',
      link_placement: link.closest('#bp-sticky-cta') ? 'sticky' : link.closest('aside') ? 'sidebar' : link.querySelector('img') ? 'image' : 'article',
      transport_type: 'beacon'
    });
  }

  document.addEventListener('click', trackClick);
  document.addEventListener('auxclick', trackClick);
  function init() {
    var control = document.createElement('button');
    control.id = 'bp-privacy-settings';
    control.type = 'button';
    control.textContent = 'Privacy choices';
    control.addEventListener('click', showSettings);
    (document.querySelector('footer') || document.body).appendChild(control);
    if (consent === null) showSettings();
    start();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
