// Configuración inicial
const apiUrl = `${API_BASE_URL}/registros`;
const token = localStorage.getItem("accessToken");
let listaPersonasGlobal = [];
// Elementos del DOM
const buscadosTableBody = document.getElementById("buscadosTableBody");
const imageModal = document.getElementById("imageModal"); // Si no está en el HTML, quita o adapta esta parte
const closeImageModal = document.getElementById("closeImageModal"); // Igual que arriba
const imageGallery = document.getElementById("imageGallery"); // Igual que arriba

const personFormModal = document.getElementById("personFormModal");
const personListSection = document.getElementById("personListSection");
const addPersonBtn = document.getElementById("addPersonBtn");
const backToListBtn = document.getElementById("backToListBtn");
const personForm = document.getElementById("personForm");

let currentView = "list"; 

// Función para cambiar vista entre lista y formulario
function switchView(view) {
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

//elimanar : 
function openDeleteModal(personId) {
    const modal = document.getElementById("deleteConfirmModal");
    const confirmButton = document.getElementById("confirmDeleteBtn");
    confirmButton.onclick = () => {
        deletePerson(personId);
        closeDeleteModal();
    };
    modal.style.display = "flex"; // Mostrar el modal
}

function closeDeleteModal() {
    const modal = document.getElementById("deleteConfirmModal");
    modal.style.display = "none"; // Ocultar el modal
}

 
async function deletePerson(personId) {
    try {
        const response = await fetch(`${apiUrl}/eliminar/${personId}`, {
            method: "DELETE",
        });

        if (response.ok) {
            alert("Persona eliminada exitosamente");
            init(); // Recargar la lista de personas
        } else {
            const error = await response.json();
            alert(`Error al eliminar persona: ${error.message || "Error desconocido"}`);
        }
    } catch (error) {
        console.error("Error en deletePerson:", error);
        alert("Error al intentar eliminar la persona.");
    }
}



// Renderizado de personas en tabla
function renderPersonas(personas) {
    buscadosTableBody.innerHTML = ""; // Limpiar la tabla
    personas.forEach((persona) => {
        const firstImage = persona.imagenes_originales.length > 0 ? persona.imagenes_originales[0] : null;
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${persona.persona_id}</td>
            <td>${persona.dni}</td>
            <td>${persona.nombre}</td>
            <td>${persona.apellido || "Sin Apellidos"}</td>
            <td>${persona.descripcion || "Sin Descripción"}</td>
            <td>
                ${
                    firstImage
                        ? `<img src="${firstImage}" alt="Imagen de ${persona.nombre}" class="foto-thumbnail" style="cursor: pointer; width: 50px; height: 50px; border-radius: 5px; object-fit: cover;" />`
                        : "<p>No hay imágenes</p>"
                }
            </td>
            <td>
                <button class="btn-primary">Editar</button>
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
    const photoInput = document.getElementById("photoInput");

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

    // Validar imágenes
    if (photoInput.files.length === 0) {
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
    console.log(formData);
    try {
        const response = await fetch(`${apiUrl}/agregar_persona`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
            body: formData,
        });

        if (!response.ok) throw new Error("Error al registrar la persona");

        personForm.reset();
        switchView("list");
        fetchPersonas();
    } catch (error) {
        console.error("Error al enviar los datos:", error);
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
    window.removeEventListener("click", handleOutsideClick); // Remover listener al cerrar
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

    addPersonBtn.addEventListener("click", () => switchView("form"));
    backToListBtn.addEventListener("click", () => switchView("list"));
    personForm.addEventListener("submit", submitPersonForm);
    
    setupBusquedaEnVivo();

    switchView("list"); // mostrar lista al inicio
}

document.addEventListener("DOMContentLoaded", init);
