# 📘 CodeAtlas Technical Error Logbook & Challenge Tracker

This logbook records all technical issues encountered during development and local execution, their underlying root causes, and the resolution applied.

---

## 📑 Issue Index

1. [ERR-001: Missing `email-validator` Dependency](#err-001-missing-email-validator-dependency)
2. [ERR-002: Frontend Auth Redirection Loop / Frozen Auth Page](#err-002-frontend-auth-redirection-loop--frozen-auth-page)
3. [ERR-003: `No GEMINI_API_KEY set` Environment Path Resolution Failure](#err-003-no-gemini_api_key-set-environment-path-resolution-failure)
4. [ERR-004: Duplicate Environment Keys in `.env`](#err-004-duplicate-environment-keys-in-env)
5. [ERR-005: Repeated HTTP 404 Ingestion Loop & Missing Exponential Backoff](#err-005-repeated-http-404-ingestion-loop--missing-exponential-backoff)
6. [ERR-006: Foreign Key Cascade Conflict on Repository Deletion (`ChatMessage` & `ChatSession`)](#err-006-foreign-key-cascade-conflict-on-repository-deletion-chatmessage--chatsession)
7. [ERR-007: TypeScript Type Error `str` Instead of `string` in `types/index.ts`](#err-007-typescript-type-error-str-instead-of-string-in-typesindexts)
8. [ERR-008: `window.confirm()` Suppressed by Browser / Not Rendering Correctly](#err-008-windowconfirm-suppressed-by-browser--not-rendering-correctly)
9. [ERR-009: TypeScript Implicit Type Definition Resolution Failure (`mdast` & `unist`)](#err-009-typescript-implicit-type-definition-resolution-failure-mdast--unist)
10. [ERR-010: TypeScript Global Type Acquisition Failure & PyreFly Virtual Buffer Warnings](#err-010-typescript-global-type-acquisition-failure--pyrefly-virtual-buffer-warnings)
11. [ERR-011: Frontend Nginx Docker Container Missing Reverse Proxy & SPA Fallback Routing](#err-011-frontend-nginx-docker-container-missing-reverse-proxy--spa-fallback-routing)

---

### ERR-001: Missing `email-validator` Dependency

- **Symptom**: FastAPI server crashed on startup with `ImportError: email-validator is not installed, run pip install 'pydantic[email]'`.
- **Root Cause**: Pydantic v2 requires the external package `email-validator` when using `EmailStr` field types in schemas (`UserCreate`, `UserLogin`).
- **Resolution**:
  - Added `email-validator>=2.1.0` and `pydantic[email]` to `backend/requirements.txt`.
  - Installed `email-validator` into the local `venv`.

---

### ERR-002: Frontend Auth Redirection Loop / Frozen Auth Page

- **Symptom**: After successful user registration or sign-in (`200 OK` on `/api/auth/register` and `/api/auth/login`), the UI remained stuck on the `/auth` page without navigating to the main dashboard.
- **Root Cause**: `AuthPage.tsx` saved the JWT token into state and `localStorage`, but lacked client-side router redirection (`navigate('/')`) upon form submission and lacked a `useEffect` hook to redirect authenticated users.
- **Resolution**:
  - Imported `useNavigate` in `frontend/src/pages/AuthPage.tsx`.
  - Implemented `useEffect` listener to redirect authenticated users (`user != null`) to `/`.
  - Explicitly called `navigate('/')` after `login(...)` resolves.

---

### ERR-003: `No GEMINI_API_KEY set` Environment Path Resolution Failure

- **Symptom**: Repository ingestion printed `No GEMINI_API_KEY set. Returning zero vector.` even though `.env` contained the API key.
- **Root Cause**:
  1. When starting Uvicorn from inside `backend/`, `pydantic-settings` searched for `.env` in `backend/.env` rather than traversing up to the workspace root `d:\workspace\codeatlas\.env`.
  2. `GeminiClient` cached `self.api_key` statically at instantiation rather than dynamically resolving it at request execution.
- **Resolution**:
  - Updated `backend/app/core/config.py` using `python-dotenv`'s `find_dotenv(usecwd=True)` and explicit parent directory fallback.
  - Modified `backend/app/core/gemini.py` to use a dynamic `@property api_key` getter that reads `settings.get_gemini_api_key()`.

---

### ERR-004: Duplicate Environment Keys in `.env`

- **Symptom**: `.env` file contained duplicated lines for `GEMINI_API_KEY`.
- **Root Cause**: Copying or appending values created redundant definitions.
- **Resolution**: Cleaned `.env` to ensure single, unambiguous key definitions.

---

### ERR-005: Repeated HTTP 404 Ingestion Loop & Missing Exponential Backoff

- **Symptom**: When an API endpoint or model returned `404 Not Found` (or 401/403 client error), the ingestion loop logged errors repeatedly for all 195 chunks without stopping.
- **Root Cause**: The service lacked error classification (client vs server errors), exponential backoff retries for transient 5xx/429 errors, and a fail-fast circuit breaker for non-retryable 4xx client errors.
- **Resolution**:
  - Implemented custom exceptions: `GeminiFatalError` (for 4xx non-retryable errors) and `GeminiRetryableError` (for 5xx/429 errors).
  - Added exponential backoff retry helper (`max_retries = 3` with delays `1s`, `2s`, `4s`).
  - Added embedding model fallback (`text-embedding-004` to `embedding-001`).
  - Implemented immediate fail-fast termination in `EmbeddingService.process_repository()` to halt background ingestion and set `repo.status = "error"` on the first fatal client error.

---

### ERR-006: Foreign Key Cascade Conflict on Repository Deletion (`ChatMessage` & `ChatSession`)

- **Symptom**: Deleting a repository threw a 500 database error (`FOREIGN KEY constraint failed: chat_messages.session_id`).
- **Root Cause**: `ChatMessage` has a strict foreign key referencing `ChatSession.id`. Attempting to delete `ChatSession` records before deleting their child `ChatMessage` records caused SQLite/Postgres FK enforcement to fail and abort the transaction.
- **Resolution**:
  - Updated `DELETE /api/repositories/{repo_id}` in `backend/app/api/repos.py` to query all `session_ids` belonging to the repository.
  - Explicitly deleted `ChatMessage` records first, then `ChatSession`, `CodeChunk`, `FileModel`, `GeneratedDoc`, and finally the parent `Repository`.

---

### ERR-007: TypeScript Type Error `str` Instead of `string` in `types/index.ts`

- **Symptom**: Vite/TypeScript compilation would fail (or produce subtle runtime type mismatches) on the `ChunkResult` interface used across `DashboardPage.tsx` and search result rendering.
- **Root Cause**: `ChunkResult.file_path` was declared as `file_path: str` — a Python type annotation inadvertently copied into TypeScript. `str` is not a valid TypeScript primitive type (correct value is `string`). This would cause a TypeScript compilation error in strict mode.
- **File**: `frontend/src/types/index.ts` line 35.
- **Resolution**: Changed `file_path: str` → `file_path: string` on the `ChunkResult` interface.

---

### ERR-008: `window.confirm()` Suppressed by Browser / Not Rendering Correctly

- **Symptom**: Clicking "Delete Repo" had no visible effect — no confirmation dialog appeared before deletion.
- **Root Cause**: `window.confirm()` is a blocking native browser dialog that can be suppressed by:
  1. Browser settings that block JavaScript dialogs on certain origins (common in Chromium-based browsers).
  2. Frameworks like React rendering inside iframes or strict CSP policies that block native dialogs.
  3. The dialog appearing and being dismissed instantly due to event propagation.
- **Resolution**:
  - Created a fully custom `ConfirmModal.tsx` React component with a backdrop, animated panel, warning icon, and styled action buttons.
  - Replaced all `window.confirm()` calls in `DashboardPage.tsx` and `Navbar.tsx` with the new controlled state-driven modal.
  - Added `animate-fade-in` and `animate-slide-up` Tailwind keyframe animations for a polished modal entrance.

---

### ERR-009: TypeScript Implicit Type Definition Resolution Failure (`mdast` & `unist`)

- **Symptom**: IDE reported compiler errors on `tsconfig.json`: `Cannot find type definition file for 'mdast'` and `Cannot find type definition file for 'unist'`.
- **Root Cause**: `react-markdown` relies on AST types (`mdast` and `unist`) from the `unified` parser ecosystem. When TypeScript compiles without explicit `@types` packages listed in `devDependencies`, TypeScript's automatic type acquisition scans `@types` folders and flags missing implicit type package declarations.
- **Resolution**:
  - Installed `@types/mdast` and `@types/unist` as explicit `devDependencies` in `frontend/package.json`.
  - Verified clean compilation with `npm run build` (`tsc && vite build`).

---

### ERR-010: TypeScript Global Type Acquisition Failure & PyreFly Virtual Buffer Warnings

- **Symptom**:
  1. `frontend/tsconfig.json` displayed IDE errors: `Cannot find type definition file for 'mdast'` and `Cannot find type definition file for 'unist'`.
  2. IDE reported parse and symbol lookup errors for transient in-memory buffers under `d:\__pyrefly_virtual__\inmemory\*.py`.
- **Root Cause**:
  1. When `@types` packages for AST node definitions (`mdast`, `unist`) are installed, TypeScript's default type acquisition mechanism scans `@types` and attempts to import them as implicit ambient global type libraries. Because these packages export module types (`export type Root = ...`) rather than global definitions, TypeScript flags an entry point acquisition error on `tsconfig.json`.
  2. PyreFly language server registers transient virtual buffers (`d:\__pyrefly_virtual__\inmemory\`) when evaluating interactive code cells or partial execution snippets. These isolated snippets lack enclosing async contexts, imports, or full class signatures, resulting in transient syntax/linter warnings in virtual buffers.
- **Resolution**:
  - Configured explicit `"types": ["vite/client"]` inside `frontend/tsconfig.json` under `compilerOptions` to restrict automatic global type library acquisition to Vite declarations and suppress implicit AST type errors.
  - Executed `npm run build` in `frontend/` (`tsc && vite build`) to confirm full type-checking and bundling success with 0 errors.
  - Executed `python -m compileall app` in `backend/` to verify that all repository python source files compile without syntax or import errors.

---

### ERR-011: Frontend Nginx Docker Container Missing Reverse Proxy & SPA Fallback Routing

- **Symptom**: In Docker environment, requests from the frontend to `/api/auth/register` (and other API endpoints) returned HTTP 404: `open() "/usr/share/nginx/html/api/auth/register" failed (2: No such file or directory)`. Direct page refreshes on client routes also failed with Nginx 404.
- **Root Cause**: The production Nginx container (`codeatlas-frontend`) served static dist files using the default Nginx configuration. It lacked a `location /api/` proxy directive pointing to the backend container (`http://backend:8000/api/`) and lacked SPA fallback routing (`try_files $uri $uri/ /index.html;`).
- **Resolution**:
  - Created `frontend/nginx.conf` with SPA client-side fallback (`try_files $uri $uri/ /index.html;`) and reverse proxy configuration for `/api/` targeting `http://backend:8000/api/`.
  - Updated `frontend/Dockerfile` to copy `nginx.conf` to `/etc/nginx/conf.d/default.conf`.
  - Rebuilt containers with `docker compose up -d --build`.

---

## 🎯 Best Practices Established

- **Explicit Bottom-Up Relational Deletion**: Always delete bottom-level child records (e.g. `ChatMessage`) before parent records (e.g. `ChatSession`) to satisfy database foreign key integrity constraints.
- **Fail-Fast Circuit Breaking**: Stop background batch jobs immediately on non-retryable 4xx client errors instead of executing repetitive failing calls.
- **Exponential Backoff**: Use progressive delays (1s, 2s, 4s) for transient server errors (5xx) or rate limits (429).
- **Dynamic Environment Resolution**: Always use recursive path discovery (`find_dotenv`) for monorepos or nested structures.
- **Strict TypeScript Typing**: Never copy Python type annotations (`str`, `int`, `bool`) into TypeScript files — always use `string`, `number`, `boolean`.
