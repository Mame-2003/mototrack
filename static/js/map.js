document.addEventListener("DOMContentLoaded", async () => {
  const container = document.getElementById("fleetMap");
  const selector = document.getElementById("historyMoto");
  const historyToggle = document.getElementById("showHistoryLine");
  const counter = document.getElementById("positionCount");
  if (!container) return;

  try {
    await window.loadGoogleMaps();
  } catch (_error) {
    window.renderGoogleMapsFallback(container, "Sénégal");
    return;
  }

  const senegalBounds = { north: 16.75, south: 12.20, west: -17.70, east: -11.30 };
  const map = new google.maps.Map(container, {
    center: { lat: 14.4974, lng: -14.4524 },
    zoom: 7,
    minZoom: 7,
    restriction: { latLngBounds: senegalBounds, strictBounds: true },
    mapTypeControl: true,
    mapTypeControlOptions: { mapTypeIds: ["roadmap", "satellite"] },
    streetViewControl: false,
    fullscreenControl: true,
  });
  let markers = [];
  let historyLine = null;
  let initialFit = false;

  const clearMarkers = () => {
    markers.forEach((marker) => marker.setMap(null));
    markers = [];
  };

  async function loadLatest() {
    const response = await fetch("/api/gps/latest/", { credentials: "same-origin" });
    if (!response.ok) return;
    const positions = await response.json();
    clearMarkers();
    const bounds = new google.maps.LatLngBounds();
    let visibleCount = 0;
    const selectedMotoId = selector?.value || "";

    positions.forEach((position) => {
      const motoId = position.moto_id ?? position.moto;
      if (selectedMotoId && String(motoId) !== selectedMotoId) return;
      const point = { lat: Number(position.latitude), lng: Number(position.longitude) };
      if (!isInsideSenegal(point)) return;
      visibleCount += 1;
      bounds.extend(point);
      const receivedAt = new Date(position.recue_le);
      const isFresh = Date.now() - receivedAt.getTime() <= 10 * 60 * 1000;
      const marker = new google.maps.Marker({
        map,
        position: point,
        title: position.moto_immatriculation,
        icon: window.motoGoogleMapIcon(isFresh),
      });
      const info = new google.maps.InfoWindow({
        content: `<div class="google-map-info"><strong>${position.moto_immatriculation}</strong>
          <span>${isFresh ? "Signal récent" : "Signal ancien"}</span>
          <small>${position.latitude}, ${position.longitude}</small>
          <time>${receivedAt.toLocaleString("fr-FR")}</time></div>`,
      });
      marker.addListener("click", () => info.open({ map, anchor: marker }));
      markers.push(marker);
    });

    counter.textContent = `${visibleCount} moto${visibleCount > 1 ? "s" : ""}`;
    if (visibleCount && !initialFit) {
      map.fitBounds(bounds, 60);
      initialFit = true;
    }
  }

  async function loadHistory() {
    historyLine?.setMap(null);
    historyLine = null;
    if (!selector?.value || !historyToggle?.checked) return;
    const response = await fetch(`/api/gps/history/${selector.value}/?limit=300`, { credentials: "same-origin" });
    if (!response.ok) return;
    const positions = await response.json();
    const points = positions.reverse()
      .map((position) => ({ lat: Number(position.latitude), lng: Number(position.longitude) }))
      .filter(isInsideSenegal);
    if (!points.length) return;
    historyLine = new google.maps.Polyline({
      map,
      path: points,
      strokeColor: "#c64035",
      strokeOpacity: .55,
      strokeWeight: 2,
    });
    const bounds = new google.maps.LatLngBounds();
    points.forEach((point) => bounds.extend(point));
    map.fitBounds(bounds, 55);
  }

  selector?.addEventListener("change", () => {
    initialFit = false;
    loadLatest();
    loadHistory();
  });
  historyToggle?.addEventListener("change", loadHistory);
  loadLatest();
  window.setInterval(loadLatest, 15000);

  function isInsideSenegal(point) {
    return point.lat >= 12.20 && point.lat <= 16.75
      && point.lng >= -17.70 && point.lng <= -11.30;
  }
});
