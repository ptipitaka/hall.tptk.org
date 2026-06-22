/** Parallax scroll background layers (WebPage scroll_bg_*). */
export function initScrollBackground() {
  var container = document.getElementById("scroll-bg");
  if (!container) {
    return;
  }

  var layers = container.querySelectorAll(".scroll-bg__layer");
  if (!layers.length) {
    return;
  }

  var maxOpacity = parseFloat(container.dataset.maxOpacity || "0.2");
  if (Number.isNaN(maxOpacity)) {
    maxOpacity = 0.2;
  }

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    layers[0].style.opacity = String(maxOpacity);
    return;
  }

  function pageHeight() {
    return Math.max(
      document.documentElement.scrollHeight,
      document.body.scrollHeight
    );
  }

  function scrollOpacities(scrollY, height, count) {
    if (count === 1) {
      return [maxOpacity];
    }

    var segment = height / count;
    if (segment <= 0) {
      var fallback = new Array(count).fill(0);
      fallback[0] = maxOpacity;
      return fallback;
    }

    var t = scrollY / segment;
    var opacities = new Array(count).fill(0);

    if (t <= 0) {
      opacities[0] = maxOpacity;
      return opacities;
    }

    if (t >= count - 1) {
      opacities[count - 1] = maxOpacity;
      return opacities;
    }

    var index = Math.floor(t);
    var blend = t - index;
    opacities[index] = (1 - blend) * maxOpacity;
    opacities[index + 1] = blend * maxOpacity;
    return opacities;
  }

  function update() {
    var opacities = scrollOpacities(
      window.scrollY || window.pageYOffset || 0,
      pageHeight(),
      layers.length
    );

    layers.forEach(function (layer, index) {
      layer.style.opacity = String(opacities[index] || 0);
    });
  }

  var ticking = false;

  function onScroll() {
    if (ticking) {
      return;
    }
    ticking = true;
    requestAnimationFrame(function () {
      update();
      ticking = false;
    });
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  update();
}
