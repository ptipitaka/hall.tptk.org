/** Respect user motion preferences (WCAG). */
export function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Double rAF ensures CSS transitions run after class changes. */
export function revealElement(el) {
  if (!el || el.classList.contains("is-visible")) {
    return;
  }
  if (prefersReducedMotion()) {
    el.classList.add("is-visible");
    return;
  }
  void el.offsetHeight;
  requestAnimationFrame(function () {
    requestAnimationFrame(function () {
      el.classList.add("is-visible");
    });
  });
}
