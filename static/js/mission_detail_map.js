document.addEventListener("DOMContentLoaded", async () => {
  const container = document.getElementById("missionDestinationMap");
  if (!container) return;

  const status = document.querySelector("[data-gps-map-status]");
  const destination = {
    lat: parseCoordinate(container.dataset.destinationLat),
    lng: parseCoordinate(container.dataset.destinationLng),
  };
  const hasDestination = container.dataset.destinationLat !== ""
    && container.dataset.destinationLng !== ""
    && isInsideSenegal(destination);
  const initialPosition = {
    lat: parseCoordinate(container.dataset.initialLat),
    lng: parseCoordinate(container.dataset.initialLng),
    recue_le: container.dataset.initialReceived,
    moto_immatriculation: container.dataset.motoRegistration || "Moto",
  };
  const hasInitialPosition = isInsideSenegal(initialPosition);

  try {
    await window.loadGoogleMaps();
  } catch (_error) {
    const query = hasDestination
      ? `${destination.lat},${destination.lng}`
      : hasInitialPosition
        ? `${initialPosition.lat},${initialPosition.lng}`
        : `${container.dataset.address}, Senegal`;
    window.renderGoogleMapsFallback(container, query);
    if (hasInitialPosition) {
      window.renderFallbackMotoMarker(container, initialPosition.moto_immatriculation);
      updateStatus(`Position de ${initialPosition.moto_immatriculation} affichee en mode simplifie`, true);
    } else {
      updateStatus(`Aucune position GPS recue pour ${container.dataset.motoRegistration || "cette moto"}`, false);
    }
    return;
  }

  const map = new google.maps.Map(container, {
    center: hasInitialPosition
      ? { lat: initialPosition.lat, lng: initialPosition.lng }
      : hasDestination
        ? destination
        : { lat: 14.4974, lng: -14.4524 },
    zoom: hasInitialPosition ? 14 : hasDestination ? 13 : 7,
    minZoom: 7,
    restriction: {
      latLngBounds: { north: 16.8, south: 12.0, west: -17.7, east: -11.3 },
      strictBounds: true,
    },
    mapTypeControl: true,
    streetViewControl: false,
  });

  const routeLegend = document.createElement("div");
  routeLegend.className = "mission-route-legend";
  routeLegend.innerHTML = `
    <strong>Legende</strong>
    <span><i class="legend-moto"></i> Moto du livreur</span>
    <span><i class="legend-destination"></i> Destination client</span>
    <small>Le bouton Google Maps ouvre le trajet routier exact.</small>`;
  container.appendChild(routeLegend);

  if (hasDestination) {
    new google.maps.Marker({
      map,
      position: destination,
      title: `${container.dataset.client} - ${container.dataset.address}`,
      label: { text: "D", color: "#fff", fontWeight: "700" },
    });
  }

  let motoMarker = null;
  let infoWindow = null;
  let fitted = false;

  if (hasInitialPosition) {
    drawMoto(initialPosition);
  } else {
    updateStatus(`Aucune position GPS recue pour ${container.dataset.motoRegistration || "cette moto"}`, false);
  }

  async function refreshMoto() {
    const response = await fetch(
      `/api/gps/history/${container.dataset.motoId}/?limit=1`,
      { credentials: "same-origin" },
    );
    if (!response.ok) {
      updateStatus("Impossible de recuperer la position GPS", false);
      return;
    }
    const positions = await response.json();
    if (!positions.length) {
      updateStatus(`Aucune position GPS recue pour ${container.dataset.motoRegistration || "cette moto"}`, false);
      return;
    }
    drawMoto(positions[0]);
  }

  function drawMoto(position) {
    const current = {
      lat: parseCoordinate(position.latitude ?? position.lat),
      lng: parseCoordinate(position.longitude ?? position.lng),
    };
    if (!isInsideSenegal(current)) {
      updateStatus("Position GPS hors zone Senegal", false);
      return;
    }

    const receivedAt = position.recue_le ? new Date(position.recue_le) : new Date();
    const receivedTime = receivedAt.getTime();
    const hasValidDate = Number.isFinite(receivedTime);
    const isFresh = hasValidDate && Date.now() - receivedTime <= 10 * 60 * 1000;
    const registration = position.moto_immatriculation || container.dataset.motoRegistration || "Moto";

    if (!motoMarker) {
      motoMarker = new google.maps.Marker({
        map,
        position: current,
        title: registration,
        icon: window.motoGoogleMapIcon(isFresh),
        zIndex: 10,
      });
      infoWindow = new google.maps.InfoWindow();
      motoMarker.addListener("click", () => infoWindow.open({ map, anchor: motoMarker }));
    } else {
      motoMarker.setPosition(current);
    }

    motoMarker.setIcon(window.motoGoogleMapIcon(isFresh));
    infoWindow.setContent(`<div class="google-map-info"><strong>${registration}</strong>
      <span>${isFresh ? "Position actuelle" : "Derniere position connue"}</span>
      <small>${current.lat.toFixed(6)}, ${current.lng.toFixed(6)}</small>
      <time>${hasValidDate ? receivedAt.toLocaleString("fr-FR") : "Date GPS non disponible"}</time></div>`);
    updateStatus(
      `Position de ${registration} recue ${hasValidDate ? receivedAt.toLocaleString("fr-FR") : ""}`,
      isFresh,
    );

    if (hasDestination) {
      updateStatus("Position moto et destination affichees. Cliquez sur Ouvrir dans Google Maps pour le trajet routier.", true);
    }

    if (!fitted) {
      if (hasDestination) {
        const bounds = new google.maps.LatLngBounds();
        bounds.extend(current);
        bounds.extend(destination);
        map.fitBounds(bounds, 55);
      } else {
        map.setCenter(current);
        map.setZoom(14);
      }
      fitted = true;
    }
  }

  function updateStatus(message, good) {
    if (!status) return;
    status.innerHTML = `<i class="dot ${good ? "online" : "stale"}"></i> ${message}`;
  }

  refreshMoto();
  window.setInterval(refreshMoto, 10000);

  function isInsideSenegal(point) {
    return Number.isFinite(point.lat) && Number.isFinite(point.lng)
      && point.lat >= 12.0 && point.lat <= 16.8
      && point.lng >= -17.7 && point.lng <= -11.3;
  }

  function parseCoordinate(value) {
    if (value === null || value === undefined || value === "") return NaN;
    return Number(String(value).trim().replace(",", "."));
  }
});
