function formatMapsPoint(point) {
  return `${Number(point.lat).toFixed(7)},${Number(point.lng).toFixed(7)}`;
}

function googleDirectionsUrl(origin, destination) {
  const start = formatMapsPoint(origin);
  const end = formatMapsPoint(destination);
  return `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(start)}&destination=${encodeURIComponent(end)}&travelmode=driving&dir_action=navigate`;
}

window.loadGoogleMaps = function loadGoogleMaps() {
  if (window.google?.maps) return Promise.resolve(window.google.maps);
  if (window.googleMapsPromise) return window.googleMapsPromise;
  const key = document.body.dataset.googleMapsKey;
  if (!key) return Promise.reject(new Error("GOOGLE_MAPS_API_KEY manquante"));

  window.googleMapsPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&v=weekly&language=fr&region=SN`;
    script.async = true;
    script.onload = () => resolve(window.google.maps);
    script.onerror = () => reject(new Error("Impossible de charger Google Maps"));
    document.head.appendChild(script);
  });
  return window.googleMapsPromise;
};

window.renderGoogleMapsFallback = function renderGoogleMapsFallback(container, query = "Senegal") {
  container.classList.add("google-map-fallback");
  container.innerHTML = `
    <iframe title="Google Maps"
      src="https://www.google.com/maps?q=${encodeURIComponent(query)}&hl=fr&output=embed"
      loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
    <div class="google-map-key-note">
      <strong>Mode Google Maps simplifie</strong>
      <span>Ajoutez GOOGLE_MAPS_API_KEY dans .env pour activer le suivi interactif.</span>
    </div>`;
};

window.renderGoogleMapsDirectionsFallback = function renderGoogleMapsDirectionsFallback(container, origin, destination) {
  container.classList.add("google-map-fallback");
  container.innerHTML = `
    <iframe title="Itineraire Google Maps"
      src="${googleDirectionsUrl(origin, destination)}&hl=fr&output=embed"
      loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
    <div class="google-map-key-note">
      <strong>Trajet affiche en mode simplifie</strong>
      <span>La position de la moto est utilisee comme point de depart.</span>
    </div>`;
};

window.renderFallbackMotoMarker = function renderFallbackMotoMarker(container, registration = "Moto") {
  const marker = document.createElement("div");
  marker.className = "fallback-moto-marker";
  marker.innerHTML = `
    <span class="fallback-moto-label">${registration}</span>
    <span class="fallback-moto-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24">
        <circle cx="5.5" cy="17.5" r="3"></circle>
        <circle cx="18.5" cy="17.5" r="3"></circle>
        <path d="M8.5 17.5h7M7 8h4l3 6h4.5M10 8l-2 5h7M16 6h3"></path>
      </svg>
    </span>`;
  container.appendChild(marker);
};

window.motoGoogleMapIcon = function motoGoogleMapIcon(isFresh) {
  const color = isFresh ? "#c64035" : "#e0a11c";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="58" height="58" viewBox="0 0 58 58">
    <circle cx="29" cy="27" r="23" fill="${color}" stroke="#fff" stroke-width="4"/>
    <path d="M20 35a6 6 0 1 1-12 0 6 6 0 0 1 12 0Zm30 0a6 6 0 1 1-12 0 6 6 0 0 1 12 0Z"
      fill="none" stroke="#fff" stroke-width="3"/>
    <path d="M20 35h18M17 20h9l7 12h11M25 20l-5 11h14M37 16h8"
      fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M24 52 29 57 34 52" fill="${color}" stroke="#fff" stroke-width="2"/>
  </svg>`;
  return {
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(58, 58),
    anchor: new google.maps.Point(29, 57),
  };
};
