document.addEventListener("DOMContentLoaded", () => {
    // Variables globales y selectores
    const cameraPlaceholder = document.querySelector(".camera-placeholder");
    const loadingOverlay = document.querySelector(".loading-overlay");
    const toggleCameraBtn = document.querySelector("#toggleCameraBtn");
    const cameraStatus = document.querySelector(".camera-status");
    const statusIndicator = document.querySelector(".status-indicator");
    const cameraView = document.querySelector(".camera-view");
    const gridView = document.querySelector(".grid-view");
    const gridPlaceholder = document.getElementById("gridPlaceholder");
    const singleView = document.getElementById("singleView");
    const toggleGridBtn = document.querySelector("#toggleGridBtn");
    const errorMessage = document.querySelector(".error-message");
    const multiViewModal = document.getElementById("multiViewModal");
    const closeMultiViewModal = document.getElementById("closeMultiViewModal");
    const modalCheckboxContainer = document.getElementById('cameraCheckboxesContainer');
    const externalCheckboxContainer = document.querySelector(".camera-checkboxes");

    let camarasCache = [];
    const apiUrl = `${API_BASE_URL}/camara`;
    const token = localStorage.getItem('accessToken');
    let isCameraActive = false;

    // ----- Funciones para UI -----
    function toggleElementDisplay(element, show, displayType = "flex") {
        element.style.display = show ? displayType : "none";
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

    function showError(message) {
        errorMessage.textContent = message;
        toggleElementDisplay(errorMessage, true);
        setTimeout(() => toggleElementDisplay(errorMessage, false), 3000);
    }

    // ----- Funciones cámara -----
    function toggleCamera() {
        isCameraActive = !isCameraActive;

        if (isCameraActive) {
            toggleElementDisplay(cameraPlaceholder, false);
            toggleElementDisplay(loadingOverlay, true);

            setTimeout(() => {
                toggleElementDisplay(loadingOverlay, false);
                updateCameraStatus(true);
                setCameraButtonState(true);
            }, 2000);
        } else {
            toggleElementDisplay(cameraPlaceholder, true);
            updateCameraStatus(false);
            setCameraButtonState(false);
        }
    }

    // ----- Fetch y render de cámaras -----
    async function fetchCamaras() {
        try {
            const response = await fetch(`${apiUrl}/obtener`, {
                method: 'GET',
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!response.ok) throw new Error(`Error: ${response.statusText}`);

            const camaras = await response.json();
            camarasCache = camaras;
            renderCheckboxes(camaras);
            inicializarCheckboxes(); // conectar eventos y sincronizar
        } catch (err) {
            console.error(err);
            alert('Error al obtener cámaras. Revisa consola.');
        }
    }

    function renderCheckboxes(camaras) {
        modalCheckboxContainer.innerHTML = '';
        externalCheckboxContainer.innerHTML = '';

        camaras.forEach(cam => {
            // Modal
            const modalLabel = document.createElement('label');
            modalLabel.innerHTML = `
                <input type="checkbox" name="multiCamera" value="${cam.id}">
                ${cam.nombre}
            `;
            modalCheckboxContainer.appendChild(modalLabel);
            modalCheckboxContainer.appendChild(document.createElement('br'));

            // Externos
            const externalLabel = document.createElement('label');
            externalLabel.innerHTML = `
                <input type="checkbox" value="${cam.id}">
                ${cam.nombre}
            `;
            externalCheckboxContainer.appendChild(externalLabel);
        });
    }

    // ----- Sincronización y eventos de checkboxes -----
    function inicializarCheckboxes() {
        const modalCheckboxes = modalCheckboxContainer.querySelectorAll('input[type=checkbox]');
        const externalCheckboxes = externalCheckboxContainer.querySelectorAll('input[type=checkbox]');

        // Al cambiar en modal, actualiza externos y grid
        modalCheckboxes.forEach(cb => cb.addEventListener('change', () => {
            sincronizarCheckboxes(modalCheckboxes, externalCheckboxes);
        }));

        // Al cambiar en externos, actualiza modal y grid
        externalCheckboxes.forEach(cb => cb.addEventListener('change', () => {
            sincronizarCheckboxes(externalCheckboxes, modalCheckboxes);
        }));
    }

    function sincronizarCheckboxes(origen, destino) {
        const checkedIds = Array.from(origen).filter(cb => cb.checked).map(cb => cb.value);
        destino.forEach(cb => cb.checked = checkedIds.includes(cb.value));
        renderGridView(checkedIds);
    }

    // ----- Renderizado del grid dinámico -----
    function renderGridView(selectedCameras) {
        gridView.classList.add("active");
        gridView.querySelectorAll(".grid-item").forEach(el => el.remove());

        if (selectedCameras.length === 0) {
            toggleElementDisplay(gridPlaceholder, true);
            if (singleView) singleView.style.display = "";
            return;
        }

        toggleElementDisplay(gridPlaceholder, false);
        if (singleView) singleView.style.display = "none";

        selectedCameras.forEach(camId => {
            const cam = camarasCache.find(c => c.id == camId);
            const nombre = cam ? cam.nombre : camId;

            const gridItem = document.createElement("div");
            gridItem.className = "grid-item";
            gridItem.style.flex = `1 1 calc(${100 / selectedCameras.length}% - 10px)`; // adaptable al número de cámaras

            gridItem.innerHTML = `
                <div class="grid-camera" style="height: 150px; background:#222; border-radius: 8px; display:flex; align-items:center; justify-content:center;">
                    <span style="color:#fff; font-size:1.2rem;">${nombre}</span>
                </div>
            `;

            gridView.appendChild(gridItem);
        });
    }

    // ----- Modal vista múltiple -----
    function setupModal() {
        if (!toggleGridBtn || !multiViewModal || !closeMultiViewModal) return;

        toggleGridBtn.addEventListener("click", () => {
            multiViewModal.style.display = "flex";
        });

        closeMultiViewModal.addEventListener("click", () => {
            multiViewModal.style.display = "none";
        });

        multiViewModal.addEventListener("click", e => {
            if (e.target === multiViewModal) multiViewModal.style.display = "none";
        });
    }

    // ----- Inicialización -----
    function init() {
        toggleCameraBtn.addEventListener("click", toggleCamera);

        document.querySelector("#fullscreenBtn")?.addEventListener("click", () => {
            if (cameraView.requestFullscreen) cameraView.requestFullscreen();
            else if (cameraView.webkitRequestFullscreen) cameraView.webkitRequestFullscreen();
            else if (cameraView.msRequestFullscreen) cameraView.msRequestFullscreen();
            else showError("Tu navegador no soporta pantalla completa.");
        });

        document.querySelector("#simulateErrorBtn")?.addEventListener("click", () => {
            showError("Error al iniciar la cámara. Intenta nuevamente.");
        });

        setupModal();
        fetchCamaras();
    }

    init();
});
