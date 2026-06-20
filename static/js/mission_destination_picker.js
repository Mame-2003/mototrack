document.addEventListener("DOMContentLoaded", async () => {
  const container = document.getElementById("destinationPickerMap");
  const latitudeInput = document.getElementById("id_destination_latitude");
  const longitudeInput = document.getElementById("id_destination_longitude");
  if (!container || !latitudeInput || !longitudeInput) return;

  try {
    await window.loadGoogleMaps();
  } catch (_error) {
    window.renderGoogleMapsFallback(container, "Sénégal");
    return;
  }

  const map = new google.maps.Map(container, {
    center: { lat: 14.4974, lng: -14.4524 },
    zoom: 7,
    minZoom: 7,
    restriction: {
      latLngBounds: { north: 16.8, south: 12.0, west: -17.7, east: -11.3 },
      strictBounds: true,
    },
    mapTypeControl: true,
    streetViewControl: false,
  });
  let marker = null;

  const setDestination = (lat, lng) => {
    latitudeInput.value = lat.toFixed(7);
    longitudeInput.value = lng.toFixed(7);
    const position = { lat, lng };
    if (!marker) marker = new google.maps.Marker({ map, position, title: "Destination de la mission" });
    else marker.setPosition(position);
  };

  const initial = { lat: Number(latitudeInput.value), lng: Number(longitudeInput.value) };
  if (isInsideSenegal(initial)) {
    setDestination(initial.lat, initial.lng);
    map.setCenter(initial);
    map.setZoom(13);
  }

  map.addListener("click", (event) => {
    const point = { lat: event.latLng.lat(), lng: event.latLng.lng() };
    if (isInsideSenegal(point)) setDestination(point.lat, point.lng);
  });

  function isInsideSenegal(point) {
    return Number.isFinite(point.lat) && Number.isFinite(point.lng)
      && point.lat >= 12.0 && point.lat <= 16.8
      && point.lng >= -17.7 && point.lng <= -11.3;
  }
});
