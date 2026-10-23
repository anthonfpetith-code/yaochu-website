/* ============================================================
   Demo 库交互
   1 只在卡片进入视口时加载视频元数据（首屏请求从 14 降到 3-6）
   2 点击打开播放弹层，ESC / 点空白关闭
   ============================================================ */
(function () {
  "use strict";

  var cards = Array.prototype.slice.call(document.querySelectorAll(".vcard"));
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- 1. 视口内再加载 ---------- */
  function prime(video) {
    if (!video || video.dataset.ready === "1") return;
    var src = video.getAttribute("data-src");
    if (!src) return;
    video.dataset.ready = "1";

    // 只有真正解出画面才淡入，避免留下黑块
    video.addEventListener("loadeddata", function () {
      video.classList.add("is-ready");
    }, { once: true });
    video.addEventListener("error", function () {
      video.classList.remove("is-ready");
    }, { once: true });

    video.src = src;
    video.addEventListener("loadedmetadata", function () {
      // 取 15% 处的一帧：跳过片头黑场与倒计时，避免缩略图全黑
      if (video.duration > 1.2) {
        video.currentTime = Math.min(Math.max(video.duration * 0.15, 1), 6);
      }
    }, { once: true });
    video.load();
  }

  var queue = [];
  var pumping = false;

  function pump() {
    if (!queue.length) { pumping = false; return; }
    prime(queue.shift());
    setTimeout(pump, 140);
  }

  function enqueue(video) {
    queue.push(video);
    if (!pumping) { pumping = true; setTimeout(pump, 0); }
  }

  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        enqueue(entry.target.querySelector("video"));
        io.unobserve(entry.target);
      });
    }, { rootMargin: "160px 0px" });
    cards.forEach(function (card) { io.observe(card); });
  } else {
    cards.forEach(function (card) { prime(card.querySelector("video")); });
  }

  /* ---------- 2. 播放弹层 ---------- */
  var modal = document.getElementById("modal");
  var player = document.getElementById("player");
  var mTitle = document.getElementById("modalTitle");
  var mGrade = document.getElementById("modalGrade");
  var mDl = document.getElementById("modalDownload");
  var mClose = document.getElementById("modalClose");
  if (!modal || !player) return;

  var lastFocus = null;

  function open(card) {
    var url = card.getAttribute("data-url");
    var title = card.getAttribute("data-title") || "Demo";
    var grade = card.getAttribute("data-grade") || "A";

    lastFocus = card;
    player.src = url;
    mTitle.textContent = title;
    mGrade.textContent = grade;
    mGrade.className = "modal__grade " + grade.toLowerCase();
    mDl.href = url;
    mDl.setAttribute("download", title + ".mp4");

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    var p = player.play();
    if (p && p.catch) p.catch(function () {});
    mClose.focus();
  }

  function close() {
    player.pause();
    player.removeAttribute("src");
    player.load();
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    if (lastFocus) lastFocus.focus();
  }

  cards.forEach(function (card) {
    card.addEventListener("click", function () { open(card); });
    card.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open(card);
      }
    });
  });

  mClose.addEventListener("click", close);
  modal.addEventListener("click", function (e) {
    if (e.target === modal) close();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal.classList.contains("is-open")) close();
  });
})();
