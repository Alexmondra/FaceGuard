(function() {
  
    // Detectar si estamos en local o producción usando window.location.hostname
    const hostname = window.location.hostname;
    // Definir las URLs para cada ambiente
    const config = {
      local: "http://127.0.0.1:5000",
      production: "https://mi-servidor-produccion.com",
      
      // Placeholder for API versioning, if needed in the future
      // apiVersion: "v1",
      
      // Additional endpoints configuration can be added here
      // e.g., userProfile: "/api/user/profile",
    };
  
    // Elegir URL según hostname
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      window.API_BASE_URL = config.local;
    } else {
      window.API_BASE_URL = config.production;
    }
  })();
  