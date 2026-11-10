'use strict';
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const source = readFileSync(require('node:path').join(__dirname, '../js/planet.js'), 'utf8');

function harness({ reduced = false, width = 1240, height = 581 } = {}) {
  function events(extra = {}) {
    const listeners = new Map();
    return Object.assign({
      addEventListener(name, fn) { listeners.set(name, [...(listeners.get(name) || []), fn]); },
      emit(name, data = {}) { for (const fn of listeners.get(name) || []) fn(data); }
    }, extra);
  }
  const callbacks = new Map();
  const captures = new Set();
  const classes = new Set();
  let id = 0, time = 0, paints = 0, drawing, path, intersection;
  const context = {
    clearRect() { paints++; drawing = { arcs: [], rings: [] }; },
    createRadialGradient(x, y) { drawing.center = [x, y]; return { addColorStop() {} }; },
    beginPath() { path = []; }, moveTo(x, y) { path.push([x, y]); }, lineTo(x, y) { path.push([x, y]); },
    stroke() { drawing.rings.push(path); }, arc(x, y, r) { drawing.arcs.push([x, y, r]); },
    fill() {}, fillRect() {}, setTransform() {}
  };
  const hero = { getBoundingClientRect: () => ({ left: 160, top: 83 }) };
  const canvas = {
    getContext: () => context, closest: () => hero,
    getBoundingClientRect: () => ({ left: 100, top: 13, width, height })
  };
  const control = events({
    style: {}, classList: { add: n => classes.add(n), remove: n => classes.delete(n) },
    getBoundingClientRect() { return { left: 160 + parseFloat(this.style.left), top: 83 + parseFloat(this.style.top), width: parseFloat(this.style.width), height: parseFloat(this.style.height) }; },
    setPointerCapture: n => captures.add(n), hasPointerCapture: n => captures.has(n),
    releasePointerCapture(n) { captures.delete(n); control.emit('lostpointercapture', { pointerId: n }); }
  });
  const media = events({ matches: reduced });
  const document = events({ hidden: false, documentElement: { dataset: { theme: 'light' } }, getElementById: () => canvas, querySelector: () => control });
  const window = events();
  vm.runInNewContext(source, {
    document, matchMedia: () => media, devicePixelRatio: 3,
    addEventListener: window.addEventListener,
    requestAnimationFrame(fn) { callbacks.set(++id, fn); return id; },
    cancelAnimationFrame(n) { callbacks.delete(n); },
    IntersectionObserver: class { constructor(fn) { intersection = fn; } observe() {} }
  });
  return {
    canvas, control, media, document, window, captures, classes,
    get pending() { return callbacks.size; }, get paints() { return paints; }, get drawing() { return drawing; },
    step(count = 1, delta = 33) {
      for (let i = 0; i < count; i++) {
        time += delta;
        const pending = [...callbacks.values()]; callbacks.clear();
        for (const fn of pending) fn(time);
        assert.ok(callbacks.size <= 1, 'Only one animation loop may run');
      }
    },
    point(x = 0, y = 0, extra = {}) {
      const rect = control.getBoundingClientRect();
      return { clientX: rect.left + rect.width * (x + 1) / 2, clientY: rect.top + rect.height * (y + 1) / 2, pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, ...extra };
    },
    intersect(value) { intersection([{ isIntersecting: value }]); }
  };
}
const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

// Compare rendered geometry, without exposing or asserting internal rotation values.
const neutral = harness(), following = harness();
neutral.control.emit('pointermove', neutral.point());
following.control.emit('pointermove', following.point(.75, -.55));
const initial = following.drawing;
following.step(2); neutral.step(2);
const early = following.drawing;
following.step(38); neutral.step(38);
const turned = following.drawing;
assert.deepEqual(turned.center, initial.center, 'Hover must rotate around a fixed center');
assert.ok(distance(turned.arcs[0], neutral.drawing.arcs[0]) > 10, 'Latitude must visibly tilt');
assert.ok(distance(early.arcs[0], initial.arcs[0]) < distance(turned.arcs[0], initial.arcs[0]), 'Follow must ease in');
assert.ok(distance(turned.rings[0][20], neutral.drawing.rings[0][20]) > 35, 'Orbit must turn with the sphere');
assert.ok(distance(turned.arcs.at(-1), neutral.drawing.arcs.at(-1)) > 20, 'Satellite must follow the same orientation');
const a = turned.arcs[100], b = neutral.drawing.arcs[100], c = turned.arcs[300], d = neutral.drawing.arcs[300];
assert.ok(Math.hypot((a[0] - b[0]) - (c[0] - d[0]), (a[1] - b[1]) - (c[1] - d[1])) > 15, 'Particles must rotate, rather than translate together');
following.control.emit('pointerleave'); following.step(50);
assert.ok(distance(following.drawing.rings[0][20], initial.rings[0][20]) < .1, 'Leaving must return the orbit smoothly to neutral');

const touch = harness({ width: 480, height: 396 });
assert.equal(touch.canvas.width, 720, 'Retain the device pixel ratio cap');
assert.equal(touch.drawing.arcs.length, 311, 'Retain the smaller mobile particle count');
const start = touch.point(0, 0, { pointerType: 'touch' });
touch.control.emit('pointerdown', start);
assert.ok(touch.captures.has(1));
touch.control.emit('pointermove', { ...start, clientX: start.clientX + 90 });
touch.step(35);
assert.ok(distance(touch.drawing.rings[0][20], harness({ width: 480, height: 396 }).drawing.rings[0][20]) > 30, 'Touch drag must rotate');
touch.control.emit('pointerup', { ...start, pointerId: 2 });
assert.ok(touch.captures.has(1), 'A second finger must not end the first drag');
touch.control.emit('pointercancel', start);
assert.equal(touch.captures.size, 0, 'Native scrolling cancellation must release capture');
assert.equal(touch.classes.size, 0);
touch.step(50);
assert.ok(distance(touch.drawing.rings[0][20], harness({ width: 480, height: 396 }).drawing.rings[0][20]) < .1);
touch.control.emit('pointerdown', start); touch.control.emit('lostpointercapture', start);
assert.equal(touch.classes.size, 0);
touch.control.emit('pointerdown', start); touch.control.emit('pointerup', start);
assert.equal(touch.captures.size, 0);

const paused = harness(); paused.step(10); paused.intersect(false);
assert.equal(paused.pending, 0);
const beforePause = paused.drawing;
paused.step(1, 60000); paused.intersect(true); paused.step();
assert.deepEqual(paused.drawing.arcs, beforePause.arcs, 'Resume must not jump ahead by the hidden time');
paused.document.hidden = true; paused.document.emit('visibilitychange');
assert.equal(paused.pending, 0);
paused.document.hidden = false; paused.document.emit('visibilitychange');
paused.document.emit('visibilitychange'); assert.equal(paused.pending, 1);
paused.media.matches = true; paused.media.emit('change'); assert.equal(paused.pending, 0);
const quiet = harness({ reduced: true }); const paints = quiet.paints;
quiet.control.emit('pointermove', quiet.point(1, 1));
quiet.control.emit('pointerdown', quiet.point()); quiet.step(20);
assert.equal(quiet.paints, paints, 'Reduced motion must stay still during pointer interaction');
assert.equal(quiet.pending, 0); assert.equal(quiet.captures.size, 0);
quiet.media.matches = false; quiet.media.emit('change'); assert.equal(quiet.pending, 1);
console.log('Planet interaction: 3D follow, orbit/satellite, easing, touch, pause and reduced motion passed.');
