document.addEventListener("DOMContentLoaded", () => {
  const apiUrl = API_BASE_URL; // Asegúrate de definir esta variable en config.js
  const container = document.getElementById("container");

  // Inicialización
  initForms();
  initPasswordValidation();

  /**
   * Inicializa la funcionalidad de los formularios de Login y Registro.
   */
  function initForms() {
    initToggleForms();
    initLoginForm();
    initRegisterForm();
  }

  /**
   * Configura el cambio entre formularios de Login y Registro.
   */
  function initToggleForms() {
    const showRegister = document.getElementById("showRegister");
    const showLogin = document.getElementById("showLogin");

    showRegister.addEventListener("click", () => container.classList.add("register-active"));
    showLogin.addEventListener("click", () => container.classList.remove("register-active"));
  }

  /**
   * Configura la funcionalidad del formulario de Login.
   */
  function initLoginForm() {
    const loginForm = document.getElementById("loginForm");

    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const loginData = getLoginFormData();

      if (!validateLoginData(loginData)) return;

      try {
        const response = await postData(`${apiUrl}/auth`, loginData);
        const data = await response.json();

        if (response.ok) {
          localStorage.setItem('accessToken', data.access_token);
          setTimeout(() => (window.location.href = "./menu.html"), 1500);
        } else {
          showFieldError("loginUser", data.mensaje || "Error en el inicio de sesión.");
        }
      } catch (error) {
        console.error(error);
        showMessage("Error de conexión con el servidor.", true);
      }
    });
  }

  /**
   * Configura la funcionalidad del formulario de Registro.
   */
  function initRegisterForm() {
    const registerForm = document.getElementById("registerForm");

    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const regData = getRegisterFormData();

      clearFieldFeedback("register");

      if (!validateRegisterData(regData)) return;

      try {
        const response = await postData(`${apiUrl}/api_guardarUsuario`, regData);
        const data = await response.json();

        if (response.ok) {
          showMessage("Registro completado con éxito.");
          resetRegisterForm();
          container.classList.remove("register-active");
        } else {
          if (data.campo === "email") {
            showFieldError("regEmail", "El correo ya está registrado.");
          } else{
            showMessage(data.mensaje || "Error en el registro.", true);
          }
        }
      } catch (error) {
        console.error(error);
        showMessage("Ocurrió un problema inesperado. Intenta nuevamente.", true);
      }
    });
  }

  /**
   * Valida contraseñas en tiempo real en el formulario de Registro.
   */
  function initPasswordValidation() {
    const regPassword = document.getElementById("regPassword");
    const regPassword2 = document.getElementById("regPassword2");
    const passwordFeedback = document.getElementById("regPassword2Feedback");

    regPassword2.addEventListener("input", () => {
      if (regPassword.value !== regPassword2.value) {
        regPassword2.classList.add("error");
        passwordFeedback.textContent = "Las contraseñas no coinciden.";
      } else {
        regPassword2.classList.remove("error");
        passwordFeedback.textContent = "";
      }
    });
  }

  // --- Funciones auxiliares ---

  /**
   * Obtiene los datos del formulario de Login.
   * @returns {Object} Datos del formulario.
   */
  function getLoginFormData() {
    return {
      email: document.getElementById("loginUser").value.trim(),
      password: document.getElementById("loginPassword").value.trim(),
    };
  }

  /**
   * Obtiene los datos del formulario de Registro.
   * @returns {Object} Datos del formulario.
   */
  function getRegisterFormData() {
    return {
      username: document.getElementById("regUsername").value.trim(),
      email: document.getElementById("regEmail").value.trim(),
      password: document.getElementById("regPassword").value.trim(),
    };
  }

  /**
   * Valida los datos del formulario de Login.
   * @param {Object} data - Datos del formulario.
   * @returns {boolean} True si los datos son válidos, False en caso contrario.
   */
  function validateLoginData({ email, password }) {
    if (!email || !password) {
      showMessage("Por favor completa todos los campos.", true);
      return false;
    }
    if (!validateEmail(email)) {
      showMessage("El email no tiene un formato válido.", true);
      return false;
    }
    return true;
  }

  /**
   * Valida los datos del formulario de Registro.
   * @param {Object} data - Datos del formulario.
   * @returns {boolean} True si los datos son válidos, False en caso contrario.
   */
  function validateRegisterData({ username, email, password }) {
    let isValid = true;

    if (!username) {
      showFieldError("regUsername", "El nombre de usuario es obligatorio.");
      isValid = false;
    }

    if (!email) {
      showFieldError("regEmail", "El correo es obligatorio.");
      isValid = false;
    } else if (!validateEmail(email)) {
      showFieldError("regEmail", "El correo no tiene un formato válido.");
      isValid = false;
    }

    const regPassword2 = document.getElementById("regPassword2");
    if (password !== regPassword2.value) {
      showFieldError("regPassword2", "Las contraseñas no coinciden.");
      isValid = false;
    }

    return isValid;
  }

  /**
   * Valida el formato del email.
   * @param {string} email - Email a validar.
   * @returns {boolean} True si el formato es válido, False en caso contrario.
   */
  function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }

  /**
   * Realiza una petición POST.
   * @param {string} url - URL de la API.
   * @param {Object} data - Datos a enviar.
   * @returns {Promise<Response>} Respuesta de la API.
   */
  async function postData(url = "", data = {}) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
  }

  /**
   * Muestra un mensaje de feedback.
   * @param {string} msg - Mensaje a mostrar.
   * @param {boolean} isError - Indica si es un mensaje de error.
   */
  function showMessage(msg, isError = false) {
    alert(msg);
    console[isError ? "error" : "log"](msg);
  }

  /**
   * Limpia los mensajes de error en los formularios.
   */
  function clearFieldFeedback() {
    document.querySelectorAll(".error-message").forEach((feedback) => {
      feedback.textContent = "";
    });
    document.querySelectorAll("input").forEach((input) => {
      input.classList.remove("error");
    });
  }

  /**
   * Muestra un error debajo de un campo específico.
   * @param {string} fieldId - ID del campo.
   * @param {string} message - Mensaje de error.
   */
  function showFieldError(fieldId, message) {
    const input = document.getElementById(fieldId);
    const feedback = document.getElementById(`${fieldId}Feedback`);
    if (input) input.classList.add("error");
    if (feedback) feedback.textContent = message;
  }

  /**
   * Resetea el formulario de Registro.
   */
  function resetRegisterForm() {
    document.getElementById("registerForm").reset();
    clearFieldFeedback();
  }
});
