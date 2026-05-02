/* ============================================================
   InterviewIQ — Global JavaScript Utilities
   ============================================================ */

/* ── Animated Number Counting ── */
function countUp(el, target, duration) {
  duration = duration || 1200;
  var start = 0, startTime = null;
  function step(ts) {
    if (!startTime) startTime = ts;
    var p = Math.min((ts - startTime) / duration, 1);
    var eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.floor(eased * target);
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = target;
  }
  requestAnimationFrame(step);
}

/* ── Intersection Observer for Fade-in ── */
document.addEventListener('DOMContentLoaded', function() {
  // Count-up elements
  document.querySelectorAll('[data-target]').forEach(function(el) {
    var t = parseInt(el.getAttribute('data-target'));
    if (!isNaN(t)) countUp(el, t);
  });

  // Animated stat bars
  document.querySelectorAll('[data-w]').forEach(function(el) {
    setTimeout(function() { el.style.width = el.getAttribute('data-w'); }, 400);
  });

  // Fade-in on scroll
  var obs = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.observe-fade').forEach(function(el) {
    obs.observe(el);
  });
});

/* ── Button Ripple ── */
document.addEventListener('click', function(e) {
  var btn = e.target.closest('.ripple, .btn-primary-glow, .btn-start, .btn-submit, .btn-signin, .sub-btn');
  if (!btn) return;
  var r = document.createElement('span');
  r.className = 'ripple-effect';
  var rect = btn.getBoundingClientRect();
  var sz = Math.max(rect.width, rect.height);
  r.style.width = r.style.height = sz + 'px';
  r.style.left = (e.clientX - rect.left - sz/2) + 'px';
  r.style.top = (e.clientY - rect.top - sz/2) + 'px';
  r.style.position = 'absolute';
  r.style.borderRadius = '50%';
  r.style.background = 'rgba(255,255,255,.3)';
  r.style.transform = 'scale(0)';
  r.style.animation = 'rippleAnim .6s linear';
  r.style.pointerEvents = 'none';
  btn.style.position = btn.style.position || 'relative';
  btn.style.overflow = 'hidden';
  btn.appendChild(r);
  setTimeout(function() { r.remove(); }, 600);
});
