document.addEventListener('DOMContentLoaded', () => {
    // Configuración
    const config = {
        serverUrl: 'http://localhost:3000', // Cambia esto por tu URL de servidor
        maxCameras: 9,
        mockCameras: [
            { id: '1', nombre: 'Cámara Entrada' },
            { id: '2', nombre: 'Cámara Sala' },
            { id: '3', nombre: 'Cámara Cocina' },
            { id: '4', nombre: 'Cámara Exterior' }
        ]
    };

    // Estado del sistema
    const state = {
        isSystemActive: false,
        selectedCameras: new Set(),
        socket: null
    };

    // Elementos del DOM
    const elements = {
        toggleSystemBtn: document.getElementById('toggleSystemBtn'),
        toggleGridBtn: document.getElementById('toggleGridBtn'),
        statusIndicator: document.querySelector('.status-indicator'),
        statusText: document.querySelector('.status-text'),
        placeholder: document.querySelector('.placeholder'),
        gridView: document.querySelector('.grid-view'),
        modal: document.getElementById('cameraSelectionModal'),
        checkboxesContainer: document.getElementById('cameraCheckboxes'),
        closeModalBtn: document.querySelector('.close-modal')
    };

    // Inicializar Socket.IO
    function initSocket() {
        state.socket = io(config.serverUrl);

        state.socket.on('connect', () => {
            console.log('Conectado al servidor Socket.IO');
        });

        state.socket.on('video_frame', (data) => {
            updateCameraFrame(data.camera_id, data.frame);
        });

        state.socket.on('disconnect', () => {
            console.log('Desconectado del servidor');
        });
    }

    // Manejar el estado del sistema
    function toggleSystem() {
        state.isSystemActive = !state.isSystemActive;

        if (state.isSystemActive) {
            // Iniciar sistema
            elements.toggleSystemBtn.innerHTML = '<i class="fas fa-stop"></i> Detener Sistema';
            elements.toggleSystemBtn.classList.add('active');
            elements.statusIndicator.classList.add('active');
            elements.statusText.textContent = 'Sistema activo';
            
            // Conectar al servidor
            initSocket();
            
            // Mostrar interfaz
            elements.placeholder.classList.add('hidden');
            elements.gridView.classList.remove('hidden');
        } else {
            // Detener sistema
            elements.toggleSystemBtn.innerHTML = '<i class="fas fa-play"></i> Iniciar Sistema';
            elements.toggleSystemBtn.classList.remove('active');
            elements.statusIndicator.classList.remove('active');
            elements.statusText.textContent = 'Sistema inactivo';
            
            // Desconectar
            if (state.socket) {
                state.socket.disconnect();
                state.socket = null;
            }
            
            // Limpiar vista
            clearGridView();
            elements.placeholder.classList.remove('hidden');
            elements.gridView.classList.add('hidden');
        }
    }

    // Manejar la selección de cámaras
    function showCameraSelection() {
        renderCameraCheckboxes();
        elements.modal.classList.remove('hidden');
    }

    function closeCameraSelection() {
        elements.modal.classList.add('hidden');
        updateSelectedCameras();
    }

    function renderCameraCheckboxes() {
        elements.checkboxesContainer.innerHTML = '';
        
        config.mockCameras.forEach(camera => {
            const label = document.createElement('label');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = camera.id;
            checkbox.checked = state.selectedCameras.has(camera.id);
            
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(camera.nombre));
            elements.checkboxesContainer.appendChild(label);
            elements.checkboxesContainer.appendChild(document.createElement('br'));
        });
    }

    function updateSelectedCameras() {
        const checkboxes = elements.checkboxesContainer.querySelectorAll('input[type="checkbox"]');
        state.selectedCameras.clear();
        
        checkboxes.forEach(checkbox => {
            if (checkbox.checked) {
                state.selectedCameras.add(checkbox.value);
            }
        });
        
        renderGridView();
    }

    // Renderizar la vista grid
    function renderGridView() {
        clearGridView();
        
        if (state.selectedCameras.size === 0) {
            elements.placeholder.classList.remove('hidden');
            elements.gridView.classList.add('hidden');
            return;
        }
        
        elements.placeholder.classList.add('hidden');
        elements.gridView.classList.remove('hidden');
        
        state.selectedCameras.forEach(cameraId => {
            addCameraToGrid(cameraId);
        });
    }

    function clearGridView() {
        elements.gridView.innerHTML = '';
    }

    function addCameraToGrid(cameraId) {
        const camera = config.mockCameras.find(cam => cam.id === cameraId);
        const cameraName = camera ? camera.nombre : `Cámara ${cameraId}`;
        
        const gridItem = document.createElement('div');
        gridItem.className = 'grid-item';
        gridItem.innerHTML = `
            <span class="camera-name">${cameraName}</span>
            <img id="cam-frame-${cameraId}" class="camera-feed" />
        `;
        
        elements.gridView.appendChild(gridItem);
        
        // Suscribirse a la cámara
        if (state.socket && state.isSystemActive) {
            state.socket.emit('subscribe_camera', { camera_id: cameraId });
        }
    }

    function updateCameraFrame(cameraId, frame) {
        const imgElement = document.getElementById(`cam-frame-${cameraId}`);
        if (imgElement) {
            imgElement.src = `data:image/jpeg;base64,${frame}`;
        }
    }

    // Event listeners
    elements.toggleSystemBtn.addEventListener('click', toggleSystem);
    elements.toggleGridBtn.addEventListener('click', showCameraSelection);
    elements.closeModalBtn.addEventListener('click', closeCameraSelection);

    // Inicialización
    renderCameraCheckboxes();
});