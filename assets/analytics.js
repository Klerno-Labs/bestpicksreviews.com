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

  // Only public channel labels and explicitly registered campaign IDs are sent.
  // Never forward arbitrary query text, search terms, email addresses or IDs.
  var sources = {
    'pinterest': 'social', 'pinterest.com': 'social',
    'instagram': 'social', 'facebook': 'social', 'tiktok': 'social',
    'youtube': 'social', 'newsletter': 'email', 'pegrio': 'referral',
    'google': 'organic', 'bing': 'organic',
    'chatgpt.com': 'referral', 'perplexity.ai': 'referral',
    'claude.ai': 'referral', 'gemini.google.com': 'referral',
    'copilot.microsoft.com': 'referral'
  };
  var media = ['social', 'organic_social', 'paid_social', 'referral', 'email', 'organic', 'cpc'];
  var campaigns = ['guide-reviews-2026-10', 'label-refill-guide', 'open-ear-fit-guide'];

  function referrerOrigin() {
    try {
      var referrer = new URL(document.referrer);
      return /^https?:$/.test(referrer.protocol) ? referrer.origin + '/' : '';
    } catch (_) { return ''; }
  }

  function start() {
    if (started || !production || consent !== 'granted') return;
    started = true;
    window['ga-disable-' + measurementId] = false;
    window.gtag('consent', 'default', { analytics_storage: 'granted', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' });
    window.gtag('js', new Date());
    var config = {
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      page_location: location.origin + location.pathname,
      page_referrer: referrerOrigin(),
      campaign_term: '',
      campaign_content: '',
      campaign_id: ''
    };
    var params = new URL(location.origin + location.pathname + location.search).searchParams;
    var source = (params.get('utm_source') || '').toLowerCase();
    if (Object.prototype.hasOwnProperty.call(sources, source)) {
      config.campaign_source = source;
      var medium = (params.get('utm_medium') || '').toLowerCase();
      config.campaign_medium = media.indexOf(medium) !== -1 ? medium : sources[source];
      var campaign = params.get('utm_campaign') || '';
      config.campaign_name = campaigns.indexOf(campaign) !== -1 ? campaign : '';
    } else {
      config.campaign_source = '';
      config.campaign_medium = '';
      config.campaign_name = '';
    }
    window.gtag('config', measurementId, config);
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
    if (!/^https?:$/.test(url.protocol) || url.hostname === location.hostname) return;
    var awin = /(^|\.)awin1\.com$/.test(url.hostname);
    var amazon = /(^|\.)amazon\.com$/.test(url.hostname) && url.searchParams.has('tag');
    if (!awin && !amazon) {
      window.gtag('event', 'outbound_click', {
        destination_domain: url.hostname,
        article_slug: location.pathname.replace(/^\/+|\/+$/g, '') || 'home',
        transport_type: 'beacon'
      });
      return;
    }
    var advertiser = url.searchParams.get('awinmid') || '';
    var clickref = url.searchParams.get('clickref') || '';
    window.gtag('event', 'affiliate_click', {
      affiliate_network: awin ? 'awin' : 'amazon',
      advertiser_id: awin ? (/^\d{1,12}$/.test(advertiser) ? advertiser : '') : 'amazon',
      article_slug: location.pathname.replace(/^\/+|\/+$/g, '') || 'home',
      clickref: /^[a-z0-9_-]{1,100}$/i.test(clickref) ? clickref : '',
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
