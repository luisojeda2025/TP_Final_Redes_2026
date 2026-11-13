# TP Integrador Final - Programación sobre Redes

* **Institución:** IFTS N° 4
* **Carrera:** Tecnicatura Superior en Desarrollo de Software (3er Año)
* **Materia:** Programación sobre Redes
* **Profesor:** Javier Blanco
* **Alumno:** Luis Segundo Ojeda
* **Año Lectivo:** 2026

---

## 📌 Descripción del Proyecto

Aplicación de red **Cliente - Servidor Concurrente** desarrollada en Python utilizando sockets TCP/IP (`socket`), gestión de hilos independientes (`threading`), persistencia en base de datos relacional MySQL (`mysql.connector`) y una interfaz gráfica de usuario desarrollada de forma nativa en `tkinter`.

El sistema permite la autenticación de múltiples clientes en simultáneo contra una base de datos MySQL, el intercambio bidireccional de mensajes de texto en tiempo real y la ejecución de comandos especiales precedidos por `/`.

---

## ⚙️ Requisitos Previos

1. **Python 3.10** o superior instalado.
2. **XAMPP** con el servicio **MySQL** iniciado en el puerto estándar `3306` (usuario `root`, contraseña vacía).
3. Instalar las dependencias del proyecto ejecutando en terminal:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Puesta en Marcha

### 1. Iniciar el Servidor (Consola de Administración)
Abrir una terminal en la carpeta del proyecto y ejecutar:
```bash
python servidor.py
```
> *Nota: Al iniciar, el servidor verifica automáticamente la existencia de la base de datos `db_github_api` y sus tablas en MySQL. Si aún no existen, las inicializa de manera automática.*

### 2. Iniciar el/los Cliente(s)
Abrir una o más terminales adicionales y ejecutar:
```bash
python cliente.py
```
1. En el panel superior ingresar los datos de conexión:
   * **IP Servidor:** `127.0.0.1` (o la IP LAN de la máquina del servidor).
   * **Puerto:** `5000`.
   * **Usuario:** `alumno` (o cualquiera de los usuarios de prueba).
   * **Contraseña:** `1234`.
2. Presionar **Conectar / Iniciar Sesión**. Una vez autenticado, se habilitará el visor de mensajes y el campo de envío.

---

## 💬 Comandos Disponibles en el Chat

Cualquier mensaje que comience con `/` es interpretado por el servidor como un comando:

| Comando | Descripción |
| :--- | :--- |
| `/hora` | Devuelve la hora oficial del servidor en formato `HH:MM:SS`. |
| `/usuarios` | Lista todos los usuarios con sesión activa conectados al servidor. |
| `/followers <usuario>` | Consulta los seguidores del usuario en la API de GitHub y los persiste en la tabla `followers` de MySQL. |
| `/repos <usuario>` | Consulta los repositorios del usuario en GitHub y los persiste en la tabla `repositorios` de MySQL. |
| `/todos <mensaje>` | Emite un mensaje de difusión (*broadcast*) a todos los clientes conectados. |
| `/adios` | Finaliza la sesión del cliente y cierra la conexión de forma ordenada. |

*Cualquier texto que no comience con `/` se transmite como mensaje de chat ordinario.*

---

## 👥 Cuentas de Acceso Precargadas

Para pruebas de concurrencia en la tabla `usuarios`:
* `alumno` / `1234`
* `javier` / `1234`
* `cliente1` / `1234`
* `cliente2` / `1234`
* `operador` / `admin`

---

## 📄 Documentación Incluida

* **`manual_usuario.txt`**: Guía detallada de operación y resolución de problemas.
* **`manual_tecnico.txt`**: Especificación técnica de arquitectura, modelo TCP/IP y threading.
* **`credenciales.txt`**: Registro de credenciales y casos de prueba para demostración.
* **`basedatos.sql`**: Script DDL/DML de la base de datos MySQL.
