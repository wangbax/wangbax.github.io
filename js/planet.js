(() => {
  'use strict';
  const canvas = document.getElementById('universe');
  const context = canvas?.getContext('2d');
  if (!context) return;

  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const pointer = { x: 0, y: 0 };
  const points = [];
  const stars = [];
  let width = 0;
  let height = 0;
  let frame = 0;
  let inView = true;
  let lastPaint = 0;
  let lastTime = 0;
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

  function render(time) {
    context.clearRect(0, 0, width, height);
    const mobile = width < 700;
    const centerX = width * (mobile ? .58 : .76) + pointer.x * 12;
    const centerY = height * (mobile ? .51 : .5) + pointer.y * 10;
    const radius = Math.min(height * .32, width * .24);
    const angle = time * .000065;
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
    context.save();
    context.translate(centerX, centerY);
    context.rotate(-.42);
    for (let orbit = 0; orbit < 3; orbit++) {
      context.beginPath();
      context.ellipse(0, 0, radius * (1.27 + orbit * .12), radius * (.32 + orbit * .08), orbit * .12, 0, Math.PI * 2);
      context.strokeStyle = 'rgba(' + palette.orbit + ',' + (.22 - orbit * .025) + ')';
      context.lineWidth = .7;
      context.stroke();
    }
    context.restore();
    const projected = [];
    points.forEach((point, index) => {
      if (mobile && index % 2) return;
      const x = point.x * Math.cos(angle) + point.z * Math.sin(angle);
      const z = -point.x * Math.sin(angle) + point.z * Math.cos(angle);
      const scale = 1 + z * .12;
      const px = centerX + x * radius * scale;
      const py = centerY + (point.y * .9 + z * .13) * radius * scale;
      const alpha = .20 + (z + 1) * .31;
      projected.push({ x: px, y: py, z });
      context.beginPath();
      context.arc(px, py, point.size * (.75 + (z + 1) * .26), 0, Math.PI * 2);
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
    const satelliteX = centerX + Math.cos(angle * 1.4 + 2) * radius * 1.45;
    const satelliteY = centerY + Math.sin(angle * 1.4 + 2) * radius * .38;
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
    if (time - lastPaint > 32) {
      lastTime = time;
      lastPaint = time;
      render(time);
    }
    frame = requestAnimationFrame(tick);
  }
  function updateAnimation() {
    const animate = inView && !document.hidden && !reducedMotion.matches;
    if (animate && !frame) frame = requestAnimationFrame(tick);
    else if (!animate) {
      cancelAnimationFrame(frame);
      frame = 0;
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
    render(reducedMotion.matches ? 0 : lastTime);
  }
  canvas.closest('.hero').addEventListener('pointermove', event => {
    const rect = event.currentTarget.getBoundingClientRect();
    pointer.x = (event.clientX - rect.left) / rect.width - .5;
    pointer.y = (event.clientY - rect.top) / rect.height - .5;
  });
  new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting;
    updateAnimation();
  }).observe(canvas);
  document.addEventListener('visibilitychange', updateAnimation);
  reducedMotion.addEventListener('change', () => {
    render(0);
    updateAnimation();
  });
  addEventListener('themechange', () => {
    palette = palettes[document.documentElement.dataset.theme] || palettes.light;
    render(reducedMotion.matches ? 0 : lastTime);
  });
  addEventListener('resize', resize);
  resize();
  updateAnimation();
})();
