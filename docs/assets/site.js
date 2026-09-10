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
