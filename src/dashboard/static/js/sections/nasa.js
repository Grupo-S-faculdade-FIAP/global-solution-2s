import { nasa } from "../core/api/endpoints.js";

export async function loadNASAGallery() {
  try {
    const r = await nasa.capturas(12);
    const d = await r.json();
    const gallery = document.getElementById("nasa-gallery");
    const empty = document.getElementById("nasa-empty");

    document.getElementById("nasa-total").textContent =
      d.total > 0 ? `${d.total} imagens disponíveis` : "Nenhuma imagem capturada ainda";

    if (!d.capturas || d.capturas.length === 0) {
      if (empty) {
        empty.innerHTML =
          '<i class="bi bi-globe-americas"></i> Nenhuma imagem NASA capturada ainda.<br>' +
          '<span style="font-size:11px">Execute <code>build_dataset_nasa.command</code> para baixar o histórico.</span>';
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
