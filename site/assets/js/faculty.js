/* 师资列表：创始人 / 导师筛选 + 空分区隐藏 */
(function () {
  "use strict";
  var buttons = Array.prototype.slice.call(document.querySelectorAll("[data-filter]"));
  if (!buttons.length) return;

  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-group]"));
  var groups = Array.prototype.slice.call(document.querySelectorAll("[data-section]"));

  function apply(filter) {
    cards.forEach(function (card) {
      var show = filter === "all" || card.getAttribute("data-group") === filter;
      card.classList.toggle("is-hidden", !show);
    });
    groups.forEach(function (group) {
      var key = group.getAttribute("data-section");
      var visible = filter === "all" || key === filter;
      group.hidden = !visible;
    });
    buttons.forEach(function (btn) {
      var on = btn.getAttribute("data-filter") === filter;
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      apply(btn.getAttribute("data-filter"));
    });
  });
})();
