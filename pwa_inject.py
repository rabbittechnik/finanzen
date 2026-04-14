"""Link Web-App-Manifest + Service Worker im Hauptfenster (wie installierbare PWA)."""
from __future__ import annotations

import streamlit.components.v1 as components


def inject_pwa_tags() -> None:
    """Registriert manifest.json und /sw.js im parent document (einmal pro Session)."""
    components.html(
        """
<script>
(function () {
  var p = window.parent;
  if (!p || !p.document) return;
  try {
    var d = p.document;
    var head = d.head;
    if (head && !d.querySelector('link[rel="manifest"]')) {
      var m = d.createElement("link");
      m.rel = "manifest";
      m.href = "/manifest.json";
      head.appendChild(m);
    }
    if (p.navigator && p.navigator.serviceWorker) {
      p.navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
    }
  } catch (e) {}
})();
</script>
        """,
        height=0,
        width=0,
    )
