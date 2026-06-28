# Contributing to GIIPS

We welcome contributions to improve the intelligence and efficiency of the GIIPS system.

## 🛠 Development Workflow
1. **Fork the Repository**: Create your own copy of the project.
2. **Create a Feature Branch**: `git checkout -b feature/your-feature-name`.
3. **Implement Changes**: Follow the existing coding standards (TypeScript for frontend, PEP8 for backend).
4. **Test Your Changes**: Ensure the backend starts with `python app.py` and the frontend runs via `npm run dev`.
5. **Submit a Pull Request**: Provide a clear description of the changes and the problem they solve.

## 📜 Guidelines

### Backend (Python/FastAPI)
- Use Pydantic models for all request/response validation.
- Keep business logic in `services.py` and route definitions in `routes.py`.
- Maintain absolute imports for compatibility with `python app.py` execution.

### Frontend (React/TypeScript)
- Use functional components and hooks.
- Maintain strict typing for all API responses in `src/types/index.ts`.
- Adhere to the existing CSS module patterns for styling.

### General
- Ensure all new API endpoints are documented in `API_DOCUMENTATION.md`.
- Update `ARCHITECTURE.md` if the system flow is modified.
