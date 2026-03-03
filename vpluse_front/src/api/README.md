# Подключение к backend

1. Скопируй `.env.example` в `.env`:
   ```
   cp .env.example .env
   ```

2. В файле `src/context/AuthContext.jsx` смени флаг:
   ```js
   const USE_MOCK = false; // было true
   ```

3. Убедись, что backend запущен на `http://localhost:8000`

4. Перезапусти frontend: `npm run dev`
