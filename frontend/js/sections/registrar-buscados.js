const photoInput = document.getElementById("photoInput");
const photoContainer = document.getElementById("photoContainer");
const addMore = document.getElementById("addMore");
const photoUpload = document.getElementById("photoUpload");

let selectedFiles = []; // Para mantener las imágenes seleccionadas

// Función para renderizar las imágenes
const renderImage = (file) => {
    const reader = new FileReader();
    reader.onload = (e) => {
        const photoItem = document.createElement("div");
        photoItem.className = "photo-item";

        photoItem.innerHTML = `
            <img src="${e.target.result}" alt="${file.name}">
            <button class="delete-btn">x</button>
        `;

        // Eliminar imagen al hacer clic en la X
        photoItem.querySelector(".delete-btn").addEventListener("click", () => {
            selectedFiles = selectedFiles.filter((f) => f !== file);
            photoItem.remove();
        });

        // Insertar antes del botón "+"
        photoContainer.insertBefore(photoItem, addMore);
    };

    reader.readAsDataURL(file);
};

// Abrir el input al hacer clic en el botón "+"
addMore.addEventListener("click", () => {
    photoInput.click();
});

// Manejar selección de imágenes
photoInput.addEventListener("change", (event) => {
    const files = Array.from(event.target.files);
    files.forEach((file) => {
        if (file.type.startsWith("image/")) {
            selectedFiles.push(file);
            renderImage(file);
        }
    });

    photoInput.value = ""; // Reiniciar el input
});

// Eventos de drag & drop
photoUpload.addEventListener("dragover", (event) => {
    event.preventDefault();
    photoUpload.classList.add("dragging");
});

photoUpload.addEventListener("dragleave", () => {
    photoUpload.classList.remove("dragging");
});

photoUpload.addEventListener("drop", (event) => {
    event.preventDefault();
    photoUpload.classList.remove("dragging");

    const files = Array.from(event.dataTransfer.files);
    files.forEach((file) => {
        if (file.type.startsWith("image/")) {
            selectedFiles.push(file);
            renderImage(file);
        }
    });
});



// Configuración inicial
const apiUrl = `${API_BASE_URL}/registros`;
const token = localStorage.getItem("accessToken");
let listaPersonasGlobal = [];

// Elementos del DOM
const buscadosTableBody = document.getElementById("buscadosTableBody");
const imageModal = document.getElementById("imageModal"); 
const closeImageModal = document.getElementById("closeImageModal"); 
const imageGallery = document.getElementById("imageGallery"); 
const personFormModal = document.getElementById("personFormModal");
const personListSection = document.getElementById("personListSection");
const addPersonBtn = document.getElementById("addPersonBtn");
const backToListBtn = document.getElementById("backToListBtn");
const personForm = document.getElementById("personForm");
addPersonBtn.addEventListener("click", () => switchView("form"));
backToListBtn.addEventListener("click", () => switchView("list"));
personForm.addEventListener("submit", submitPersonForm);

let currentView = "list"; 

// Función para cambiar vista entre lista y formulario
function switchView(view) {
    document.getElementById("photoInput").value = ""; 
    if (view === "list") {
        personFormModal.style.display = "none";
        personListSection.style.display = "block";
        addPersonBtn.style.display = "inline-block";
        backToListBtn.style.display = "none";
        currentView = "list";
    } else if (view === "form") {
        personFormModal.style.display = "block";
        personListSection.style.display = "none";
        addPersonBtn.style.display = "none";
        backToListBtn.style.display = "inline-block";
        currentView = "form";
    }
}

// modal de sms de confirmacion 

function showTemporaryMessage(message, duration = 2000) {
    const messageModal = document.getElementById("messageModal");
    messageModal.textContent = message;
    messageModal.style.display = "block";

    setTimeout(() => {
        messageModal.style.display = "none";
    }, duration);
}

//elimanar : 
function openDeleteModal(personId) {
    const modal = document.getElementById("deleteConfirmModal");
    const confirmButton = document.getElementById("confirmDeleteBtn");
    const cancelButton = document.getElementById("cancelDeleteBtn");
    const closeModal = () => {
        modal.style.display = "none";
    }
    confirmButton.onclick = () => {
        deletePerson(personId);
        closeModal();
    };
    cancelButton.onclick = closeModal;
    modal.style.display = "flex";
}

async function deletePerson(personId) {
    try {
        const response = await fetch(`${apiUrl}/eliminar/${personId}`, {
            method: "DELETE",
        });

        if (response.ok) {
            showTemporaryMessage("Persona eliminada exitosamente", 2000);
            init();
        } else {
            const error = await response.json();
            alert(`Error al eliminar persona: ${error.message || "Error desconocido"}`);
        }
    } catch (error) {
        console.error("Error en deletePerson:", error);
        alert("Error al intentar eliminar la persona.");
    }
}

// modal de editar persona::

let imagesToDelete = [];

function openEditModal(person) {
    console.log("Abriendo modal de edición para:", person);
    
    const modal = document.getElementById("personEditModal");
    const form = document.getElementById("editPersonForm");
    const preview = document.getElementById("edit-photo-preview");

    // Limpiar errores previos
    document.querySelectorAll('.edit-error').forEach(el => el.textContent = '');

    // Llenar campos del formulario
    document.getElementById("edit-id").value = person.persona_id || "";
    document.getElementById("edit-name").value = person.nombre || "";
    document.getElementById("edit-lastname").value = person.apellido || "";
    document.getElementById("edit-dni").value = person.dni || "";
    
    // Seleccionar el sexo (M/F)
    const genderSelect = document.getElementById("edit-gender");
    if (person.genero) {
        genderSelect.value = person.genero.toUpperCase() === 'MASCULINO' ? 'M' : 
                          person.genero.toUpperCase() === 'FEMENINO' ? 'F' : 
                          person.genero;
    } else {
        genderSelect.value = "";
    }

    // Formatear fecha de nacimiento
    if (person.fecha_nacimiento) {
        let birthDate;
        if (typeof person.fecha_nacimiento === 'string') {
            birthDate = person.fecha_nacimiento.includes('T') 
                ? new Date(person.fecha_nacimiento) 
                : new Date(person.fecha_nacimiento + 'T00:00:00');
        } else if (person.fecha_nacimiento.toISOString) {
            birthDate = person.fecha_nacimiento;
        } else {
            birthDate = new Date();
        }
        
        const formattedDate = birthDate.toISOString().split('T')[0];
        document.getElementById("edit-birthdate").value = formattedDate;
    }

    // Descripción física
    document.getElementById("edit-description").value = person.descripcion || "";

    // Limpiar y cargar imágenes existentes
    preview.innerHTML = '';
    imagesToDelete = [];

    if (person.imagenes_originales && person.imagenes_originales.length > 0) {
        person.imagenes_originales.forEach((imgUrl, index) => {
            try {
                const fullImgUrl = imgUrl.startsWith('http') ? imgUrl : `${API_BASE_URL}${imgUrl}`;
                const imgHash = imgUrl.split('/').pop().split('.')[0];

                const imgContainer = document.createElement("div");
                imgContainer.className = "edit-photo-item";

                const img = document.createElement("img");
                img.src = fullImgUrl;
                img.alt = `Foto ${index + 1}`;
                
                const deleteBtn = document.createElement("span");
                deleteBtn.className = "edit-photo-delete";
                deleteBtn.innerHTML = "&times;";
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    imgContainer.classList.toggle("marked-for-delete");
                    if (imgContainer.classList.contains("marked-for-delete")) {
                        imagesToDelete.push(imgHash);
                    } else {
                        imagesToDelete = imagesToDelete.filter(h => h !== imgHash);
                    }
                };

                imgContainer.appendChild(img);
                imgContainer.appendChild(deleteBtn);
                preview.appendChild(imgContainer);

                // Click para vista previa
                img.onclick = () => {
                    openImageModal([fullImgUrl], `Imagen ${index + 1}`);
                };
            } catch (error) {
                console.error(`Error procesando imagen ${index}:`, error);
            }
        });
    }

    // Manejar nuevas imágenes
    const photoInput = document.getElementById("edit-photo-input");
    photoInput.value = ""; // Resetear input
    photoInput.onchange = function(e) {
        const files = e.target.files;
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (!file.type.match('image.*')) continue;

            const reader = new FileReader();
            reader.onload = function(e) {
                const imgContainer = document.createElement("div");
                imgContainer.className = "edit-photo-item new-photo";

                const img = document.createElement("img");
                img.src = e.target.result;
                
                imgContainer.appendChild(img);
                preview.appendChild(imgContainer);
            }
            reader.readAsDataURL(file);
        }
    };

    // Validación al enviar
    form.onsubmit = function(e) {
        e.preventDefault();
        
        // Validar campos
        let isValid = true;
        const nombre = document.getElementById("edit-name").value.trim();
        const apellido = document.getElementById("edit-lastname").value.trim();
        const dni = document.getElementById("edit-dni").value.trim();
        const sexo = document.getElementById("edit-gender").value;
        const fechaNacimiento = document.getElementById("edit-birthdate").value;

        if (!nombre) {
            document.getElementById("edit-name-error").textContent = "Nombre requerido";
            isValid = false;
        }

        if (!apellido) {
            document.getElementById("edit-lastname-error").textContent = "Apellido requerido";
            isValid = false;
        }

        if (!dni || !/^\d+$/.test(dni)) {
            document.getElementById("edit-dni-error").textContent = "DNI inválido";
            isValid = false;
        }

        if (sexo !== "M" && sexo !== "F") {
            document.getElementById("edit-gender-error").textContent = "Seleccione M o F";
            isValid = false;
        }

        if (!fechaNacimiento) {
            document.getElementById("edit-birthdate-error").textContent = "Fecha requerida";
            isValid = false;
        }

        if (isValid) {
            saveEditedPerson();
        }
    };

    // Mostrar modal - CAMBIO IMPORTANTE AQUÍ
    modal.style.display = "block";
    modal.classList.remove("hidden");
}

function closeEditModal() {
    const modal = document.getElementById("personEditModal");
    modal.style.display = "none";
    modal.classList.add("hidden");
}



// Renderizado de personas en tabla
function renderPersonas(personas) {
    buscadosTableBody.innerHTML = ""; // Limpiar la tabla
    personas.forEach((persona, index) => {
        const firstImage = persona.imagenes_originales.length > 0 ? persona.imagenes_originales[0] : null;
        const tr = document.createElement("tr");
        
        const personaData = JSON.stringify(persona)
            .replace(/"/g, '&quot;')
            .replace(/'/g, "\\'");
        
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td>${persona.dni}</td>
            <td>${persona.nombre}</td>
            <td>${persona.apellido || "Sin Apellidos"}</td>
            <td>${persona.genero || "No Definido"}</td>
            <td>${persona.descripcion ? persona.descripcion.substring(0, 50) + (persona.descripcion.length > 50 ? "..." : "") : "Sin Descripción"}</td>
            <td>
                ${
                    firstImage
                        ? `<img src="${firstImage}" alt="Imagen de ${persona.nombre}" class="foto-thumbnail" style="cursor: pointer; width: 50px; height: 50px; border-radius: 5px; object-fit: cover;" />`
                        : `<div class="spinner"></div>`
                }
            </td>
            <td>
                <button class="btn-primary" onclick="openEditModal(${JSON.stringify(persona).replace(/"/g, '&quot;')})">Editar</button>
                <button class="btn-danger" onclick="openDeleteModal(${persona.persona_id})">Eliminar</button>
            </td>
        `;

        // Evento para abrir modal con imágenes
        if (persona.imagenes_originales.length > 0) {
            const imgThumb = tr.querySelector(".foto-thumbnail");
            imgThumb.addEventListener("click", () => {
                openImageModal(persona.imagenes_originales, persona.nombre);
            });
        }

        buscadosTableBody.appendChild(tr);
    });
}

function filtrarPersonas(texto) {
    const filtro = texto.trim().toLowerCase();
    if (!filtro) {
        renderPersonas(listaPersonasGlobal);
        return;
    }
    const filtradas = listaPersonasGlobal.filter(({ nombre, apellido, dni }) =>
        nombre.toLowerCase().includes(filtro) ||
        (apellido && apellido.toLowerCase().includes(filtro)) ||
        dni.toLowerCase().includes(filtro)
    );
    renderPersonas(filtradas);
}


// Obtener personas desde backend
async function fetchPersonas() {
    try {
        const response = await fetch(`${apiUrl}/obtener_personas`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error("Error al obtener personas");

        const data = await response.json();
        listaPersonasGlobal = data.personas || [];
        renderPersonas(listaPersonasGlobal);
    } catch (error) {
        console.error("Error al cargar personas:", error);
    }
}

// Configura evento para búsqueda en vivo
function setupBusquedaEnVivo() {
    const inputBusqueda = document.getElementById("searchInput");
    inputBusqueda.addEventListener("input", (e) => {
        filtrarPersonas(e.target.value);
    });
}

// Validar formulario
function validateForm() {
    let isValid = true;

    const fullNameInput = document.getElementById("fullName");
    const lastNameInput = document.getElementById("lastName");
    const idNumberInput = document.getElementById("idNumber");

    // Validar nombre completo
    if (!fullNameInput.value.trim()) {
        showError("fullNameError", "El nombre es obligatorio.");
        isValid = false;
    } else {
        clearError("fullNameError");
    }

    // Validar apellidos
    if (!lastNameInput.value.trim()) {
        showError("lastNameError", "Los apellidos son obligatorios.");
        isValid = false;
    } else {
        clearError("lastNameError");
    }

    // Validar número de identificación
    if (!idNumberInput.value.trim()) {
        showError("idNumberError", "El número de identificación es obligatorio.");
        isValid = false;
    } else {
        clearError("idNumberError");
    }

    // Validar imágenes usando selectedFiles
    if (selectedFiles.length === 0) {
        showError("photoError", "Debes agregar al menos una imagen.");
        isValid = false;
    } else {
        clearError("photoError");
    }

    return isValid;
}

function showError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) errorElement.textContent = message;
}

function clearError(elementId) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) errorElement.textContent = "";
}

// Enviar datos formulario
async function submitPersonForm(event) {
    event.preventDefault();

    if (!validateForm()) return;

    const formData = new FormData(personForm);
    selectedFiles.forEach((file, index) => {
        formData.append('photos', file);
    });
    console.log(formData);
    try {
        const response = await fetch(`${apiUrl}/agregar_persona`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            body: formData,
        });

        if (!response.ok) throw new Error("Error al registrar la persona");
        personForm.reset();
        selectedFiles = []; 
        switchView("list"); 
        fetchPersonas();
    } catch (error) {
        console.error("Error al enviar los datos:", error);
    }
}

// editar personas:: 
async function saveEditedPerson() {
    const form = document.getElementById("editPersonForm");
    const formData = new FormData();
    const personaId = document.getElementById("edit-id").value;
    
    // Agregar solo los campos necesarios manualmente
    formData.append('idNumber', document.getElementById("edit-dni").value);
    formData.append('fullName', document.getElementById("edit-name").value);
    formData.append('lastName', document.getElementById("edit-lastname").value);
    formData.append('idSexo', document.getElementById("edit-gender").value);
    formData.append('idFecha', document.getElementById("edit-birthdate").value);
    formData.append('physicDescription', document.getElementById("edit-description").value);
    
    // Agregar las imágenes a eliminar
    imagesToDelete.forEach(imgHash => {
        formData.append('imagenes_eliminar[]', imgHash);
    });
    
    // Agregar las nuevas imágenes seleccionadas (solo si hay)
    const photoInput = document.getElementById("edit-photo-input");
    if (photoInput.files.length > 0) {
        Array.from(photoInput.files).forEach(file => {
            formData.append('photos', file);
        });
    }

    try {
        const response = await fetch(`${apiUrl}/editar_persona/${personaId}`, {
            method: "PUT",
            headers: { 
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || "Error al actualizar la persona");
        }

        // Limpiar y cerrar
        imagesToDelete = [];
        closeEditModal();
        fetchPersonas();
        showTemporaryMessage("Persona actualizada correctamente", 2000);

    } catch (error) {
        console.error("Error al guardar los cambios:", error);
        alert(error.message || "Error al actualizar la persona"); // Temporal
    }
}
// Modal de imágenes (si tienes, sino borra estas funciones)

function openImageModal(imagenes, nombrePersona) {
    if (!imageGallery || !imageModal) return; // Seguridad
    imageGallery.innerHTML = ""; // Limpiar galería anterior
    imagenes.forEach((imagen) => {
        const imgElement = document.createElement("img");
        imgElement.src = imagen;
        imgElement.alt = `Imagen de ${nombrePersona}`;
        imgElement.classList.add("gallery-image");
        imageGallery.appendChild(imgElement);
    });

    imageModal.style.display = "flex"; // Mostrar modal como flex
    window.addEventListener("click", handleOutsideClick); // Añadir evento para clics fuera
}

function setupImageModalClose() {
    if (closeImageModal) {
        closeImageModal.addEventListener("click", closeImageModalHandler);
    }
}

function closeImageModalHandler() {
    imageModal.style.display = "none";
    window.removeEventListener("click", handleOutsideClick);
}

function handleOutsideClick(event) {
    if (event.target === imageModal) {
        closeImageModalHandler();
    }
}

// Inicialización
function init() {
    fetchPersonas();
    setupImageModalClose();
    setupBusquedaEnVivo();
    switchView("list"); 
}

document.addEventListener("DOMContentLoaded", init);
