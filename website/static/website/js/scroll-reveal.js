(function () {
  "use strict";

  var observer = null;
  var observed = typeof WeakSet !== "undefined" ? new WeakSet() : null;

  var HERO_STAGGER_MS = 100;
  var HERO_START_MS = 150;
  var GOAL_STAGGER_MS = 120;

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function showReveal(el) {
    if (!el || el.classList.contains("is-visible")) {
      return;
    }
    if (prefersReducedMotion()) {
      el.classList.add("is-visible");
      return;
    }
    void el.offsetHeight;
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        el.classList.add("is-visible");
      });
    });
  }

  function markReveal(el, variant, delayMs) {
    if (!el || el.classList.contains("is-visible")) {
      return;
    }
    if (!el.classList.contains("home-reveal")) {
      el.classList.add("home-reveal", "home-reveal--" + variant);
    }
    if (delayMs) {
      el.style.setProperty("--reveal-delay", delayMs + "ms");
    }
    if (prefersReducedMotion()) {
      el.classList.add("is-visible");
      return;
    }
    if (observer && (!observed || !observed.has(el))) {
      if (observed) {
        observed.add(el);
      }
      observer.observe(el);
    }
  }

  function animateHero(root) {
    var heroSelectors = [
      ".home-fullname",
      ".home-title",
      ".home-title-divider",
      ".home-acronym",
    ];
    heroSelectors.forEach(function (selector, index) {
      var el = root.querySelector(selector);
      if (!el) {
        return;
      }
      if (!el.classList.contains("home-reveal")) {
        el.classList.add("home-reveal", "home-reveal--up");
      }
      if (prefersReducedMotion()) {
        el.classList.add("is-visible");
        return;
      }
      window.setTimeout(function () {
        showReveal(el);
      }, HERO_START_MS + index * HERO_STAGGER_MS);
    });
  }

  function setupReveals(root) {
    animateHero(root);

    root.querySelectorAll(".home-section").forEach(function (section) {
      var isGoals = section.classList.contains("home-section--goals");
      var isTimeline = section.classList.contains(
        "home-section--corpus-timeline"
      );
      var title = section.querySelector(".home-section-title");

      if (title) {
        markReveal(title, "up", 0);
      }

      if (isGoals) {
        document.querySelectorAll(".home-goals .home-goal-card").forEach(
          function (card, index) {
            markReveal(card, "up", index * GOAL_STAGGER_MS);
          }
        );
        return;
      }

      if (isTimeline) {
        section
          .querySelectorAll(".home-corpus-timeline-entry")
          .forEach(function (entry, index) {
            var variant = entry.classList.contains(
              "home-corpus-timeline-entry--left"
            )
              ? "left"
              : "right";
            markReveal(entry, variant, index * 100);
          });
        return;
      }

      section
        .querySelectorAll(".home-principle, .home-cases-fold")
        .forEach(function (el, index) {
          markReveal(el, "up", 120 + index * 80);
        });
    });
  }

  function initObserver() {
    if (prefersReducedMotion()) {
      return;
    }
    observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            showReveal(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      {
        root: null,
        rootMargin: "0px 0px -8% 0px",
        threshold: 0.12,
      }
    );
  }

  function init() {
    if (!document.body.classList.contains("sacred-home")) {
      return;
    }
    var root = document.getElementById("content");
    if (!root || !root.querySelector(".home-hero")) {
      return;
    }

    initObserver();
    setupReveals(root);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
