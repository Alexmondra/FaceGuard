document.addEventListener("DOMContentLoaded", () => {
    const apiUrl = `${API_BASE_URL}/registros`;
    const token = localStorage.getItem("accessToken");

    const buscadosTableBody = document.getElementById("buscadosTableBody");
    const personForm = document.getElementById("personForm");
    const photoInput = document.getElementById("photoInput");
    const photoPreviewContainer = document.getElementById("photoPreviewContainer");
    const imageModal = document.getElementById("imageModal");
    const closeImageModal = document.getElementById("closeImageModal");
    const imageGallery = document.getElementById("imageGallery");

    // Función para abrir el modal de imágenes
    function openImageModal(imagenes) {
        imageGallery.innerHTML = ""; // Limpiar contenido previo
        imagenes.forEach((imagen) => {
            const imgElement = document.createElement("img");
            imgElement.src = imagen;
            imgElement.alt = "Imagen de persona";
            imgElement.classList.add("gallery-image");
            imageGallery.appendChild(imgElement);
        });
        imageModal.style.display = "block";
    }

    // Cerrar el modal de imágenes
    closeImageModal.addEventListener("click", () => {
        imageModal.style.display = "none";
    });

    // Renderizar datos en la tabla
    function renderPersonas(personas) {
        buscadosTableBody.innerHTML = ""; // Limpiar tabla previa
        personas.forEach((persona) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${persona.persona_id}</td>
                <td>${persona.dni}</td>
                <td>${persona.nombres}</td>
                <td>${persona.apellidos}</td>
                <td>${persona.descripcion}</td>
                <td>
                    <img 
                        src="${persona.imagenes_originales[0] || ''}" 
                        alt="Imagen principal" 
                        class="foto-thumbnail" 
                        onclick='openImageModal(${JSON.stringify(persona.imagenes_originales)})'
                    />
                </td>
                <td>
                    <button class="btn-primary">Editar</button>
                    <button class="btn-danger">Eliminar</button>
                </td>
            `;
            buscadosTableBody.appendChild(tr);
        });
    }

    // Cargar datos desde el backend
    async function fetchPersonas() {
        try {
            const response = await fetch(`${apiUrl}/obtener_personas`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!response.ok) throw new Error("Error al obtener personas");

            const data = await response.json();
            renderPersonas(data.personas);
        } catch (error) {
            console.error("Error al cargar personas:", error);
        }
    }

    // Mostrar vista previa de imágenes cargadas
    photoInput.addEventListener("change", () => {
        photoPreviewContainer.innerHTML = ""; // Limpiar previsualizaciones previas
        Array.from(photoInput.files).forEach((file) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = document.createElement("img");
                img.src = e.target.result;
                img.alt = file.name;
                img.classList.add("photo-preview");
                photoPreviewContainer.appendChild(img);
            };
            reader.readAsDataURL(file);
        });
    });

    // Enviar datos al backend para registrar una persona
    personForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData(personForm);
        Array.from(photoInput.files).forEach((file) => {
            formData.append("imagenes[]", file);
        });

        try {
            const response = await fetch(`${apiUrl}/agregar_persona`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            });

            if (!response.ok) throw new Error("Error al registrar persona");

            const data = await response.json();
            alert(data.mensaje);
            fetchPersonas(); // Recargar la tabla
            personForm.reset(); // Limpiar formulario
            photoPreviewContainer.innerHTML = ""; // Limpiar previsualizaciones
        } catch (error) {
            console.error("Error al registrar persona:", error);
            alert("Ocurrió un error al registrar la persona. Intenta nuevamente.");
        }
    });

    // Cargar datos al inicializar la página
    fetchPersonas();
});
