import { getLanguage } from "./i18n.js";
/* Mazhai AI interactive geographic weather explorer.
   Add this module after /js/app.js in frontend/index.html.
   Real state boundaries are loaded from an openly hosted GeoJSON file.
   Optional district/ward GeoJSON files are documented in README-INTEGRATION.md.
*/
const API_BASE = "/api";
const INDIA_STATES_GEOJSON =
  "https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson";

const explorerState = {
  map: null,
  districts: [],
  selectedDistrict: null,
  selectedArea: null,
  forecast: null,
  stateLayer: null,
  districtMarkers: [],
  localLayer: null,
  requestId: 0,
  avatarMessageVisible: false,
  // Places (towns / taluk HQs) inside the selected district.
  places: [],
  placeMarkers: [],
  placeTotals: {},
  placesStatus: "idle", // idle | loading | ready | error
  placesError: "",
  placesRequestId: 0,
  selectedPlace: null,
  placeForecast: null,
  placeRequestId: 0,
  cityViewOpen: false, // Chennai ward view hides the place markers
};

const byId = (id) => document.getElementById(id);
const safe = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[ch]));
const number = (value, digits = 1) =>
  typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";

function explorerMarkup() {
  const panel = document.querySelector("#view-overview .map-panel");
  if (!panel || byId("mazhai-explorer-root")) return;
  panel.innerHTML = `
    <div class="panel-header">
      <div>
        <h2>Interactive weather explorer</h2>
        <p id="wx-breadcrumb">India · select a state or Tamil Nadu district</p>
      </div>
      <button class="text-btn" id="wx-back" type="button" disabled>← Back</button>
    </div>
    <div class="wx-layout" id="mazhai-explorer-root">
      <div class="wx-map-column">
        <div id="wx-map" class="map-canvas" role="application"
             aria-label="Interactive map of India and Tamil Nadu"></div>
        <div class="map-legend wx-legend">
          <span><i class="legend-dot rain-mid"></i> Tamil Nadu district reference point</span>
          <span><i class="legend-dot wx-place-dot"></i> Town / taluk HQ in the selected district</span>
          <span class="wx-legend-note">Markers are representative coordinates, not boundaries.</span>
        </div>
      </div>
      <aside class="wx-details" aria-live="polite">
        <div id="wx-detail-content" class="wx-detail-content">
          <div class="wx-empty"><span class="wx-empty-icon">⌖</span>
            <h3>Explore local weather</h3>
            <p>Select a Tamil Nadu district marker to view weather and available geographic detail.</p>
          </div>
        </div>
      </aside>
    </div>`;
}

function updateBreadcrumb(text) {
  const el = byId("wx-breadcrumb");
  if (el) el.textContent = text;
}
function updateBackButton(enabled) {
  const button = byId("wx-back");
  if (button) button.disabled = !enabled;
}

async function getJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      message = data.detail?.message || data.detail || data.message || message;
    } catch {}
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response.json();
}

function initExplorerMap() {
  if (!window.L || explorerState.map) return;
  explorerState.map = L.map("wx-map", {
    zoomControl: true,
    scrollWheelZoom: false,
    minZoom: 4,
  }).setView([22.7, 79.0], 4.5);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(explorerState.map);

  explorerState.map.on("click", (event) => {
    // A map click itself is not treated as a known place or weather observation.
    if (explorerState.selectedDistrict && explorerState.selectedArea) return;
  });

  loadIndiaStateBoundaries();
  setTimeout(() => explorerState.map?.invalidateSize(), 150);
}

function stateName(feature) {
  const p = feature?.properties || {};
  return String(p.NAME_1 || p.name || p.NAME || p.st_nm || p.state || "");
}

async function loadIndiaStateBoundaries() {
  const map = explorerState.map;
  try {
    const geojson = await getJSON(INDIA_STATES_GEOJSON);
    explorerState.stateLayer = L.geoJSON(geojson, {
      style: () => ({
        color: "#5f819a", weight: 1, opacity: 0.8,
        fillColor: "#15334a", fillOpacity: 0.16,
      }),
      onEachFeature: (feature, layer) => {
        const name = stateName(feature);
        if (name) layer.bindTooltip(safe(name), { sticky: true });
        layer.on("mouseover", () => layer.setStyle({ fillColor: "#247b91", fillOpacity: 0.35, weight: 1.8 }));
        layer.on("mouseout", () => explorerState.stateLayer?.resetStyle(layer));
        layer.on("click", () => {
          if (/tamil\s*nadu/i.test(name)) {
            map.fitBounds(layer.getBounds(), { padding: [22, 22], maxZoom: 7 });
            updateBreadcrumb("India → Tamil Nadu → select a district marker");
            renderDistrictDirectory();
          } else {
            showStateNotCovered(name);
          }
        });
      },
    }).addTo(map);
  } catch (error) {
    showNotice(`State boundary data could not be loaded. The basemap and Tamil Nadu district markers remain available. (${error.message})`);
  }
}

function showStateNotCovered(name) {
  const content = byId("wx-detail-content");
  if (!content) return;
  content.innerHTML = `<div class="wx-empty"><span class="wx-empty-icon">⌖</span>
    <h3>${safe(name)}</h3>
    <p>This release contains weather reference points for Tamil Nadu districts only. Weather for this state is not configured in the existing backend.</p>
    <p class="wx-muted">No weather reading is inferred for this state.</p></div>`;
  explorerState.selectedDistrict = null;
  explorerState.selectedArea = null;
  explorerState.forecast = null;
  updateBreadcrumb(`India → ${name}`);
  updateBackButton(true);
}

function addDistrictMarkers() {
  const map = explorerState.map;
  explorerState.districtMarkers.forEach((marker) => map.removeLayer(marker));
  explorerState.districtMarkers = [];

  for (const d of explorerState.districts) {
    const marker = L.circleMarker([d.lat, d.lon], {
      radius: d.id === explorerState.selectedDistrict?.id ? 8 : 5.5,
      color: "#07111f",
      weight: 1.2,
      fillColor: "#4bd5e8",
      fillOpacity: 0.95,
    }).addTo(map);
    marker.bindTooltip(safe(d.name), { direction: "top", offset: [0, -5] });
    marker.on("click", () => selectDistrict(d));
    explorerState.districtMarkers.push(marker);
  }
}

function renderDistrictDirectory() {
  const content = byId("wx-detail-content");
  if (!content) return;
  const items = explorerState.districts.map((d) =>
    `<button class="wx-place-button" type="button" data-wx-district="${safe(d.id)}">
      <span>${safe(d.name)}</span><span aria-hidden="true">›</span></button>`).join("");
  content.innerHTML = `<div class="wx-panel-eyebrow">TAMIL NADU</div>
    <h3>Choose a district</h3>
    <p class="wx-muted">Select a marker or district name. Weather is based on representative coordinates.</p>
    <div class="wx-place-list">${items}</div>`;
}

function weatherReaction(forecast) {
  const c = forecast?.current || {};
  const temp = c.temperature_c;
  const rain = c.precipitation_mm;
  const wind = c.wind_kmh;
  const cloud = c.cloud_cover_pct;

  if (![temp, rain, wind, cloud].some((v) => typeof v === "number")) {
    return { mood: "neutral", title: "Weather unknown",
      action: "I can’t read the weather right now. I’ll wait for an update.",
      tip: "Try refreshing the weather data later." };
  }
  if (typeof rain === "number" && rain >= 7) {
    return { mood: "heavy-rain", title: "Heavy rain",
      action: "Whoa, that’s a downpour! I’m holding my umbrella and hurrying to shelter.",
      tip: "Carry rain protection and avoid waterlogged roads." };
  }
  if (typeof rain === "number" && rain >= 2) {
    return { mood: "rain", title: "Rainy",
      action: "Rain is coming down. I’m opening my umbrella to stay dry!",
      tip: "Take care on wet and slippery surfaces." };
  }
  if (typeof rain === "number" && rain > 0) {
    return { mood: "drizzle", title: "Light drizzle",
      action: "Just a little drizzle! I’m smiling and enjoying the tiny raindrops.",
      tip: "A light raincoat or umbrella may be useful." };
  }
  if (typeof temp === "number" && temp >= 38) {
    return { mood: "very-hot", title: "Very hot",
      action: "Phew! I’m wiping my forehead and looking for shade. Time for some water!",
      tip: "Avoid prolonged direct sun and stay hydrated." };
  }
  if (typeof temp === "number" && temp >= 33) {
    return { mood: "hot", title: "Hot",
      action: "It’s hot! I’m fanning myself and trying to cool down.",
      tip: "Drink water regularly, especially outdoors." };
  }
  if (typeof temp === "number" && temp <= 19) {
    return { mood: "cool", title: "Cool",
      action: "Brr! I’m shivering and hugging myself to keep warm.",
      tip: "A light jacket may be comfortable." };
  }
  if (typeof wind === "number" && wind >= 35) {
    return { mood: "windy", title: "Windy",
      action: "Whoosh! The wind is pushing me around. I’m leaning into the breeze.",
      tip: "Secure loose objects and follow local advisories if winds intensify." };
  }
  if (typeof cloud === "number" && cloud >= 70) {
    return { mood: "cloudy", title: "Cloudy",
      action: "It’s cloudy overhead. I’m looking up to see if rain is on the way.",
      tip: "Check the forecast for the chance of rain." };
  }
  return { mood: "pleasant", title: "Comfortable",
    action: "The weather feels lovely! I’m waving hello to you.",
    tip: "Enjoy your day and keep an eye on changing conditions." };
}

function avatarWeatherProps(mood) {
  if (["heavy-rain", "rain", "drizzle"].includes(mood)) {
    const drops = `<g class="wx-rain-drops" fill="none" stroke="#70d9ff" stroke-width="3" stroke-linecap="round">
      <path d="M28 25l-5 12"/><path d="M54 43l-5 12"/><path d="M177 22l-5 12"/><path d="M198 48l-5 12"/><path d="M155 53l-5 12"/></g>`;
    return drops;
  }
  if (["hot", "very-hot"].includes(mood)) {
    return `<g class="wx-sun"><circle cx="183" cy="42" r="15" fill="#ffcc59"/><g stroke="#ffcc59" stroke-width="3" stroke-linecap="round"><path d="M183 18v-7M183 66v7M159 42h-7M207 42h7M166 25l-5-5M200 59l5 5M200 25l5-5M166 59l-5 5"/></g></g>
      <g class="wx-sweat" fill="#70d9ff"><path d="M119 67q-8 12 0 14q8-2 0-14Z"/><path d="M132 79q-6 9 0 11q6-2 0-11Z"/></g>`;
  }
  if (mood === "cool") return `<g class="wx-cold-puffs" fill="#b9eaff" font-size="19" font-weight="700"><text x="28" y="68">~</text><text x="185" y="83">~</text></g>`;
  if (mood === "cloudy") return `<g class="wx-cloud"><path d="M145 43q0-11 12-11q7-17 22-5q14 0 14 15q12 2 8 13h-53q-10-2-3-12Z" fill="#c6d8e6" stroke="#edf8ff" stroke-width="2"/></g>`;
  if (mood === "windy") return `<g class="wx-wind-lines" fill="none" stroke="#b8e8ff" stroke-width="3" stroke-linecap="round"><path d="M24 48h34q8 0 5-7"/><path d="M18 61h25q8 0 5 7"/><path d="M169 96h30q8 0 5-7"/></g>`;
  return "";
}

function avatarCharacterMarkup(mood) {
  const isCold = mood === "cool";
  const isRain = ["rain", "heavy-rain"].includes(mood);
  const isHot = ["hot", "very-hot"].includes(mood);
  const isWindy = mood === "windy";
  const isCloudy = mood === "cloudy";
  const SKIN = "#f3c49b";

  const outfit = {
    pleasant: "#27a9bd", neutral: "#27a9bd", drizzle: "#4aa3df",
    rain: "#f2c230", "heavy-rain": "#f2c230", hot: "#ff8a5c", "very-hot": "#ff6b6b",
    cool: "#3f7cc4", windy: "#59b89c", cloudy: "#8d9db0",
  }[mood] || "#27a9bd";

  // [left path, left hand, right path, right hand]
  const hang = "M79 126 Q70 140 66 152";
  const pose = isCold
    ? ["M79 126 Q91 130 105 145", [105, 145], "M121 126 Q109 130 96 145", [96, 145]]
    : isHot
      ? ["M79 126 Q58 122 52 104", [52, 104], "M121 126 Q129 105 111 83", [111, 83]]
      : isRain
        ? [hang, [66, 152], "M121 126 Q136 120 144 98", [144, 98]]
        : isWindy
          ? ["M79 126 Q53 120 43 104", [43, 104], "M121 126 Q147 118 158 101", [158, 101]]
          : isCloudy
            ? [hang, [66, 152], "M121 126 Q143 108 128 76", [128, 76]]
            : [hang, [66, 152], "M121 126 Q142 111 145 91", [145, 91]];

  const fan = isHot
    ? `<path d="M52 104L32 84Q52 66 72 84Z" fill="#ffd36b" stroke="#c98f1a" stroke-width="2"/>` : "";
  const umbrella = isRain
    ? `<path d="M92 50Q144 -4 196 50Q182 42 170 50Q157 42 144 50Q131 42 118 50Q105 42 92 50Z" fill="#e5484d" stroke="#ffd5d5" stroke-width="2"/>
       <path d="M144 98V50" stroke="#6b4a2f" stroke-width="3.5" stroke-linecap="round"/>` : "";

  const arm = (side, d, h, held = "") =>
    `<g class="wx-arm-grp wx-arm-${side}"><path class="wx-arm-path" d="${d}"/>
      <circle class="wx-hand" cx="${h[0]}" cy="${h[1]}" r="6"/>${held}</g>`;

  const eyes = mood === "very-hot"
    ? `<rect x="78" y="55" width="20" height="12" rx="4" fill="#111"/><rect x="104" y="55" width="20" height="12" rx="4" fill="#111"/><path d="M98 59h6" stroke="#111" stroke-width="2.5"/>`
    : isCold || mood === "heavy-rain"
      ? `<path d="M82 61q6-5 12 0M106 61q6-5 12 0" fill="none" stroke="#382a32" stroke-width="3.2" stroke-linecap="round"/>`
      : isHot
        ? `<path d="M82 62h10M106 62h10" stroke="#382a32" stroke-width="3.2" stroke-linecap="round"/>`
        : isCloudy
          ? `<ellipse cx="88" cy="60" rx="3.2" ry="4.5" fill="#382a32"/><ellipse cx="112" cy="57" rx="3.2" ry="4.5" fill="#382a32"/>`
          : `<ellipse cx="88" cy="62" rx="3.4" ry="4.7" fill="#382a32"/><ellipse cx="112" cy="62" rx="3.4" ry="4.7" fill="#382a32"/>`;

  const mouth = isCold || mood === "heavy-rain"
    ? `<path d="M94 83q7-7 14 0" fill="none" stroke="#9b4e50" stroke-width="3" stroke-linecap="round"/>`
    : isHot
      ? `<ellipse cx="101" cy="84" rx="4" ry="5" fill="#9b4e50"/>`
      : `<path d="M89 81q12 14 24 0" fill="none" stroke="#9b4e50" stroke-width="3" stroke-linecap="round"/>`;

  const headwear = isCold
    ? `<path d="M67 54Q69 18 101 18Q133 18 135 54Z" fill="#e5484d"/><rect x="65" y="48" width="72" height="10" rx="5" fill="#c93a3f"/><circle cx="101" cy="16" r="6" fill="#fff"/>`
    : mood === "hot"
      ? `<path d="M68 50Q101 14 134 50Z" fill="#ff8a5c"/><rect x="104" y="46" width="44" height="6" rx="3" fill="#e0693f"/>`
      : isWindy
        ? `<path d="M74 35q27-20 53 1l-4 8q-24-10-45 2Z" fill="#4c9bb8" stroke="#b9f4f4" stroke-width="2"/>`
        : mood === "drizzle"
          ? `<path d="M66 62Q62 22 101 22Q140 22 136 62Q124 44 101 44Q78 44 66 62Z" fill="#4aa3df"/>`
          : "";

  const scarf = isCold
    ? `<path d="M75 105q26 12 52 0l-4 12q-22 12-44 0Z" fill="#f0b86a" stroke="#ffe2a9" stroke-width="2"/>` : "";

  return `<svg class="wx-character wx-character-${safe(mood)}" viewBox="0 0 220 220"
      role="img" aria-label="Weather buddy acting out ${safe(mood.replace("-", " "))} weather"
      xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="101" cy="202" rx="43" ry="7" fill="#020812" opacity=".3"/>
    ${avatarWeatherProps(mood)}
    <g class="wx-character-body">
      <path d="M87 157l-2 26h-12l-4-25M111 157l4 26h12l4-25" fill="#f0b98c" stroke="#d99770" stroke-width="2" stroke-linejoin="round"/>
      <path d="M73 181q9-5 16 1l3 9H68q-3-5 5-10ZM114 182q9-5 16 0l7 9h-24Z" fill="#304d73" stroke="#7da9d4" stroke-width="2" stroke-linejoin="round"/>
      <path d="M82 113q19-13 38 0l13 45q-31 15-64 0Z" fill="${outfit}" stroke="#ffffff55" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M93 122l8 9 8-9" fill="none" stroke="#ffffffaa" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M92 91v18q9 7 18 0V91Z" fill="#e9ae83"/>
      <circle cx="69" cy="65" r="7" fill="${SKIN}" stroke="#d99770" stroke-width="1.5"/>
      <circle cx="133" cy="65" r="7" fill="${SKIN}" stroke="#d99770" stroke-width="1.5"/>
      <circle cx="101" cy="64" r="33" fill="${SKIN}" stroke="#d99770" stroke-width="2"/>
      <path d="M68 58q1-27 24-34q26-8 41 14l-6 7q-15-13-28-5q-13 8-31 18Z" fill="#3a2530"/>
      ${headwear}
      ${eyes}
      <path d="M100 66l-3 8h6" fill="none" stroke="#d99770" stroke-width="2" stroke-linecap="round"/>
      ${mouth}
      <ellipse cx="80" cy="75" rx="6" ry="3" fill="#ef8d88" opacity=".6"/>
      <ellipse cx="122" cy="75" rx="6" ry="3" fill="#ef8d88" opacity=".6"/>
      ${scarf}
      ${arm("left", pose[0], pose[1], fan)}
      ${arm("right", pose[2], pose[3], umbrella)}
    </g>
  </svg>`;
}
function avatarMarkup(forecast, locationName) {
  const reaction = weatherReaction(forecast);
  const c = forecast?.current || {};
  const speech = explorerState.avatarMessageVisible
    ? `<div class="wx-speech" role="status">${safe(reaction.action)}</div>` : "";
  return `<section class="wx-avatar-card">
    <div class="wx-avatar-heading"><div><div class="wx-panel-eyebrow">WEATHER BUDDY</div>
      <h3>${safe(reaction.title)}</h3></div><span class="wx-temp">${number(c.temperature_c)}°C</span></div>
    <button type="button" class="wx-child wx-mood-${safe(reaction.mood)}"
      id="wx-avatar-button" aria-label="Hear the weather buddy’s reaction to ${safe(locationName)} weather"
      aria-expanded="${explorerState.avatarMessageVisible}">
      <span class="wx-avatar-scene">${avatarCharacterMarkup(reaction.mood)}</span>
      <span class="wx-child-caption">Tap the character to hear its reaction</span>
    </button>
    ${speech}
    <p class="wx-avatar-tip">${safe(reaction.tip)}</p>
  </section>`;
}

function weatherDetails(forecast, scope = "district") {
  const c = forecast?.current || {};
  const where = scope === "place"
    ? "this place’s approximate town coordinates (about a 10 km model grid)"
    : "this district’s representative coordinates";
  return `<div class="wx-weather-stats">
    <div><span>Temperature</span><b>${number(c.temperature_c)} °C</b></div>
    <div><span>Precipitation</span><b>${number(c.precipitation_mm)} mm</b></div>
    <div><span>Humidity</span><b>${number(c.humidity_pct, 0)}%</b></div>
    <div><span>Wind</span><b>${number(c.wind_kmh)} km/h</b></div>
  </div>
  <p class="wx-source-note">${safe(forecast?.source || "Weather source unavailable")} · ${forecast?.retrieved_at ? `updated ${safe(new Date(forecast.retrieved_at).toLocaleString(getLanguage() === "ta" ? "ta-IN" : "en-IN"))}` : "update time unavailable"}${forecast?.stale ? " · cached/stale data" : ""}</p>
  <p class="wx-data-note">Weather is a model/grid estimate at ${where}, not a local weather-station observation. It is not an official warning.</p>`;
}

function dailyOutlook(forecast) {
  const days = Array.isArray(forecast?.daily) ? forecast.daily : [];
  if (!days.length) return "";
  const locale = getLanguage() === "ta" ? "ta-IN" : "en-IN";
  const rows = days.map((d) => {
    const when = d.date ? new Date(`${d.date}T00:00:00`) : null;
    const label = when && !Number.isNaN(when.getTime())
      ? when.toLocaleDateString(locale, { weekday: "short", day: "numeric", month: "short" })
      : safe(d.date || "—");
    return `<li><span>${label}</span><b>${number(d.precipitation_mm)} mm</b>
      <span>${number(d.temp_min_c, 0)}–${number(d.temp_max_c, 0)} °C</span></li>`;
  }).join("");
  return `<div class="wx-panel-eyebrow">7-DAY OUTLOOK</div><ul class="wx-daily">${rows}</ul>`;
}

/* ---------- Places inside a district ---------- */

function clearPlaceMarkers() {
  const map = explorerState.map;
  explorerState.placeMarkers.forEach((marker) => map?.removeLayer(marker));
  explorerState.placeMarkers = [];
}

function resetPlaces() {
  explorerState.placesRequestId += 1; // drop any in-flight places response
  explorerState.placeRequestId += 1;
  explorerState.places = [];
  explorerState.placeTotals = {};
  explorerState.placesStatus = "idle";
  explorerState.placesError = "";
  explorerState.selectedPlace = null;
  explorerState.placeForecast = null;
  explorerState.cityViewOpen = false;
  clearPlaceMarkers();
}

function placeRain(place) {
  const total = explorerState.placeTotals?.[place.id];
  return typeof total === "number" && Number.isFinite(total) ? total : null;
}

function drawPlaceMarkers() {
  const map = explorerState.map;
  if (!map) return;
  clearPlaceMarkers();
  if (explorerState.cityViewOpen) return;
  for (const place of explorerState.places) {
    const selected = place.id === explorerState.selectedPlace?.id;
    const marker = L.circleMarker([place.lat, place.lon], {
      radius: selected ? 8 : 5,
      color: selected ? "#ffffff" : "#07111f",
      weight: selected ? 2 : 1.2,
      fillColor: "#f2c230",
      fillOpacity: 0.95,
    }).addTo(map);
    const rain = placeRain(place);
    marker.bindTooltip(
      `${safe(place.name)}${rain === null ? "" : `<br>7-day rain: ${number(rain)} mm`}`,
      { direction: "top", offset: [0, -5] },
    );
    marker.on("click", () => selectPlace(place));
    marker.bringToFront();
    explorerState.placeMarkers.push(marker);
  }
}

function fitDistrictToPlaces(district) {
  // Chennai's ward layer already frames the city.
  if (district.id === "chennai" || !explorerState.places.length || !explorerState.map) return;
  const points = explorerState.places.map((p) => [p.lat, p.lon]);
  points.push([district.lat, district.lon]);
  explorerState.map.fitBounds(L.latLngBounds(points), { padding: [28, 28], maxZoom: 10 });
}

function renderPlacesSection() {
  const section = byId("wx-places-section");
  if (!section) return;
  const district = explorerState.selectedDistrict;
  const name = safe(district?.name || "this district");
  const eyebrow = `<div class="wx-panel-eyebrow">PLACES IN ${safe((district?.name || "DISTRICT").toUpperCase())}</div>`;
  if (explorerState.placesStatus === "loading") {
    section.innerHTML = `${eyebrow}<p class="wx-muted">Loading places…</p>`;
    return;
  }
  if (explorerState.placesStatus === "error") {
    section.innerHTML = `${eyebrow}<p class="wx-muted">Places could not be loaded: ${safe(explorerState.placesError)}</p>
      <button type="button" class="btn btn-secondary wx-full" id="wx-places-retry">Retry</button>`;
    byId("wx-places-retry")?.addEventListener("click", () => district && loadDistrictPlaces(district));
    return;
  }
  if (!explorerState.places.length) {
    section.innerHTML = `${eyebrow}<p class="wx-muted">No places are configured for ${name} yet.</p>`;
    return;
  }
  const items = explorerState.places.map((place) => {
    const rain = placeRain(place);
    return `<button class="wx-place-button" type="button" data-wx-place="${safe(place.id)}">
      <span>${safe(place.name)}</span>
      <span class="wx-place-rain">${rain === null ? "›" : `${number(rain)} mm`}</span></button>`;
  }).join("");
  const hasTotals = Object.keys(explorerState.placeTotals || {}).length > 0;
  section.innerHTML = `${eyebrow}
    <p class="wx-muted">Select a town on the map or in this list to check its weather.${hasTotals ? " Figures show forecast rain for the next 7 days." : ""}</p>
    <div class="wx-place-list">${items}</div>
    <p class="wx-data-note">Towns are approximate points, not boundaries. Values are model/grid estimates, not station readings.</p>`;
}

async function loadDistrictPlaces(district) {
  const token = ++explorerState.placesRequestId;
  explorerState.places = [];
  explorerState.placeTotals = {};
  explorerState.placesStatus = "loading";
  explorerState.placesError = "";
  clearPlaceMarkers();
  renderPlacesSection();
  try {
    const data = await getJSON(`${API_BASE}/districts/${encodeURIComponent(district.id)}/places`);
    if (token !== explorerState.placesRequestId) return;
    explorerState.places = Array.isArray(data.places) ? data.places : [];
    explorerState.placesStatus = "ready";
    drawPlaceMarkers();
    if (!explorerState.selectedPlace) fitDistrictToPlaces(district);
    renderPlacesSection();
  } catch (error) {
    if (token !== explorerState.placesRequestId) return;
    explorerState.placesStatus = "error";
    explorerState.placesError = error.message;
    renderPlacesSection();
    return;
  }
  // Rain totals are a bonus: the list and map work without them.
  try {
    const data = await getJSON(`${API_BASE}/weather/district-places?district_id=${encodeURIComponent(district.id)}`);
    if (token !== explorerState.placesRequestId) return;
    explorerState.placeTotals = Object.fromEntries(
      (Array.isArray(data.places) ? data.places : []).map((p) => [p.place_id, p.total_mm]),
    );
    drawPlaceMarkers();
    // Don't rebuild the list while a single place is open in the panel.
    if (!explorerState.selectedPlace) renderPlacesSection();
  } catch {
    // Totals unavailable (offline / rate-limited): keep the plain list.
  }
}

async function selectPlace(place) {
  const district = explorerState.selectedDistrict;
  if (!district || !place) return;
  const requestId = ++explorerState.placeRequestId;
  explorerState.selectedPlace = place;
  explorerState.placeForecast = null;
  explorerState.avatarMessageVisible = false;
  drawPlaceMarkers();
  explorerState.map.flyTo([place.lat, place.lon], 11, { duration: 0.6 });
  updateBreadcrumb(`India → Tamil Nadu → ${district.name} → ${place.name}`);
  updateBackButton(true);
  const content = byId("wx-detail-content");
  if (!content) return;
  content.innerHTML = `<div class="wx-loading"><span class="wx-spinner"></span><p>Loading ${safe(place.name)} weather…</p></div>`;
  try {
    const query = `district_id=${encodeURIComponent(district.id)}&place_id=${encodeURIComponent(place.id)}`;
    const forecast = await getJSON(`${API_BASE}/weather/place?${query}`);
    if (requestId !== explorerState.placeRequestId) return;
    explorerState.placeForecast = forecast;
    renderPlaceDetail(place, forecast);
  } catch (error) {
    if (requestId !== explorerState.placeRequestId) return;
    content.innerHTML = `<div class="wx-error"><h3>${safe(place.name)}</h3>
      <p>Weather could not be loaded: ${safe(error.message)}</p>
      <button type="button" class="btn btn-secondary" id="wx-retry">Retry</button>
      <button type="button" class="btn btn-secondary wx-full" id="wx-place-back">← ${safe(district.name)} places</button></div>`;
    byId("wx-retry")?.addEventListener("click", () => selectPlace(place));
    byId("wx-place-back")?.addEventListener("click", backToDistrict);
  }
}

function renderPlaceDetail(place, forecast) {
  const content = byId("wx-detail-content");
  const district = explorerState.selectedDistrict;
  if (!content || !district) return;
  content.innerHTML = `<div class="wx-panel-eyebrow">SELECTED PLACE</div>
    <h3>${safe(place.name)}</h3>
    <p class="wx-muted">${safe(district.name)} district, Tamil Nadu · approximate town coordinates</p>
    ${avatarMarkup(forecast, place.name)}
    ${weatherDetails(forecast, "place")}
    <div class="wx-section-divider"></div>
    ${dailyOutlook(forecast)}
    <button type="button" class="btn btn-secondary wx-full" id="wx-place-back">← ${safe(district.name)} places</button>`;
  byId("wx-avatar-button")?.addEventListener("click", () => {
    explorerState.avatarMessageVisible = !explorerState.avatarMessageVisible;
    renderPlaceDetail(place, forecast);
  });
  byId("wx-place-back")?.addEventListener("click", backToDistrict);
}

function backToDistrict() {
  const district = explorerState.selectedDistrict;
  if (!district) return;
  explorerState.placeRequestId += 1; // cancel any in-flight place request
  explorerState.selectedPlace = null;
  explorerState.placeForecast = null;
  explorerState.avatarMessageVisible = false;
  explorerState.cityViewOpen = false;
  updateBreadcrumb(`India → Tamil Nadu → ${district.name}`);
  if (!explorerState.forecast) {
    selectDistrict(district);
    return;
  }
  drawPlaceMarkers();
  if (district.id === "chennai") explorerState.map.flyTo([13.0827, 80.2707], 11, { duration: 0.6 });
  else if (explorerState.places.length) fitDistrictToPlaces(district);
  else explorerState.map.flyTo([district.lat, district.lon], 8, { duration: 0.6 });
  renderDistrictDetail(district, explorerState.forecast);
}

async function selectDistrict(district) {
  if (!district) return;
  const requestId = ++explorerState.requestId;
  explorerState.selectedDistrict = district;
  explorerState.selectedArea = null;
  explorerState.avatarMessageVisible = false;
  explorerState.forecast = null;
  resetPlaces();
  // A previous district's ward polygons (Chennai) must not linger under another district.
  if (explorerState.localLayer) {
    explorerState.map.removeLayer(explorerState.localLayer);
    explorerState.localLayer = null;
  }
  addDistrictMarkers();
  explorerState.map.flyTo([district.lat, district.lon], district.id === "chennai" ? 10 : 8, { duration: 0.7 });
  updateBreadcrumb(`India → Tamil Nadu → ${district.name}`);
  updateBackButton(true);
  const content = byId("wx-detail-content");
  content.innerHTML = `<div class="wx-loading"><span class="wx-spinner"></span><p>Loading ${safe(district.name)} weather…</p></div>`;

  // Places load in parallel and independently of the district forecast.
  loadDistrictPlaces(district);

  try {
    const forecast = await getJSON(`${API_BASE}/weather/forecast?district_id=${encodeURIComponent(district.id)}`);
    if (requestId !== explorerState.requestId) return;
    explorerState.forecast = forecast;
    // The user may have opened a place while the district forecast was still loading.
    if (explorerState.selectedPlace) return;
    renderDistrictDetail(district, forecast);
    if (district.id === "chennai") loadChennaiBoundaries();
  } catch (error) {
    if (requestId !== explorerState.requestId) return;
    if (explorerState.selectedPlace) return;
    content.innerHTML = `<div class="wx-error"><h3>${safe(district.name)}</h3>
      <p>Weather could not be loaded: ${safe(error.message)}</p>
      <button type="button" class="btn btn-secondary" id="wx-retry">Retry</button></div>
      <div class="wx-section-divider"></div>
      <div id="wx-places-section"></div>`;
    byId("wx-retry")?.addEventListener("click", () => selectDistrict(district));
    renderPlacesSection();
  }
}

function renderDistrictDetail(district, forecast) {
  const content = byId("wx-detail-content");
  if (!content) return;
  content.innerHTML = `<div class="wx-panel-eyebrow">SELECTED DISTRICT</div>
    <h3>${safe(district.name)}, Tamil Nadu</h3>
    <p class="wx-muted">Representative coordinate weather view</p>
    ${avatarMarkup(forecast, district.name)}
    ${weatherDetails(forecast)}
    <div class="wx-section-divider"></div>
    <div id="wx-places-section"></div>
    <div class="wx-section-divider"></div>
    <div class="wx-panel-eyebrow">GEOGRAPHIC DETAIL</div>
    <h4>${district.id === "chennai" ? "Greater Chennai" : district.name}</h4>
    <p class="wx-muted">${district.id === "chennai"
      ? "Open the city view to inspect supported corporation zones or wards."
      : "Town and taluk boundaries are not included in the current district directory. Use the places above to check individual towns."}</p>
    ${district.id === "chennai"
      ? '<button type="button" class="btn btn-primary wx-full" id="wx-open-city">Open Chennai map ↗</button>'
      : '<div class="wx-boundary-unavailable">Detailed boundaries are not configured for this district.</div>'}`;
  renderPlacesSection();
  byId("wx-avatar-button")?.addEventListener("click", () => {
    explorerState.avatarMessageVisible = !explorerState.avatarMessageVisible;
    renderDistrictDetail(district, forecast);
  });
  byId("wx-open-city")?.addEventListener("click", () => openChennaiView(district));
}

function openChennaiView(district) {
  // Hide the place markers while the 200 ward polygons are being explored.
  explorerState.cityViewOpen = true;
  explorerState.selectedPlace = null;
  explorerState.placeRequestId += 1;
  drawPlaceMarkers();
  explorerState.map.flyTo([13.0827, 80.2707], 11, { duration: 0.8 });
  updateBreadcrumb("India → Tamil Nadu → Chennai → local boundaries");
  const content = byId("wx-detail-content");
  if (content) {
    content.innerHTML = `<div class="wx-panel-eyebrow">CITY EXPLORER</div><h3>Chennai</h3>
      <p class="wx-muted">The map is zoomed to Chennai. Real ward boundaries will appear if a valid GeoJSON file is configured.</p>
      <div id="wx-boundary-status" class="wx-boundary-unavailable">Checking for Chennai boundary data…</div>
      ${avatarMarkup(explorerState.forecast, "Chennai")}
      ${weatherDetails(explorerState.forecast)}
      <button type="button" class="btn btn-secondary wx-full" id="wx-city-back">← Chennai district details</button>`;
  }
  byId("wx-avatar-button")?.addEventListener("click", () => {
    explorerState.avatarMessageVisible = !explorerState.avatarMessageVisible;
    openChennaiView(district);
  });
  byId("wx-city-back")?.addEventListener("click", () => {
    explorerState.cityViewOpen = false;
    drawPlaceMarkers();
    renderDistrictDetail(district, explorerState.forecast);
  });
  loadChennaiBoundaries();
}

async function loadChennaiBoundaries() {
  const status = byId("wx-boundary-status");
  if (explorerState.selectedDistrict?.id !== "chennai") return;
  const url = "/data/geo/chennai-wards.geojson";
  const sourceUrl = "https://github.com/datameet/Municipal_Spatial_Data/blob/master/Chennai/Wards.geojson";
  const licenseUrl = "https://creativecommons.org/licenses/by-sa/2.5/in/";
  try {
    const geojson = await getJSON(url);
    if (!geojson || geojson.type !== "FeatureCollection" || !Array.isArray(geojson.features)) {
      throw new Error("GeoJSON must be a FeatureCollection");
    }
    const wardNumbers = geojson.features.map(feature => Number(feature?.properties?.Ward_No));
    const uniqueWards = new Set(wardNumbers);
    if (geojson.features.length !== 200 || uniqueWards.size !== 200 ||
        Array.from({length: 200}, (_, i) => i + 1).some(number => !uniqueWards.has(number))) {
      throw new Error("Expected one polygon for each Chennai ward numbered 1–200");
    }
    if (explorerState.localLayer) explorerState.map.removeLayer(explorerState.localLayer);
    explorerState.localLayer = L.geoJSON(geojson, {
      style: () => ({ color: "#4bd5e8", weight: 1.5, fillColor: "#1c7184", fillOpacity: 0.18 }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties || {};
        const ward = p.ward_no ?? p.Ward_No ?? p.WARD_NO ?? p.ward ?? p.Ward;
        const zone = p.zone_name ?? p.Zone_Name ?? p.ZONE_NAME ?? p.zone ?? p.Zone;
        const name = p.name || p.NAME || p.ward_name || p.WARD_NAME ||
          (ward != null ? `Ward ${ward}${zone ? ` · ${zone}` : ""}` : null) ||
          p.zone_name || p.ZONE_NAME || p.id || "Mapped area";
        layer.bindTooltip(safe(name), { sticky: true });
        layer.on("mouseover", () => layer.setStyle({ fillOpacity: 0.42, weight: 2.5 }));
        layer.on("mouseout", () => explorerState.localLayer?.resetStyle(layer));
        layer.on("click", () => selectLocalArea(String(name), p));
      },
    }).addTo(explorerState.map);
    if (explorerState.localLayer.getBounds().isValid()) {
      explorerState.map.fitBounds(explorerState.localLayer.getBounds(), { padding: [16, 16] });
    }
    if (status) {
      status.innerHTML = `<strong>200 Chennai ward boundaries loaded.</strong> Hover over a polygon to see its ward number and zone, or select it for details. Historical community-curated boundary data; verify against the latest GCC Gazette for authoritative use. <a href="${sourceUrl}" target="_blank" rel="noreferrer">Source: DataMeet / Transparent Chennai</a> · <a href="${licenseUrl}" target="_blank" rel="noreferrer">CC BY-SA 2.5 India</a>.`;
    }
  } catch (error) {
    if (status) status.textContent = `Chennai ward boundaries could not be loaded: ${error.message}. Check the deployed GeoJSON asset and its 200 ward features.`;
  }
}

function selectLocalArea(name, properties) {
  explorerState.selectedArea = { name, properties };
  updateBreadcrumb(`India → Tamil Nadu → Chennai → ${name}`);
  const content = byId("wx-detail-content");
  if (!content) return;
  content.innerHTML = `<div class="wx-panel-eyebrow">SELECTED MAP FEATURE</div><h3>${safe(name)}</h3>
    <p class="wx-muted">The selected boundary comes from the configured GeoJSON. Confirm the source metadata to determine its administrative level.</p>
    ${avatarMarkup(explorerState.forecast, name)}
    ${weatherDetails(explorerState.forecast)}
    <div class="wx-data-note">The existing weather API provides Chennai district reference-point weather, not ward-specific observations. The avatar therefore represents the available district-level estimate.</div>
    <button type="button" class="btn btn-secondary wx-full" id="wx-area-back">← Chennai map</button>`;
  byId("wx-avatar-button")?.addEventListener("click", () => {
    explorerState.avatarMessageVisible = !explorerState.avatarMessageVisible;
    selectLocalArea(name, properties);
  });
  byId("wx-area-back")?.addEventListener("click", () => openChennaiView(explorerState.selectedDistrict));
}

function showNotice(message) {
  const content = byId("wx-detail-content");
  if (content && !explorerState.selectedDistrict) {
    content.innerHTML = `<div class="wx-empty"><h3>Map notice</h3><p>${safe(message)}</p></div>`;
  }
}

async function bootWeatherExplorer() {
  // app.js owns the legacy marker map; this enhancement replaces only the map
  // panel body after that module has initialized. Other dashboard views remain.
  const waitForDistricts = async () => {
    for (let i = 0; i < 80; i++) {
      if (window.L && byId("tn-map")) {
        try {
          const data = await getJSON(`${API_BASE}/districts`);
          if (Array.isArray(data.districts) && data.districts.length) return data.districts;
        } catch {}
      }
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
    return [];
  };

  const districts = await waitForDistricts();
  if (!districts.length) return;
  explorerState.districts = districts;
  explorerMarkup();
  initExplorerMap();
  addDistrictMarkers();

  byId("wx-detail-content")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-wx-district]");
    if (button) {
      const item = explorerState.districts.find((d) => d.id === button.dataset.wxDistrict);
      if (item) selectDistrict(item);
      return;
    }
    const placeButton = event.target.closest("[data-wx-place]");
    if (placeButton) {
      const place = explorerState.places.find((p) => p.id === placeButton.dataset.wxPlace);
      if (place) selectPlace(place);
    }
  });

  byId("wx-back")?.addEventListener("click", () => {
    if (explorerState.selectedPlace) {
      backToDistrict();
      return;
    }
    if (explorerState.selectedArea || explorerState.selectedDistrict?.id === "chennai") {
      if (explorerState.selectedDistrict?.id === "chennai") {
        explorerState.selectedArea = null;
        explorerState.cityViewOpen = false;
        if (explorerState.localLayer) explorerState.map.removeLayer(explorerState.localLayer);
        explorerState.localLayer = null;
        drawPlaceMarkers();
        explorerState.map.setView([13.0827, 80.2707], 10);
        renderDistrictDetail(explorerState.selectedDistrict, explorerState.forecast);
        updateBreadcrumb("India → Tamil Nadu → Chennai");
      } else {
        explorerState.selectedArea = null;
        renderDistrictDirectory();
        updateBreadcrumb("India → Tamil Nadu → select a district marker");
      }
    } else {
      explorerState.selectedDistrict = null;
      explorerState.forecast = null;
      explorerState.selectedArea = null;
      resetPlaces(); // the previous district's town markers must not stay on the state map
      addDistrictMarkers();
      explorerState.map.setView([22.7, 79.0], 4.5);
      updateBreadcrumb("India · select a state or Tamil Nadu district");
      updateBackButton(false);
      renderDistrictDirectory();
    }
  });

  // Default district mirrors the existing app's saved district when possible.
  const preferred = districts.find((d) => d.id === "chennai");
  if (preferred) renderDistrictDirectory();
  setTimeout(() => explorerState.map?.invalidateSize(), 200);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootWeatherExplorer, { once: true });
} else {
  bootWeatherExplorer();
}
