document.addEventListener('DOMContentLoaded', function () {
    const apiUrl = `${API_BASE_URL}/camara`;
    const token = localStorage.getItem('accessToken');

    const tabListaBtn = document.getElementById("tabListaBtn");
    const tabRegistrarBtn = document.getElementById("tabRegistrarBtn");
    const camarasListaPanel = document.getElementById("camarasListaPanel");
    const camarasRegistroPanel = document.getElementById("camarasRegistroPanel");

    const modal = document.getElementById('editarModal');
    const closeModalBtn = document.querySelector('.close-btn');
    const formEditarCamara = document.getElementById('formEditarCamara');

    let camarasCache = [];  // Aquí guardamos las cámaras obtenidas

    function switchTab(tab) {
        if (tab === 'lista') {
            tabListaBtn.classList.add('active');
            tabRegistrarBtn.classList.remove('active');
            camarasListaPanel.classList.add('active');
            camarasRegistroPanel.classList.remove('active');
        } else {
            tabListaBtn.classList.remove('active');
            tabRegistrarBtn.classList.add('active');
            camarasListaPanel.classList.remove('active');
            camarasRegistroPanel.classList.add('active');
        }
    }
    tabListaBtn.addEventListener('click', () => switchTab('lista'));
    tabRegistrarBtn.addEventListener('click', () => switchTab('registrar'));

    async function fetchCamaras() {
        try {
            const response = await fetch(`${apiUrl}/obtener`, {
                method: 'GET',
                headers: { 'Authorization': 'Bearer ' + token }
            });

            if (!response.ok) throw new Error(`Error al obtener cámaras: ${response.statusText}`);

            const camaras = await response.json();
            camarasCache = camaras;  // Guardamos en cache
            renderCamarasTabla(camaras);
        } catch (error) {
            console.error('Error al traer las cámaras:', error);
            alert('Hubo un problema al obtener las cámaras. Revisa la consola para más detalles.');
        }
    }

    function renderCamarasTabla(camarasData) {
        const tbody = document.getElementById("camarasTableBody");
        tbody.innerHTML = "";
        if (!camarasData.length) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color: #888;">No hay cámaras registradas</td></tr>`;
            return;
        }
        camarasData.forEach((cam , index) => {
            const estadoClase = cam.estado.toLowerCase(); 
            tbody.insertAdjacentHTML("beforeend", `
                <tr>
                    <td>${index + 1 }</td>
                    <td>${cam.nombre}</td>
                    <td>${cam.ubicacion}</td>
                    <td>${cam.fuente}</td>
                    <td>
                    <span class="estado ${estadoClase}">
                        ${cam.estado.charAt(0).toUpperCase() + cam.estado.slice(1)}
                    </span>
                        
                    </td>
                    <td>
                        <button class="op-btn editar-btn" data-id="${cam.id}" title="Editar">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="op-btn eliminar-btn" data-id="${cam.id}" title="Eliminar">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
        });

        // Eventos editar
        tbody.querySelectorAll('.editar-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                abrirModalEdicion(id);
            });
        });

        // Eventos eliminar (pendiente)
        tbody.querySelectorAll('.eliminar-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                if (confirm(`¿Eliminar cámara ID ${id}?`)) {
                    alert('Funcionalidad de eliminar pendiente.');
                }
            });
        });
    }

    function abrirModalEdicion(id) {
        const camData = camarasCache.find(cam => String(cam.id) === String(id));
        if (!camData) {
            alert('Cámara no encontrada en cache.');
            return;
        }
        console.log(camData);
        document.getElementById('editarNombre').value = camData.nombre || '';
        document.getElementById('editarLocal').value = camData.local || '';
        document.getElementById('editarUbicacion').value = camData.ubicacion || '';
        document.getElementById('editarTipoCamara').value = camData.tipo_camara || '';
        document.getElementById('editarFuente').value = camData.fuente || '';

        const estadoInput = document.getElementById('editarEstado');
        if (estadoInput) {
            estadoInput.innerHTML = '';
    
            // Opciones para cada estado
            let opciones = [];
            if (camData.estado === 'Inactivo') {
                opciones = ['Desactivado','Inactivo'];
            } else if (camData.estado === 'Activo') {
                opciones = ['Activo', 'Desactivado'];
            } else if (camData.estado === 'Desactivado') {
                opciones = ['Activo','Desactivaddo'];
            }
    
            // Insertamos las opciones dinámicamente
            opciones.forEach(opcion => {
                const optionElement = document.createElement('option');
                optionElement.value = opcion;
                optionElement.textContent = opcion;
                if (camData.estado === opcion) {
                    optionElement.selected = true;
                }
                estadoInput.appendChild(optionElement);
            });
        }
 
        modal.classList.remove('hidden');

        // Guardamos el id de la cámara editada para usarlo en el submit
        formEditarCamara.dataset.editingId = id;
    }

    closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
    window.addEventListener('click', e => { if (e.target === modal) modal.classList.add('hidden'); });

    formEditarCamara.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = formEditarCamara.dataset.editingId;
        if (!id) {
            alert('Error interno: no se encontró la cámara a editar.');
            return;
        }
    
        const datosCamara = {
            nombre: document.getElementById('editarNombre').value.trim(),
            local: document.getElementById('editarLocal').value.trim(),
            ubicacion: document.getElementById('editarUbicacion').value.trim(),
            tipo_camara: document.getElementById('editarTipoCamara').value,
            fuente: document.getElementById('editarFuente').value.trim(),  // <- corregido aquí
            estado: document.getElementById('editarEstado').value
        };
    
        try {
            const res = await fetch(`${apiUrl}/editar/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(datosCamara)
            });
    
            if (!res.ok) throw new Error(`Error al actualizar la cámara: ${res.statusText}`);
    
            alert('Cámara actualizada exitosamente.');
            modal.classList.add('hidden');
            fetchCamaras();  // refrescamos la lista
        } catch (error) {
            console.error('Error al actualizar la cámara:', error);
            alert('No se pudo actualizar la cámara. Revisa la consola para más detalles.');
        }
    });
    

    // Registro nueva cámara (tu código existente)
    const formRegistrarCamara = document.getElementById("formRegistrarCamara");
    if (formRegistrarCamara) {
        formRegistrarCamara.addEventListener("submit", async (e) => {
            e.preventDefault();

            const formData = new FormData(formRegistrarCamara);
            const datosCamara = {
                nombre: formData.get("nombre").trim(),
                local: formData.get("local").trim(),
                ubicacion: formData.get("ubicacion").trim(),
                tipo_camara: formData.get("tipo_camara"),
                fuente: formData.get("fuente").trim()
            };

            if (!datosCamara.nombre || !datosCamara.local || !datosCamara.tipo_camara || !datosCamara.fuente) {
                alert("Por favor, completa todos los campos requeridos.");
                return;
            }

            try {
                const response = await fetch(`${apiUrl}/registrar`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`
                    },
                    body: JSON.stringify(datosCamara)
                });

                const result = await response.json();

                if (response.ok) {
                    alert("Cámara registrada exitosamente.");
                    formRegistrarCamara.reset();
                    switchTab('lista');
                    fetchCamaras();
                } else {
                    alert(`Error al registrar cámara: ${result.error || "Error desconocido"}`);
                }
            } catch (error) {
                console.error("Error al registrar cámara:", error);
                alert("Ocurrió un error al intentar registrar la cámara.");
            }
        });
    }

    // Carga inicial de cámaras
    fetchCamaras();
});
