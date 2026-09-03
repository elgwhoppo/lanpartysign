const WINDOWS = {
  "5m": "5 minutes",
  "15m": "15 minutes",
  "1h": "1 hour",
  "6h": "6 hours",
  "24h": "24 hours",
  "72h": "72 hours",
};

let selectedWindow = "72h";
const page = document.body.dataset.page || "hud";
const bodyFont = '"Open Sans", system-ui, sans-serif';
const displayFont = '"Poppins", "Open Sans", system-ui, sans-serif';
const SPEEDOMETER_STORAGE_KEY = "lanparty-speedometer-settings";
const DEFAULT_SPEEDOMETER = {
  download: {
    maxMbps: 1000,
    redzoneMbps: 750,
  },
  upload: {
    maxMbps: 100,
    redzoneMbps: 75,
  },
};
const LATENCY_TEMP_MAX_MS = 100;
const LATENCY_TEMP_RED_MS = 75;
const NEEDLE_GLIDE_MS = 950;

const ids = {
  collectorState: document.getElementById("collector-state"),
  lastUpdate: document.getElementById("last-update"),
  currentTotal: document.getElementById("current-total"),
  currentDownload: document.getElementById("current-download"),
  currentUpload: document.getElementById("current-upload"),
  latencyGoogle: document.getElementById("latency-google"),
  latencyCloudflare: document.getElementById("latency-cloudflare"),
  latencyQuad9: document.getElementById("latency-quad9"),
  sampleCount: document.getElementById("sample-count"),
  windowTitle: document.getElementById("window-title"),
  windowGrid: document.getElementById("window-grid"),
  chart: document.getElementById("throughput-chart"),
  hudDownload: document.getElementById("hud-download"),
  hudUpload: document.getElementById("hud-upload"),
  hudGoogle: document.getElementById("hud-google"),
  hudCloudflare: document.getElementById("hud-cloudflare"),
  hudQuad9: document.getElementById("hud-quad9"),
  hudGoogleStatus: document.getElementById("hud-google-status"),
  hudCloudflareStatus: document.getElementById("hud-cloudflare-status"),
  hudQuad9Status: document.getElementById("hud-quad9-status"),
  latencyGoogleStatus: document.getElementById("latency-google-status"),
  latencyCloudflareStatus: document.getElementById("latency-cloudflare-status"),
  latencyQuad9Status: document.getElementById("latency-quad9-status"),
  hudSparkline: document.getElementById("hud-sparkline"),
  hudState: document.getElementById("hud-state"),
  latencyTempGauge: document.getElementById("latency-temp-gauge"),
  latencyTempValue: document.getElementById("latency-temp-value"),
  downloadTachometer: document.getElementById("download-tachometer"),
  uploadTachometer: document.getElementById("upload-tachometer"),
  downloadTachometerValue: document.getElementById("download-tachometer-value"),
  uploadTachometerValue: document.getElementById("upload-tachometer-value"),
  downloadTachometerMax: document.getElementById("download-tachometer-max"),
  downloadTachometerRedzone: document.getElementById("download-tachometer-redzone"),
  uploadTachometerMax: document.getElementById("upload-tachometer-max"),
  uploadTachometerRedzone: document.getElementById("upload-tachometer-redzone"),
};

let pingRingState = null;
let pingRingFrame = null;
let cursorTimer = null;
let speedometerSettings = loadSpeedometerSettings();
let speedometerTargetValues = { download: null, upload: null };
let speedometerDisplayedValues = { download: 0, upload: 0 };
let speedometerAnimations = {
  download: { from: 0, to: null, startedAt: 0 },
  upload: { from: 0, to: null, startedAt: 0 },
};
let speedometerFrame = null;
let latencyTempTargetValue = null;
let latencyTempDisplayedValue = 0;
let latencyTempAnimation = { from: 0, to: null, startedAt: 0 };
let latencyTempFailed = false;
let latencyTempFrame = null;
if (page === "hud") {
  window.addEventListener("mousemove", () => {
    document.body.classList.add("cursor-active");
    clearTimeout(cursorTimer);
    cursorTimer = setTimeout(() => {
      document.body.classList.remove("cursor-active");
    }, 1200);
  });
}

setupSpeedometerControls();
drawLatencyTempGauge({ value: null, display: "--", failed: false });

document.querySelectorAll("[data-window]").forEach((button) => {
  button.addEventListener("click", () => {
    selectedWindow = button.dataset.window;
    document.querySelectorAll("[data-window]").forEach((item) => {
      item.classList.toggle("active", item === button);
    });
    ids.windowTitle.textContent = WINDOWS[selectedWindow];
    refreshChart();
  });
});

async function refreshSummary() {
  try {
    const response = await fetch("/api/summary", { cache: "no-store" });
    const data = await response.json();
    if (page === "hud") {
      renderHud(data);
    } else {
      renderDetailsSummary(data);
    }
  } catch (error) {
    setCollectorState(false, "Offline");
    if (ids.lastUpdate) ids.lastUpdate.textContent = "Dashboard API unreachable";
  }
}

async function refreshChart() {
  const query = page === "hud"
    ? "window=1m&bucket=1"
    : `window=${selectedWindow}`;
  try {
    const response = await fetch(`/api/timeseries?${query}`, { cache: "no-store" });
    const data = await response.json();
    if (page === "hud") {
      drawHudSparkline(data.points || [], data.now, data.seconds);
    } else {
      drawChart(data.points || []);
    }
  } catch (error) {
    if (page === "hud") {
      drawHudSparkline([]);
    } else {
      drawChart([]);
    }
  }
}

function renderHud(data) {
  const current = data.current || {};
  const collector = data.collector || {};
  const isDemo = data.mode === "demo";
  const isLive = data.mode === "unifi" && collector.connected && Boolean(current.timestamp);

  document.body.classList.toggle("demo-mode", isDemo);
  document.body.classList.toggle("offline-mode", !isDemo && !isLive);
  if (ids.hudState) {
    ids.hudState.hidden = isLive;
    ids.hudState.textContent = isDemo ? "Demo data" : "No live data";
  }

  ids.hudDownload.textContent = formatCompactNumber(current.download_mbps);
  ids.hudUpload.textContent = formatCompactNumber(current.upload_mbps);
  renderPings(data.pings, {
    cloudflare: { value: ids.hudCloudflare, status: ids.hudCloudflareStatus },
    google: { value: ids.hudGoogle, status: ids.hudGoogleStatus },
    quad9: { value: ids.hudQuad9, status: ids.hudQuad9Status },
  });
}

function renderDetailsSummary(data) {
  const current = data.current || {};
  const collector = data.collector || {};
  const online = Boolean(collector.connected);

  setCollectorState(online, online ? "Online" : "Waiting");
  ids.lastUpdate.textContent = current.timestamp
    ? `Updated ${formatRelativeSeconds(Date.now() / 1000 - current.timestamp)}`
    : (collector.last_error || "No samples yet");

  ids.currentTotal.textContent = formatNumber(current.total_mbps);
  ids.currentDownload.textContent = formatNumber(current.download_mbps);
  ids.currentUpload.textContent = formatNumber(current.upload_mbps);
  updateSpeedometers({
    download: current.download_mbps,
    upload: current.upload_mbps,
  });
  updateLatencyTempGauge(data.pings);
  renderPings(data.pings, {
    cloudflare: { value: ids.latencyCloudflare, status: ids.latencyCloudflareStatus },
    google: { value: ids.latencyGoogle, status: ids.latencyGoogleStatus },
    quad9: { value: ids.latencyQuad9, status: ids.latencyQuad9Status },
  });
  ids.sampleCount.textContent = `${data.sample_count || 0} samples retained`;

  ids.windowGrid.innerHTML = "";
  (data.windows || []).forEach((windowSummary) => {
    ids.windowGrid.appendChild(renderWindowCard(windowSummary));
  });
}

function renderWindowCard(windowSummary) {
  const average = windowSummary.average || {};
  const peak = windowSummary.peak || {};
  const card = document.createElement("article");
  card.className = "window-card";
  card.innerHTML = `
    <h3>${windowSummary.label}</h3>
    ${row("Avg total", formatMbps(average.total_mbps))}
    ${row("Peak total", formatMbps(peak.total_mbps))}
    ${row("Avg down", formatMbps(average.download_mbps))}
    ${row("Peak down", formatMbps(peak.download_mbps))}
    ${row("Worst ping", formatLatency(windowSummary.pings?.worst_latency_ms))}
  `;
  return card;
}

function setupSpeedometerControls() {
  if (!ids.downloadTachometer && !ids.uploadTachometer) return;
  document.querySelector(".speedometer-controls")?.addEventListener("submit", (event) => {
    event.preventDefault();
  });

  if (ids.downloadTachometerMax) ids.downloadTachometerMax.value = String(speedometerSettings.download.maxMbps);
  if (ids.downloadTachometerRedzone) ids.downloadTachometerRedzone.value = String(speedometerSettings.download.redzoneMbps);
  if (ids.uploadTachometerMax) ids.uploadTachometerMax.value = String(speedometerSettings.upload.maxMbps);
  if (ids.uploadTachometerRedzone) ids.uploadTachometerRedzone.value = String(speedometerSettings.upload.redzoneMbps);

  [
    ids.downloadTachometerMax,
    ids.downloadTachometerRedzone,
    ids.uploadTachometerMax,
    ids.uploadTachometerRedzone,
  ].forEach((input) => {
    if (!input) return;
    input.addEventListener("input", () => {
      speedometerSettings = readSpeedometerInputs();
      saveSpeedometerSettings(speedometerSettings);
      drawTachometer("download");
      drawTachometer("upload");
    });
  });

  drawTachometer("download");
  drawTachometer("upload");
}

function loadSpeedometerSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(SPEEDOMETER_STORAGE_KEY) || "{}");
    return normalizeSpeedometerSettings(saved);
  } catch (error) {
    return { ...DEFAULT_SPEEDOMETER };
  }
}

function readSpeedometerInputs() {
  return normalizeSpeedometerSettings({
    download: {
      maxMbps: ids.downloadTachometerMax?.value,
      redzoneMbps: ids.downloadTachometerRedzone?.value,
    },
    upload: {
      maxMbps: ids.uploadTachometerMax?.value,
      redzoneMbps: ids.uploadTachometerRedzone?.value,
    },
  });
}

function normalizeSpeedometerSettings(settings) {
  const migratedDownload = settings.download || {
    maxMbps: settings.maxMbps,
    redzoneMbps: settings.redzoneMbps,
  };
  return {
    download: normalizeGaugeSettings(migratedDownload, DEFAULT_SPEEDOMETER.download),
    upload: normalizeGaugeSettings(settings.upload || {}, DEFAULT_SPEEDOMETER.upload),
  };
}

function normalizeGaugeSettings(settings, defaults) {
  const maxMbps = Math.max(1, Math.round(Number(settings.maxMbps) || defaults.maxMbps));
  const redzoneMbps = Math.max(1, Math.min(maxMbps, Math.round(Number(settings.redzoneMbps) || defaults.redzoneMbps)));
  return { maxMbps, redzoneMbps };
}

function saveSpeedometerSettings(settings) {
  try {
    localStorage.setItem(SPEEDOMETER_STORAGE_KEY, JSON.stringify(settings));
  } catch (error) {
    // Local display preferences are best-effort.
  }
}

function updateSpeedometers(values) {
  if (!ids.downloadTachometer && !ids.uploadTachometer) return;
  const now = performance.now();
  ["download", "upload"].forEach((kind) => {
    const number = Number(values[kind]);
    speedometerTargetValues[kind] = Number.isFinite(number) ? Math.max(0, number) : null;
    if (speedometerTargetValues[kind] === null) {
      drawTachometer(kind);
      speedometerAnimations[kind] = { from: speedometerDisplayedValues[kind], to: null, startedAt: now };
      return;
    }
    speedometerAnimations[kind] = {
      from: speedometerDisplayedValues[kind],
      to: speedometerTargetValues[kind],
      startedAt: now,
    };
  });

  if (!speedometerFrame) {
    speedometerFrame = requestAnimationFrame(animateSpeedometer);
  }
}

function animateSpeedometer(timestamp) {
  if (!ids.downloadTachometer && !ids.uploadTachometer) {
    speedometerFrame = null;
    return;
  }

  let settled = true;
  ["download", "upload"].forEach((kind) => {
    const animation = speedometerAnimations[kind];
    if (animation.to === null) return;
    const progress = Math.min(1, Math.max(0, (timestamp - animation.startedAt) / NEEDLE_GLIDE_MS));
    const eased = easeNeedle(progress);
    speedometerDisplayedValues[kind] = animation.from + ((animation.to - animation.from) * eased);
    if (progress < 1) {
      settled = false;
    } else {
      speedometerDisplayedValues[kind] = animation.to;
    }
    drawTachometer(kind);
  });

  speedometerFrame = settled
    ? null
    : requestAnimationFrame(animateSpeedometer);
}

function drawTachometer(kind) {
  const canvas = kind === "download" ? ids.downloadTachometer : ids.uploadTachometer;
  const valueElement = kind === "download" ? ids.downloadTachometerValue : ids.uploadTachometerValue;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.43;
  const startAngle = radians(132);
  const endAngle = radians(408);
  const maxMbps = speedometerSettings[kind].maxMbps;
  const redzoneMbps = Math.min(speedometerSettings[kind].redzoneMbps, maxMbps);
  const value = Number.isFinite(speedometerDisplayedValues[kind]) ? Math.max(0, speedometerDisplayedValues[kind]) : 0;
  const actual = Number.isFinite(speedometerTargetValues[kind]) ? Math.max(0, speedometerTargetValues[kind]) : null;
  const clampedValue = Math.min(value, maxMbps);
  const needleAngle = valueToGaugeAngle(clampedValue, maxMbps, startAngle, endAngle);

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#050607";
  ctx.fillRect(0, 0, width, height);

  drawTachometerFace(ctx, centerX, centerY, radius, kind);
  drawTachometerScale(ctx, centerX, centerY, radius, maxMbps, redzoneMbps, startAngle, endAngle);
  drawNeedle(ctx, centerX, centerY, radius, needleAngle);

  if (valueElement) {
    valueElement.textContent = actual === null ? "--" : formatNumber(actual);
    valueElement.classList.toggle("redzone", actual !== null && actual >= redzoneMbps);
  }
}

function valueToGaugeAngle(value, maxValue, startAngle, endAngle) {
  const ratio = Math.max(0, Math.min(1, value / maxValue));
  return startAngle + (endAngle - startAngle) * ratio;
}

function drawTachometerFace(ctx, centerX, centerY, radius, kind) {
  const faceGradient = ctx.createRadialGradient(centerX, centerY, radius * 0.1, centerX, centerY, radius);
  faceGradient.addColorStop(0, "#22272b");
  faceGradient.addColorStop(0.52, "#10151a");
  faceGradient.addColorStop(1, "#050607");
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.fillStyle = faceGradient;
  ctx.fill();

  const ringGradient = ctx.createRadialGradient(centerX, centerY, radius * 0.82, centerX, centerY, radius * 1.08);
  ringGradient.addColorStop(0, "#3a4248");
  ringGradient.addColorStop(0.36, "#f2f6f7");
  ringGradient.addColorStop(0.48, "#67717a");
  ringGradient.addColorStop(0.7, "#101419");
  ringGradient.addColorStop(1, "#dce7ee");
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius + 19, 0, Math.PI * 2);
  ctx.strokeStyle = ringGradient;
  ctx.lineWidth = 16;
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(centerX, centerY, radius + 3, 0, Math.PI * 2);
  ctx.strokeStyle = "rgba(66, 191, 255, 0.75)";
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.save();
  ctx.globalAlpha = 0.18;
  ctx.fillStyle = kind === "download" ? "#42bfff" : "#a15bff";
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius * 0.72, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawTachometerScale(ctx, centerX, centerY, radius, maxMbps, redzoneMbps, startAngle, endAngle) {
  const majorTicks = 10;
  const minorTicks = 60;

  for (let i = 0; i <= minorTicks; i += 1) {
    const value = maxMbps * (i / minorTicks);
    const angle = valueToGaugeAngle(value, maxMbps, startAngle, endAngle);
    const major = i % (minorTicks / majorTicks) === 0;
    const redline = value >= redzoneMbps;
    const inner = pointOnGauge(centerX, centerY, radius - (major ? 44 : 30), angle);
    const outer = pointOnGauge(centerX, centerY, radius - 12, angle);
    ctx.beginPath();
    ctx.moveTo(inner.x, inner.y);
    ctx.lineTo(outer.x, outer.y);
    ctx.strokeStyle = redline ? "#ff2028" : "#f2f7f9";
    ctx.lineWidth = major ? 4 : 2;
    ctx.lineCap = "butt";
    ctx.stroke();
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "#f2f7f9";
  ctx.font = `34px ${displayFont}`;
  for (let i = 0; i <= majorTicks; i += 1) {
    const value = maxMbps * (i / majorTicks);
    const angle = valueToGaugeAngle(value, maxMbps, startAngle, endAngle);
    const label = pointOnGauge(centerX, centerY, radius - 82, angle);
    ctx.save();
    ctx.translate(label.x, label.y);
    ctx.rotate(angle + Math.PI / 2);
    ctx.fillText(formatNumber(value), 0, 0);
    ctx.restore();
  }

  ctx.fillStyle = "#dce7ee";
  ctx.font = `24px ${displayFont}`;
  ctx.fillText("Mbps", centerX, centerY - radius * 0.33);

  ctx.fillStyle = "#ff2028";
  ctx.font = `20px ${bodyFont}`;
  const redlineLabel = pointOnGauge(centerX, centerY, radius - 132, valueToGaugeAngle(redzoneMbps, maxMbps, startAngle, endAngle));
  ctx.fillText("REDLINE", redlineLabel.x, redlineLabel.y);
}

function drawNeedle(ctx, centerX, centerY, radius, angle) {
  const tip = pointOnGauge(centerX, centerY, radius - 88, angle);
  const tail = pointOnGauge(centerX, centerY, 28, angle + Math.PI);
  const color = "#ff2028";

  ctx.save();
  ctx.shadowColor = color;
  ctx.shadowBlur = 12;
  ctx.beginPath();
  ctx.moveTo(tail.x, tail.y);
  ctx.lineTo(tip.x, tip.y);
  ctx.strokeStyle = color;
  ctx.lineWidth = 8;
  ctx.lineCap = "round";
  ctx.stroke();
  ctx.restore();

  ctx.beginPath();
  ctx.arc(centerX, centerY, 24, 0, Math.PI * 2);
  ctx.fillStyle = "#0b0e10";
  ctx.fill();
  ctx.lineWidth = 7;
  ctx.strokeStyle = color;
  ctx.stroke();
}

function updateLatencyTempGauge(pings) {
  if (!ids.latencyTempGauge) return;
  const metric = getLatencyTempMetric(pings);
  const now = performance.now();
  latencyTempFailed = metric.failed;
  latencyTempTargetValue = Number.isFinite(metric.value) ? metric.value : null;
  if (ids.latencyTempValue) {
    ids.latencyTempValue.textContent = metric.display;
    ids.latencyTempValue.classList.toggle("hot", metric.failed || (metric.value !== null && metric.value >= LATENCY_TEMP_RED_MS));
  }

  if (latencyTempTargetValue === null) {
    latencyTempAnimation = { from: latencyTempDisplayedValue, to: null, startedAt: now };
    drawLatencyTempGauge(metric);
    return;
  }

  latencyTempAnimation = {
    from: latencyTempDisplayedValue,
    to: latencyTempTargetValue,
    startedAt: now,
  };

  if (!latencyTempFrame) {
    latencyTempFrame = requestAnimationFrame(animateLatencyTempGauge);
  }
}

function getLatencyTempMetric(pings) {
  const targets = pings?.targets || [];
  const latencies = [];
  let failed = false;

  targets.forEach((target) => {
    const latest = target.latest || {};
    if (!latest.timestamp) return;
    if (!latest.success) {
      failed = true;
      return;
    }
    const latency = Number(latest.latency_ms);
    if (Number.isFinite(latency)) {
      latencies.push(latency);
    }
  });

  if (failed) {
    return { value: LATENCY_TEMP_MAX_MS, display: "FAIL", failed: true };
  }
  if (!latencies.length) {
    return { value: null, display: "--", failed: false };
  }

  const worstLatency = Math.max(...latencies);
  return { value: worstLatency, display: formatLatency(worstLatency), failed: false };
}

function animateLatencyTempGauge(timestamp) {
  if (!ids.latencyTempGauge || latencyTempAnimation.to === null) {
    latencyTempFrame = null;
    return;
  }

  const progress = Math.min(1, Math.max(0, (timestamp - latencyTempAnimation.startedAt) / NEEDLE_GLIDE_MS));
  const eased = easeNeedle(progress);
  latencyTempDisplayedValue = latencyTempAnimation.from + ((latencyTempAnimation.to - latencyTempAnimation.from) * eased);
  if (progress >= 1) latencyTempDisplayedValue = latencyTempAnimation.to;

  drawLatencyTempGauge({
    value: latencyTempDisplayedValue,
    display: ids.latencyTempValue?.textContent || "--",
    failed: latencyTempFailed,
  });
  latencyTempFrame = progress >= 1
    ? null
    : requestAnimationFrame(animateLatencyTempGauge);
}

function drawLatencyTempGauge(metric) {
  const canvas = ids.latencyTempGauge;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const centerX = width * 0.5;
  const centerY = height * 0.61;
  const radius = Math.min(width * 0.58, height * 0.38);
  const startAngle = radians(205);
  const endAngle = radians(335);
  const value = Number.isFinite(metric.value) ? Math.max(0, Math.min(LATENCY_TEMP_MAX_MS, metric.value)) : 0;
  const needleAngle = valueToGaugeAngle(value, LATENCY_TEMP_MAX_MS, startAngle, endAngle);
  const redAngle = valueToGaugeAngle(LATENCY_TEMP_RED_MS, LATENCY_TEMP_MAX_MS, startAngle, endAngle);

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#080a0c";
  ctx.fillRect(0, 0, width, height);

  const backdrop = ctx.createLinearGradient(0, 0, 0, height);
  backdrop.addColorStop(0, "rgba(255, 255, 255, 0.08)");
  backdrop.addColorStop(0.42, "rgba(66, 191, 255, 0.08)");
  backdrop.addColorStop(1, "rgba(0, 0, 0, 0.08)");
  ctx.fillStyle = backdrop;
  ctx.fillRect(0, 0, width, height);

  drawLatencyArc(ctx, centerX, centerY, radius, startAngle, endAngle, "rgba(235, 244, 248, 0.28)", 14);
  drawLatencyArc(ctx, centerX, centerY, radius, startAngle, redAngle, "#42bfff", 9);
  drawLatencyArc(ctx, centerX, centerY, radius, redAngle, endAngle, "#ff2028", 9);

  for (let i = 0; i <= 10; i += 1) {
    const tickValue = LATENCY_TEMP_MAX_MS * (i / 10);
    const angle = valueToGaugeAngle(tickValue, LATENCY_TEMP_MAX_MS, startAngle, endAngle);
    const major = i % 5 === 0;
    const hot = tickValue >= LATENCY_TEMP_RED_MS;
    const inner = pointOnGauge(centerX, centerY, radius - (major ? 30 : 20), angle);
    const outer = pointOnGauge(centerX, centerY, radius - 2, angle);
    ctx.beginPath();
    ctx.moveTo(inner.x, inner.y);
    ctx.lineTo(outer.x, outer.y);
    ctx.strokeStyle = hot ? "#ff2028" : "#f2f7f9";
    ctx.lineWidth = major ? 4 : 2;
    ctx.stroke();
  }

  ctx.fillStyle = "#f2f7f9";
  ctx.font = `23px ${displayFont}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText("C", centerX - radius * 0.9, centerY + radius * 0.42);
  ctx.fillText("H", centerX + radius * 0.9, centerY + radius * 0.42);

  ctx.fillStyle = "#cbd6dc";
  ctx.font = `20px ${bodyFont}`;
  ctx.fillText("ms", centerX, centerY - radius * 0.44);

  drawTempNeedle(ctx, centerX, centerY, radius, needleAngle, metric.failed || value >= LATENCY_TEMP_RED_MS);
}

function drawLatencyArc(ctx, centerX, centerY, radius, startAngle, endAngle, color, lineWidth) {
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, startAngle, endAngle, false);
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.lineCap = "round";
  ctx.stroke();
}

function drawTempNeedle(ctx, centerX, centerY, radius, angle, hot) {
  const color = hot ? "#ff2028" : "#42bfff";
  const tip = pointOnGauge(centerX, centerY, radius - 35, angle);
  const tail = pointOnGauge(centerX, centerY, 18, angle + Math.PI);

  ctx.save();
  ctx.shadowColor = color;
  ctx.shadowBlur = 10;
  ctx.beginPath();
  ctx.moveTo(tail.x, tail.y);
  ctx.lineTo(tip.x, tip.y);
  ctx.strokeStyle = color;
  ctx.lineWidth = 6;
  ctx.lineCap = "round";
  ctx.stroke();
  ctx.restore();

  ctx.beginPath();
  ctx.arc(centerX, centerY, 20, 0, Math.PI * 2);
  ctx.fillStyle = "#0a0d10";
  ctx.fill();
  ctx.lineWidth = 6;
  ctx.strokeStyle = "#dce7ee";
  ctx.stroke();
}

function radians(degrees) {
  return degrees * (Math.PI / 180);
}

function easeNeedle(progress) {
  return 0.5 - (Math.cos(Math.PI * progress) / 2);
}

function pointOnGauge(centerX, centerY, radius, angle) {
  return {
    x: centerX + Math.cos(angle) * radius,
    y: centerY + Math.sin(angle) * radius,
  };
}

function renderPings(pings, elements) {
  const targets = pings?.targets || [];
  const now = pings?.now || Date.now() / 1000;
  const targetInterval = pings?.target_interval_seconds || 15;
  const ringTargets = [];
  targets.forEach((target) => {
    const group = elements[target.key] || {};
    const element = group.value;
    if (!element) return;
    const latest = target.latest || {};
    const state = pingState(latest);
    const row = element.closest("span");
    element.textContent = latest.success ? formatLatency(latest.latency_ms) : "--";
    if (row) {
      row.classList.toggle("ping-ok", state === "ok");
      row.classList.toggle("ping-warn", state === "warn");
      row.classList.toggle("ping-failed", state === "failed");
      row.classList.toggle("ping-waiting", state === "waiting");
    }

    const status = group.status;
    if (!status) return;
    const age = latest.timestamp ? Math.max(0, now - latest.timestamp) : targetInterval;
    const progress = Math.max(0, Math.min(1, age / targetInterval));
    status.classList.toggle("ok", state === "ok");
    status.classList.toggle("warn", state === "warn");
    status.classList.toggle("failed", state === "failed");
    status.classList.toggle("waiting", state === "waiting");
    status.textContent = "";
    status.dataset.mark = state === "ok" ? "✓" : state === "warn" ? "!" : state === "failed" ? "X" : "?";
    status.title = latest.timestamp
      ? `${target.label} ${target.address}: ${latest.success ? formatLatency(latest.latency_ms) : "failed"} ${formatRelativeSeconds(age)}`
      : `${target.label} ${target.address}: waiting`;
    status.style.setProperty("--progress", `${(progress * 100).toFixed(2)}%`);
    ringTargets.push({ status, timestamp: latest.timestamp || null });
  });
  animatePingRingsFrom(ringTargets, now, targetInterval);
}

function animatePingRingsFrom(targets, serverNow, targetInterval) {
  pingRingState = {
    targets,
    serverNow,
    targetInterval,
    receivedAt: performance.now() / 1000,
  };
  if (!pingRingFrame) {
    pingRingFrame = requestAnimationFrame(updatePingRings);
  }
}

function updatePingRings() {
  if (!pingRingState || !pingRingState.targets.length) {
    pingRingFrame = null;
    return;
  }

  const elapsed = performance.now() / 1000 - pingRingState.receivedAt;
  const now = pingRingState.serverNow + elapsed;
  pingRingState.targets.forEach(({ status, timestamp }) => {
    const age = timestamp ? Math.max(0, now - timestamp) : pingRingState.targetInterval;
    const progress = Math.max(0, Math.min(1, age / pingRingState.targetInterval));
    status.style.setProperty("--progress", `${(progress * 100).toFixed(2)}%`);
  });

  pingRingFrame = requestAnimationFrame(updatePingRings);
}

function pingState(latest) {
  if (!latest.timestamp) return "waiting";
  if (!latest.success) return "failed";
  const latency = Number(latest.latency_ms);
  if (!Number.isFinite(latency)) return "failed";
  if (latency < 50) return "ok";
  if (latency <= 75) return "warn";
  return "failed";
}

function row(label, value) {
  return `<div class="window-row"><span>${label}</span><strong>${value}</strong></div>`;
}

function drawHudSparkline(points, now, seconds = 60) {
  if (!ids.hudSparkline) return;
  const canvas = ids.hudSparkline;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const bottom = height - 12;
  const top = 8;
  const slotCount = Math.max(1, Math.min(60, Math.round(seconds)));
  const endBucket = Math.floor(now || Date.now() / 1000);
  const startBucket = endBucket - slotCount + 1;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#101214";
  ctx.fillRect(0, 0, width, height);

  if (!points.length) {
    ctx.strokeStyle = "#965cff";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, bottom);
    ctx.lineTo(width, bottom);
    ctx.stroke();
    return;
  }

  const values = Array.from({ length: slotCount }, () => ({ down: 0, up: 0 }));
  points.forEach((point) => {
    const index = Math.floor(point.timestamp) - startBucket;
    if (index < 0 || index >= values.length) return;
    values[index] = {
      down: point.average?.download_mbps || 0,
      up: point.average?.upload_mbps || 0,
    };
  });
  const maxValue = Math.max(10, ...values.map((item) => item.down + item.up));
  const step = width / slotCount;
  const barWidth = Math.max(2, Math.floor(step) - 2);

  values.forEach((value, index) => {
    const x = index * step;
    const downloadHeight = ((value.down / maxValue) * (bottom - top));
    const uploadHeight = ((value.up / maxValue) * (bottom - top));
    ctx.fillStyle = "rgba(118, 205, 255, 0.42)";
    ctx.fillRect(x, bottom - downloadHeight, barWidth, downloadHeight);
    ctx.strokeStyle = "#70caff";
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 0.5, bottom - downloadHeight + 0.5, barWidth, downloadHeight);
    ctx.fillStyle = "#9b55ff";
    ctx.fillRect(x, bottom - uploadHeight, barWidth, 2);
  });

  ctx.strokeStyle = "#9b55ff";
  ctx.lineWidth = 3;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = index * step + barWidth / 2;
    const y = bottom - ((value.up / maxValue) * (bottom - top));
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

function drawChart(points) {
  const canvas = ids.chart;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 24, right: 42, bottom: 38, left: 58 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#1a2024";
  ctx.fillRect(0, 0, width, height);

  if (!points.length) {
    ctx.fillStyle = "#9aa7a1";
    ctx.font = `34px ${displayFont}`;
    ctx.textAlign = "center";
    ctx.fillText("Waiting for metrics", width / 2, height / 2);
    return;
  }

  const maxValue = Math.max(
    10,
    ...points.map((point) => point.peak?.total_mbps || point.average?.total_mbps || 0)
  );
  const yMax = niceCeil(maxValue);

  drawGrid(ctx, padding, chartWidth, chartHeight, yMax);
  drawSeries(ctx, points, padding, chartWidth, chartHeight, yMax, "download_mbps", "#65d86e", "average");
  drawSeries(ctx, points, padding, chartWidth, chartHeight, yMax, "upload_mbps", "#3db7d9", "average");
  drawSeries(ctx, points, padding, chartWidth, chartHeight, yMax, "total_mbps", "#f2b950", "peak");
  drawLegend(ctx);
}

function drawGrid(ctx, padding, chartWidth, chartHeight, yMax) {
  ctx.strokeStyle = "#344047";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#9aa7a1";
  ctx.font = `22px ${bodyFont}`;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  for (let i = 0; i <= 4; i += 1) {
    const y = padding.top + chartHeight * (i / 4);
    const value = yMax - yMax * (i / 4);
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(padding.left + chartWidth, y);
    ctx.stroke();
    ctx.fillText(String(Math.round(value)), padding.left - 10, y);
  }
}

function drawSeries(ctx, points, padding, chartWidth, chartHeight, yMax, field, color, group) {
  ctx.strokeStyle = color;
  ctx.lineWidth = group === "peak" ? 3 : 5;
  ctx.globalAlpha = group === "peak" ? 0.75 : 1;
  ctx.beginPath();

  points.forEach((point, index) => {
    const value = point[group]?.[field] || 0;
    const x = padding.left + (points.length === 1 ? chartWidth : chartWidth * (index / (points.length - 1)));
    const y = padding.top + chartHeight - (value / yMax) * chartHeight;
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });

  ctx.stroke();
  ctx.globalAlpha = 1;
}

function drawLegend(ctx) {
  const items = [
    ["Avg down", "#65d86e"],
    ["Avg up", "#3db7d9"],
    ["Peak total", "#f2b950"],
  ];
  ctx.font = `22px ${bodyFont}`;
  ctx.textAlign = "left";
  items.forEach((item, index) => {
    const x = 78 + index * 180;
    ctx.fillStyle = item[1];
    ctx.fillRect(x, 22, 18, 18);
    ctx.fillStyle = "#f2f6f4";
    ctx.fillText(item[0], x + 28, 32);
  });
}

function setCollectorState(online, text) {
  if (!ids.collectorState) return;
  ids.collectorState.textContent = text;
  ids.collectorState.classList.toggle("online", online);
  ids.collectorState.classList.toggle("offline", !online);
}

function formatNumber(value) {
  if (value === null || value === undefined) return "--";
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  if (Math.abs(number) < 1) return number.toFixed(2);
  return String(Math.round(number));
}

function formatCompactNumber(value) {
  return formatNumber(value);
}

function formatMbps(value) {
  return value === null || value === undefined ? "--" : `${formatNumber(value)}`;
}

function formatLatency(value) {
  return value === null || value === undefined ? "--" : `${Math.round(value)}ms`;
}

function formatRelativeSeconds(seconds) {
  if (seconds < 2) return "just now";
  if (seconds < 60) return `${Math.round(seconds)} sec ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  return `${Math.round(seconds / 3600)} hr ago`;
}

function niceCeil(value) {
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const normalized = value / magnitude;
  const step = normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return step * magnitude;
}

refreshSummary();
refreshChart();
setInterval(refreshSummary, 1000);
setInterval(refreshChart, page === "hud" ? 1000 : 5000);

if (document.fonts) {
  document.fonts.ready.then(refreshChart);
}
