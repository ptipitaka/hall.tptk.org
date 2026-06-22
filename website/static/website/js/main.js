import { onReady } from "./core/dom-ready.js";
import { initScrollBackground } from "./components/scroll-background.js";
import { initScrollReveal } from "./components/scroll-reveal.js";
import { initHomeCasesFold } from "./components/home-cases-fold.js";

onReady(function () {
  initScrollBackground();
  initScrollReveal();
  initHomeCasesFold();
});
