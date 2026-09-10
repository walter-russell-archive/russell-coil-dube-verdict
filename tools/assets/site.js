// Theme. Light is the default; a reader can switch to dark, and the choice sticks.
(function () {
  "use strict";
  var button = document.querySelector("[data-theme-toggle]");
  if (!button) return;
  var root = document.documentElement;

  function paint() {
    var dark = root.dataset.theme === "dark";
    var label = dark ? "Switch to the light theme" : "Switch to the dark theme";
    button.setAttribute("aria-pressed", dark ? "true" : "false");
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
  }

  button.addEventListener("click", function () {
    var dark = root.dataset.theme !== "dark";
    root.dataset.theme = dark ? "dark" : "light";
    try {
      localStorage.setItem("theme", root.dataset.theme);
    } catch (e) {
      /* private mode: the choice lasts for this page only */
    }
    paint();
  });

  paint();
})();

// Scan lightbox. Click a page image to see it larger; Esc or a click closes it.
(function () {
  "use strict";
  var box = document.getElementById("lightbox");
  if (!box) return;
  var img = box.querySelector("img");
  var cap = box.querySelector(".lb-caption");

  function open(src, text) {
    img.src = src;
    cap.textContent = text || "";
    box.classList.add("open");
  }

  function close() {
    box.classList.remove("open");
    img.removeAttribute("src");
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    if (box.classList.contains("open")) {
      close();
      return;
    }
    if (target instanceof HTMLImageElement && target.closest(".scan-frame")) {
      var figure = target.closest("figure");
      var caption = figure ? figure.querySelector("figcaption") : null;
      open(target.currentSrc || target.src, caption ? caption.textContent.trim() : target.alt);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") close();
  });
})();
