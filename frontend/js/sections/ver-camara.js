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
        gridView: document.getElementById("gridView"),
        gridPlaceholder: document.getElementById("gridPlaceholder"),
        singleView: document.getElementById("singleView"),
        toggleGridBtn: document.querySelector("#toggleGridBtn"),
        errorMessage: document.querySelector(".error-message"),
        multiViewModal: document.getElementById("multiViewModal"),
        closeMultiViewModal: document.getElementById("closeMultiViewModal"),
        modalCheckboxContainer: document.getElementById("cameraCheckboxesContainer"),
        externalCheckboxContainer: document.querySelector(".camera-checkboxes"),
        connectBtn: document.getElementById("connectBtn"),
        disconnectBtn: document.getElementById("disconnectBtn")
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
        },
        
        createCameraElement(cameraId, cameraName, userName) {
            const cameraContainer = document.createElement('div');
            cameraContainer.className = 'grid-item camera-container';
            cameraContainer.id = `camera_${cameraId}`;
            cameraContainer.innerHTML = `
                <div class="camera-header">
                    <span>${cameraName || `Cámara ${cameraId}`} <span class="status-indicator status-inactive"></span></span>
                    <div class="camera-controls">
                        <button class="settings-btn" data-cam-id="${cameraId}">
                            <i class="fas fa-cog"></i>
                        </button>
                        <div class="settings-menu" data-cam-id="${cameraId}">
                            <div class="tracking-control">
                                <label>Seguimiento:</label>
                                <div class="radio-group">
                                    <label>
                                        <input type="radio" name="tracking_${cameraId}" value="off" checked>
                                        Desactivado
                                    </label>
                                    <label>
                                        <input type="radio" name="tracking_${cameraId}" value="on">
                                        Activado
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <img class="camera-feed" id="feed_${cameraId}" />
                <div class="loading" id="loading_${cameraId}">Inactiva</div>
            `;
            return cameraContainer;
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
            
            // Actualizar estado de los botones de conexión
            selectors.connectBtn.disabled = isActive;
            selectors.disconnectBtn.disabled = !isActive;
        },
    
        renderCameraCheckboxes(cameras) {
            const container = selectors.modalCheckboxContainer;
            container.innerHTML = "";
    
            // Agrupar cámaras por usuario
            const camerasByUser = cameras.reduce((acc, cam) => {
                const userId = cam.usuarios?.[0]?.usuario_id || 'sin-usuario';
                const userName = cam.usuarios?.[0]?.usuario_nombre || 'Sin usuario';
                
                if (!acc[userId]) {
                    acc[userId] = {
                        userName: userName,
                        cameras: []
                    };
                }
                
                acc[userId].cameras.push(cam);
                return acc;
            }, {});
    
            // Renderizar cada grupo de usuario
            Object.values(camerasByUser).forEach(userGroup => {
                const userSection = document.createElement('div');
                userSection.className = 'user-section';
                
                const userHeader = document.createElement('h3');
                userHeader.textContent = userGroup.userName;
                userSection.appendChild(userHeader);
                
                const camerasContainer = document.createElement('div');
                camerasContainer.className = 'cameras-container';
                
                userGroup.cameras.forEach(cam => {
                    const camItem = document.createElement('div');
                    camItem.className = 'cam-item';
                    
                    const label = document.createElement('label');
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.name = 'multiCamera';
                    checkbox.value = cam.id;
                    
                    label.appendChild(checkbox);
                    label.appendChild(document.createTextNode(cam.nombre));
                    camItem.appendChild(label);
                    camerasContainer.appendChild(camItem);
                });
                
                userSection.appendChild(camerasContainer);
                container.appendChild(userSection);
            });
        },
    
        setupCheckboxSync() {
            const syncCheckboxes = (source, target) => {
                const checkedIds = Array.from(source)
                    .filter(cb => cb.checked)
                    .map(cb => cb.value);
                
                target.forEach(cb => {
                    cb.checked = checkedIds.includes(cb.value);
                });
                
                CameraGrid.render(checkedIds);
            };
    
            const setupEvents = (source, target) => {
                source.forEach(cb => {
                    cb.addEventListener("change", () => {
                        syncCheckboxes(source, target);
                        
                        // Actualizar suscripciones
                        const camId = cb.value;
                        if (cb.checked) {
                            state.socket.emit("subscribe_camera", { camera_id: camId });
                        } else {
                            state.socket.emit("unsubscribe_camera", { camera_id: camId });
                        }
                    });
                });
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
        },
        
        setupConnectionControls() {
            if (!selectors.connectBtn || !selectors.disconnectBtn) return;
            
            selectors.connectBtn.addEventListener("click", () => {
                Controller.toggleSystem();
                Comms.connectToCameras();
            });
            
            selectors.disconnectBtn.addEventListener("click", () => {
                Controller.toggleSystem();
                Comms.disconnectFromCameras();
            });
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
            // Limpiar solo las vistas, no las suscripciones
            selectors.gridView.querySelectorAll(".grid-item").forEach(el => el.remove());
        },
    
        addCamera(camId) {
            camId = Utils.normalizeCameraId(camId);
            const cam = state.cameras.find(c => Utils.normalizeCameraId(c.id) === camId);
            const nombre = cam ? cam.nombre : camId;
            const userName = cam?.usuarios?.[0]?.usuario_nombre || 'Sin usuario';
    
            const cameraElement = Utils.createCameraElement(camId, nombre, userName);
            selectors.gridView.appendChild(cameraElement);
    
            // Configurar eventos de control
            const settingsBtn = cameraElement.querySelector(".settings-btn");
            const settingsMenu = cameraElement.querySelector(".settings-menu");
    
            settingsBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                settingsMenu.style.display = settingsMenu.style.display === 'block' ? 'none' : 'block';
            });
    
            // Configurar eventos de seguimiento
            cameraElement.querySelectorAll(`input[name="tracking_${camId}"]`).forEach(radio => {
                radio.addEventListener("change", (e) => {
                    const trackingEnabled = e.target.value === 'on';
                    if (trackingEnabled) {
                        state.socket.emit("activar_seguimiento", { camera_id: camId });
                    } else {
                        state.socket.emit("desactivar_seguimiento", { camera_id: camId });
                    }
                });
            });
    
            // Si no está suscrito, suscribirse
            if (!state.subscribedCameras.has(camId)) {
                state.socket.emit("subscribe_camera", { camera_id: camId });
                state.subscribedCameras.set(camId, {
                    element: cameraElement,
                    active: false,
                    lastFrame: null,
                    trackingEnabled: false
                });
                
                // Mostrar estado de carga
                const loadingElement = document.getElementById(`loading_${camId}`);
                if (loadingElement) {
                    loadingElement.textContent = 'Conectando...';
                }
            }
        },
    
        updateCameraFrame(cameraId, frame) {
            const normalizedId = Utils.normalizeCameraId(cameraId);
            const cameraData = state.subscribedCameras.get(normalizedId);
            
            if (cameraData) {
                const feedElement = document.getElementById(`feed_${normalizedId}`);
                const loadingElement = document.getElementById(`loading_${normalizedId}`);
                const statusIndicator = cameraData.element.querySelector(".status-indicator");
                
                if (feedElement && frame) {
                    feedElement.src = `data:image/jpeg;base64,${frame}`;
                    if (loadingElement) loadingElement.style.display = 'none';
                    if (statusIndicator) {
                        statusIndicator.className = 'status-indicator status-active';
                    }
                    cameraData.active = true;
                    cameraData.lastFrame = frame;
                }
            }
        },
        
        updateTrackingStatus(cameraId, isActive) {
            const normalizedId = Utils.normalizeCameraId(cameraId);
            const cameraData = state.subscribedCameras.get(normalizedId);
            
            if (cameraData) {
                cameraData.trackingEnabled = isActive;
                const radioOn = cameraData.element.querySelector(`input[name="tracking_${normalizedId}"][value="on"]`);
                const radioOff = cameraData.element.querySelector(`input[name="tracking_${normalizedId}"][value="off"]`);
                
                if (radioOn && radioOff) {
                    if (isActive) {
                        radioOn.checked = true;
                    } else {
                        radioOff.checked = true;
                    }
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
            
            state.socket.on("tracking_status", ({ camera_id, active }) => {
                CameraGrid.updateTrackingStatus(camera_id, active);
            });
        },
        
        connectToCameras() {
            if (!state.socket) return;
            
            // Suscribirse a todas las cámaras seleccionadas
            const checkboxes = selectors.modalCheckboxContainer.querySelectorAll("input[type=checkbox]:checked");
            checkboxes.forEach(cb => {
                const cameraId = cb.value;
                state.socket.emit("subscribe_camera", { camera_id: cameraId });
            });
        },
        
        disconnectFromCameras() {
            if (!state.socket) return;
            
            // Desuscribirse de todas las cámaras
            state.subscribedCameras.forEach((_, cameraId) => {
                state.socket.emit("unsubscribe_camera", { camera_id: cameraId });
                
                // Restablecer el elemento de la cámara
                const feedElement = document.getElementById(`feed_${cameraId}`);
                const loadingElement = document.getElementById(`loading_${cameraId}`);
                const statusIndicator = document.querySelector(`#camera_${cameraId} .status-indicator`);
                
                if (feedElement) feedElement.src = '';
                if (loadingElement) {
                    loadingElement.textContent = 'Desconectado';
                    loadingElement.style.display = 'block';
                }
                if (statusIndicator) {
                    statusIndicator.className = 'status-indicator status-inactive';
                }
            });
            
            state.subscribedCameras.clear();
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
            UI.setupConnectionControls();

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