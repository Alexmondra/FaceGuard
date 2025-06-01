-- Tabla personas
DROP TABLE IF EXISTS `personas`;
CREATE TABLE IF NOT EXISTS `personas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dni` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombres` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `apellidos` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_nacimiento` date DEFAULT NULL,
  `genero` varchar(1) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha_registro` datetime NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `chk_genero` CHECK (`genero` in ('M','F'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_520_ci;

-- Tabla camaras
DROP TABLE IF EXISTS `camaras`;
CREATE TABLE IF NOT EXISTS `camaras` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) DEFAULT NULL,
  `local` varchar(100) NOT NULL,
  `ubicacion` varchar(255) DEFAULT NULL,
  `tipo_camara` enum('USB','IP','WEB','Otro') NOT NULL,
  `fuente` varchar(255) NOT NULL,
  `estado` enum('Activo','Inactivo','Desactivado') DEFAULT 'Inactivo',
  `fecha_registro` timestamp NULL DEFAULT current_timestamp(),
  `fecha_modificacion` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla usuarios
DROP TABLE IF EXISTS `usuarios`;
CREATE TABLE IF NOT EXISTS `usuarios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `rol` enum('admin','usuario','moderador') DEFAULT 'usuario',
  `estado` enum('activo','inactivo') DEFAULT 'activo',
  `fecha_registro` datetime DEFAULT current_timestamp(),
  `ultimo_inicio_sesion` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla embeddings_personas
DROP TABLE IF EXISTS `embeddings_personas`;
CREATE TABLE IF NOT EXISTS `embeddings_personas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `persona_id` int(11) NOT NULL,
  `embedding` blob NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `imagen_ruta` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `persona_id` (`persona_id`) USING BTREE,
  CONSTRAINT `fk_persona_id` FOREIGN KEY (`persona_id`) REFERENCES `personas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla detectados
DROP TABLE IF EXISTS `detectados`;
CREATE TABLE IF NOT EXISTS `detectados` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `persona_id` int(11) NOT NULL,
  `camara_id` int(11) NOT NULL,
  `fecha_hora` datetime DEFAULT current_timestamp(),
  `foto_captura` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `persona_id` (`persona_id`),
  KEY `camara_id` (`camara_id`),
  CONSTRAINT `detectados_ibfk_1` FOREIGN KEY (`persona_id`) REFERENCES `personas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `detectados_ibfk_2` FOREIGN KEY (`camara_id`) REFERENCES `camaras` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla usuario_camara
DROP TABLE IF EXISTS `usuario_camara`;
CREATE TABLE IF NOT EXISTS `usuario_camara` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `usuario_id` int(11) NOT NULL,
  `camara_id` int(11) NOT NULL,
  `fecha_asignacion` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `usuario_id` (`usuario_id`),
  KEY `camara_id` (`camara_id`),
  CONSTRAINT `usuario_camara_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuarios` (`id`) ON DELETE CASCADE,
  CONSTRAINT `usuario_camara_ibfk_2` FOREIGN KEY (`camara_id`) REFERENCES `camaras` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insertar registros iniciales en usuarios si no existen
INSERT INTO `usuarios` (`id`, `username`, `email`, `password_hash`, `rol`, `estado`, `fecha_registro`, `ultimo_inicio_sesion`)
SELECT * FROM (
  SELECT 1 AS id, 'admin' AS username, 'alexmondragon666@outlook.com' AS email, 
         '$2b$12$zNgRRP0VaWb52RFrjMwBkeZZvmqkfWTIxrtA6njL5sO4pIUQAFdoO' AS password_hash,
         'admin' AS rol, 'activo' AS estado, '2025-05-23 23:53:41' AS fecha_registro, NULL AS ultimo_inicio_sesion
  UNION ALL
  SELECT 2, 'alex', 'mfernandezalex@uss.edu.pe', 
         '$2b$12$UYSoPJ/.DrpGaGOhI6ZHIuGDN5fTpftRqS0kWe.msZW2ldnHkvHyi', 
         'usuario', 'activo', '2025-05-24 17:30:22', NULL
) AS tmp
WHERE NOT EXISTS (SELECT 1 FROM `usuarios` WHERE `id` IN (1, 2));
