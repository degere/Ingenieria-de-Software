
(function () {
  const fmt = (n) => "$" + n.toLocaleString("es-CL");

  // --- Selección de asientos: lista, total y botón continuar (R21) ---
  const formAsientos = document.querySelector("[data-asientos]");
  if (formAsientos) {
    const checks = formAsientos.querySelectorAll('input[name="asientos"]');
    const tipo = formAsientos.querySelector('[name="tipo_entrada"]');
    const lista = formAsientos.querySelector("[data-lista]");
    const total = formAsientos.querySelector("[data-total]");
    const boton = formAsientos.querySelector("[data-continuar]");
    const actualizar = () => {
      const sel = [...checks].filter((c) => c.checked);
      const precio = Number(tipo.selectedOptions[0].dataset.precio);
      lista.textContent = sel.length ? sel.map((c) => c.value).join(", ") : "Ninguno";
      total.textContent = fmt(sel.length * precio);
      boton.disabled = sel.length === 0;
    };
    checks.forEach((c) => c.addEventListener("change", actualizar));
    tipo.addEventListener("change", actualizar);
    actualizar();
  }

  // --- Confitería: cantidades y subtotal (R29) ---
  const formConf = document.querySelector("[data-confiteria]");
  if (formConf) {
    const base = Number(formConf.dataset.base || 0);
    const inputs = formConf.querySelectorAll("input[data-precio]");
    const sub = formConf.querySelector("[data-subtotal-conf]");
    const total = formConf.querySelector("[data-total]");
    const actualizar = () => {
      let s = 0;
      inputs.forEach((i) => (s += Number(i.value || 0) * Number(i.dataset.precio)));
      sub.textContent = fmt(s);
      total.textContent = fmt(base + s);
    };
    formConf.querySelectorAll("[data-accion]").forEach((b) =>
      b.addEventListener("click", () => {
        const i = b.parentElement.querySelector("input");
        const v = Number(i.value || 0) + (b.dataset.accion === "mas" ? 1 : -1);
        i.value = Math.max(0, Math.min(20, v));
        actualizar();
      })
    );
    inputs.forEach((i) => i.addEventListener("input", actualizar));
    actualizar();
  }

  // --- Temporizador de reserva de asientos: 10 minutos (R21) ---
  const t = document.querySelector("[data-temporizador]");
  if (t) {
    let seg = Number(t.dataset.temporizador);
    const salida = t.querySelector("strong");
    const pintar = () => {
      const m = String(Math.floor(seg / 60)).padStart(2, "0");
      const s = String(seg % 60).padStart(2, "0");
      salida.textContent = seg > 0 ? m + ":" + s : "Reserva expirada";
    };
    pintar();
    setInterval(() => { if (seg > 0) { seg--; pintar(); } }, 1000);
  }


  document.querySelectorAll("[data-confirmar]").forEach((b) =>
    b.addEventListener("click", (e) => { if (!confirm(b.dataset.confirmar)) e.preventDefault(); })
  );

  const copiar = (entrada, salida, formato) => {
    const i = document.querySelector(entrada), o = document.querySelector(salida);
    if (!i || !o) return;
    const pintar = () => { o.textContent = formato(i.value); };
    i.addEventListener("input", pintar); i.addEventListener("change", pintar);
  };
  copiar("[data-vista-titulo]", "[data-vista-salida-titulo]", (v) => v || "Título");
  copiar("[data-vista-titulo]", "[data-vista-salida-vacio]", (v) => v || "Título de la película");
  copiar("[data-vista-clasificacion]", "[data-vista-salida-clasificacion]", (v) => v);
  copiar("[data-vista-detalle]", "[data-vista-salida-detalle]", (v) => v || "Descripción");
  copiar("[data-vista-precio]", "[data-vista-salida-precio]", (v) => fmt(Number(v || 0)));
  const metas = document.querySelectorAll("[data-vista-meta]");
  const salidaMeta = document.querySelector("[data-vista-salida-meta]");
  if (metas.length && salidaMeta) {
    const pintarMeta = () => {
      const [genero, duracion] = [...metas].map((m) => m.value);
      salidaMeta.textContent = genero + (duracion ? " · " + duracion + " min" : "");
    };
    metas.forEach((m) => { m.addEventListener("input", pintarMeta); m.addEventListener("change", pintarMeta); });
  }
  const afiche = document.querySelector("[data-vista-afiche]");
  if (afiche) {
    const img = document.querySelector("[data-vista-salida-afiche]");
    const vacio = document.querySelector("[data-vista-salida-vacio]");
    const mostrar = (hayImagen) => { img.hidden = !hayImagen; vacio.hidden = hayImagen; };
    afiche.addEventListener("change", () => { if (afiche.value) { img.src = afiche.value; mostrar(true); } else { mostrar(false); } });
    img.addEventListener("error", () => mostrar(false));
  }

  const categoria = document.querySelector("[data-categoria]");
  const bloqueCombo = document.querySelector("[data-si-combo]");
  if (categoria && bloqueCombo) {
    const revisar = () => { bloqueCombo.hidden = categoria.value !== "Combos"; };
    categoria.addEventListener("change", revisar);
    revisar();
  }

  const formSala = document.querySelector("[data-form-sala]");
  if (formSala) {
    const num = (sel) => Math.max(0, Number(formSala.querySelector(sel).value || 0));
    const vista = formSala.querySelector("[data-sala-vista]");
    const dibujar = () => {
      const filas = Math.min(num("[data-sala-filas]"), 20), porFila = Math.min(num("[data-sala-por-fila]"), 24);
      const pasillo = num("[data-sala-pasillo]"), accesibles = num("[data-sala-accesibles]");
      formSala.querySelector("[data-sala-capacidad]").value = filas * porFila;
      vista.innerHTML = "";
      for (let f = 0; f < filas; f++) {
        const fila = document.createElement("div");
        fila.className = "fila";
        for (let n = 1; n <= porFila; n++) {
          const a = document.createElement("span");
          const esAccesible = f === filas - 1 && n <= accesibles;
          a.className = "asiento" + (esAccesible ? " movilidad" : "") + (n === pasillo && n < porFila ? " pasillo" : "");
          fila.appendChild(a);
        }
        vista.appendChild(fila);
      }
    };
    formSala.querySelectorAll("input[type=number]").forEach((i) => i.addEventListener("input", dibujar));
    dibujar();
  }

  const cierre = document.querySelector("[data-cierre-caja]");
  if (cierre) {
    const esperado = Number(cierre.dataset.esperado);
    const contado = cierre.querySelector("[data-contado]");
    const caja = cierre.querySelector("[data-diferencia]");
    const calcular = () => {
      const d = Number(contado.value || 0) - esperado;
      cierre.querySelector("[data-diferencia-valor]").textContent = (d < 0 ? "-" : "") + fmt(Math.abs(d));
      cierre.querySelector("[data-diferencia-texto]").textContent = d === 0 ? "La caja cuadra." : d < 0 ? "Falta dinero en la caja." : "Sobra dinero en la caja.";
      caja.classList.toggle("error", d !== 0);
    };
    contado.addEventListener("input", calcular);
    calcular();
  }
})();
