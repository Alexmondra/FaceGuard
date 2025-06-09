// Módulo principal
document.addEventListener("DOMContentLoaded", () => {
    CameraSystem.initialize();
});

// Namespace principal
const CameraSystem = (() => {
    // Configuración y estado
    const config = {
        apiUrl: `${API_BASE_URL}/camara`,
        socketOptions: {
            extraHeaders: { Authorization: `Bearer ${localStorage.getItem("accessToken")}` }
        },
        maxCameras: 16, // Límite escalable
        frameRate: 30 // FPS objetivo
    };

    // Estado de la aplicación
    const state = {
        cameras: [],
        subscribedCameras: new Map(), // {id: {element, lastFrame, active}}
        isSystemActive: false,
        socket: null
    };

    // Selectores del DOM
    const selectors = {
        cameraPlaceholder: document.querySelector(".camera-placeholder"),
        loadingOverlay: document.querySelector(".loading-overlay"),
        toggleCameraBtn: document.querySelector("#toggleCameraBtn"),
        cameraStatus: document.querySelector(".camera-status"),
        statusIndicator: document.querySelector(".status-indicator"),
        cameraView: document.querySelector(".camera-view"),
        gridView: document.querySelector(".grid-view"),
        gridPlaceholder: document.getElementById("gridPlaceholder"),
        singleView: document.getElementById("singleView"),
        toggleGridBtn: document.querySelector("#toggleGridBtn"),
        errorMessage: document.querySelector(".error-message"),
        multiViewModal: document.getElementById("multiViewModal"),
        closeMultiViewModal: document.getElementById("closeMultiViewModal"),
        modalCheckboxContainer: document.getElementById("cameraCheckboxesContainer"),
        externalCheckboxContainer: document.querySelector(".camera-checkboxes"),
    };

    // ==================== Módulo de Utilidades ====================
    const Utils = {
        toggleElement(element, show, displayType = "flex") {
            element.style.display = show ? displayType : "none";
        },

        showError(message, duration = 3000) {
            selectors.errorMessage.textContent = message;
            this.toggleElement(selectors.errorMessage, true);
            setTimeout(() => this.toggleElement(selectors.errorMessage, false), duration);
        },

        normalizeCameraId(id) {
            return String(id).trim();
        }
    };

    // ==================== Módulo de UI ====================
    const UI = {
        updateSystemStatus(isActive) {
            selectors.cameraStatus.textContent = isActive ? "Sistema activo" : "Sistema inactivo";
            selectors.statusIndicator.classList.toggle("status-active", isActive);
            selectors.statusIndicator.classList.toggle("status-inactive", !isActive);
            selectors.toggleCameraBtn.innerHTML = isActive
                ? '<i class="fas fa-stop"></i> Detener'
                : '<i class="fas fa-play"></i> Iniciar';
            selectors.toggleCameraBtn.classList.toggle("active", isActive);
        },

        renderCameraCheckboxes(cameras) {
            const container = selectors.modalCheckboxContainer;
            container.innerHTML = ""; // Limpiar contenedor principal
        
            cameras.forEach(cam => {
                const userContainer = document.createElement("div");
                userContainer.className = "user-container"; // Clase para estilos personalizados
        
                // Título del usuario o "Sin usuario asociado"
                const userTitle = document.createElement("h3");
                userTitle.textContent = cam.usuarios && cam.usuarios.length > 0 
                    ? `Usuario: ${cam.usuarios[0].usuario_nombre}` 
                    : "Sin usuario asociado";
                userContainer.appendChild(userTitle);
        
                // Crear lista de cámaras asociadas al usuario
                const cameraList = document.createElement("div");
                cameraList.className = "camera-list"; // Clase para estilos de cámaras
        
                cam.usuarios?.forEach(user => {
                    const cameraContainer = document.createElement("div");
                    cameraContainer.className = "camera-container";
        
                    const label = document.createElement("label");
                    label.innerHTML = `
                        <input type="checkbox" name="multiCamera" value="${cam.id}">
                        ${cam.nombre}
                    `;
                    cameraContainer.appendChild(label);
                    cameraList.appendChild(cameraContainer);
                });
        
                userContainer.appendChild(cameraList);
                container.appendChild(userContainer);
            });
        },
        

        setupCheckboxSync() {
            const syncCheckboxes = (source, target) => {
                const checkedIds = Array.from(source)
                    .filter(cb => cb.checked)
                    .map(cb => cb.value);
                target.forEach(cb => cb.checked = checkedIds.includes(cb.value));
                CameraGrid.render(checkedIds);
            };

            const setupEvents = (source, target) => {
                source.forEach(cb => cb.addEventListener("change", () => syncCheckboxes(source, target)));
            };

            const modalCheckboxes = selectors.modalCheckboxContainer.querySelectorAll("input[type=checkbox]");
            const externalCheckboxes = selectors.externalCheckboxContainer.querySelectorAll("input[type=checkbox]");

            setupEvents(modalCheckboxes, externalCheckboxes);
            setupEvents(externalCheckboxes, modalCheckboxes);
        },

        setupModalControls() {
            if (!selectors.toggleGridBtn || !selectors.multiViewModal || !selectors.closeMultiViewModal) return;

            selectors.toggleGridBtn.addEventListener("click", () => 
                Utils.toggleElement(selectors.multiViewModal, true));
            
            selectors.closeMultiViewModal.addEventListener("click", () => 
                Utils.toggleElement(selectors.multiViewModal, false));
        }
    };

    // ==================== Módulo de Grid ====================
    const CameraGrid = {
        render(cameraIds) {
            selectors.gridView.classList.add("active");
            this.clear();

            if (cameraIds.length === 0) {
                Utils.toggleElement(selectors.gridPlaceholder, true);
                Utils.toggleElement(selectors.singleView, true);
                return;
            }

            Utils.toggleElement(selectors.gridPlaceholder, false);
            Utils.toggleElement(selectors.singleView, false);

            cameraIds.forEach(camId => this.addCamera(camId));
        },

        clear() {
            selectors.gridView.querySelectorAll(".grid-item").forEach(el => el.remove());
        },

        addCamera(camId) {
            camId = Utils.normalizeCameraId(camId);
            const cam = state.cameras.find(c => Utils.normalizeCameraId(c.id) === camId);
            const nombre = cam ? cam.nombre : camId;

            const gridItem = document.createElement("div");
            gridItem.className = "grid-item";
            gridItem.style.flex = `1 1 calc(${100 / state.subscribedCameras.size}% - 10px)`;
            gridItem.innerHTML = `
                <div class="grid-camera">
                    <span class="camera-name">${nombre}</span>
                    <img id="camFrame_${camId}" class="camera-feed" />
                </div>
            `;

            selectors.gridView.appendChild(gridItem);

            if (!state.subscribedCameras.has(camId)) {
                state.socket.emit("subscribe_camera", { camera_id: camId });
                state.subscribedCameras.set(camId, {
                    element: gridItem,
                    active: true,
                    lastFrame: null
                });
            }
        },

        updateCameraFrame(cameraId, frame) {
            const normalizedId = Utils.normalizeCameraId(cameraId);
            const cameraData = state.subscribedCameras.get(normalizedId);
            
            if (cameraData) {
                const img = cameraData.element.querySelector(".camera-feed");
                if (img) {
                    img.src = `data:image/jpeg;base64,${frame}`;
                    cameraData.lastFrame = frame;
                }
            }
        }
    };

    // ==================== Módulo de Comunicación ====================
    const Comms = {
        async fetchCameras() {
            try {
                const response = await fetch(`${config.apiUrl}/obtener_activas`, {
                    method: "GET",
                    headers: { Authorization: `Bearer ${localStorage.getItem("accessToken")}` },
                });

                if (!response.ok) throw new Error(`Error: ${response.statusText}`);

                const cameras = await response.json();
                state.cameras = cameras;
                UI.renderCameraCheckboxes(cameras);
                UI.setupCheckboxSync();
            } catch (err) {
                console.error("Error fetching cameras:", err);
                Utils.showError("Error al obtener cámaras. Revisa consola.");
            }
        },

        setupSocketHandlers() {
            state.socket = io(API_BASE_URL, config.socketOptions);

            // Handlers de Socket.IO
            state.socket.on("video_frame", ({ camera_id, frame }) => {
                CameraGrid.updateCameraFrame(camera_id, frame);
            });

            state.socket.on("connect_error", (err) => {
                console.error("Socket connection error:", err);
                Utils.showError("Error de conexión con el servidor");
            });
        }
    };

    // ==================== Módulo de Control ====================
    const Controller = {
        toggleSystem() {
            state.isSystemActive = !state.isSystemActive;

            if (state.isSystemActive) {
                Utils.toggleElement(selectors.cameraPlaceholder, false);
                Utils.toggleElement(selectors.loadingOverlay, true);

                setTimeout(() => {
                    Utils.toggleElement(selectors.loadingOverlay, false);
                    UI.updateSystemStatus(true);
                }, 1000);
            } else {
                Utils.toggleElement(selectors.cameraPlaceholder, true);
                UI.updateSystemStatus(false);
            }
        },

        initialize() {
            // Configurar eventos UI
            selectors.toggleCameraBtn.addEventListener("click", () => this.toggleSystem());
            UI.setupModalControls();

            // Iniciar comunicación
            Comms.setupSocketHandlers();
            Comms.fetchCameras();
        }
    };

    // API Pública
    return {
        initialize: Controller.initialize
    };
})();