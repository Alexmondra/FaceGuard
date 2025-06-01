// Menu and content functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing menu system...');

    // Initialize menu elements
    const menuBtn = document.getElementById('menuBtn');
    const sideMenu = document.getElementById('sideMenu');
    const closeMenu = document.getElementById('closeMenu');
    const mainContent = document.getElementById('mainContent');
    const configBtn = document.getElementById('configBtn');
    const configSubmenu = document.getElementById('configSubmenu');

    console.log('Menu elements:', { menuBtn, sideMenu, closeMenu, mainContent, configBtn, configSubmenu });

    // Show initial section
    showSection('records');

    // Menu button click handler
    if (menuBtn) {
        menuBtn.addEventListener('click', function(e) {
            console.log('Menu button clicked');
            e.stopPropagation();
            sideMenu.style.display = 'block'; // Ensure menu is visible
            sideMenu.classList.toggle('active');
            mainContent.classList.toggle('shifted');
        });
    }

    // Close button click handler
    if (closeMenu) {
        closeMenu.addEventListener('click', function(e) {
            console.log('Close button clicked');
            e.stopPropagation();
            sideMenu.classList.remove('active');
            mainContent.classList.remove('shifted');
        });
    }

    // Config button click handler
    if (configBtn) {
        configBtn.addEventListener('click', function(e) {
            console.log('Config button clicked');
            e.preventDefault();
            e.stopPropagation();
            configSubmenu.classList.toggle('active');
            this.classList.toggle('active');
        });
    }

    // Handle all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.id !== 'configBtn') {
            item.addEventListener('click', function() {
                console.log('Nav item clicked:', this.textContent);
                
                // Remove active class from all items
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                
                // Add active class to clicked item
                this.classList.add('active');
                
                // Close submenu
                if (configSubmenu) {
                    configSubmenu.classList.remove('active');
                }
                
                // Close menu on mobile
                if (window.innerWidth <= 768) {
                    setTimeout(() => {
                        sideMenu.classList.remove('active');
                        mainContent.classList.remove('shifted');
                    }, 300);
                }
            });
        }
    });

    // Handle submenu items
    document.querySelectorAll('.submenu-item').forEach(item => {
        item.addEventListener('click', function() {
            console.log('Submenu item clicked:', this.textContent);
            
            // Remove active class from all submenu items
            document.querySelectorAll('.submenu-item').forEach(i => i.classList.remove('active'));
            
            // Add active class to clicked item
            this.classList.add('active');
            
            // Keep config button active
            if (configBtn) {
                configBtn.classList.add('active');
            }
            
            // Close menu on mobile
            if (window.innerWidth <= 768) {
                setTimeout(() => {
                    sideMenu.classList.remove('active');
                    mainContent.classList.remove('shifted');
                }, 300);
            }
        });
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (sideMenu && !sideMenu.contains(e.target) && 
            !menuBtn.contains(e.target) && 
            sideMenu.classList.contains('active')) {
            console.log('Clicking outside menu - closing');
            sideMenu.classList.remove('active');
            mainContent.classList.remove('shifted');
        }
    });
});

// --------------------- MODAL REGISTRO DE USUARIO ---------------------
window.openRegisterModal = function() {
    document.getElementById('registerUserModal').style.display = 'flex';
}
window.closeRegisterModal = function() {
    document.getElementById('registerUserModal').style.display = 'none';
}

// Vincula el botón del menú (por si el handler HTML se pierde)
document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('registerUserBtn');
    if (btn) btn.onclick = openRegisterModal;
});

// Envía el formulario de registro AJAX
window.handleRegisterUser = async function(e) {
    e.preventDefault();
    // Recoge valores
    const user = document.getElementById('regUsername').value.trim();
    const fname = document.getElementById('regFirstname').value.trim();
    const lname = document.getElementById('regLastname').value.trim();
    const pass = document.getElementById('regPassword').value;
    const pass2 = document.getElementById('regConfirmPassword').value;
    if (!user || !fname || !lname || !pass || !pass2)
        return alert("Completa todos los campos");
    if (pass !== pass2)
        return alert("Las contraseñas no coinciden");
    try {
        const response = await fetch(`${serverUrl}/api_guardarUsuario`, { 
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: user,
                firstname: fname,
                lastname: lname,
                password: pass
            })
        });
        const data = await response.json();
        if (response.ok) {
            alert("Usuario registrado exitosamente");
            closeRegisterModal();
            document.getElementById('registerUserForm').reset();
        } else {
            alert(data.error || "No se pudo registrar el usuario.");
        }
    } catch (e) {
        alert("Error de conexión al registrar usuario: " + e);
    }
};


// Function to show content sections
function showSection(sectionId) {
    console.log('Showing section:', sectionId);
    
    // Hide all sections first
    document.querySelectorAll('.content').forEach(section => {
        section.style.display = 'none';
    });
    
    // Show selected section
    const selectedSection = document.getElementById(sectionId);
    if (selectedSection) {
        selectedSection.style.display = 'block';
        
        // Load section-specific content
        switch(sectionId) {
            case 'records':
                loadPersonRecords();
                break;
            case 'attendance':
                cargarAsistencias();
                break;
            case 'liveCamera':
                const videoFeed = document.getElementById('videoFeed');
                if (videoFeed) {
                    videoFeed.style.display = 'block';
                }
                break;
            case 'cameraSettings':
                const camaraForm = document.getElementById('camaraForm');
                if (camaraForm) {
                    camaraForm.reset();
                }
                break;
        }
    }
}

// Make sure the showSection function is globally available
window.showSection = showSection;

const serverUrl = "http://127.0.0.1:5000"; // Cambia aquí la URL si es necesario
        const socket = io.connect(serverUrl, {
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 2000,
            timeout: 20000,
            transports: ["websocket"],
        });

        socket.on("connect", () => {
            console.log("Conexión establecida");
        });

        socket.on("disconnect", () => {
            console.warn("Conexión perdida. Intentando reconectar...");
        });

        socket.on("connect_error", (error) => {
            console.error("Error de conexión WebSocket:", error);
        });

    //lo de tarsmitir video y reconoc
        // Elementos del DOM
        const videoFeed = document.getElementById("videoFeed");
        const startVideoBtn = document.getElementById("startVideoBtn");
        const stopVideoBtn = document.getElementById("stopVideoBtn");
        const startRecognitionBtn = document.getElementById("startRecognitionBtn");
        const stopRecognitionBtn = document.getElementById("stopRecognitionBtn");

        // Evento para iniciar el video
        startVideoBtn.addEventListener("click", async () => {
            videoFeed.style.display = "none";
            try {
                // Activar cámara primero
                const resp = await fetch(`${serverUrl}/activar_camara`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ tipo_camara: "USB", fuente: "0" })
                });
                const data = await resp.json();
                if (data.status === "success") {
                    socket.emit('request_video');
                    setTimeout(() => {
                        socket.emit('start_video');
                    }, 100); // asegura que hilo arranca antes del flag
                    videoFeed.style.display = "block";
                    console.log("Video iniciado");
                    // Control de timeout: si no llegan frames tras 5s, alerta
                    let frameRecibido = false;
                    const frameListener = () => { frameRecibido = true; };
                    socket.once("video_frame", frameListener);
                    setTimeout(() => {
                        socket.off("video_frame", frameListener);
                        if (!frameRecibido) {
                            alert("No se reciben imágenes desde la cámara. Verifica que esté conectada y funcional.");
                        }
                    }, 5000);
                } else {
                    alert(data.message || "No se pudo conectar la cámara.");
                }
            } catch (e) {
                alert("No se pudo activar la cámara: " + e);
            }
        });

        // Evento para detener el video
        stopVideoBtn.addEventListener("click", () => {
            socket.emit('stop_video'); // Notificar al backend para detener el envío de frames
            videoFeed.style.display = "none"; // Ocultar la transmisión de video
            console.log("Video detenido");
        });

        // Evento para iniciar el reconocimiento
        startRecognitionBtn.addEventListener("click", () => {
            socket.emit('start_recognition'); // Notificar al backend para iniciar el reconocimiento facial
            console.log("Reconocimiento facial iniciado");
        });

        // Evento para detener el reconocimiento
        stopRecognitionBtn.addEventListener("click", () => {
            socket.emit('stop_recognition'); // Notificar al backend para detener el reconocimiento facial
            console.log("Reconocimiento facial detenido");
        }); 


        /*el de video*/

            socket.on("video_frame", (data) => {
                if (data && data.frame) {
                    const feed = document.getElementById("videoFeed");
                    if (feed) {
                        feed.src = "data:image/jpeg;base64," + data.frame;
                        feed.style.display = "block";
                    }
                }
            });

            document.addEventListener("DOMContentLoaded", () => {
                document.getElementById("liveCameraButton").addEventListener("click", () => {
                    console.log("Solicitando transmisión de video...");
                    socket.emit("request_video");
                });
            });





        /**aun vendo si sievre*/
        function conectarCamara(event) {
            event.preventDefault(); // Evitar el comportamiento por defecto del formulario
    
            const tipoCamara = document.getElementById("tipoCamara").value;
            const camaraFuente = document.getElementById("camaraFuente").value;
    
            if (tipoCamara && camaraFuente) {
                // Enviar el tipo de cámara y la fuente (IP o URL) a través de una solicitud POST
                fetch(`${serverUrl}/activar_camara`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        tipo_camara: tipoCamara,
                        fuente: camaraFuente
                    })
                })
                .then(response => response.json())
                .then(data => {
                    console.log(data);  // Aquí puedes mostrar el resultado en el cliente
                    alert(data.message);  // Muestra el mensaje de éxito o error
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Hubo un problema al conectar la cámara.');
                });
            } else {
                alert("Por favor, ingrese todos los datos.");
            }
        }


        /*aqui va lo demas */

        function showContent(sectionId) {
            document.querySelectorAll('.content').forEach(section => {
                section.style.display = section.id === sectionId ? 'block' : 'none';
            });

            // Cargar registros cuando se selecciona la sección "REGISTROS"
            if (sectionId === 'records') {
                loadPersonRecords();
            }
            if(sectionId === 'attendance'){
                cargarAsistencias();
            }
        }

async function loadPersonRecords() {
    const personGrid = document.getElementById("personGrid");
    personGrid.innerHTML = ""; // Limpiar contenido previo

    try {
        const response = await fetch(`${serverUrl}/obtener_personas`);
        if (!response.ok) {
            throw new Error("Error al cargar los registros");
        }

        const data = await response.json();
        const personas = data.personas;

        personas.forEach(person => {
            const personCard = document.createElement("div");
            personCard.classList.add("person-card"); 
            personCard.setAttribute("data-id", person.id);

            const personImage = document.createElement("img");
            personImage.src = person.imagenes.length > 0 
                ? `${serverUrl}/${person.imagenes[0]}` 
                : "https://via.placeholder.com/200x150";
            personImage.alt = `Imagen de ${person.nombre} ${person.apellido ?? ''}`;

            const personInfo = document.createElement("div");
            personInfo.classList.add("info");

            const personName = document.createElement("p");
            personName.textContent = `Nombre: ${person.nombre || ''} ${person.apellido || ''}`;

            const personDNI = document.createElement("p");
            personDNI.textContent = `DNI: ${person.dni}`;

            const personOptions = document.createElement("div");
            personOptions.classList.add("options");

            // Botón de Editar
            const editButton = document.createElement("button");
            editButton.textContent = "Editar";
            editButton.classList.add("edit-button");
            editButton.addEventListener("click", (event) => {
                event.stopPropagation();
                // Pre-cargar también el apellido desde el backend si está
                openPersonModal(person);
            });

            // Botón de Eliminar
            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Eliminar";
            deleteButton.classList.add("delete-button");
            deleteButton.addEventListener("click", (event) => {
                event.stopPropagation();
                openDeleteModal(person.id, `${person.nombre} ${person.apellido || ''}`);
            });

            personOptions.appendChild(editButton);
            personOptions.appendChild(deleteButton);

            personInfo.appendChild(personName);
            personInfo.appendChild(personDNI);
            personInfo.appendChild(personOptions);

            personCard.appendChild(personImage);
            personCard.appendChild(personInfo);

            // Clic en la tarjeta (pero no en botones) abre el modal para ver imágenes
            personCard.addEventListener("click", (e) => {
                if (![editButton, deleteButton].includes(e.target)) {
                    openModal(`${person.nombre} ${person.apellido || ''}`, person.imagenes);
                }
            });

            personGrid.appendChild(personCard);
        });

    } catch (error) {
        console.error("Error al cargar los registros:", error);
        const errorMsg = document.createElement("p");
        errorMsg.textContent = "Error al cargar los registros.";
        personGrid.appendChild(errorMsg);
    }
}

/** --- Modal Unificado Agregar/Editar Persona --- **/

let imagesToDelete = [];

function openPersonModal(person = null) {
    document.getElementById('personModal').style.display = 'flex';

    // Limpiar imágenes previas y arrays de gestión
    document.getElementById('previewImages').innerHTML = "";
    imagesToDelete = [];

    // Si no hay persona, es agregar
    if (!person) {
        document.getElementById('personModalTitle').textContent = "Agregar Nueva Persona";
        document.getElementById('personId').value = "";
        document.getElementById('personDNI').value = "";
        document.getElementById('personDNI').disabled = false;
        document.getElementById('personName').value = "";
        document.getElementById('personLastName').value = "";
        document.getElementById('personImages').value = "";
        document.getElementById('personSubmitButton').textContent = "Agregar Persona";
    } else {
        document.getElementById('personModalTitle').textContent = "Editar Persona";
        document.getElementById('personId').value = person.id ?? "";
        document.getElementById('personDNI').value = person.dni ?? "";
        document.getElementById('personDNI').disabled = true; // No editable
        document.getElementById('personName').value = person.nombre ?? "";
        // Cargar el apellido si viene del backend, si no lo trae lo dejamos vacío
        document.getElementById('personLastName').value = person.apellido ?? "";
        document.getElementById('personImages').value = "";
        document.getElementById('personSubmitButton').textContent = "Guardar Cambios"; 
        // Renderizar imágenes actuales para eliminar
        const preview = document.getElementById('previewImages');
        preview.innerHTML = '';
        if (person.imagenes && person.imagenes.length > 0) {
            person.imagenes.forEach(imgUrl => {
                // extraer solo hash de la ruta para backend
                // ej: /imagenes/12345678/e9ee9f05bf...jpg
                const hashMatch = imgUrl.match(/\/([a-f0-9]{32,})\.jpg$/i);
                const imgHash = hashMatch ? hashMatch[1] : imgUrl;
                const div = document.createElement("div");
                div.className = "img-thumb-removable";
                const img = document.createElement("img");
                img.src = serverUrl + "/" + imgUrl;
                img.className = "thumb-img";
                img.title = "Clic para marcar/desmarcar para eliminar";
                div.appendChild(img);

                // Mostrar un tache para eliminar y marcar visual
                const mark = document.createElement("span");
                mark.className = "delete-x";
                mark.innerHTML = "&times;";
                div.appendChild(mark);

                div.onclick = function() {
                    // toggle selección visual
                    if (div.classList.contains("selected-for-delete")) {
                        div.classList.remove("selected-for-delete");
                        imagesToDelete = imagesToDelete.filter(h => h !== imgHash);
                    } else {
                        div.classList.add("selected-for-delete");
                        imagesToDelete.push(imgHash);
                    }
                };
                preview.appendChild(div);
            });
        }
    }

    // Cambiar onclick según contexto
    document.getElementById('personSubmitButton').onclick = submitPerson;
}

function closePersonModal() {
    document.getElementById('personModal').style.display = 'none';
    // Limpia campos e imágenes por si acaso
    document.getElementById('personForm').reset();
    document.getElementById('previewImages').innerHTML = "";
    document.getElementById('personDNI').disabled = false;
    imagesToDelete = [];
}

async function submitPerson() {
    const id = document.getElementById('personId').value;
    const dni = document.getElementById('personDNI').value;
    const nombre = document.getElementById('personName').value;
    const apellido = document.getElementById('personLastName').value;
    const imageInput = document.getElementById('personImages');
    const images = imageInput.files;

    // Validación de campos
    if (!nombre || !apellido || !dni) {
        alert("Por favor, complete todos los campos obligatorios.");
        return;
    }
    // Si es agregar, debe tener imágenes. Si es editar, pueden omitirse.
    if (!id && images.length === 0) {
        alert("Por favor, seleccione al menos una imagen.");
        return;
    }

    if (images.length > 10) {
        alert("Por favor, seleccione como máximo 10 imágenes.");
        return;
    }

    const formData = new FormData();
    formData.append('nombre', nombre);
    formData.append('apellido', apellido);
    formData.append('dni', dni);

    // Imágenes nuevas
    for (let i = 0; i < images.length; i++) {
        formData.append("imagenes[]", images[i]);
    }
    // Imágenes a eliminar solo en edición
    // Asegurarse de incluir imágenes a eliminar (como array), y hacerlo compatible con el backend
    if (id && Array.isArray(imagesToDelete) && imagesToDelete.length > 0) {
        imagesToDelete.forEach(h => {
            // Fuerza nombre y valor en FormData
            formData.append("imagenes_eliminar[]", h);
        });
    }

    let url, method;
    if (id) {
        url = `${serverUrl}/editar_persona/${id}`;
        method = "POST";
    } else {
        url = `${serverUrl}/agregar_persona`;
        method = "POST";
    }

    try {
        const response = await fetch(url, {
            method,
            body: formData,
        });
        const data = await response.json();

        if (response.ok) {
            alert(id ? "Persona actualizada exitosamente." : "Persona agregada exitosamente.");
            closePersonModal();
            // Limpiar file input tras guardar para evitar duplicados en la siguiente edición
            document.getElementById('personImages').value = "";
            if (typeof loadPersonRecords === "function") loadPersonRecords();
        } else {
            alert('Error: ' + (data?.error || 'Error desconocido'));
        }
    } catch (e) {
        alert('Error conectando al backend: ' + e);
    }
}

function openAddPersonModal() { openPersonModal(null); }

// Renderizado actualizado para incluir el botón Editar con modal unificado
function renderPersonGrid(personas) {
    const grid = document.getElementById('personGrid');
    grid.innerHTML = '';
    personas.forEach(person => {
        const card = document.createElement('div');
        card.classList.add('person-card');
        card.setAttribute("data-id", person.id);

        // Imagen preview
        let imgHtml = '';
        if (person.imagenes && person.imagenes.length > 0) {
            imgHtml = `<img src="${serverUrl}/${person.imagenes[0]}" alt="Imagen de ${person.nombre}" class="person-img" style="width:100px; height:100px; object-fit:cover;">`;
        } else {
            imgHtml = `<img src="https://via.placeholder.com/200x150" alt="Sin imagen" style="width:100px; height:100px; object-fit:cover;">`;
        }

        // Botones (ambos siempre)
        const editBtn = document.createElement("button");
        editBtn.classList.add("edit-button");
        editBtn.textContent = "Editar";
        editBtn.onclick = function(e) {
            e.stopPropagation();
            openPersonModal(person);
        };

        const delBtn = document.createElement("button");
        delBtn.classList.add("delete-button");
        delBtn.textContent = "Eliminar";
        delBtn.onclick = function(e) {
            e.stopPropagation();
            openDeleteModal(person.id, `${person.nombre || ''} ${person.apellido || ''}`);
        };

        card.innerHTML = `
            ${imgHtml}
            <h3>${person.nombre || ''} ${person.apellido || ''}</h3>
            <p><b>DNI:</b> ${person.dni || ''}</p>
        `;
        card.appendChild(editBtn);
        card.appendChild(delBtn);

        grid.appendChild(card);

        // (Opcional) Click en la tarjeta para ver imágenes
        card.addEventListener("click", (e) => {
            if (![editBtn, delBtn].includes(e.target)) {
                openModal(`${person.nombre} ${person.apellido || ''}`, person.imagenes);
            }
        });
    });
}

// Unifica para que cargarPersonas y loadPersonRecords usen el mismo render:
window.cargarPersonas = async function () {
    try {
        const resp = await fetch(`${serverUrl}/obtener_personas`);
        const data = await resp.json();
        if (data && data.personas) {
            renderPersonGrid(data.personas);
        }
    } catch (e) {
        console.error('Error obteniendo personas:', e);
    }
};

async function loadPersonRecords() {
    try {
        const response = await fetch(`${serverUrl}/obtener_personas`);
        if (!response.ok) {
            throw new Error("Error al cargar los registros");
        }
        const data = await response.json();
        const personas = data.personas;
        renderPersonGrid(personas);
    } catch (error) {
        console.error("Error al cargar los registros:", error);
        const personGrid = document.getElementById("personGrid");
        personGrid.innerHTML = "<p>Error al cargar los registros.</p>";
    }
}

// ---------------------- FLUJO ELIMINAR PERSONA (modal + AJAX + feedback) ------------------

// Estado actual para eliminar (se inicializa en null)
let idToDelete = null;

// Abre el modal y conserva el id de persona a eliminar
window.openDeleteModal = function(personaId, personaNombre) {
    idToDelete = personaId;
    const modalText = document.getElementById('deleteModalText');
    if (modalText)
        modalText.textContent = '¿Estás seguro de que deseas eliminar a ' + (personaNombre || 'esta persona') + '?';
    document.getElementById('deleteConfirmModal').style.display = 'block';
};

// Cierra el modal y resetea estado
window.closeDeleteModal = function() {
    idToDelete = null;
    document.getElementById('deleteConfirmModal').style.display = 'none';
};

// Feedback visual "toast"
function showToast(msg) {
    let toast = document.getElementById('toastMsg');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toastMsg';
        toast.style.position = 'fixed';
        toast.style.bottom = '24px';
        toast.style.left = '50%';
        toast.style.transform = 'translateX(-50%)';
        toast.style.background = '#28a745';
        toast.style.color = '#fff';
        toast.style.padding = '12px 32px';
        toast.style.borderRadius = '6px';
        toast.style.fontSize = '18px';
        toast.style.zIndex = '9999';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.display = 'none';
    }, 2200);
}

// Evento confirmación del modal: DELETE AJAX y actualizar UI
document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('confirmDeleteBtn');
    if (btn) {
        btn.onclick = async function() {
            if (idToDelete) {
                try {
                    // AJAX DELETE con id del backend (ajustar url a serverUrl si necesario)
                    const response = await fetch(`${serverUrl}/eliminar_persona/${idToDelete}`, {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const result = await response.json();
                    if (result.success) {
                        showToast("Eliminado correctamente");
                        // Quitar la tarjeta de la persona del DOM
                        const grid = document.getElementById('personGrid');
                        if (grid) {
                            // Para que funcione: asegurarse en render que cada card tenga atributo data-id
                            const card = grid.querySelector(`.person-card[data-id="${idToDelete}"]`);
                            if (card) card.remove();
                            else {
                                // fallback: recargar listado si no hay data-id
                                if (typeof loadPersonRecords === 'function') loadPersonRecords();
                            }
                        }
                    } else {
                        showToast(result.message || "No se pudo eliminar");
                    }
                } catch (e) {
                    showToast("Error de conexión al eliminar");
                }
                window.closeDeleteModal();
            }
        }
    }
});

// Adaptar renderPersonGrid/creación de tarjetas para que cada .person-card tenga el atributo data-id
// Por ejemplo, en el bucle donde se crean personCard:
// personCard.setAttribute("data-id", person.id)
// --------------------------------------------------------------------------------

// Sobrescribe (o provee) la función global de cargar personas (invocada en el HTML)
window.cargarPersonas = async function () {
    try {
        const resp = await fetch(`${serverUrl}/obtener_personas`);
        const data = await resp.json();
        if (data && data.personas) {
            renderPersonGrid(data.personas);
        }
    } catch (e) {
        console.error('Error obteniendo personas:', e);
    }
};
document.addEventListener("DOMContentLoaded", cargarPersonas);
// openEditModal obsoleto, toda la lógica usa openPersonModal(person)

function openModal(personName, images) {
    const modal = document.getElementById("personImagesModal");
    const gallery = document.getElementById("imageGallery");
    const title = document.getElementById("personNameTitle");

    // Limpiar contenido previo
    gallery.innerHTML = "";
    title.textContent = `Imágenes de ${personName}`;

    // Agregar imágenes al modal
    images.forEach(image => {
        const imgElement = document.createElement("img");
        imgElement.src = `${serverUrl}/${image}`;
        imgElement.alt = `Imagen de ${personName}`;
        gallery.appendChild(imgElement);
    });

    // Mostrar modal
    modal.style.display = "flex";
}

function closeModal() {
    const modal = document.getElementById("personImagesModal");
    modal.style.display = "none";
}

function openAddPersonModal() {
    document.getElementById("addPersonModal").style.display = "flex";
}

function closeAddPersonModal() {
    // Obsoleto con modal único, dejar vacío o eliminar si ya no se invoca en ningún lado
}
/*enviar imagenes */

/*agregar mas img a la misma persona*/

// Función para consumir el endpoint y renderizar la tabla
function calcularSemanaActual(fechaReferencia) {
    const diasSemana = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
    const fecha = new Date(fechaReferencia);
   
    const diaActual = fecha.getDay(); // Obtiene el día de la semana (0 a 6)
    console.log(diaActual)
    const semana = {};
    for (let i = 0; i < 7; i++) {
        const nuevaFecha = new Date(fecha);
        nuevaFecha.setDate(fecha.getDate() - diaActual + i); // Alinea las fechas correctamente
        semana[diasSemana[(diaActual + i) % 7]] = nuevaFecha.toISOString().split("T")[0]; // Mapear día correctamente
    }
  
    return semana;
}

async function cargarAsistencias() {
    try {
        const response = await fetch(`${serverUrl}/obtener_asistencias`);
        if (!response.ok) {
            throw new Error("Error al obtener los datos de asistencias");
        }

        const data = await response.json();
        const asistencias = data.personas_asistencias;
        const dniTableBody = document.getElementById("dniTableBody");

        dniTableBody.innerHTML = ""; // Limpiar la tabla

        if (!asistencias || asistencias.length === 0) {
            dniTableBody.innerHTML = "<tr><td colspan='8'>No hay asistencias registradas esta semana.</td></tr>";
            return;
        }

        // Calcular la semana actual acordes a la zona horaria de Lima/Peru
        // (esto depende del sistema del cliente)
        const diasSemana = ["Domingo","Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"];
        const hoy = new Date();
        hoy.setHours(0,0,0,0);

        // Obtener la fecha del domingo anterior o del mismo día si es domingo
        const primerDia = new Date(hoy);
        primerDia.setDate(hoy.getDate() - hoy.getDay());

        // Crear referencia semana [{nombre, fecha: 'YYYY-MM-DD', isToday, diaIdx}]
        const semana = [];
        for(let d=0; d<7; d++) {
            const date = new Date(primerDia);
            date.setDate(primerDia.getDate() + d);
            semana.push({
                nombre: diasSemana[d],
                fecha: date.toISOString().split("T")[0],
                isToday: date.getTime() === hoy.getTime(),
                diaIdx: d
            });
        }

        // Resalta el th (encabezado) del día actual
        document.querySelectorAll(".dni-table th").forEach((th, idx) => {
            th.classList.remove("highlight-today");
            // idx 1/2: domingo entrada/salida, 3/4: lunes etc. 
            if (idx > 0 && ((idx-1) % 2 === 0)) {
                // busca día semana relativo
                const semanaIdx = Math.floor((idx-1)/2);
                if (semana[semanaIdx] && semana[semanaIdx].isToday) {
                    th.classList.add("highlight-today");
                    // Añadir también a la siguiente col (entrada/salida)
                    if (document.querySelector(`.dni-table th:nth-child(${idx+2})`))
                        document.querySelector(`.dni-table th:nth-child(${idx+2})`).classList.add("highlight-today");
                }
            }
        });

        // Render para cada persona
        asistencias.forEach(persona => {
            const fila = document.createElement("tr");

            const celdaNombre = document.createElement("td");
            celdaNombre.textContent = persona.nombre || "Sin Nombre";
            fila.appendChild(celdaNombre);

            // Mapear asistencias llegada a {fecha: {...}}
            const asistenciasPorFecha = {};
            (persona.asistencias || []).forEach(asist => {
                // El campo fecha viene como yyyy-mm-dd
                asistenciasPorFecha[asist.fecha] = asist;
            });

            semana.forEach((dayInfo, idx) => {
                const asistencia = asistenciasPorFecha[dayInfo.fecha];
                // Celda de entrada
                const celdaEntrada = document.createElement("td");
                celdaEntrada.textContent = asistencia ? asistencia.hora_entrada || "-" : "-";
                if(dayInfo.isToday) celdaEntrada.classList.add("highlight-today");
                fila.appendChild(celdaEntrada);
                // Celda de salida
                const celdaSalida = document.createElement("td");
                celdaSalida.textContent = asistencia ? asistencia.hora_salida || "-" : "-";
                if(dayInfo.isToday) celdaSalida.classList.add("highlight-today");
                fila.appendChild(celdaSalida);
            });

            dniTableBody.appendChild(fila);
        });

    } catch (error) {
        console.error("Error al cargar las asistencias:", error);
    }
}

//inicio de sexin
document.addEventListener('DOMContentLoaded', function () {
            var token = localStorage.getItem('authToken');
            if (!token) {
                // Crear overlay de mensaje centrado
                var msgDiv = document.createElement('div');
                msgDiv.textContent = "No está logeado o el token ha expirado. Por favor, inicie sesión.";
                msgDiv.style.position = "fixed";
                msgDiv.style.top = "0";
                msgDiv.style.left = "0";
                msgDiv.style.width = "100vw";
                msgDiv.style.height = "100vh";
                msgDiv.style.background = "rgba(255,255,255,0.96)";
                msgDiv.style.display = "flex";
                msgDiv.style.justifyContent = "center";
                msgDiv.style.alignItems = "center";
                msgDiv.style.fontSize = "2em";
                msgDiv.style.zIndex = "2000";
                document.body.appendChild(msgDiv);

                setTimeout(function () {
                    window.location.href = "../login.html";
                }, 2000);
            }
});

// --- Función para cerrar sesión ---
function cerrarSesion() {
            localStorage.removeItem('authToken');
            window.location.href = '../login.html';
        }
