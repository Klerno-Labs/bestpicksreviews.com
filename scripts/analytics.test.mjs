import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../assets/analytics.js', import.meta.url), 'utf8');

// Only the DOM behavior consumed by analytics.js is simulated. No fetch or real
// browser transport exists in this context, so tests cannot send user events.
function browser({ stored = null, hostname = 'bestpicksreviews.com', storageBlocked = false } = {}) {
  class Element {
    constructor(tag) { this.tagName = tag; this.children = []; this.events = {}; this.dataset = {}; }
    appendChild(child) { this.children.push(child); child.parent = this; return child; }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(c => c !== this); }
    setAttribute(name, value) { this[name] = value; }
    addEventListener(type, callback) { (this.events[type] ??= []).push(callback); }
    trigger(type) { for (const callback of this.events[type] ?? []) callback({ type, target: this }); }
    focus() { this.focused = true; }
    set innerHTML(value) {
      this.markup = value;
      if (value.includes('data-bp-consent')) {
        for (const choice of ['denied', 'granted']) {
          const button = new Element('button'); button.dataset.bpConsent = choice; this.appendChild(button);
        }
      }
    }
    querySelectorAll(selector) { return this.children.filter(c => c.tagName === selector); }
  }
  const body = new Element('body');
  const head = new Element('head');
  const footer = body.appendChild(new Element('footer'));
  const events = {};
  const find = (node, id) => node.id === id ? node : node.children.map(c => find(c, id)).find(Boolean);
  const document = {
    body, head, readyState: 'complete',
    createElement: tag => new Element(tag),
    getElementById: id => find(body, id) || find(head, id),
    querySelector: selector => selector === 'footer' ? footer : null,
    addEventListener(type, callback) { (events[type] ??= []).push(callback); },
  };
  const values = new Map(stored === null ? [] : [['bp-analytics-consent', stored]]);
  const localStorage = {
    getItem(key) { if (storageBlocked) throw new Error('unavailable'); return values.get(key) ?? null; },
    setItem(key, value) { if (storageBlocked) throw new Error('unavailable'); values.set(key, value); },
  };
  const location = { hostname, origin: `https://${hostname}`, pathname: '/best-open-ear-headphones-for-running/', search: '?private=not-collected' };
  const window = {};
  vm.runInNewContext(source, { window, document, location, localStorage, URL, Date });
  return {
    window, document, values,
    loads: () => head.children.filter(c => c.tagName === 'script'),
    calls: () => Array.from(window.dataLayer, item => Array.from(item)),
    choose(value) {
      if (!document.getElementById('bp-privacy-panel')) document.getElementById('bp-privacy-settings').trigger('click');
      const button = document.getElementById('bp-privacy-panel').children.find(c => c.dataset.bpConsent === value);
      assert.ok(button, 'consent choice exists'); button.trigger('click');
    },
    click(href, { placement = 'article', type = 'click', button = 0 } = {}) {
      const link = {
        href,
        closest(selector) {
          if (selector === 'a[href]') return this;
          if (selector === '#bp-sticky-cta') return placement === 'sticky' ? {} : null;
          if (selector === 'aside') return placement === 'sidebar' ? {} : null;
          return null;
        },
        querySelector: selector => selector === 'img' && placement === 'image' ? {} : null,
      };
      let prevented = false;
      for (const callback of events[type] ?? []) callback({ type, button, target: link, preventDefault() { prevented = true; } });
      return { href: link.href, prevented };
    },
  };
}

const awin = 'https://www.awin1.com/cread.php?awinmid=38859&awinaffid=123&clickref=running-top-pick&ued=https%3A%2F%2Fmerchant.example%2Fproduct';
const affiliateEvents = context => context.calls().filter(args => args[0] === 'event' && args[1] === 'affiliate_click');

test('no collection or custom events before a consent choice', () => {
  const context = browser();
  context.click(awin);
  assert.equal(context.loads().length, 0);
  assert.equal(context.calls().length, 0);
  assert.equal(context.window['ga-disable-G-H5VHR2H1ZK'], true);
});

test('opt-in loads the verified property once and omits query strings from page location', () => {
  const context = browser();
  context.choose('granted');
  context.choose('granted');
  assert.equal(context.loads().length, 1);
  assert.equal(context.loads()[0].src, 'https://www.googletagmanager.com/gtag/js?id=G-H5VHR2H1ZK');
  const configs = context.calls().filter(args => args[0] === 'config');
  assert.equal(configs.length, 1);
  assert.equal(configs[0][2].page_location, 'https://bestpicksreviews.com/best-open-ear-headphones-for-running/');
  assert.equal(configs[0][2].allow_google_signals, false);
});

test('denied consent and revoked consent suppress affiliate events', () => {
  const denied = browser({ stored: 'denied' });
  denied.click(awin);
  assert.equal(denied.loads().length, 0);
  assert.equal(affiliateEvents(denied).length, 0);
  const context = browser({ stored: 'granted' });
  context.choose('denied');
  context.click(awin);
  assert.equal(context.window['ga-disable-G-H5VHR2H1ZK'], true);
  assert.equal(affiliateEvents(context).length, 0);
  assert.equal(context.values.get('bp-analytics-consent'), 'denied');
});

test('Awin click carries real URL parameters without rewriting or preventing navigation', () => {
  const context = browser({ stored: 'granted' });
  assert.deepEqual(context.click(awin, { placement: 'sticky' }), { href: awin, prevented: false });
  const [event] = affiliateEvents(context);
  assert.equal(event[2].affiliate_network, 'awin');
  assert.equal(event[2].advertiser_id, '38859');
  assert.equal(event[2].article_slug, 'best-open-ear-headphones-for-running');
  assert.equal(event[2].clickref, 'running-top-pick');
  assert.equal(event[2].link_placement, 'sticky');
  assert.equal(event[2].transport_type, 'beacon');
});

test('local previews never load Google or send events, even after opt-in', () => {
  for (const hostname of ['localhost', '127.0.0.1', 'preview.example', 'bestpicksreviews.com.example']) {
    const context = browser({ hostname, stored: 'granted' });
    context.choose('granted');
    context.click(awin);
    assert.equal(context.loads().length, 0, hostname);
    assert.equal(context.calls().length, 0, hostname);
  }
});

test('unrelated links and right clicks are ignored while middle-click purchases remain measurable', () => {
  const context = browser({ stored: 'granted' });
  context.click('https://merchant.example/plain-product');
  context.click('https://awin1.com.example/?awinmid=38859');
  context.click(awin, { type: 'auxclick', button: 2 });
  assert.equal(affiliateEvents(context).length, 0);
  context.click(awin, { type: 'auxclick', button: 1 });
  assert.equal(affiliateEvents(context).length, 1);
});

test('blocked browser storage does not prevent consent controls or cause pre-consent collection', () => {
  const context = browser({ storageBlocked: true });
  assert.equal(context.loads().length, 0);
  context.choose('granted');
  assert.equal(context.loads().length, 1);
});
