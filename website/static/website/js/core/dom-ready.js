/** Run callback when DOM is ready. */
export function onReady(callback) {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", callback);
    return;
  }
  callback();
}

/** Read a numeric CSS custom property from :root (fallback in px/ms). */
export function cssMs(name, fallback) {
  var raw = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  if (!raw) {
    return fallback;
  }
  if (raw.endsWith("ms")) {
    return parseFloat(raw);
  }
  if (raw.endsWith("s")) {
    return parseFloat(raw) * 1000;
  }
  return parseFloat(raw) || fallback;
}
