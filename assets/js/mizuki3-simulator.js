/* MIZ OKI 3.5 — Decision Control Simulator + 90-second walkthrough player.
 *
 * Deterministic by construction: the same scenario, dials, and policy toggles
 * produce the same run, the same figures, and the same trace id every time.
 * No randomness anywhere. Vanilla JS, no dependencies, honors
 * prefers-reduced-motion. Figures are an illustrative model — not customer
 * data and not a live API: ACT lines are explicitly labeled simulated.
 *
 * Vocabulary contract (mandatory translation key): copy in this file speaks
 * plain English only — Structured Signal Evidence, Cross-Stack Root Cause
 * Engine, Channel Intelligence Modules, the 7-Stage Decision Control System,
 * and Compounding ROI Memory.
 */
(function () {
  "use strict";

  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function $(id) { return document.getElementById(id); }
  function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
  function round50(v) { return Math.round(v / 50) * 50; }
  function ceil50(v) { return Math.ceil(v / 50) * 50; }
  function usd(v) { return "$" + Math.round(v).toLocaleString("en-US"); }
  function x(v) { return (Math.round(v * 100) / 100).toFixed(2) + "×"; }

  /* FNV-1a — deterministic trace ids from run inputs. */
  function traceId(str) {
    var h = 0x811c9dc5;
    for (var i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = (h * 0x01000193) >>> 0;
    }
    return ("00000000" + h.toString(16)).slice(-8);
  }

  /* ================= Decision Control Simulator ================= */

  var MODEL = {
    baseRoas: 2.9,        // healthy blended return per ad dollar
    healthyLatency: 1.2,  // seconds — money page at full speed
    decayPerSecond: 0.14, // relative conversion loss per second above healthy
    roasFloor: 2.2,       // Target ROAS Floor policy
    autoShiftCap: 5000,   // Max Auto-Shift policy (per action)
    skuShare: 0.35,       // budget share promoting the hero SKU
    sellRate: 90,         // hero SKU units sold per day at current spend
    driftInflation: 0.28, // reported-vs-verified inflation after the tag change
    reportedRoasDrift: 3.4,
    scaleUpFraction: 0.25 // the naive scale-up queued on inflated numbers
  };

  function readInputs() {
    var scn = document.querySelector('input[name="mzkScenario"]:checked');
    return {
      scenario: scn ? scn.value : "latency",
      latency: parseFloat($("mzkLat").value),
      inventory: parseInt($("mzkInv").value, 10),
      budget: parseInt($("mzkBud").value, 10),
      floorOn: $("mzkFloor").checked,
      capOn: $("mzkCap").checked
    };
  }

  /* Pure model: inputs -> full decision (cause, plan, gates, outcome). */
  function evaluate(inp) {
    var d = {
      scenario: inp.scenario,
      riskPerDay: 0,
      truthLabel: "Effective ROAS",
      truthText: "—",
      truthClass: "",
      actionText: "—",
      shift: 0,
      projRoas: MODEL.baseRoas,
      veto: false,
      vetoReason: "",
      escalated: false,
      noAction: false,
      prevented: 0,
      roasKept: "",
      roasKeptHeld: false,
      cause: "",
      sense: [],
      planLines: [],
      dispatch: []
    };
    var maxShift = inp.capOn ? Math.min(MODEL.autoShiftCap, inp.budget) : inp.budget;

    if (inp.scenario === "latency") {
      var over = Math.max(0, inp.latency - MODEL.healthyLatency);
      var cvrMult = Math.max(0.25, 1 - MODEL.decayPerSecond * over);
      var trueRoas = MODEL.baseRoas * cvrMult;
      d.riskPerDay = inp.budget * (1 - cvrMult);
      d.truthText = x(trueRoas);
      d.truthClass = trueRoas < MODEL.roasFloor ? "bad" : (over > 0.8 ? "warn" : "ok");
      d.cause = "landing-page latency " + inp.latency.toFixed(1) +
        "s vs " + MODEL.healthyLatency.toFixed(1) + "s healthy — conversion decay " +
        Math.round((1 - cvrMult) * 100) + "%";
      d.sense = [
        "evidence in ← web-vitals: money page p75 " + inp.latency.toFixed(1) + "s (deploy 09:14)",
        "evidence in ← ads: spend pacing 100% · CVR −" + Math.round((1 - cvrMult) * 100) + "% vs 7-day norm",
        "evidence in ← analytics: checkout starts down on paid sessions only"
      ];
      var desired = round50(d.riskPerDay * 0.8);
      var shift = Math.min(desired, maxShift);
      var proj = function (s) {
        return trueRoas + (s / inp.budget) * (MODEL.baseRoas - trueRoas) * 0.9;
      };
      d.projRoas = proj(shift);
      if (inp.floorOn && d.projRoas < MODEL.roasFloor) {
        var frac = (MODEL.roasFloor - trueRoas) / ((MODEL.baseRoas - trueRoas) * 0.9);
        var needed = ceil50(frac * inp.budget);
        if (needed <= maxShift) {
          shift = needed;
          d.projRoas = proj(shift);
          d.escalated = true;
        } else {
          d.veto = true;
          d.vetoReason = "projected ROAS " + x(proj(maxShift)) +
            " below the " + x(MODEL.roasFloor) + " floor at the maximum allowed shift";
        }
      }
      d.shift = shift;
      d.actionText = d.veto
        ? "Hold spend · route to human"
        : "Shift " + usd(shift) + " → brand & retention";
      d.planLines = [
        "plan: shift " + usd(shift) + "/day away from the degraded landing path",
        "plan: pause prospecting scale-ups until p75 latency ≤ " + MODEL.healthyLatency.toFixed(1) + "s",
        "plan: open incident with the deploy evidence attached"
      ];
      d.dispatch = [
        "dispatch → googleads.budgets.patch cmp-1189 −" + usd(shift),
        "dispatch → meta.adsets.update as-2231 +" + usd(shift),
        "dispatch → incident.open web-perf · evidence attached"
      ];
      d.prevented = d.veto ? d.riskPerDay : Math.min(d.riskPerDay, shift);
      d.roasKept = d.veto ? x(MODEL.roasFloor) + " floor held" : x(d.projRoas);
      d.roasKeptHeld = d.veto;

    } else if (inp.scenario === "inventory") {
      var skuSpend = inp.budget * MODEL.skuShare;
      var coverDays = inp.inventory / MODEL.sellRate;
      var oosFrac = Math.max(0, 1 - Math.min(inp.inventory, MODEL.sellRate) / MODEL.sellRate);
      var blended = MODEL.baseRoas * (1 - MODEL.skuShare * oosFrac);
      d.truthLabel = "Days of stock cover";
      d.truthText = coverDays.toFixed(1) + " days";
      d.truthClass = coverDays < 1 ? "bad" : (coverDays < 3 ? "warn" : "ok");
      d.sense = [
        "evidence in ← commerce: hero SKU inventory " + inp.inventory + " units · sell-through " + MODEL.sellRate + "/day",
        "evidence in ← ads: hero-SKU ad sets pacing " + usd(skuSpend) + "/day",
        "evidence in ← web: product page traffic steady · add-to-cart intact while stocked"
      ];
      if (coverDays >= 3) {
        d.noAction = true;
        d.riskPerDay = 0;
        d.cause = "stock cover " + coverDays.toFixed(1) + " days — no starvation risk inside the planning window";
        d.actionText = "No action — monitors armed";
        d.planLines = [
          "plan: no action earns execution — stock cover is healthy",
          "plan: keep the inventory-vs-delivery monitor armed at 3-day cover"
        ];
        d.prevented = 0;
        d.roasKept = x(MODEL.baseRoas) + " steady";
        d.projRoas = MODEL.baseRoas;
      } else {
        var desired2, wasted;
        if (coverDays < 1) {
          wasted = skuSpend * oosFrac;
          d.riskPerDay = wasted;
          d.cause = "hero SKU runs dry today — " + Math.round(oosFrac * 100) +
            "% of its ad spend buys clicks a dead product page cannot convert";
          desired2 = round50(skuSpend);
          d.planLines = [
            "plan: pause hero-SKU ad sets · reroute " + usd(Math.min(desired2, maxShift)) + " to in-stock winners",
            "plan: swap catalog placements to alternates with cover ≥ 5 days",
            "plan: restock trigger → resume paused sets automatically"
          ];
        } else {
          wasted = 0;
          d.riskPerDay = skuSpend * (1 - coverDays / 3) * 0.5;
          d.cause = "hero SKU runs dry in " + coverDays.toFixed(1) +
            " days at current sell-through — starvation inside the planning window";
          desired2 = round50(skuSpend * 0.4);
          d.planLines = [
            "plan: taper hero-SKU spend " + usd(Math.min(desired2, maxShift)) + " toward in-stock alternates",
            "plan: hold remaining spend while cover ≥ 1 day · alert merchandising"
          ];
        }
        var shift2 = Math.min(desired2, maxShift);
        d.shift = shift2;
        d.projRoas = blended + (shift2 / inp.budget) * (MODEL.baseRoas - blended) * 0.9;
        if (inp.floorOn && d.projRoas < MODEL.roasFloor) {
          d.veto = true;
          d.vetoReason = "projected ROAS " + x(d.projRoas) + " below the " +
            x(MODEL.roasFloor) + " floor — reroute cannot cover the stock-out";
          d.actionText = "Hold spend · route to human";
          d.prevented = d.riskPerDay;
          d.roasKept = x(MODEL.roasFloor) + " floor held";
          d.roasKeptHeld = true;
        } else {
          d.actionText = (coverDays < 1 ? "Pause hero-SKU sets · reroute " : "Taper ")
            + usd(shift2) + " → in-stock SKUs";
          d.prevented = coverDays < 1 ? wasted : d.riskPerDay;
          d.roasKept = x(d.projRoas);
        }
        d.dispatch = [
          "dispatch → googleads.adgroups.pause ag-hero-sku (" + Math.round(oosFrac * 100) + "% dry)",
          "dispatch → meta.adsets.update as-catalog +" + usd(shift2),
          "dispatch → shopify.webhook restock-resume armed"
        ];
      }

    } else { /* pixel attribution drift */
      var reported = MODEL.reportedRoasDrift;
      var verified = reported * (1 - MODEL.driftInflation);
      var scaleUp = inp.budget * MODEL.scaleUpFraction;
      d.truthLabel = "Verified vs reported ROAS";
      d.truthText = x(verified) + " vs " + x(reported);
      d.truthClass = "warn";
      d.riskPerDay = scaleUp * MODEL.driftInflation;
      d.cause = "attribution drift after the tag change — reported " + x(reported) +
        " inflates verified " + x(verified) + " by " + Math.round(MODEL.driftInflation * 100) + "%";
      d.sense = [
        "evidence in ← tag-monitor: conversion pixel fired 2× on checkout since 06:40",
        "evidence in ← ads: reported ROAS " + x(reported) + " · step-change, no creative or bid change",
        "evidence in ← analytics: order count flat — revenue truth did not move"
      ];
      var realloc = Math.min(round50(inp.budget * 0.15), maxShift);
      d.shift = realloc;
      d.projRoas = verified;
      if (inp.floorOn && verified < MODEL.roasFloor) {
        d.veto = true;
        d.vetoReason = "verified ROAS " + x(verified) + " below the " + x(MODEL.roasFloor) + " floor";
        d.actionText = "Hold spend · route to human";
        d.prevented = scaleUp;
        d.roasKept = x(MODEL.roasFloor) + " floor held";
        d.roasKeptHeld = true;
      } else {
        d.actionText = "Block " + usd(scaleUp) + " scale-up · re-baseline";
        d.prevented = scaleUp * MODEL.driftInflation;
        d.roasKept = x(verified) + " verified";
      }
      d.planLines = [
        "plan: block the queued " + usd(scaleUp) + " scale-up — it would buy the mirage",
        "plan: re-baseline attribution on Structured Signal Evidence · hold budget flat",
        "plan: reallocate " + usd(realloc) + " only where lift is verified"
      ];
      d.dispatch = [
        "dispatch → queue.cancel scale-up-" + usd(scaleUp).replace(/[$,]/g, "") + " (blocked)",
        "dispatch → attribution.rebaseline source-of-truth=verified",
        "dispatch → meta.adsets.update as-verified +" + usd(realloc)
      ];
    }

    d.autoTier = !d.veto && !d.noAction && d.shift <= MODEL.autoShiftCap;
    d.trace = "MZK-" + traceId([inp.scenario, inp.latency, inp.inventory,
      inp.budget, inp.floorOn ? 1 : 0, inp.capOn ? 1 : 0].join("|"));
    return d;
  }

  /* ---------- live readouts (recalculate on every input) ---------- */

  var els = {};
  var runEpoch = 0;          // invalidates stale timeouts when inputs change
  var pendingDecision = null;

  function fmtLatency(v) { return v.toFixed(1) + "s"; }

  function updateReadouts() {
    var inp = readInputs();
    var d = evaluate(inp);
    $("mzkLatOut").textContent = fmtLatency(inp.latency);
    $("mzkInvOut").textContent = String(inp.inventory);
    $("mzkBudOut").textContent = usd(inp.budget);

    $("mzkDialLat").classList.toggle("dim", inp.scenario !== "latency");
    $("mzkDialInv").classList.toggle("dim", inp.scenario !== "inventory");

    $("mzkRoRisk").textContent = usd(d.riskPerDay) + "/day";
    $("mzkRoRisk").className = d.riskPerDay > inp.budget * 0.25 ? "bad" :
      (d.riskPerDay > 0 ? "warn" : "ok");
    $("mzkRoTruthLabel").textContent = d.truthLabel;
    $("mzkRoTruth").textContent = d.truthText;
    $("mzkRoTruth").className = d.truthClass;
    $("mzkRoAction").textContent = d.actionText;
    $("mzkRoAction").className = d.veto ? "bad" : (d.noAction ? "ok" : "");
    $("mzkRoTier").textContent = d.veto ? "VETO — held for human" :
      d.noAction ? "no action needed" :
      d.autoTier ? "low-risk · auto-eligible" : "routed for approval";
    $("mzkRoTier").className = d.veto ? "bad" : (d.autoTier || d.noAction ? "ok" : "warn");
    return d;
  }

  function onInputsChanged() {
    updateReadouts();
    if (pendingDecision) {
      runEpoch++;
      pendingDecision = null;
      $("mzkGate").classList.remove("show");
      logLine("inputs changed — run superseded. Press Run for a fresh decision.", "warn");
      resetPhases();
    }
  }

  /* ---------- terminal ---------- */

  var logStamp = 0;

  function logLine(text, cls) {
    var log = $("mzkLog");
    var ln = document.createElement("div");
    ln.className = "ln" + (cls ? " " + cls : "");
    var ts = document.createElement("span");
    ts.className = "ts";
    logStamp += 0.32;
    ts.textContent = "t+" + logStamp.toFixed(2) + "s";
    ln.appendChild(ts);
    ln.appendChild(document.createTextNode(text));
    log.appendChild(ln);
    log.scrollTop = log.scrollHeight;
  }

  function resetPhases() {
    var phs = $("mzkPhases").querySelectorAll(".ph");
    for (var i = 0; i < phs.length; i++) phs[i].className = "ph";
  }

  function phase(name, state) {
    var ph = $("mzkPhases").querySelector('[data-ph="' + name + '"]');
    if (ph) ph.className = "ph " + state;
  }

  var tickerTimer = null;

  function setTicker(prevented, roasKept, held) {
    var pv = $("mzkPrevented"), rk = $("mzkRoasKept");
    if (tickerTimer) { clearInterval(tickerTimer); tickerTimer = null; }
    rk.textContent = roasKept;
    rk.className = "tv" + (held ? " held" : "");
    pv.className = "tv" + (held ? " held" : "");
    var target = Math.round(prevented);
    if (reduceMotion || target === 0) { pv.textContent = usd(target); return; }
    var steps = 24, n = 0;
    tickerTimer = setInterval(function () {
      n++;
      pv.textContent = usd(target * (n / steps));
      if (n >= steps) { clearInterval(tickerTimer); tickerTimer = null; }
    }, 40);
  }

  function schedule(steps) {
    var epoch = runEpoch;
    var delay = 0;
    steps.forEach(function (step) {
      delay += reduceMotion ? 0 : step[0];
      setTimeout(function () {
        if (epoch === runEpoch) step[1]();
      }, delay);
    });
  }

  function startRun() {
    runEpoch++;
    pendingDecision = null;
    var inp = readInputs();
    var d = evaluate(inp);
    var log = $("mzkLog");
    log.textContent = "";
    logStamp = 0;
    resetPhases();
    $("mzkGate").classList.remove("show");
    setTicker(0, "—", false);
    $("mzkRun").disabled = true;

    var steps = [];
    steps.push([0, function () {
      phase("sense", "lit");
      logLine("run " + d.trace + " · scenario: " + inp.scenario +
        " · budget " + usd(inp.budget) + "/day", "sys");
      logLine("SENSE — full-stack radar sweep", "seam");
    }]);
    d.sense.forEach(function (line) { steps.push([420, function () { logLine(line); }]); });
    steps.push([420, function () {
      phase("sense", "done"); phase("reason", "lit");
      logLine("REASON — Cross-Stack Root Cause Engine", "seam");
      logLine("candidates tested: creative fatigue · audience saturation · bid policy · stack change");
    }]);
    steps.push([520, function () {
      logLine("named driver → " + d.cause, "sys");
    }]);
    steps.push([520, function () {
      phase("reason", "done"); phase("plan", "lit");
      logLine("PLAN — actionable strategy", "seam");
    }]);
    d.planLines.forEach(function (line) { steps.push([380, function () { logLine(line); }]); });
    steps.push([420, function () {
      phase("plan", "done"); phase("validate", "lit");
      logLine("VALIDATE — safety brakes", "seam");
      logLine("check ✓ budget limit — action inside " + usd(inp.budget) + "/day envelope", "ok");
    }]);
    steps.push([360, function () {
      logLine("check ✓ brand rules — no excluded placements or claims touched", "ok");
    }]);
    steps.push([360, function () {
      if (inp.floorOn) {
        if (d.veto) {
          logLine("check ✗ margin threshold — " + d.vetoReason, "bad");
        } else {
          logLine("check ✓ margin threshold — projected ROAS " + x(d.projRoas) +
            " ≥ " + x(MODEL.roasFloor) + " floor" +
            (d.escalated ? " (shift escalated to clear the floor)" : ""), "ok");
        }
      } else {
        logLine("check ○ margin threshold — ROAS floor disabled by operator", "warn");
      }
      logLine(inp.capOn
        ? "check ✓ auto-shift cap — single action ≤ " + usd(MODEL.autoShiftCap)
        : "check ○ auto-shift cap — disabled; large moves route to approval", inp.capOn ? "ok" : "warn");
    }]);

    if (d.veto) {
      steps.push([520, function () {
        phase("validate", "blocked");
        logLine("VETO — the plan is stopped, not softened. Nothing executes.", "bad");
        logLine("held → routed to a human with the evidence file attached", "bad");
      }]);
      steps.push([520, function () {
        phase("learn", "done");
        logLine("LEARN — veto recorded to Compounding ROI Memory · " + d.trace, "seam");
        setTicker(d.prevented, d.roasKept, true);
        $("mzkRun").disabled = false;
      }]);
      schedule(steps);
      return;
    }

    if (d.noAction) {
      steps.push([520, function () {
        phase("validate", "done"); phase("decide", "done"); phase("act", "done");
        logLine("DECIDE — no action earns execution this run. Restraint is a decision too.", "sys");
      }]);
      steps.push([480, function () {
        phase("learn", "done");
        logLine("LEARN — healthy state recorded to Compounding ROI Memory · " + d.trace, "seam");
        setTicker(0, d.roasKept, false);
        $("mzkRun").disabled = false;
      }]);
      schedule(steps);
      return;
    }

    steps.push([520, function () {
      phase("validate", "done"); phase("decide", "lit");
      logLine("DECIDE — " + (d.autoTier
        ? "low-risk tier: in production this clears automatically inside your policy envelope"
        : "above the auto tier: routed to Slack / Teams for a one-click decision"), "sys");
      logLine("awaiting approval — evidence and projected outcome attached", "warn");
      var tier = $("mzkTier");
      tier.textContent = d.autoTier ? "low-risk · auto-eligible" : "routed for approval · slack / teams";
      tier.className = "tier" + (d.autoTier ? " auto" : "");
      $("mzkGate").classList.add("show");
      pendingDecision = d;
      $("mzkRun").disabled = false;
    }]);
    schedule(steps);
  }

  function approve() {
    if (!pendingDecision) return;
    var d = pendingDecision;
    pendingDecision = null;
    $("mzkGate").classList.remove("show");
    var steps = [];
    steps.push([0, function () {
      phase("decide", "done"); phase("act", "lit");
      logLine("approved — 1-click · decision signed " + d.trace, "ok");
      logLine("ACT — hands-free execution (simulated — no live API is called)", "seam");
    }]);
    d.dispatch.forEach(function (line) { steps.push([420, function () { logLine(line, "ok"); }]); });
    steps.push([520, function () {
      phase("act", "done"); phase("learn", "lit");
      logLine("LEARN — outcome recorded → Compounding ROI Memory", "seam");
      logLine("wasted spend prevented " + usd(d.prevented) + "/day · ROAS preserved " +
        d.roasKept + " · next decision starts smarter", "sys");
    }]);
    steps.push([420, function () {
      phase("learn", "done");
      setTicker(d.prevented, d.roasKept, false);
      logLine("run complete · replay with the same dials reproduces this exact decision.", "sys");
    }]);
    schedule(steps);
  }

  function initSim() {
    if (!$("mzkSim")) return;
    ["mzkLat", "mzkInv", "mzkBud"].forEach(function (id) {
      $(id).addEventListener("input", onInputsChanged);
    });
    ["mzkFloor", "mzkCap"].forEach(function (id) {
      $(id).addEventListener("change", onInputsChanged);
    });
    var radios = document.querySelectorAll('input[name="mzkScenario"]');
    for (var i = 0; i < radios.length; i++) {
      radios[i].addEventListener("change", onInputsChanged);
    }
    $("mzkRun").addEventListener("click", startRun);
    $("mzkApprove").addEventListener("click", approve);
    updateReadouts();
  }

  /* ================= 90-second walkthrough player ================= */

  var DURATION = 90;

  function fmtClock(t) {
    var m = Math.floor(t / 60);
    var s = Math.floor(t % 60);
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  function initPlayer() {
    var player = $("mzkPlayer");
    if (!player) return;
    var scenes = player.querySelectorAll(".scene");
    var chips = $("mzkChips").querySelectorAll("button[data-seek]");
    var txScenes = $("mzkTranscript").querySelectorAll(".tx-scene");
    var seekBtns = player.querySelectorAll("button[data-seek]");
    var playBtn = $("mzkPlay");
    var track = $("mzkTrack");
    var fill = $("mzkFill");
    var clock = $("mzkClock");
    var t = 0;
    var playing = false;
    var timer = null;

    function render() {
      var activeIdx = 0;
      for (var i = 0; i < scenes.length; i++) {
        if (t >= parseFloat(scenes[i].getAttribute("data-t"))) activeIdx = i;
      }
      for (var j = 0; j < scenes.length; j++) {
        scenes[j].classList.toggle("on", j === activeIdx);
        if (chips[j]) chips[j].classList.toggle("now", j === activeIdx);
        if (txScenes[j]) txScenes[j].classList.toggle("now", j === activeIdx);
      }
      fill.style.width = (t / DURATION * 100) + "%";
      clock.textContent = fmtClock(t) + " / " + fmtClock(DURATION);
      track.setAttribute("aria-valuenow", String(Math.round(t)));
    }

    function stop(label) {
      playing = false;
      if (timer) { clearInterval(timer); timer = null; }
      playBtn.textContent = label || "▶ Play";
    }

    function play() {
      if (t >= DURATION) t = 0;
      playing = true;
      playBtn.textContent = "❚❚ Pause";
      timer = setInterval(function () {
        t = Math.min(DURATION, t + 0.25);
        render();
        if (t >= DURATION) stop("↻ Replay");
      }, 250);
    }

    playBtn.addEventListener("click", function () {
      if (playing) stop(); else play();
    });

    function seek(to) {
      t = clamp(to, 0, DURATION);
      render();
    }

    for (var k = 0; k < seekBtns.length; k++) {
      seekBtns[k].addEventListener("click", function () {
        seek(parseFloat(this.getAttribute("data-seek")));
        if (!playing) play();
      });
    }

    track.addEventListener("click", function (ev) {
      var rect = track.getBoundingClientRect();
      seek((ev.clientX - rect.left) / rect.width * DURATION);
    });
    track.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowRight") { seek(t + 5); ev.preventDefault(); }
      if (ev.key === "ArrowLeft") { seek(t - 5); ev.preventDefault(); }
    });

    var txBtn = $("mzkTx");
    txBtn.addEventListener("click", function () {
      var panel = $("mzkTranscript");
      var open = panel.classList.toggle("open");
      txBtn.setAttribute("aria-expanded", open ? "true" : "false");
      txBtn.textContent = open ? "Close transcript" : "Open transcript";
    });

    render();
  }

  function init() {
    initSim();
    initPlayer();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
