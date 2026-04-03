# MyContri Demo - Quick Reference Guide
## Individual Member Responsibilities

---

## 👤 **MEMBER 1: ADMIN (Reviewer)**

### Your Role:
You are the **platform administrator** responsible for reviewing and approving user submissions.

### Your Tasks:

#### **1. Login as Admin**
- URL: `http://localhost:5173/login`
- Email: `admin@example.com`
- Password: `admin123`

#### **2. Review KYC Requests**
- Navigate to `/admin`
- Click "KYC Verification" card
- View pending KYC requests
- Click "View Details" → Download document
- Click **"Approve"** or **"Reject"**
- **Key Point:** "I'm verifying user identity documents to ensure platform security"

#### **3. Review Contributions**
- In Admin Dashboard, click "Contributions Review"
- View pending contributions list
- Click "View Details" on any contribution
- Review:
  - Title and description
  - Author information
  - Attached file (download to verify)
- Click **"Approve Contribution"**
- **Show:** IPFS CID appears, Pinata link opens
- **Key Point:** "Upon approval, the file is uploaded to IPFS and the hash is recorded on blockchain. The contributor automatically receives 100 CTRI tokens."

#### **4. What to Say:**
- "As an admin, I review all submissions to ensure quality"
- "When I approve, the system automatically uploads to IPFS and records on blockchain"
- "The contributor receives tokens automatically - no manual transfer needed"

---

## 👤 **MEMBER 2: CONTRIBUTOR 1 (John)**

### Your Role:
You are a **contributor** who submits work and earns rewards.

### Your Tasks:

#### **1. Register & Login**
- URL: `http://localhost:5173/signup`
- Name: `John Contributor`
- Email: `john@example.com`
- Password: `password123`
- Login after registration

#### **2. Complete KYC Verification**
- Navigate to `/profile`
- Click "Start Verification"
- **Step 1:** Enter email → Send OTP → Enter OTP (check toast if EmailJS not configured)
- **Step 2:** Upload a test document (PDF/Image)
- Click "Submit KYC"
- **Key Point:** "I need to verify my identity before I can submit contributions"

#### **3. Submit Contribution**
- Navigate to `/submit`
- Fill form:
  - Title: "Decentralized Voting System"
  - Description: "A blockchain-based voting system for transparent elections"
  - Upload a test PDF file
- Click "Submit Contribution"
- **Key Point:** "I'm submitting my work for review. Once approved, I'll receive tokens."

#### **4. Check Status & Rewards**
- Navigate to `/dashboard`
- Show your contribution with "Pending" status
- After admin approves, refresh to show "Accepted"
- Navigate to `/profile`
- Show token balance: "100 CTRI"
- Click "My Contributions" → View contribution details
- **Key Point:** "I can track all my submissions and see my rewards in real-time"

#### **5. What to Say:**
- "I submit my work through a simple form"
- "The system tracks my contributions and rewards me automatically"
- "I can see my IPFS hash proving my work is on the blockchain"

---

## 👤 **MEMBER 3: BUYER/CONTRIBUTOR 2 (Alice)**

### Your Role:
You are a **buyer** who purchases contributions from the marketplace.

### Your Tasks:

#### **1. Register & Login**
- URL: `http://localhost:5173/signup`
- Name: `Alice Buyer`
- Email: `alice@example.com`
- Password: `password123`
- Login after registration

#### **2. Browse Marketplace**
- Navigate to `/marketplace`
- Show available contributions
- Browse through contribution cards
- **Key Point:** "I can browse all approved contributions available for purchase"

#### **3. Purchase Contribution**
- Click on a contribution card
- View full details (title, description, price)
- Click "Purchase" button
- Confirm purchase
- **Key Point:** "I purchase contributions using CTRI tokens. The file becomes accessible to me."

#### **4. Access Purchased Content**
- Navigate to `/profile`
- Click "Purchased Contributions" card
- View your purchased contributions
- Click on a contribution to view details
- Click "Download" to access the file
- **Key Point:** "All my purchased content is stored in my profile for easy access"

#### **5. Optional: Submit Your Own Contribution**
- Navigate to `/submit`
- Submit a contribution (follow Member 2's steps)
- Show you can also be a contributor

#### **6. What to Say:**
- "The marketplace lets me discover and purchase valuable contributions"
- "Once purchased, I have permanent access to the content"
- "The platform supports both contributing and purchasing"

---

## 🎯 **SHARED RESPONSIBILITIES**

### **All Members Should:**
1. **Know the Flow:** Understand the complete user journey
2. **Be Ready:** Have test files ready, know your credentials
3. **Explain Clearly:** Describe what you're doing as you do it
4. **Handle Errors:** If something fails, explain it's a demo environment
5. **Stay Coordinated:** Wait for your turn, don't interrupt others

---

## ⚡ **QUICK TROUBLESHOOTING**

### **If Login Fails:**
- Check backend is running: `cd backend && python app.py`
- Check database exists: `backend/dev.db`

### **If KYC OTP Doesn't Arrive:**
- Check toast notification (dev mode shows OTP)
- Use the OTP shown in the toast

### **If File Upload Fails:**
- Check file size (should be reasonable)
- Try a different file format (PDF, JPG, PNG)

### **If IPFS Upload Fails:**
- Check Pinata API keys in `.env`
- File will still be stored locally

### **If Page Doesn't Load:**
- Check frontend is running: `cd glow-contrib && npm run dev`
- Check browser console for errors

---

## 📋 **DEMO FLOW ORDER**

1. **Member 2:** Register → KYC → Submit Contribution
2. **Member 1:** Login as Admin → Approve KYC → Approve Contribution
3. **Member 2:** Check rewards and status
4. **Member 3:** Register → Browse Marketplace → Purchase
5. **All:** Show dashboard, profile, and analytics

---

## 💡 **KEY TALKING POINTS**

### **For All Members:**
- "This is a full-stack platform with Flask backend and React frontend"
- "We use blockchain for document attestation and IPFS for storage"
- "The system automates token rewards upon approval"
- "All user actions are tracked and visible in real-time"

### **Technical Highlights:**
- **Backend:** Flask REST API with SQLAlchemy
- **Frontend:** React + Vite + TypeScript + Tailwind
- **Blockchain:** Smart contract integration for IPFS hash storage
- **Storage:** Pinata IPFS for decentralized file storage
- **Auth:** JWT-based authentication
- **Database:** SQLite (can be upgraded to PostgreSQL)

---

## 🎬 **PRESENTATION TIPS**

1. **Speak Clearly:** Explain each action before performing it
2. **Show, Don't Tell:** Let the UI demonstrate features
3. **Highlight Uniqueness:** Point out blockchain/IPFS integration
4. **Keep It Moving:** Don't spend too long on one feature
5. **Be Confident:** If something doesn't work, explain it's a demo

---

**Remember: You're demonstrating a complete, working system! 🚀**




