(() => {
  'use strict';
  const canvas = document.getElementById('universe');
  const context = canvas?.getContext('2d');
  if (!context) return;

  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const control = document.querySelector('.planet-control');
  const rotation = { yaw: 0, pitch: 0 };
  const target = { yaw: 0, pitch: 0 };
  let drag = null;
  let hovering = false;
  let spin = 0;
  const points = [];
  const stars = [];
  let width = 0;
  let height = 0;
  let frame = 0;
  let inView = true;
  let lastPaint = 0;
  let seed = 17;
  const palettes = {
    light: { star: '150,125,100', glow: ['184,148,107,.22', '211,183,145,.10', '224,205,176,0'], orbit: '160,127,92', gold: '176,139,81', dot: '139,110,85', line: '177,144,105,.18', satellite: '#a48351', shadow: '#c7a46b' },
    dark: { star: '220,187,153', glow: ['191,137,89,.12', '173,123,79,.07', '173,123,79,0'], orbit: '207,161,116', gold: '239,198,134', dot: '219,178,143', line: '209,166,121,.20', satellite: '#e9c28c', shadow: '#e3b172' }
  };
  let palette = palettes[document.documentElement.dataset.theme] || palettes.light;

  function random() {
    seed = seed * 16807 % 2147483647;
    return (seed - 1) / 2147483646;
  }
  for (let index = 0; index < 620; index++) {
    const y = 1 - index / 619 * 2;
    const radius = Math.sqrt(1 - y * y);
    const angle = index * 2.399963;
    points.push({ x: Math.cos(angle) * radius, y, z: Math.sin(angle) * radius, size: .5 + random() * 1.25 });
  }
  for (let index = 0; index < 120; index++) {
    stars.push({ x: random(), y: random(), size: random() * 1.2, alpha: .08 + random() * .35 });
  }

  function geometry() {
    const mobile = width < 700;
    return { mobile, centerX: width * (mobile ? .58 : .76), centerY: height * (mobile ? .51 : .5), radius: Math.min(height * .32, width * .24) };
  }

  function render() {
    context.clearRect(0, 0, width, height);
    const { mobile, centerX, centerY, radius } = geometry();
    const cy = Math.cos(rotation.yaw), sy = Math.sin(rotation.yaw);
    const cp = Math.cos(rotation.pitch), sp = Math.sin(rotation.pitch);
    const cr = Math.cos(rotation.yaw * .08), sr = Math.sin(rotation.yaw * .08);
    // Rotate the sphere, rings and satellite in the same 3D space.
    function orient(x, y, z) {
      const rx = x * cy + z * sy;
      const rz = -x * sy + z * cy;
      const ry = y * cp - rz * sp;
      return { x: rx * cr - ry * sr, y: rx * sr + ry * cr, z: y * sp + rz * cp };
    }
    function orbitPoint(angle, orbit) {
      const radius = 1.27 + orbit * .12;
      const tilt = (.32 + orbit * .08) / radius;
      const roll = -.42 + orbit * .12;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius * tilt;
      return orient(x * Math.cos(roll) - y * Math.sin(roll), x * Math.sin(roll) + y * Math.cos(roll), Math.sin(angle) * radius * Math.sqrt(1 - tilt * tilt));
    }
    for (const star of stars) {
      context.fillStyle = 'rgba(' + palette.star + ',' + star.alpha * .55 + ')';
      context.fillRect(star.x * width, star.y * height, star.size, star.size);
    }
    const glow = context.createRadialGradient(centerX, centerY, radius * .1, centerX, centerY, radius * 1.7);
    glow.addColorStop(0, 'rgba(' + palette.glow[0] + ')');
    glow.addColorStop(.5, 'rgba(' + palette.glow[1] + ')');
    glow.addColorStop(1, 'rgba(' + palette.glow[2] + ')');
    context.fillStyle = glow;
    context.fillRect(0, 0, width, height);
    for (let orbit = 0; orbit < 3; orbit++) {
      context.beginPath();
      for (let step = 0; step <= 80; step++) {
        const point = orbitPoint(step / 80 * Math.PI * 2, orbit);
        const x = centerX + point.x * radius;
        const y = centerY + point.y * radius;
        if (step === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      }
      context.strokeStyle = 'rgba(' + palette.orbit + ',' + (.22 - orbit * .025) + ')';
      context.lineWidth = .7;
      context.stroke();
    }
    const projected = [];
    const cosSpin = Math.cos(spin), sinSpin = Math.sin(spin);
    points.forEach((point, index) => {
      if (mobile && index % 2) return;
      const x = point.x * cosSpin + point.z * sinSpin;
      const z = -point.x * sinSpin + point.z * cosSpin;
      const rotated = orient(x, point.y * .9 + z * .13, z);
      const scale = 1 + rotated.z * .12;
      const px = centerX + rotated.x * radius * scale;
      const py = centerY + rotated.y * radius * scale;
      const alpha = .20 + (rotated.z + 1) * .31;
      projected.push({ x: px, y: py, z: rotated.z });
      context.beginPath();
      context.arc(px, py, point.size * (.75 + (rotated.z + 1) * .26), 0, Math.PI * 2);
      context.fillStyle = 'rgba(' + (index % 19 === 0 ? palette.gold : palette.dot) + ',' + alpha + ')';
      context.fill();
    });
    context.lineWidth = .45;
    for (let index = 0; index < projected.length; index += 4) {
      const a = projected[index];
      const b = projected[(index + 7) % projected.length];
      if (Math.hypot(a.x - b.x, a.y - b.y) < radius * .27 && a.z > -.2 && b.z > -.2) {
        context.strokeStyle = 'rgba(' + palette.line + ')';
        context.beginPath();
        context.moveTo(a.x, a.y);
        context.lineTo(b.x, b.y);
        context.stroke();
      }
    }
    const satellite = orbitPoint(spin * 1.4 + 2, 1);
    const satelliteX = centerX + satellite.x * radius;
    const satelliteY = centerY + satellite.y * radius;
    context.beginPath();
    context.arc(satelliteX, satelliteY, 3, 0, Math.PI * 2);
    context.shadowBlur = 12;
    context.shadowColor = palette.shadow;
    context.fillStyle = palette.satellite;
    context.fill();
    context.shadowBlur = 0;
  }

  function tick(time) {
    frame = 0;
    if (!inView || document.hidden || reducedMotion.matches) return;
    if (time - lastPaint >= 32) {
      const delta = lastPaint ? Math.min(time - lastPaint, 64) : 0;
      lastPaint = time;
      const ease = 1 - Math.exp(-delta / 150);
      rotation.yaw += (target.yaw - rotation.yaw) * ease;
      rotation.pitch += (target.pitch - rotation.pitch) * ease;
      spin = (spin + delta * .000065 * (hovering || drag ? .2 : 1)) % (Math.PI * 2);
      render();
    }
    frame = requestAnimationFrame(tick);
  }
  function updateAnimation() {
    const animate = inView && !document.hidden && !reducedMotion.matches;
    if (animate && !frame) frame = requestAnimationFrame(tick);
    else if (!animate) {
      cancelAnimationFrame(frame);
      frame = 0;
      lastPaint = 0;
      resetInteraction();
    }
  }
  function resize() {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(devicePixelRatio || 1, 1.5);
    width = rect.width;
    height = rect.height;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    if (control) {
      const hero = canvas.closest('.hero').getBoundingClientRect();
      const { centerX, centerY, radius } = geometry();
      const size = radius * 2.2;
      Object.assign(control.style, { left: rect.left - hero.left + centerX - size / 2 + 'px', top: rect.top - hero.top + centerY - size / 2 + 'px', width: size + 'px', height: size + 'px' });
    }
    render();
  }
  const clamp = (value, limit) => Math.max(-limit, Math.min(limit, value));
  function follow(event) {
    const rect = control.getBoundingClientRect();
    target.yaw = clamp((event.clientX - rect.left - rect.width / 2) / (rect.width / 2), 1) * 1.05;
    target.pitch = -clamp((event.clientY - rect.top - rect.height / 2) / (rect.height / 2), 1) * .65;
  }
  function resetInteraction() {
    const pointerId = drag?.id;
    drag = null;
    hovering = false;
    target.yaw = target.pitch = 0;
    control?.classList.remove('is-dragging');
    if (pointerId !== undefined && control.hasPointerCapture(pointerId)) control.releasePointerCapture(pointerId);
  }
  if (control) {
    control.addEventListener('pointermove', event => {
      if (reducedMotion.matches) return;
      if (drag) {
        if (event.pointerId !== drag.id) return;
        const { radius } = geometry();
        target.yaw = clamp(drag.yaw + (event.clientX - drag.x) / radius * 1.5, 2.4);
        target.pitch = clamp(drag.pitch - (event.clientY - drag.y) / radius * .8, .9);
      } else if (event.pointerType !== 'touch') {
        hovering = true;
        follow(event);
      }
    });
    control.addEventListener('pointerdown', event => {
      if (reducedMotion.matches || drag || !event.isPrimary || event.button !== 0) return;
      drag = { id: event.pointerId, x: event.clientX, y: event.clientY, yaw: rotation.yaw, pitch: rotation.pitch };
      control.setPointerCapture(event.pointerId);
      control.classList.add('is-dragging');
    });
    control.addEventListener('pointerleave', () => { if (!drag) resetInteraction(); });
    control.addEventListener('pointerup', event => {
      if (event.pointerId !== drag?.id) return;
      resetInteraction();
      const rect = control.getBoundingClientRect();
      const x = (event.clientX - rect.left - rect.width / 2) / (rect.width / 2);
      const y = (event.clientY - rect.top - rect.height / 2) / (rect.height / 2);
      if (event.pointerType !== 'touch' && x * x + y * y <= 1) { hovering = true; follow(event); }
    });
    control.addEventListener('pointercancel', event => { if (event.pointerId === drag?.id) resetInteraction(); });
    control.addEventListener('lostpointercapture', event => { if (event.pointerId === drag?.id) resetInteraction(); });
  }
  new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting;
    updateAnimation();
  }).observe(canvas);
  document.addEventListener('visibilitychange', updateAnimation);
  reducedMotion.addEventListener('change', () => {
    updateAnimation();
    rotation.yaw = rotation.pitch = 0;
    render();
  });
  addEventListener('themechange', () => {
    palette = palettes[document.documentElement.dataset.theme] || palettes.light;
    render();
  });
  addEventListener('resize', resize);
  resize();
  updateAnimation();
})();
