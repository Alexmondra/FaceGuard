// Variables globales
let uploadBox, fileInput, imagePreview, recognizeBtn, loadingOverlay, successStatus, errorStatus, resultsContainer;
let currentStream = null; // Para la cámara

// Función principal
function main() {
  inicializarElementos();
  inicializarEventos();
}

function inicializarElementos() {
  uploadBox = document.getElementById("dropArea");
  fileInput = document.getElementById("fileInput");
  recognizeBtn = document.getElementById("recognizeBtn");
  loadingOverlay = document.getElementById("loadingOverlay");
  successStatus = document.getElementById("successStatus");
  errorStatus = document.getElementById("errorStatus");
  resultsContainer = document.querySelector("#resultsPanel .results-container");

  // Elementos de cámara
  liveCamera = document.getElementById("liveCamera");
  cameraPlaceholder = document.getElementById("cameraPlaceholder");
  captureBtn = document.getElementById("captureBtn");
  startCameraBtn = document.getElementById("startCameraBtn");

  // Click para subir archivo
  uploadBox.addEventListener("click", () => fileInput.click());
  uploadBox.addEventListener("dragover", (e) => e.preventDefault());
  uploadBox.addEventListener("drop", manejarDrop);

  // Cambiar archivo
  fileInput.addEventListener("change", manejarCambioArchivo);

  // Reconocer imagen
  recognizeBtn.addEventListener("click", procesarImagen);

  // Tabs para opción "Subir" y "Cámara"
  const uploadTab = document.querySelector('.option-tab[data-option="upload"]');
  const cameraTab = document.querySelector('.option-tab[data-option="camera"]');

  uploadTab.addEventListener("click", () => {
    procesarImagen()
    mostrarOpcion("upload");
    resetStatus();
  });

  cameraTab.addEventListener("click", () => {
    mostrarOpcion("camera");
    resetStatus();
  });

  // Botones cámara
  startCameraBtn.addEventListener("click", startCamera);
  captureBtn.addEventListener("click", () => {
    capturePhoto();
    stopCurrentStream();
  });
}

function inicializarEventos() {
  // Repetidos por si algo queda pendiente (se pueden eliminar)
  uploadBox.addEventListener("click", () => fileInput.click());
  uploadBox.addEventListener("dragover", (e) => e.preventDefault());
  uploadBox.addEventListener("drop", manejarDrop);
  fileInput.addEventListener("change", manejarCambioArchivo);
  recognizeBtn.addEventListener("click", procesarImagen);
}

// Mostrar opción activa y ocultar otras
function mostrarOpcion(opcion) {
  const uploadOption = document.getElementById("upload-option");
  const cameraOption = document.getElementById("camera-option");
  const uploadTab = document.querySelector('.option-tab[data-option="upload"]');
  const cameraTab = document.querySelector('.option-tab[data-option="camera"]');

  if (opcion === "upload") {
    uploadOption.classList.add("active");
    cameraOption.classList.remove("active");
    uploadTab.classList.add("active");
    cameraTab.classList.remove("active");
    stopCurrentStream();
  } else if (opcion === "camera") {
    uploadOption.classList.remove("active");
    cameraOption.classList.add("active");
    uploadTab.classList.remove("active");
    cameraTab.classList.add("active");
  }

 
}

// Manejar drag & drop
function manejarDrop(event) {
  event.preventDefault();
  const file = event.dataTransfer.files[0];
  if (file) {
    fileInput.files = event.dataTransfer.files;
    mostrarPrevisualizacion(file);
  }
}

// Manejar cambio archivo
function manejarCambioArchivo(event) {
  const file = event.target.files[0];
  if (file) mostrarPrevisualizacion(file);
}

// Mostrar imagen subida o capturada en el recuadro
function mostrarPrevisualizacion(file) {
  const reader = new FileReader();
  reader.onload = (event) => {
    uploadBox.innerHTML = `
      <img src="${event.target.result}" alt="Imagen subida" class="image-preview" />
    `;
  };
  reader.readAsDataURL(file);
}

// Procesar imagen para reconocimiento facial
async function procesarImagen() {
  if (!fileInput.files.length) {
    alert("Por favor, sube una imagen primero.");
    return;
  }

  toggleLoading(true);
  resetStatus();

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const response = await fetch(`${API_BASE_URL}/persona/reconocer`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
      },
      body: formData,
    });

    toggleLoading(false);

    if (!response.ok) {
      displayError("Error en el servidor al reconocer la imagen.");
      return;
    }

    const data = await response.json();

    if (data.error) {
      displayError(data.error);
    } else {
      mostrarResultados(data.resultados, data.imagen);
      // Actualizar imagen procesada en el recuadro
      if (data.imagen) {
        uploadBox.innerHTML = `<img src="data:image/jpeg;base64,${data.imagen}" alt="Imagen reconocida" class="image-preview" />`;
      }
      toggleStatus(successStatus, true);
    }
  } catch (error) {
    console.error("Error general:", error);
    displayError("Ocurrió un error inesperado.");
  }
}

// Mostrar resultados
function mostrarResultados(resultados, imagenBase64) {
  resultsContainer.innerHTML = "";

  resultados.forEach(({ rostro, nombre, dni, confianza }) => {
    const resultDiv = document.createElement("div");
    resultDiv.className = "result-item";
    resultDiv.innerHTML = `
      <p><strong>Rostro:</strong> ${rostro}</p>
      <p><strong>Nombre:</strong> ${nombre}</p>
      <p><strong>DNI:</strong> ${dni}</p>
      <p><strong>Confianza:</strong> ${confianza}%</p>
    `;
    resultsContainer.appendChild(resultDiv);
  });
}

// Mostrar error
function displayError(message) {
  toggleStatus(errorStatus, true);
  errorStatus.querySelector("span").textContent = message;
}

// Mostrar/ocultar carga
function toggleLoading(show) {
  loadingOverlay.style.display = show ? "flex" : "none";
}

// Mostrar/ocultar status éxito/error
function toggleStatus(statusElement, show) {
  statusElement.style.display = show ? "block" : "none";
}

// Resetear estados
function resetStatus() {
  toggleStatus(successStatus, false);
  toggleStatus(errorStatus, false);
}

// Cámara: iniciar streaming (preferencia cámara trasera)

async function startCamera() {
  stopCurrentStream();
  try {
    const constraints = {
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    };
    currentStream = await navigator.mediaDevices.getUserMedia(constraints);
    liveCamera.srcObject = currentStream;
    liveCamera.style.display = "block";
    cameraPlaceholder.style.display = "none";
    captureBtn.style.display = "inline-block";
  } catch (error) {
    alert("Error al acceder a la cámara: " + error.message);
  }
}

// Cámara: detener streaming
function stopCurrentStream() {
  if (currentStream) {
    currentStream.getTracks().forEach((track) => track.stop());
    currentStream = null;
  }
  liveCamera.style.display = "none";
  captureBtn.style.display = "none";
  cameraPlaceholder.style.display = "block";
}

// Cámara: capturar foto, mostrar en recuadro y simular archivo para reconocimiento
function capturePhoto() {
  if (!currentStream) return alert("La cámara no está activa");

  const canvas = document.createElement("canvas");
  canvas.width = liveCamera.videoWidth;
  canvas.height = liveCamera.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(liveCamera, 0, 0, canvas.width, canvas.height);

  const dataURL = canvas.toDataURL("image/jpeg");

  // Mostrar foto capturada en recuadro
  uploadBox.innerHTML = `<img src="${dataURL}" alt="Foto capturada" class="image-preview" />`;

  // Convertir base64 a File para simular archivo en input file
  dataURLtoFile(dataURL, "captura.jpg").then((file) => {
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;
  });
}

// Convertir base64 a File
function dataURLtoFile(dataurl, filename) {
  return fetch(dataurl)
    .then((res) => res.arrayBuffer())
    .then((buf) => new File([buf], filename, { type: "image/jpeg" }));
}

document.addEventListener("DOMContentLoaded", main);
