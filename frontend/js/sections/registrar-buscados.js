
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

    // --------- Lógica para buscados: tabla, buscador y modal simple ---------
    // Registros de prueba iniciales
    const buscadosData = [
        {
            id: 1,
            dni: "80221999",
            nombre: "Juan",
            apellido: "Pérez",
            descripcion: "Alto, cabello corto, barba. Última vez con chaqueta azul.",
            foto: "https://randomuser.me/api/portraits/men/10.jpg"
        },
        {
            id: 2,
            dni: "45000211",
            nombre: "María",
            apellido: "Gómez",
            descripcion: "Estatura media, cabello largo, tatuaje en brazo izquierdo.",
            foto: "https://randomuser.me/api/portraits/women/44.jpg"
        },
        {
            id: 3,
            dni: "16729155",
            nombre: "Carlos",
            apellido: "Ramírez",
            descripcion: "Bajo, cicatriz en la ceja derecha, usa lentes.",
            foto: "https://randomuser.me/api/portraits/men/32.jpg"
        },
        {
            id: 4,
            dni: "25261198",
            nombre: "Lucía",
            apellido: "Fernández",
            descripcion: "Mediana edad, tez clara, lunar en mejilla derecha.",
            foto: "https://randomuser.me/api/portraits/women/68.jpg"
        },
    ];
    let tableData = [...buscadosData];
    let lastId = buscadosData.length;

    // Elementos
    const tableBody = document.getElementById("buscadosTableBody");
    const searchInput = document.getElementById("searchInput");
    const addPersonBtn = document.getElementById("addPersonBtn");
    // const addPersonModal = document.getElementById("addPersonModal");
    // const closeAddPersonModal = document.getElementById("closeAddPersonModal");
    // const addPersonForm = document.getElementById("addPersonForm");
    const personFormModal = document.getElementById("personFormModal");
    const closePersonFormModal = document.getElementById("closePersonFormModal");
    const personForm = document.getElementById("personForm");

    function renderTable(data) {
        tableBody.innerHTML = "";
        if (data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;color: #888;">No hay registros para mostrar</td></tr>`;
            return;
        }
        data.forEach(persona => {
            // render always all fields to ensure table shows (reset innerHTML each time)
            tableBody.insertAdjacentHTML('beforeend', `
                <tr>
                    <td>${persona.id}</td>
                    <td>${persona.dni || ""}</td>
                    <td>${persona.nombre}</td>
                    <td>${persona.apellido}</td>
                    <td>${persona.descripcion}</td>
                    <td>
                        <img src="${persona.foto}" alt="foto" class="foto-perfil" style="width:40px;height:40px;border-radius:5px;object-fit:cover;">
                    </td>
                    <td>
                        <button class="op-btn editar-btn" title="Editar"><i class="fas fa-edit"></i></button>
                        <button class="op-btn eliminar-btn" title="Eliminar"><i class="fas fa-trash"></i></button>
                    </td>
                </tr>
            `);
        });
    }

    // Buscador rápido por nombre o apellido
    if (searchInput) {
        searchInput.addEventListener("input", function() {
            const q = this.value.toLowerCase();
            const filtered = tableData.filter(item =>
                item.dni.toLowerCase().includes(q) ||
                item.nombre.toLowerCase().includes(q) ||
                item.apellido.toLowerCase().includes(q)
            );
            renderTable(filtered);
        });
    }

    // Botón agregar: abre modal
    // MODAL DE FORMULARIO AVANZADO
    if (addPersonBtn && personFormModal) {
        addPersonBtn.addEventListener("click", () => {
            personFormModal.style.display = "flex";
            setTimeout(() => {
              personFormModal.querySelector('.modal-large').scrollTop = 0;
            }, 100);
        });
    }
    if (closePersonFormModal && personFormModal && personForm) {
        closePersonFormModal.addEventListener("click", () => {
            personFormModal.style.display = "none";
            personForm.reset();
            // Reiniciar imágenes, validaciones, mensajes...
            if(typeof resetBtn!=='undefined') resetBtn.click();
        });
        personFormModal.addEventListener("click", e => {
            if (e.target === personFormModal) {
                personFormModal.style.display = "none";
                personForm.reset();
                if(typeof resetBtn!=='undefined') resetBtn.click();
            }
        });
    }
    // Agregado rápido (sin validación archivo)
    if (addPersonForm) {
        addPersonForm.addEventListener("submit", function(e) {
            e.preventDefault();
            const formData = new FormData(addPersonForm);
            const dni = formData.get("dni");
            const nombre = formData.get("nombre");
            const apellido = formData.get("apellido");
            const descripcion = formData.get("descripcion");
            let foto = "";
            const fotoFile = formData.get("foto");
            if (fotoFile && fotoFile.size) {
                // Leer archivo como dataURL
                const reader = new FileReader();
                reader.onload = function(evt) {
                    foto = evt.target.result;
                    addRow(dni, nombre, apellido, descripcion, foto);
                };
                reader.readAsDataURL(fotoFile);
            } else {
                // Foto placeholder por defecto
                foto = "https://randomuser.me/api/portraits/lego/6.jpg";
                addRow(dni, nombre, apellido, descripcion, foto);
            }
            addPersonModal.style.display = "none";
            addPersonForm.reset();
        });
    }
    // (Nota: la función addRow y el modal pequeño antiguo pueden eliminarse si dejarás solo el formulario avanzado)
    function addRow(dni, nombre, apellido, descripcion, foto) {
        lastId += 1;
        const newObj = {
            id: lastId,
            dni,
            nombre,
            apellido,
            descripcion,
            foto
        };
        tableData.push(newObj);
        renderTable(tableData);
    }
    // Inicial
    renderTable(tableData);

    // --------- Fin lógica tabla y modal superior ---------
    //const personForm = document.getElementById('personForm');
    const photoUpload = document.getElementById('photoUpload');
    const photoInput = document.getElementById('photoInput');
    const photoPreviewContainer = document.getElementById('photoPreviewContainer');
    const priorityOptions = document.querySelectorAll('.priority-option');
    const priorityValue = document.getElementById('priorityValue');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const successMessage = document.getElementById('successMessage');
    const errorMessage = document.getElementById('errorMessage');
    const resetBtn = document.getElementById('resetBtn');
    
    let uploadedPhotos = [];
    
    // Photo upload handling
    photoUpload.addEventListener('click', function() {
        photoInput.click();
    });
    
    photoInput.addEventListener('change', function(e) {
        handleFileSelect(e.target.files);
    });
    
    // Drag and drop handling
    photoUpload.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.style.borderColor = 'var(--accent-color)';
    });
    
    photoUpload.addEventListener('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.style.borderColor = 'var(--border-color)';
    });
    
    photoUpload.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        this.style.borderColor = 'var(--border-color)';
        
        if (e.dataTransfer.files.length) {
            handleFileSelect(e.dataTransfer.files);
        }
    });
    
    function handleFileSelect(files) {
        if (files.length === 0) return;
        
        // Clear error if exists
        clearError('photoError');
        
        Array.from(files).forEach(file => {
            if (!file.type.match('image.*')) {
                showError('photoError', 'Solo se permiten archivos de imagen');
                return;
            }
            
            if (uploadedPhotos.length >= 5) {
                showError('photoError', 'Máximo 5 fotos permitidas');
                return;
            }
            
            const reader = new FileReader();
            
            reader.onload = function(e) {
                const photoObj = {
                    file: file,
                    dataUrl: e.target.result
                };
                
                uploadedPhotos.push(photoObj);
                addPhotoPreview(photoObj, uploadedPhotos.length - 1);
            };
            
            reader.readAsDataURL(file);
        });
    }
    
    function addPhotoPreview(photoObj, index) {
        const previewDiv = document.createElement('div');
        previewDiv.className = 'photo-preview';
        previewDiv.dataset.index = index;
        
        const img = document.createElement('img');
        img.src = photoObj.dataUrl;
        
        const removeBtn = document.createElement('div');
        removeBtn.className = 'remove-photo';
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            uploadedPhotos.splice(index, 1);
            updatePhotoPreview();
        });
        
        previewDiv.appendChild(img);
        previewDiv.appendChild(removeBtn);
        photoPreviewContainer.appendChild(previewDiv);
        
        // Show the preview container
        photoPreviewContainer.style.display = 'flex';
    }
    
    function updatePhotoPreview() {
        photoPreviewContainer.innerHTML = '';
        
        if (uploadedPhotos.length === 0) {
            photoPreviewContainer.style.display = 'none';
            return;
        }
        
        uploadedPhotos.forEach((photoObj, index) => {
            addPhotoPreview(photoObj, index);
        });
    }
    
    // Priority selection
    priorityOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options
            priorityOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Add selected class to clicked option
            this.classList.add('selected');
            
            // Update hidden input value
            priorityValue.value = this.dataset.value;
            
            // Clear error if exists
            clearError('priorityError');
        });
    });
    
    // Form reset
    resetBtn.addEventListener('click', function() {
        // Reset form fields
        personForm.reset();
        
        // Reset priority selection
        priorityOptions.forEach(opt => opt.classList.remove('selected'));
        priorityValue.value = '';
        
        // Clear uploaded photos
        uploadedPhotos = [];
        updatePhotoPreview();
        
        // Clear all errors
        document.querySelectorAll('.field-error').forEach(el => {
            el.style.display = 'none';
        });
        
        document.querySelectorAll('.input-error').forEach(el => {
            el.classList.remove('input-error');
        });
        
        // Hide messages
        successMessage.style.display = 'none';
        errorMessage.style.display = 'none';
    });
    
    // Form submission
    personForm.addEventListener('submit', function(e) {
        e.preventDefault();
        if (validateForm()) {
            loadingOverlay.style.display = 'flex';
            // Extraer campos relevantes para tabla
            const fullName = document.getElementById('fullName').value.trim();
            const idNumber = document.getElementById('idNumber').value.trim();
            const physicDescription = document.getElementById('physicDescription').value.trim();
            // extraer nombre/apellido
            let nombre = fullName, apellido = "";
            if (fullName.includes(" ")) {
                const partes = fullName.split(" ");
                nombre = partes.shift();
                apellido = partes.join(" ");
            }
            // obtener foto principal (la primera)
            let foto = uploadedPhotos.length > 0 ? uploadedPhotos[0].dataUrl : "https://randomuser.me/api/portraits/lego/6.jpg";

            // Al finalizar el “visible” de loading, se agrega a la tabla
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
                // Agregar a tabla:
                lastId += 1;
                const nuevoRegistro = {
                    id: lastId,
                    dni: idNumber,
                    nombre,
                    apellido,
                    descripcion: physicDescription,
                    foto
                };
                tableData.push(nuevoRegistro);
                renderTable(tableData);
                // Mensaje de éxito
                successMessage.style.display = 'flex';
                // Ocultar success a los 5s
                setTimeout(() => {
                    successMessage.style.display = 'none';
                }, 5000);
                // Resetear form y cerrar modal
                resetBtn.click();
                if (personFormModal) personFormModal.style.display = "none";
                // En app real: aquí se enviaría al backend
            }, 2000);
        }
    });
    
    function validateForm() {
        let isValid = true;
        
        // Clear all previous errors
        document.querySelectorAll('.field-error').forEach(el => {
            el.style.display = 'none';
        });
        
        document.querySelectorAll('.input-error').forEach(el => {
            el.classList.remove('input-error');
        });
        
        // Validate full name
        const fullName = document.getElementById('fullName');
        if (!fullName.value.trim()) {
            showError('fullNameError', 'El nombre completo es requerido');
            fullName.classList.add('input-error');
            isValid = false;
        }
        
        // Validate ID number
        const idNumber = document.getElementById('idNumber');
        if (!idNumber.value.trim()) {
            showError('idNumberError', 'El número de identificación es requerido');
            idNumber.classList.add('input-error');
            isValid = false;
        }
        
        // Validate photos
        if (uploadedPhotos.length === 0) {
            showError('photoError', 'Al menos una fotografía es requerida');
            isValid = false;
        }
        
        // Validate priority
        if (!priorityValue.value) {
            showError('priorityError', 'Seleccione un nivel de prioridad');
            isValid = false;
        }
        
        return isValid;
    }
    
    function showError(elementId, message) {
        const errorElement = document.getElementById(elementId);
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
    
    function clearError(elementId) {
        const errorElement = document.getElementById(elementId);
        errorElement.style.display = 'none';
    }
});
