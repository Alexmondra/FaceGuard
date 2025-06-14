// detectados.js (modificado)
let allDetections = [];
let cameras = new Set(); 

document.addEventListener('DOMContentLoaded', fetchDetections);
        
async function fetchDetections() {
    try {
        const response = await fetch(`${API_BASE_URL}/detectados/registros`);
        if (!response.ok) throw new Error('Error al obtener datos');
        
        const data = await response.json();
        allDetections = flattenDetections(data);
        buildFolderTree(data);
        populateCameraFilter();
        document.getElementById('loadingSpinner').style.display = 'none';
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('loadingSpinner').innerHTML = `
            <div class="alert alert-danger">
                Error al cargar las detecciones: ${error.message}
            </div>
        `;
    }
}

// Aplanar todas las detecciones en un solo array para búsqueda
function flattenDetections(data) {
    const detections = [];
    for (const year in data) {
        for (const month in data[year]) {
            for (const day in data[year][month]) {
                data[year][month][day].forEach(det => {
                    det.datePath = `${year}/${month}/${day}`;
                    detections.push(det);
                    if (det.camara_nombre) cameras.add(det.camara_nombre);
                });
            }
        }
    }
    return detections;
}

// Llenar el filtro de cámaras
function populateCameraFilter() {
    const filter = document.getElementById('cameraFilter');
    cameras.forEach(camera => {
        const option = document.createElement('option');
        option.value = camera;
        option.textContent = camera;
        filter.appendChild(option);
    });
}

function buildFolderTree(data) {
    const folderTree = document.getElementById('folderTree');
    const years = Object.keys(data).sort().reverse();
    
    years.forEach(year => {
        const yearItem = document.createElement('div');
        yearItem.className = 'mb-2';
        
        const yearLink = document.createElement('a');
        yearLink.className = 'folder-structure text-decoration-none';
        yearLink.innerHTML = `<i class="bi bi-folder-fill folder-icon"></i> ${year}`;
        yearLink.onclick = () => toggleFolder(year, yearLink);
        
        const monthsContainer = document.createElement('div');
        monthsContainer.className = 'ms-3 d-none';
        monthsContainer.id = `year-${year}`;
        
        const months = Object.keys(data[year]).sort().reverse();
        months.forEach(month => {
            const monthItem = document.createElement('div');
            monthItem.className = 'mb-1';
            
            const monthLink = document.createElement('a');
            monthLink.className = 'folder-structure text-decoration-none';
            monthLink.innerHTML = `<i class="bi bi-folder-fill folder-icon"></i> ${getMonthName(month)}`;
            monthLink.onclick = () => toggleFolder(`${year}/${month}`, monthLink);
            
            const daysContainer = document.createElement('div');
            daysContainer.className = 'ms-3 d-none';
            daysContainer.id = `month-${year}-${month}`;
            
            const days = Object.keys(data[year][month]).sort().reverse();
            days.forEach(day => {
                const dayLink = document.createElement('a');
                dayLink.className = 'folder-structure d-block text-decoration-none';
                dayLink.innerHTML = `<i class="bi bi-folder-fill folder-icon"></i> ${day}`;
                dayLink.onclick = () => showDetections(data, `${year}/${month}/${day}`);
                
                daysContainer.appendChild(dayLink);
            });
            
            monthItem.appendChild(monthLink);
            monthItem.appendChild(daysContainer);
            monthsContainer.appendChild(monthItem);
        });
        
        yearItem.appendChild(yearLink);
        yearItem.appendChild(monthsContainer);
        folderTree.appendChild(yearItem);
    });
}

function toggleFolder(path, linkElement) {
    const containerId = path.includes('/') ? `month-${path.replace('/', '-')}` : `year-${path}`;
    const container = document.getElementById(containerId);
    
    if (container.classList.contains('d-none')) {
        container.classList.remove('d-none');
        linkElement.innerHTML = linkElement.innerHTML.replace('bi-folder-fill', 'bi-folder2-open');
    } else {
        container.classList.add('d-none');
        linkElement.innerHTML = linkElement.innerHTML.replace('bi-folder2-open', 'bi-folder-fill');
    }
}

function showDetections(data, path) {
    const [year, month, day] = path.split('/');
    const detections = data[year]?.[month]?.[day] || [];
    renderDetections(detections);
}

function renderDetections(detections) {
    const container = document.getElementById('detectionsContainer');
    container.innerHTML = '';
    
    detections.forEach(det => {
        const col = document.createElement('div');
        col.className = 'col-md-4 col-lg-3 mb-4';
        
        col.innerHTML = `
            <div class="card h-100">
                <img src="${API_BASE_URL}/detectados/images/${det.foto_captura}" class="card-img-top image-thumbnail" 
                     onclick="showDetectionDetails(${JSON.stringify(det).replace(/"/g, '&quot;')})">
                <div class="card-body">
                    <h5 class="card-title">${det.persona_nombres || 'Desconocido'} ${det.persona_apellidos || ''}</h5>
                    <p class="card-text text-muted small">
                        ${new Date(det.fecha_hora).toLocaleString()}<br>
                        ${det.camara_nombre ? 'Cámara: ' + det.camara_nombre : ''}
                    </p>
                </div>
            </div>
        `;
        
        container.appendChild(col);
    });
}

function showDetectionDetails(detection) {
    document.getElementById('modalDetectionImage').src = `${API_BASE_URL}/detectados/images/${detection.foto_captura}`;
    document.getElementById('personDni').textContent = detection.persona_dni || 'N/A';
    document.getElementById('personNames').textContent = detection.persona_nombres || 'N/A';
    document.getElementById('personLastnames').textContent = detection.persona_apellidos || 'N/A';
    document.getElementById('personBirthdate').textContent = detection.persona_fecha_nacimiento || 'N/A';
    document.getElementById('personGender').textContent = getGenderName(detection.persona_genero);
    document.getElementById('personDescription').textContent = detection.persona_descripcion || 'N/A';
    document.getElementById('cameraName').textContent = detection.camara_nombre || 'N/A';
    document.getElementById('cameraLocal').textContent = detection.camara_local || 'N/A';
    document.getElementById('cameraLocation').textContent = detection.camara_ubicacion || 'N/A';
    document.getElementById('cameraType').textContent = detection.camara_tipo || 'N/A';
    document.getElementById('cameraStatus').textContent = detection.camara_estado || 'N/A';
    document.getElementById('detectionDate').textContent = new Date(detection.fecha_hora).toLocaleString();
    
    // Mostrar modal
    new bootstrap.Modal(document.getElementById('detectionModal')).show();
}

// Buscar por DNI

function applyRealTimeFilters() {
    const dni = document.getElementById('searchDni').value.trim().toLowerCase();
    const camera = document.getElementById('cameraFilter').value;

    let results = allDetections;

    if (dni) {
        results = results.filter(det => 
            det.persona_dni && det.persona_dni.toLowerCase().includes(dni)
        );
    }

    if (camera) {
        results = results.filter(det => 
            det.camara_nombre === camera
        );
    }

    if (results.length > 0) {
        renderDetections(results);
    } else {
        document.getElementById('detectionsContainer').innerHTML = `
            <div class="col-12 text-center py-4">
                <i class="bi bi-exclamation-circle fs-1 text-muted"></i>
                <p class="mt-2">No se encontraron resultados</p>
            </div>
        `;
    }
}

document.getElementById('searchDni').addEventListener('input', applyRealTimeFilters);
document.getElementById('cameraFilter').addEventListener('change', applyRealTimeFilters);

function getMonthName(month) {
    const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                   'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    return months[parseInt(month) - 1] || month;
}

function getGenderName(gender) {
    return {'M': 'Masculino', 'F': 'Femenino', 'O': 'Otro'}[gender] || gender;
}