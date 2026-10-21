/* ============================================================
   遥触灵境 官网 · 交互脚本
   1 滚动进度  2 导航状态  3 进场动画  4 数字滚动
   5 移动端菜单  6 主视觉视差  7 滚动高亮
   全部原生实现，无第三方依赖。
   ============================================================ */
(function () {
  "use strict";

  document.documentElement.classList.add("js");

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 1. 滚动进度 ---------- */
  var bar = document.getElementById("progress");
  function syncProgress() {
    var max = document.documentElement.scrollHeight - window.innerHeight;
    if (bar) bar.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + "%";
  }

  /* ---------- 2. 导航状态 ---------- */
  var nav = document.getElementById("nav");
  function syncNav() {
    if (nav) nav.classList.toggle("is-scrolled", window.scrollY > 24);
  }

  window.addEventListener("scroll", function () {
    syncProgress();
    syncNav();
  }, { passive: true });
  syncProgress();
  syncNav();

  /* ---------- 3. 进场动画 ---------- */
  var targets = document.querySelectorAll("[data-reveal]");
  if (reduce || !("IntersectionObserver" in window)) {
    targets.forEach(function (el) { el.classList.add("is-in"); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-in");
        io.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
    targets.forEach(function (el) { io.observe(el); });
  }

  /* ---------- 4. 数字滚动 ---------- */
  function countUp(el) {
    var target = parseInt(el.getAttribute("data-count"), 10) || 0;
    if (reduce) { el.textContent = target; return; }
    var start = performance.now();
    var dur = 1250;
    function tick(now) {
      var p = Math.min((now - start) / dur, 1);
      var e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(e * target);
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  var metrics = document.querySelector(".metrics");
  if (metrics) {
    if (!("IntersectionObserver" in window)) {
      metrics.querySelectorAll("[data-count]").forEach(countUp);
    } else {
      var numIO = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.querySelectorAll("[data-count]").forEach(countUp);
          numIO.unobserve(entry.target);
        });
      }, { threshold: 0.4 });
      numIO.observe(metrics);
    }
  }

  /* ---------- 5. 移动端菜单 ---------- */
  var sheet = document.getElementById("sheet");
  var toggle = document.getElementById("navToggle");
  var close = document.getElementById("sheetClose");

  function setSheet(open) {
    if (!sheet || !toggle) return;
    sheet.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.style.overflow = open ? "hidden" : "";
    if (open && close) close.focus();
  }

  if (toggle) toggle.addEventListener("click", function () { setSheet(true); });
  if (close) close.addEventListener("click", function () { setSheet(false); });
  if (sheet) {
    sheet.addEventListener("click", function (e) {
      if (e.target === sheet || e.target.closest("a")) setSheet(false);
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") setSheet(false);
  });

  /* ---------- 6. 主视觉视差 ---------- */
  var orbit = document.querySelector(".orbit");
  var fine = window.matchMedia("(pointer: fine)").matches;
  if (orbit && fine && !reduce) {
    var tx = 0, ty = 0, cx = 0, cy = 0, raf = null;
    var loop = function () {
      cx += (tx - cx) * 0.08;
      cy += (ty - cy) * 0.08;
      orbit.style.transform = "translate3d(" + cx.toFixed(2) + "px," + cy.toFixed(2) + "px,0)";
      if (Math.abs(tx - cx) > 0.1 || Math.abs(ty - cy) > 0.1) {
        raf = requestAnimationFrame(loop);
      } else {
        raf = null;
      }
    };
    window.addEventListener("mousemove", function (e) {
      tx = (e.clientX / window.innerWidth - 0.5) * 26;
      ty = (e.clientY / window.innerHeight - 0.5) * 20;
      if (!raf) raf = requestAnimationFrame(loop);
    }, { passive: true });
  }

  /* ---------- 7. 滚动高亮导航 ---------- */
  var links = Array.prototype.slice.call(document.querySelectorAll(".nav__links a")).filter(function (a) {
    return (a.getAttribute("href") || "").charAt(0) === "#";
  });
  var sections = links.map(function (a) {
    return document.querySelector(a.getAttribute("href"));
  }).filter(Boolean);
  if (sections.length && "IntersectionObserver" in window) {
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (a) {
          var on = a.getAttribute("href") === "#" + entry.target.id;
          a.style.color = on ? "var(--ink)" : "";
          if (on) a.setAttribute("aria-current", "true");
          else a.removeAttribute("aria-current");
        });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach(function (s) { spy.observe(s); });
  }

  /* ---------- 8. 图片加载淡入 ---------- */
  document.querySelectorAll("img[loading='lazy']").forEach(function (img) {
    if (img.complete) return;
    img.style.opacity = "0";
    img.style.transition = "opacity .6s ease";
    img.addEventListener("load", function () { img.style.opacity = "1"; }, { once: true });
    img.addEventListener("error", function () { img.style.opacity = "1"; }, { once: true });
  });
})();
