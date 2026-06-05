import { nasa } from "../core/api/endpoints.js";

export async function loadNASAGallery() {
  try {
    const r = await nasa.capturas(12);
    const d = await r.json();
    const gallery = document.getElementById("nasa-gallery");
    const empty = document.getElementById("nasa-empty");

    const storageLabel =
      d.storage === "s3" ? ` · S3 ${d.bucket || ""}` : d.storage === "dataset" ? " · dataset local" : "";
    document.getElementById("nasa-total").textContent =
      d.total > 0
        ? `${d.total} imagens${storageLabel}`
        : "Nenhuma imagem no S3 ainda";

    if (!d.capturas || d.capturas.length === 0) {
      if (empty) {
        empty.innerHTML =
          '<i class="bi bi-globe-americas"></i> Nenhuma imagem NASA no S3 ainda.<br>' +
          '<span style="font-size:11px">Configure <code>S3_BUCKET_IMAGES</code> no .env e rode ' +
          '<code>python -m app.cron.capture_nasa_data</code> ou o workflow <code>NASA Capture</code>.</span>';
      }
      return;
    }

    empty?.remove();
    d.capturas.forEach((cap) => {
      const div = document.createElement("div");
      div.className = "nasa-card";
      const ts = new Date(cap.criado_em).toLocaleString("pt-BR", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
      const thumb = cap.url
        ? `<img src="${cap.url}" alt="${cap.arquivo}" loading="lazy" width="120" height="80">`
        : `<i class="bi bi-globe-americas"></i>`;
      div.innerHTML = `
        <div class="nasa-card-thumb">${thumb}</div>
        <div class="nasa-card-body">
          <div class="nasa-card-title">${cap.arquivo}</div>
          <div class="nasa-card-meta">${ts} · ${cap.tamanho_kb} KB</div>
        </div>`;
      gallery.appendChild(div);
    });
  } catch {
    const emptyEl = document.getElementById("nasa-empty");
    if (emptyEl) {
      emptyEl.className = "section-error";
      emptyEl.style.gridColumn = "1/-1";
      emptyEl.innerHTML = '<i class="bi bi-exclamation-circle"></i> Galeria indisponível';
    }
  }
}
