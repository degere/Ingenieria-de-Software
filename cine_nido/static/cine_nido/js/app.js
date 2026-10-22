/* JS mínimo y TEMPORAL solo para que las pantallas de demostración se sientan reales.
   La lógica de verdad (reserva de asientos, precios, pagos) irá en el backend. */
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
})();
