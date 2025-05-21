document.addEventListener("DOMContentLoaded", () => {
    const cameraPlaceholder = document.querySelector(".camera-placeholder");
    const loadingOverlay = document.querySelector(".loading-overlay");
    const toggleCameraBtn = document.querySelector("#toggleCameraBtn");
    const cameraStatus = document.querySelector(".camera-status");
    const statusIndicator = document.querySelector(".status-indicator");
    const cameraView = document.querySelector(".camera-view");
    const gridView = document.querySelector(".grid-view");
const gridPlaceholder = document.getElementById("gridPlaceholder");
const singleView = document.getElementById("singleView");
const externalCameraCheckboxes = document.querySelectorAll(".camera-checkboxes input[type=checkbox]");
    const toggleGridBtn = document.querySelector("#toggleGridBtn");
    const errorMessage = document.querySelector(".error-message");

    let isCameraActive = false;

    function toggleElementDisplay(element, shouldShow, displayType = "flex") {
        element.style.display = shouldShow ? displayType : "none";
    }

    function setCameraButtonState(isActive) {
        toggleCameraBtn.innerHTML = isActive
            ? '<i class="fas fa-stop"></i> Detener'
            : '<i class="fas fa-play"></i> Iniciar';
        toggleCameraBtn.classList.toggle("active", isActive);
    }

    function updateCameraStatus(isActive) {
        cameraStatus.textContent = isActive ? "Cámara activa" : "Cámara inactiva";
        statusIndicator.classList.toggle("status-active", isActive);
        statusIndicator.classList.toggle("status-inactive", !isActive);
    }

    function toggleCamera() {
        isCameraActive = !isCameraActive;

        if (isCameraActive) {
            toggleElementDisplay(cameraPlaceholder, false);
            toggleElementDisplay(loadingOverlay, true);
            setTimeout(() => {
                toggleElementDisplay(loadingOverlay, false);
                updateCameraStatus(true);
                setCameraButtonState(true);
            }, 2000); // Simulación de carga
        } else {
            toggleElementDisplay(cameraPlaceholder, true);
            updateCameraStatus(false);
            setCameraButtonState(false);
        }
    }

    // Eliminado: función toggleGridView innecesaria, el gridView siempre está visible y el botón sólo abre el modal.

    function showError(message) {
        errorMessage.textContent = message;
        toggleElementDisplay(errorMessage, true);
        setTimeout(() => {
            toggleElementDisplay(errorMessage, false);
        }, 3000); // Ocultar después de 3 segundos
    }

    // Manejo de eventos
    toggleCameraBtn.addEventListener("click", toggleCamera);
    // El listener para toggleGridBtn (Vista Múltiple) se controla abajo para evitar duplicidad

    // Simulación de error (solo para pruebas)
    document.querySelector("#simulateErrorBtn")?.addEventListener("click", () => {
        showError("Error al iniciar la cámara. Intenta nuevamente.");
    });

    // Ajuste para pantalla completa (opcional)
    document.querySelector("#fullscreenBtn")?.addEventListener("click", () => {
        if (cameraView.requestFullscreen) {
            cameraView.requestFullscreen();
        } else if (cameraView.webkitRequestFullscreen) { // Safari
            cameraView.webkitRequestFullscreen();
        } else if (cameraView.msRequestFullscreen) { // IE/Edge
            cameraView.msRequestFullscreen();
        } else {
            showError("Tu navegador no soporta pantalla completa.");
        }
    });
    // ---- LÓGICA PARA MODAL DE VISTA MÚLTIPLE ----
    const toggleGridBtnCustom = document.getElementById("toggleGridBtn");
    const multiViewModal = document.getElementById("multiViewModal");
    const closeMultiViewModal = document.getElementById("closeMultiViewModal");

    if (toggleGridBtnCustom && multiViewModal && closeMultiViewModal) {
        // Siempre que pulses el botón, se abre el modal, sin cambiar nada del grid ni del botón.
        toggleGridBtnCustom.addEventListener("click", () => {
            multiViewModal.style.display = "flex";
        });
        closeMultiViewModal.addEventListener("click", () => {
            multiViewModal.style.display = "none";
        });

        // Cerrar el modal al hacer clic fuera del cuadro modal
        multiViewModal.addEventListener("click", (e) => {
            if (e.target === multiViewModal) {
                multiViewModal.style.display = "none";
            }
        });
    }
    // ---- LÓGICA UNIFICADA PARA RENDERIZAR EL GRID DE CÁMARAS ----
    function renderGridView(selectedCameras) {
        // Siempre activa el gridView
        gridView.classList.add("active");
        // Limpiar el contenido dinámico del grid, pero dejar el placeholder en DOM
        // Eliminamos solo los grid-items existentes (por si acaso)
        gridView.querySelectorAll(".grid-item").forEach(el => el.remove());

        if (selectedCameras.length === 0) {
            gridPlaceholder.style.display = "block";
            if (singleView) singleView.style.display = "";
        } else {
            gridPlaceholder.style.display = "none";
            if (singleView) singleView.style.display = "none";
            selectedCameras.forEach(cam => {
                const gridItem = document.createElement("div");
                gridItem.className = "grid-item";
                gridItem.innerHTML = `
                    <div class="grid-camera">
                        <div style="color:#fff; text-align:center; margin-top:85px; font-size:1.3rem;">${cam}</div>
                    </div>
                `;
                gridView.appendChild(gridItem);
            });
        }
    }

    // Lógica para detectar cámaras seleccionadas desde el modal
    function getSelectedCamerasModal() {
        const multiViewForm = document.getElementById("multiViewForm");
        if (!multiViewForm || !multiViewForm.elements["multiCamera"]) return [];
        return Array.from(multiViewForm.elements["multiCamera"])
            .filter(input => input.checked)
            .map(input => input.value);
    }

    // Lógica para detectar cámaras seleccionadas desde los checkboxes externos
    function getSelectedCamerasExternal() {
        return Array.from(document.querySelectorAll(".camera-checkboxes input[type=checkbox]:checked"))
            .map(input => input.value);
    }

    // ---- LOGICA PARA ENVIO DEL FORMULARIO DE MULTIVISTA ----
    const multiViewForm = document.getElementById("multiViewForm");
    const multiViewError = document.getElementById("multiViewError");
    const multiViewModal2 = document.getElementById("multiViewModal");
    if (multiViewForm && multiViewError && multiViewModal2) {
        multiViewForm.addEventListener("submit", function(e) {
            e.preventDefault();
            const selected = getSelectedCamerasModal();
            if (selected.length === 0) {
                multiViewError.textContent = "Selecciona al menos una cámara.";
                multiViewError.style.display = "block";
                renderGridView([]); // Muestra placeholder y singleView
                return;
            }
            multiViewError.style.display = "none";
            multiViewModal2.style.display = "none";
            // (No modificar el texto del botón, mantenerlo estático)
            // Marcar los checkboxes externos igual que los del modal (opcional, sincronización)
            selected.forEach(camVal => {
                document.querySelectorAll(`.camera-checkboxes input[type=checkbox][value="${camVal}"]`)
                    .forEach(cb => cb.checked = true);
            });
            renderGridView(selected);
        });
    }

    // --- Evento para checkboxes externos (actualiza grid dinámicamente) ---
    document.querySelectorAll(".camera-checkboxes input[type=checkbox]").forEach(cb => {
        cb.addEventListener("change", () => {
            // Descarta los posibles checkboxes duplicados (con el mismo valor) 
            const selected = getSelectedCamerasExternal();
            // Actualizar el grid y podría (opcional) desmarcar en el modal los checkboxes que se quiten aquí
            // (sincronización modal-external)
            renderGridView(selected);
        });
    });

    // --- Inicialización del grid al cargar la página (por si acaso) ---
    renderGridView(getSelectedCamerasExternal());
});
