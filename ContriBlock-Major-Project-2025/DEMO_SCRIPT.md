# MyContri Platform - Complete Demo Script
## For 3-Member Presentation

---

## 🎯 **Demo Overview**
**Duration:** 15-20 minutes  
**Team Roles:**
- **Member 1:** Admin (Reviewer)
- **Member 2:** Contributor (User 1)
- **Member 3:** Buyer/Contributor (User 2)

---

## 📋 **Pre-Demo Setup Checklist**

### Before Starting:
1. ✅ Backend server running (`cd backend && python app.py`)
2. ✅ Frontend server running (`cd glow-contrib && npm run dev`)
3. ✅ Database initialized (SQLite should auto-create)
4. ✅ Admin account exists (email: `admin@example.com`, password: `admin123`)
5. ✅ Test files ready (PDF documents for contributions)
6. ✅ EmailJS configured (or dev mode OTP will be shown)
7. ✅ Pinata API keys configured (for IPFS uploads)
8. ✅ Blockchain/Ganache running (if testing on-chain features)

---

## 🎬 **DEMO FLOW - Step by Step**

---

### **PHASE 1: Introduction & Landing Page** (2 minutes)
**Presenter: All members**

1. **Open Landing Page** (`http://localhost:5173`)
   - Show hero section with platform description
   - Highlight key features:
     - Open contribution management
     - Blockchain-based attestation
     - IPFS document storage
     - Token rewards system
   - Show total supply from blockchain (if connected)
   - Navigate through the landing page sections

**Key Points to Mention:**
- "This is a decentralized platform for managing open-source contributions"
- "Contributors get rewarded with CTRI tokens for approved submissions"
- "All documents are stored on IPFS and attested on blockchain"

---

### **PHASE 2: User Registration & Login** (2 minutes)
**Presenter: Member 2 (Contributor 1)**

1. **Sign Up as New User**
   - Click "Sign Up" or navigate to `/signup`
   - Fill in:
     - Name: `John Contributor`
     - Email: `john@example.com`
     - Password: `password123`
   - Submit registration
   - Show success message

2. **Login**
   - Navigate to `/login`
   - Enter credentials
   - Show dashboard redirect after login

**Key Points:**
- "Users must register to submit contributions"
- "Authentication uses JWT tokens for security"

---

### **PHASE 3: KYC Verification Process** (3 minutes)
**Presenter: Member 2 (Contributor 1)**

1. **Navigate to Profile**
   - Click "Profile" in navigation
   - Show KYC status: "KYC Not Verified"

2. **Start KYC Verification**
   - Click "Start Verification" button
   - **Step 1: Email Verification**
     - Enter email: `john@example.com`
     - Click "Send OTP"
     - **If EmailJS configured:** Check email for OTP
     - **If not configured:** Show dev mode OTP in toast notification
     - Enter 6-digit OTP
     - Click "Verify Email"

3. **Step 2: Document Upload**
   - Upload a test document (PDF/Image)
   - Show file selection
   - Click "Submit KYC"
   - Show "KYC Submitted - Under Review" message

**Key Points:**
- "KYC ensures only verified users can publish contributions"
- "Email verification prevents spam accounts"
- "Documents are stored securely on the server"

---

### **PHASE 4: Admin KYC Review** (2 minutes)
**Presenter: Member 1 (Admin)**

1. **Login as Admin**
   - Navigate to `/login`
   - Email: `admin@example.com`
   - Password: `admin123`
   - Login

2. **Access Admin Dashboard**
   - Click "Admin" in navigation
   - Show admin dashboard overview:
     - Total contributions count
     - Pending review count
     - Approved count

3. **Review KYC Request**
   - Click on "KYC Verification" card
   - Show list of pending KYC requests
   - Click on John's KYC request
   - View uploaded document (download button)
   - **Approve** the KYC request
   - Show success notification

**Key Points:**
- "Admins review identity documents manually"
- "Approved users can now submit contributions"
- "KYC status updates in real-time"

---

### **PHASE 5: Contribution Submission** (3 minutes)
**Presenter: Member 2 (Contributor 1)**

1. **Switch Back to Contributor Account**
   - Logout from admin
   - Login as `john@example.com`

2. **Submit Contribution**
   - Navigate to `/submit`
   - Fill in contribution form:
     - **Title:** "Decentralized Voting System"
     - **Description:** "A blockchain-based voting system for transparent elections with IPFS document storage"
     - **File:** Upload a test PDF document
   - Click "Submit Contribution"
   - Show success message

3. **View Submission Status**
   - Navigate to `/dashboard`
   - Show contribution in "Your Contributions" section
   - Status: "Pending"
   - Navigate to `/profile` → "My Contributions"
   - Show contribution card with pending status

**Key Points:**
- "Contributions require title, description, and supporting file"
- "Files are stored locally and will be uploaded to IPFS upon approval"
- "Status updates in real-time"

---

### **PHASE 6: Admin Contribution Review** (3 minutes)
**Presenter: Member 1 (Admin)**

1. **Login as Admin Again**
   - Navigate to `/admin`

2. **Review Contribution**
   - Click on "Contributions Review" card
   - Show list of pending contributions
   - Click "View Details" on John's contribution
   - Review:
     - Title and description
     - Author information
     - Attached file (download to verify)
   - **Approve Contribution**
   - Show success toast with IPFS CID
   - Show Pinata dashboard link (if configured)
   - Explain: "File uploaded to IPFS, hash recorded on blockchain"

3. **Verify Token Reward**
   - Explain: "100 CTRI tokens automatically credited to contributor"
   - Show notification about reward

**Key Points:**
- "Admin reviews each contribution manually"
- "Approved files are uploaded to Pinata IPFS"
- "IPFS CID is recorded on blockchain via smart contract"
- "Contributor receives 100 CTRI tokens automatically"

---

### **PHASE 7: View Rewards & Profile** (2 minutes)
**Presenter: Member 2 (Contributor 1)**

1. **Check Token Balance**
   - Navigate to `/profile`
   - Show updated balance: "100 CTRI"
   - Refresh balance button (if needed)

2. **View Contribution Status**
   - Navigate to `/dashboard`
   - Show contribution status changed to "Accepted"
   - Show IPFS CID displayed
   - Click on contribution card to view details
   - Show full details including:
     - IPFS CID
     - File download link
     - Reward amount

**Key Points:**
- "Tokens are automatically credited upon approval"
- "IPFS CID proves document authenticity"
- "Contributors can track all their submissions"

---

### **PHASE 8: Marketplace & Purchase** (3 minutes)
**Presenter: Member 3 (Buyer/Contributor 2)**

1. **Register Second User**
   - Sign up as:
     - Name: `Alice Buyer`
     - Email: `alice@example.com`
     - Password: `password123`
   - Login

2. **Browse Marketplace**
   - Navigate to `/marketplace`
   - Show available contributions
   - Show John's contribution (if approved and listed)
   - Display:
     - Contribution title
     - Description
     - Price (in CTRI tokens)
     - Author information

3. **Purchase Contribution**
   - Click on a contribution card
   - View full details
   - Click "Purchase" button
   - Show purchase confirmation
   - Explain: "Tokens deducted from buyer, credited to seller"

4. **Access Purchased Content**
   - Navigate to `/profile`
   - Click on "Purchased Contributions" card
   - Show purchased contribution
   - Click to view details
   - Show download button for file access

**Key Points:**
- "Marketplace allows users to buy/sell contributions"
- "Purchased content is accessible in user profile"
- "Token transfers happen automatically"

---

### **PHASE 9: Dashboard Analytics** (2 minutes)
**Presenter: Member 2 (Contributor 1)**

1. **View Dashboard Statistics**
   - Navigate to `/dashboard` as John
   - Show key metrics:
     - Total Contributions: 1
     - Impact Score: (calculated)
     - Tokens Earned: 100 CTRI
     - Active Projects: 1

2. **View Charts**
   - Show "Impact Over Time" bar chart
   - Show "Contribution Status" pie chart
   - Show "Recent Activity" timeline

3. **View Contribution Cards**
   - Show contribution cards with:
     - Status badges
     - Reward amounts
     - IPFS CIDs
   - Click to view full details

**Key Points:**
- "Dashboard provides comprehensive analytics"
- "Users can track their contribution history"
- "Visual charts show impact over time"

---

### **PHASE 10: Advanced Features** (2 minutes)
**Presenter: All members (quick overview)**

1. **Duplicate Detection**
   - Admin: Try to approve a duplicate file
   - Show duplicate detection message
   - Explain: "System prevents duplicate submissions"

2. **Rejection Flow**
   - Admin: Reject a contribution (if any pending)
   - Show rejection reason input
   - Contributor: View rejection reason in profile

3. **KYC Rejection**
   - Admin: Reject a KYC request
   - User: See rejection status, option to resubmit

**Key Points:**
- "System includes duplicate detection"
- "Rejected contributions include feedback"
- "Users can resubmit after rejection"

---

## 🎯 **Key Features to Highlight**

### **Technical Highlights:**
1. ✅ **Blockchain Integration** - IPFS hashes recorded on-chain
2. ✅ **IPFS Storage** - Decentralized file storage via Pinata
3. ✅ **Token Rewards** - Automatic CTRI token distribution
4. ✅ **KYC Verification** - Email OTP + document verification
5. ✅ **Admin Dashboard** - Centralized review system
6. ✅ **Marketplace** - Buy/sell contributions
7. ✅ **Real-time Updates** - Status changes reflect immediately
8. ✅ **Secure Authentication** - JWT-based auth system

### **User Experience Highlights:**
1. ✅ **Modern UI** - Glass morphism, animations, responsive design
2. ✅ **Intuitive Navigation** - Clear user flows
3. ✅ **Real-time Feedback** - Toast notifications, status updates
4. ✅ **Comprehensive Dashboard** - Analytics and insights
5. ✅ **File Management** - Easy upload/download

---

## 🚨 **Troubleshooting During Demo**

### If Something Goes Wrong:

1. **Backend Not Running:**
   ```bash
   cd backend
   python app.py
   ```

2. **Frontend Not Running:**
   ```bash
   cd glow-contrib
   npm run dev
   ```

3. **Database Issues:**
   - Check `backend/dev.db` exists
   - Restart backend to auto-migrate

4. **EmailJS Not Working:**
   - OTP will show in toast notification (dev mode)
   - Use the displayed OTP

5. **IPFS Upload Fails:**
   - Check Pinata API keys in `.env`
   - File will still be stored locally

6. **Blockchain Connection Issues:**
   - System works without blockchain (SQL-only mode)
   - Explain: "On-chain features require local blockchain"

---

## 📝 **Demo Script Notes**

### **What Each Member Should Prepare:**

**Member 1 (Admin):**
- Admin credentials ready
- Understand review process
- Know how to approve/reject
- Be ready to explain admin features

**Member 2 (Contributor 1):**
- Test file ready (PDF)
- Understand submission process
- Know how to check status
- Be ready to show profile/dashboard

**Member 3 (Buyer/Contributor 2):**
- Understand marketplace flow
- Know how to purchase
- Be ready to show purchased content

### **Presentation Tips:**
1. **Speak Clearly:** Explain each action before doing it
2. **Show, Don't Tell:** Let the UI speak for itself
3. **Highlight Features:** Point out unique aspects
4. **Handle Errors Gracefully:** If something fails, explain it's a demo environment
5. **Keep It Flowing:** Don't get stuck on one feature too long

---

## 🎬 **Closing Statement**

**Suggested Closing:**
> "This is MyContri - a complete platform for managing open-source contributions with blockchain attestation, IPFS storage, and token rewards. The system handles the full lifecycle from user registration, KYC verification, contribution submission, admin review, blockchain recording, and marketplace transactions. All built with modern web technologies and a focus on user experience."

---

## 📊 **Demo Checklist**

- [ ] Landing page shown
- [ ] User registration demonstrated
- [ ] KYC verification process shown
- [ ] Admin KYC review demonstrated
- [ ] Contribution submission shown
- [ ] Admin contribution review demonstrated
- [ ] IPFS upload and blockchain recording explained
- [ ] Token rewards shown
- [ ] Marketplace browsing shown
- [ ] Purchase flow demonstrated
- [ ] Dashboard analytics shown
- [ ] Profile features demonstrated
- [ ] All key features highlighted

---

**Good luck with your demo! 🚀**

