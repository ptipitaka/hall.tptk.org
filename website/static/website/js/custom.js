(function () {
  function toggleHomeCases(toggle) {
    var fold = toggle.closest(".home-cases-fold");
    if (!fold) {
      return;
    }
    var open = !fold.classList.contains("is-open");
    fold.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  document.addEventListener("click", function (event) {
    var toggle = event.target.closest(".home-cases-toggle");
    if (toggle) {
      toggleHomeCases(toggle);
    }
  });

  document.addEventListener("keydown", function (event) {
    var toggle = event.target.closest(".home-cases-toggle");
    if (!toggle) {
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggleHomeCases(toggle);
    }
  });
})();
