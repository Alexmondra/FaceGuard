// Inherit dark mode from parent
function checkParentTheme() {
    try {
        const parentTheme = window.parent.document.documentElement.getAttribute('data-theme');
        if (parentTheme) {
            document.documentElement.setAttribute('data-theme', parentTheme);
        }
    } catch (e) {
        console.log('Could not access parent theme');
    }
}

// Initial check
checkParentTheme();

// Recheck periodically in case theme changes
setInterval(checkParentTheme, 1000);

document.addEventListener('DOMContentLoaded', function() {
    // --- Tabs y paneles ---
    const tabListaBtn = document.getElementById("tabListaBtn");
    const tabRegistrarBtn = document.getElementById("tabRegistrarBtn");
    const camarasListaPanel = document.getElementById("camarasListaPanel");
    const camarasRegistroPanel = document.getElementById("camarasRegistroPanel");

    function switchTab(tab) {
        if(tab === 'lista') {
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

    // --- Mock de cámaras iniciales ---
    let camarasData = [
        {id: 1, nombre: 'Entrada Principal', ubicacion: 'Puerta', url: 'rtsp://192.168.1.101/live', estado: 'activa'},
        {id: 2, nombre: 'Estacionamiento', ubicacion: 'Garage', url: 'http://192.168.1.102:8080', estado: 'activa'},
        {id: 3, nombre: 'Sala', ubicacion: 'Interiores', url: 'rtsp://192.168.1.103:554', estado: 'inactiva'},
    ];
    let proxId = 4;

    function renderCamarasTabla() {
        const tbody = document.getElementById("camarasTableBody");
        tbody.innerHTML = "";
        if(!camarasData.length) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color: #888;">No hay cámaras registradas</td></tr>`;
            return;
        }
        camarasData.forEach(cam => {
            tbody.insertAdjacentHTML("beforeend", `
                <tr>
                    <td>${cam.id}</td>
                    <td>${cam.nombre}</td>
                    <td>${cam.ubicacion}</td>
                    <td>${cam.url}</td>
                    <td>
                        <span class="estado ${cam.estado === 'activa' ? 'activa' : 'inactiva'}">${cam.estado.charAt(0).toUpperCase() + cam.estado.slice(1)}</span>
                    </td>
                    <td>
                        <button class="op-btn editar-btn" data-id="${cam.id}" title="Editar"><i class="fas fa-edit"></i></button>
                        <button class="op-btn eliminar-btn" data-id="${cam.id}" title="Eliminar"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `); // Aseguramos ambos botones visibles siempre, con las clases y los iconos
        });
        // Eventos de editar/eliminar (solo alert por ahora)
        tbody.querySelectorAll('.editar-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.getAttribute('data-id');
                alert('Editar cámara ID: ' + id + ' (próximamente)');
            });
        });
        tbody.querySelectorAll('.eliminar-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.getAttribute('data-id');
                if(confirm('¿Eliminar cámara ID ' + id + '?')) {
                    camarasData = camarasData.filter(c => c.id != id);
                    renderCamarasTabla();
                }
            });
        });
    }
    renderCamarasTabla();

    // --- Registro de nueva cámara ---
    const formRegistrarCamara = document.getElementById("formRegistrarCamara");
    if(formRegistrarCamara) {
        formRegistrarCamara.addEventListener('submit', function(e) {
            e.preventDefault();
            const fd = new FormData(formRegistrarCamara);
            const nombre = fd.get("nombre").trim();
            const ubicacion = fd.get("ubicacion").trim();
            const url = fd.get("url").trim();
            const estado = fd.get("estado");
            if(!nombre || !ubicacion || !url || !estado) {
                alert("Completa todos los campos.");
                return;
            }
            camarasData.push({
                id: proxId++,
                nombre, ubicacion, url, estado
            });
            renderCamarasTabla();
            formRegistrarCamara.reset();
            switchTab('lista');
        });
    }
});
