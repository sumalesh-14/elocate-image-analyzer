"""
ELocate platform knowledge base for EcoBot.
Describes every feature, page, and user flow on the website.
"""

ELOCATE_PLATFORM_KNOWLEDGE = """
## ABOUT ELOCATE
ELocate is an e-waste management platform that connects citizens, recycling facilities, intermediary collectors, and administrators. It helps people responsibly recycle electronic devices, find nearby certified recycling centers, understand the environmental impact of e-waste, and track their recycling contributions.

The platform has 4 types of users:
- **Citizens** — individuals who want to recycle their e-waste
- **Intermediaries / Partners** — certified recycling centers, logistics partners, and processors who collect e-waste from citizens and deliver or process it at their facilities
- **Admins** — platform administrators who manage the entire network
- **Drivers** — handle physical pickup and delivery of e-waste on behalf of intermediaries

---

## CITIZEN PORTAL — HOW TO GET STARTED

### How to Register / Sign Up
1. Visit the ELocate homepage at `/` — you will be redirected to `/citizen`.
2. Click the **Sign In** button in the navigation header.
3. On the sign-in page, click **Register** or **Create Account**.
4. Fill in your full name, email address, mobile number, and password, then submit.
5. You will be logged in and redirected to the citizen dashboard.

### How to Sign In
1. Go to `/citizen/sign-in` and enter your registered **email address** and **password**.
2. Click the **Login** button — on success you are redirected to the citizen home page.
3. If you forgot your password, click the **Forgot Password** link on the sign-in page.

### Citizen Home Page (`/citizen`)
The home page has:
- A hero section with animated background showing ELocate's mission
- A **Features** section explaining what you can do (recycle, find facilities, analyze devices, learn)
- A **FAQ** section answering common questions
- Navigation header with links to all sections

---

## CORE CITIZEN FEATURES

### 1. Book a Recycle Request (`/citizen/book-recycle`)
This is the main feature for scheduling e-waste pickup or drop-off.

**Requires login.** If not signed in, you will be redirected to the sign-in page.

**Steps to book a recycling request:**
1. Go to **Book Recycle** from the navigation menu — you land on the Book Recycle dashboard.
2. Click **New Recycle Request** (or navigate to `/citizen/book-recycle/new`).
3. Select the device type/category (e.g., Smartphone, Laptop, TV, Refrigerator, Accessories).
4. Enter device details — brand, model, and condition.
5. Choose pickup or drop-off, enter your address and preferred date/time, then submit.
6. You will receive a confirmation and can track the status from **My Requests**.

**View your requests:**
- Go to `/citizen/book-recycle/requests` or click **My Requests** in the sidebar
- See all past and current requests with their status (Pending, In Transit, Completed, Cancelled)

**Sidebar navigation inside Book Recycle:**
- Dashboard — overview of your recycling stats
- Recycle Request — create a new request
- My Requests — view all your requests
- Settings — manage preferences

---

### 2. Analyze Your Device (`/citizen/analyze`)
An AI-powered tool that tells you the material composition and estimated recycling value of your device.

**Steps to analyze a device:**
1. Go to **Analyze** from the navigation menu at `/citizen/analyze`.
2. Select your device **Category** from the dropdown (e.g., Mobile Phone, Laptop, Tablet).
3. Select the **Brand** — this loads automatically based on the category you chose.
4. Select the **Model** — this loads automatically based on the brand you chose.
5. If your device is not in the list, toggle **Manual Input** and type the details.
6. Select the **Condition** of your device: Pristine/Working, Fair/Minor Issues, Broken/Damaged, or Scrap/Parts.
7. Click **Analyze** — the AI will show material breakdown, estimated value, and environmental impact.

---

### 3. Find E-Waste Facilities (`/citizen/e-facilities`)
Locate certified e-waste recycling centers near you.

**Steps:**
1. Go to **E-Facilities** from the navigation menu at `/citizen/e-facilities`.
2. An interactive map loads showing nearby certified recycling centers.
3. Search by location or browse the map, then click any facility marker to see its name, address, contact info, accepted device types, and operating hours.

---

### 4. Education Lab (`/citizen/education`)
Learn about e-waste, its environmental impact, and best practices for recycling.

**What you'll find:**
- Articles and guides on e-waste recycling
- Environmental impact statistics
- How different devices are recycled
- Tips for responsible disposal
- Why recycling electronics matters

---

### 5. Recycling Rules (`/citizen/rules`)
Understand the rules and guidelines for proper e-waste disposal.

**Covers:**
- What items are accepted for recycling
- How to prepare your device before recycling (data wipe, battery removal)
- Prohibited items
- Legal regulations around e-waste disposal

---

### 6. Your Profile (`/citizen/profile`)
Manage your personal account details.

**Requires login.**

**What you can do:**
- View your profile information (name, email, phone, address)
- Edit your profile — go to `/citizen/profile/edit-profile`
- View your impact score (CO2 diverted, items recycled)
- Manage account settings at `/citizen/profile/settings`

---

### 7. Contact Us (`/citizen/contactus`)
Reach the ELocate support team.

**Steps:**
1. Go to **Contact Us** from the footer or navigation at `/citizen/contactus`.
2. Fill in the contact form with your name, email, and message, then submit — the team will respond to your email.

---

### 8. Support (`/citizen/support`)
Get help with common issues and platform usage.

---

### 9. About (`/citizen/about`)
Learn about ELocate's mission, team, and vision for sustainable e-waste management.

---

## INTERMEDIARY PORTAL

Intermediaries are logistics partners who collect e-waste from citizens and deliver it to recycling facilities.

### How to become an Intermediary / Partner
1. Contact ELocate through the **Contact Us** page at `/citizen/contactus`.
2. The admin team reviews your application and approves qualified organizations.
3. Once approved, you receive intermediary login credentials and can sign in at `/intermediary/sign-in`.

### Intermediary Dashboard (`/intermediary/dashboard`)
After signing in, intermediaries see:
- **Total Collections** — total items collected
- **Pending Items** — items awaiting pickup
- **Completion Rate** — monthly performance
- **Recycled Items** — total units processed
- Recent activity feed with collection IDs, client names, dates, and statuses

### Intermediary Features:
- **Collections** (`/intermediary/collections`) — view all collection jobs
- **Clients** (`/intermediary/clients`) — manage client directory
- **Assign Drivers** (`/intermediary/assign-drivers`) — assign drivers to pickup jobs
- **Schedule** (`/intermediary/schedule`) — view and manage pickup schedule
- **Reports** (`/intermediary/reports`) — generate performance reports
- **Settings** (`/intermediary/settings`) — account settings

---

## ADMIN PORTAL (`/admin`)

The admin panel is for ELocate administrators only. Access is restricted.

### Admin Features:
- **Dashboard** — real-time KPIs: total recycled, active centers, CO2 offset, pending approvals
- **Recycle Requests** — view and manage all citizen recycle requests
- **Device Categories** — manage the list of device categories
- **Device Brands** — manage device brands
- **Device Models** — manage device models
- **Partner Network** — approve/reject partner applications, manage active partners
- **Citizen Management** — view, edit, suspend/activate citizen accounts

### How to reach Admin:
The admin portal is not publicly accessible. Admins are appointed internally by the ELocate team.

---

## DRIVER PORTAL

Drivers handle the physical pickup and delivery of e-waste.
- Drivers receive pickup requests and can accept or reject them
- After completing a pickup, they confirm via the driver portal
- Driver pages: `/driver/pickup/accept`, `/driver/pickup/reject`, `/driver/pickup/success`

---

## FREQUENTLY ASKED QUESTIONS

**Q: Do I need to create an account to use ELocate?**
A: You need an account to book a recycle request or view your profile. You can browse the education section, find facilities, and analyze devices without logging in.

**Q: How do I track my recycle request?**
A: Go to `/citizen/book-recycle/requests` after logging in. All your requests are listed with their current status.

**Q: What devices can I recycle through ELocate?**
A: Smartphones, laptops, tablets, TVs, refrigerators, batteries, chargers, cables, accessories, and other electronic devices.

**Q: Is there a cost to recycle through ELocate?**
A: ELocate connects you with certified recycling facilities. Costs depend on the facility and device type. Many accept common devices for free.

**Q: How do I wipe my data before recycling?**
A: Perform a factory reset on your device. For phones: Settings → General → Reset → Erase All Content. For laptops: use the built-in reset option in your OS settings.

**Q: How do I become a recycling partner/facility?**
A: Contact ELocate through the Contact Us page. The admin team reviews applications and approves qualified facilities.

**Q: Where can I see my environmental impact?**
A: Your profile page shows your impact score including CO2 diverted and total items recycled.
"""
