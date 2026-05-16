# Factoria Frontend

This is the browser-based operational dashboard for Factoria.

## Tech Stack
- React
- Vite
- TypeScript
- Tailwind CSS

## Prerequisites
Ensure the Factoria backend is running locally.

## Running the Frontend

1. Install dependencies:
`npm install`

2. Start the dev server:
`npm run dev &`

The frontend will run at `http://localhost:5173` by default.

## Configuration

The frontend expects the backend API to be available at `http://localhost:8000`.
You can override this by setting `VITE_API_BASE_URL` in a `.env` file in the `frontend` directory.

```env
VITE_API_BASE_URL=http://localhost:8000
```
