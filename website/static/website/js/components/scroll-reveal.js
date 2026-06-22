import { cssMs } from "../core/dom-ready.js";
import { prefersReducedMotion, revealElement } from "../core/motion.js";

var observer = null;
var observed = typeof WeakSet !== "undefined" ? new WeakSet() : null;

function heroStartMs() {
  return cssMs("--hall-reveal-hero-start", 150);
}

function heroStaggerMs() {
  return cssMs("--hall-reveal-hero-stagger", 100);
}

function goalStaggerMs() {
  return cssMs("--hall-reveal-goal-stagger", 120);
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
  var selectors = [
    ".home-fullname",
    ".home-title",
    ".home-title-divider",
    ".home-acronym",
  ];

  selectors.forEach(function (selector, index) {
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
      revealElement(el);
    }, heroStartMs() + index * heroStaggerMs());
  });
}

function setupGoalCards(root) {
  var title = root.querySelector(".home-section--goals .home-section-title");
  var grid = root.querySelector(".home-goals");
  var cards = root.querySelectorAll(".home-goals .home-goal-card");
  var stagger = goalStaggerMs();

  if (title) {
    markReveal(title, "up", 0);
  }

  cards.forEach(function (card, index) {
    if (!card.classList.contains("home-reveal")) {
      card.classList.add("home-reveal", "home-reveal--up");
    }
    card.style.setProperty("--reveal-delay", index * stagger + "ms");
  });

  if (prefersReducedMotion()) {
    cards.forEach(function (card) {
      card.classList.add("is-visible");
    });
    return;
  }

  if (!observer || !grid) {
    return;
  }

  if (!observed || !observed.has(grid)) {
    if (observed) {
      observed.add(grid);
    }
    observer.observe(grid);
  }
}

function revealGoalCards(grid) {
  grid.querySelectorAll(".home-goal-card").forEach(function (card) {
    revealElement(card);
  });
}

function setupSections(root) {
  root
    .querySelectorAll(".home-section:not(.home-section--goals)")
    .forEach(function (section) {
      var isTimeline = section.classList.contains(
        "home-section--corpus-timeline"
      );
      var title = section.querySelector(".home-section-title");

      if (title) {
        markReveal(title, "up", 0);
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
        if (!entry.isIntersecting) {
          return;
        }
        if (entry.target.classList.contains("home-goals")) {
          revealGoalCards(entry.target);
        } else {
          revealElement(entry.target);
        }
        observer.unobserve(entry.target);
      });
    },
    {
      root: null,
      rootMargin: "0px 0px -8% 0px",
      threshold: 0.12,
    }
  );
}

/** Scroll-triggered fade-up on SACRED homepage. */
export function initScrollReveal() {
  if (!document.body.classList.contains("sacred-home")) {
    return;
  }

  var root = document.getElementById("content");
  if (!root || !root.querySelector(".home-hero")) {
    return;
  }

  initObserver();
  animateHero(root);
  setupGoalCards(root);
  setupSections(root);
}
