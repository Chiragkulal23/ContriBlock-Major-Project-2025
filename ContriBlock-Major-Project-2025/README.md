# MyContri Platform

## Overview
MyContri is a full-stack platform for managing open contributions, on-chain document attestation, and contributor rewards. The system pairs a Flask REST backend with a Vite/React frontend to let organizations collect submissions, approve them through an admin console, and pin supporting evidence to IPFS. Identity verification is handled with an email-based KYC flow so only vetted users can publish or redeem rewards.

## Feature Highlights
- **Email-based KYC** – Users verify their inbox with a one-time passcode sent through EmailJS before uploading identity documents. Admins review pending requests and approve or reject them from the dashboard.
- **Contribution Lifecycle** – Contributors submit work, admins review submissions, and approved entries record their IPFS hash on-chain while updating token balances in the database.
- **IPFS Metadata** – Pinata uploads now persist the CID, file size, and pin timestamp so frontend cards can display richer context.
- **Marketplace & Rewards** – Verified users can browse the marketplace, view token balances, and (optionally) claim rewards. Token transfers are currently tracked in SQL only; on-chain transfers can be added later.
- **Blockchain Automation** – Approval transactions are signed server-side with a deployer key, so admins never see MetaMask popups during reviews.

## Repository Structure
```text
backend/        Flask API, smart-contract integration, SQLAlchemy models
glow-contrib/   React + Vite frontend with Tailwind and shadcn/ui
contracts/      Compiled contract artifact (referenced by backend/config.py)
uploads/        Local storage for user-submitted documents (git-ignored in production)
```

## Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- SQLite (bundled) or a Postgres instance if you set `DATABASE_URL`
- Local blockchain RPC (e.g., Ganache) for development signing
- Pinata API keys for IPFS storage
- EmailJS account for OTP email delivery

## Backend Setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate    # On Windows
pip install -r requirements.txt
python app.py             # Runs Flask app with built-in migrations
```

To apply schema changes explicitly:
```bash
flask db upgrade
```
The app automatically adds missing IPFS metadata columns on startup if you use SQLite.

## Frontend Setup
```bash
cd glow-contrib
npm install
npm run dev       # serves on http://localhost:5173 by default
```

For a production build:
```bash
npm run build
npm run preview   # optional smoke test
```

## Environment Configuration

### Backend (`backend/.env` or system variables)
- `FLASK_SECRET_KEY` – Session signing key.
- `DATABASE_URL` – Defaults to `sqlite:///dev.db`.
- `JWT_SECRET` – Token signing secret.
- `FRONTEND_ORIGIN` – Origin allowed for CORS (`http://localhost:5173` in dev).
- `UPLOAD_FOLDER` – Absolute path for stored documents.
- `GANACHE_URL` – JSON-RPC endpoint for transactions.
- `DEPLOYER_PRIVATE_KEY` – Private key used to sign blockchain transactions.
- `CONTRACT_ADDRESS` / `CONTRACT_ABI_PATH` – Smart contract configuration.
- `PINATA_API_KEY` / `PINATA_SECRET_API_KEY` – Pinata credentials for uploads.

### Frontend (`glow-contrib/.env.local`)
- `VITE_API_URL` – Points to the Flask API (default `http://localhost:5001/api`).
- `VITE_EMAILJS_SERVICE_ID`, `VITE_EMAILJS_TEMPLATE_ID`, `VITE_EMAILJS_PUBLIC_KEY` – EmailJS OTP delivery.
- `VITE_FIREBASE_*` – Optional Firebase project settings (warning logs guide setup).
- `VITE_CHAIN_ID`, `VITE_RPC_URL`, `VITE_CHAIN_NAME` – Wallet connection defaults for local blockchain.

Restart both dev servers after updating environment files so changes are picked up.

## Core Workflows

### KYC Verification
1. User opens `Profile` → starts KYC verification.
2. EmailJS sends a six-digit OTP; the UI exposes the code in dev mode if EmailJS is unconfigured.
3. After handshake, users upload ID files that are stored under `backend/uploads/`.
4. Admins review requests within the dashboard and approve/reject, unlocking restricted features for verified profiles.

### Contribution Review & Blockchain Recording
1. Admin decides on a submission in the dashboard (`glow-contrib/src/pages/Admin.tsx`).
2. Frontend calls `POST /contributions/<id>/review` with the desired action.
3. The backend (`backend/api/contributions.py`) stores the Pinata metadata, signs the `saveHash` transaction using the deployer key, and sends it via Web3.
4. Contributor reward balances update in SQL. On-chain token transfers are a future enhancement.

### IPFS Metadata Capture
`backend/services/storage.py` uploads files to Pinata and returns CID, size, timestamp, and filename. Models expose this data via `to_card()` and `to_detail()` so the frontend can display richer attachment info.

## Testing & Tooling
- Backend unit tests live in `backend/tests/`. Run them with:
  ```bash
  cd backend
  pytest
  ```
- `test_pinata_upload.py` is a utility script for validating Pinata credentials.
- Frontend components rely on TypeScript and ESLint via the Vite dev server.

## Troubleshooting
- **EmailJS** – Confirm service ID, template ID, and public key match EmailJS, and add `localhost`/`127.0.0.1` to authorized domains. In dev mode, the app logs configuration status and exposes the OTP toasts for manual testing.
- **Gmail 412 scopes** – Reconnect the Gmail provider in EmailJS or issue an App Password if you use 2FA. A custom SMTP service can be configured if Gmail remains blocked.
- **Blockchain signing** – Ensure `DEPLOYER_PRIVATE_KEY`, `CONTRACT_ADDRESS`, and `GANACHE_URL` are set. The backend signs automatically; MetaMask is not required for admins.
- **Pinata uploads** – Verify API keys and confirm the backend process has network access. Successful responses now include file size and pin timestamp; missing fields indicate credential issues.

## Deployment Notes
- Build the frontend (`npm run build`) and serve the `dist/` folder via your hosting provider.
- Containerize the backend (Dockerfile provided) or deploy to platforms like Railway/Render/Heroku. Set environment variables for secrets and RPC endpoints.
- Remember to secure `DEPLOYER_PRIVATE_KEY` and EmailJS credentials through your hosting provider’s secrets manager.

---

With this README, all prior documentation has been consolidated into a single reference. Remove any remaining Markdown guides before pushing to GitHub to keep the repository focused on code and this end-to-end overview.


