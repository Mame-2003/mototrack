(function () {
  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/service-worker.js").catch(function () {
      // L'application reste utilisable meme si l'installation PWA echoue.
    });
  });
})();
