# Frontend - File Share UI

Vue 3 + Vite single-page application for the File Share microservices project.

## Features

- **Simple Authentication**: Name-based login (automatically creates user if doesn't exist)
- **File Upload**: Upload files with visual feedback
- **File Download**: Download files via dropdown selection
- **File Management**: View all your files with size display and delete functionality
- **Responsive Design**: Modern, clean UI with gradient backgrounds and smooth animations

## Tech Stack

- **Vue 3**: Composition API with `<script setup>`
- **Vite**: Fast development server and optimized builds
- **nginx**: Production web server (in Docker)

## Development

```bash
# Install dependencies
npm install

# Run dev server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Docker

The frontend uses a multi-stage Docker build:

1. **Build stage**: Node.js 20 to build the Vue app with Vite
2. **Production stage**: nginx:alpine to serve the static files

```bash
# Build and run with Docker Compose (from project root)
docker compose up --build frontend

# Access at http://localhost
```

## API Integration

The frontend communicates with the fileshare service through nginx proxy configuration:
- Development: Vite proxy in `vite.config.js`
- Production: nginx proxy in `nginx.conf`

All API requests to `/fileshare/*` are proxied to the backend fileshare service.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── LoginView.vue       # Login/registration screen
│   │   └── FileManager.vue     # Main file management interface
│   ├── App.vue                 # Root component (routing between login/manager)
│   ├── main.js                 # App entry point
│   └── style.css               # Global styles
├── index.html                  # HTML entry point
├── vite.config.js             # Vite configuration
├── nginx.conf                 # nginx configuration for Docker
├── Dockerfile                 # Multi-stage build
└── package.json               # Dependencies
```

## Notes

- No actual authentication/authorization - uses name for user identification
- Files are scoped per user (person)
- The UI automatically refreshes file lists after upload/download/delete operations
- Error messages are displayed inline for better UX
