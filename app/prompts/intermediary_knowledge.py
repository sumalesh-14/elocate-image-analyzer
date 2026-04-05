"""
E-Locate platform knowledge base for the Intermediary Ops Co-Pilot.
Covers all intermediary portal pages, CPCB compliance rules, and operational workflows.
"""

INTERMEDIARY_PLATFORM_KNOWLEDGE = """
## ABOUT THE INTERMEDIARY ROLE
Intermediaries (also called Partners or Facility Managers) are certified e-waste collectors and processors registered on the E-Locate platform. They receive e-waste pickup requests from citizens, assign drivers to collect the items, and process or forward them to certified recycling facilities.

Intermediaries sign in at `/intermediary/sign-in` and access their dedicated portal.

---

## INTERMEDIARY PORTAL PAGES

### Dashboard (`/intermediary/dashboard`)
The main overview page after sign-in. Shows:
- **Total Collections** — cumulative items collected across all time
- **Pending Items** — requests awaiting driver assignment or pickup
- **Completion Rate** — percentage of requests completed this month
- **Recycled Items** — total units successfully processed
- **Recent Activity Feed** — latest collection IDs, client names, dates, and statuses
- Quick-action buttons to navigate to Collections, Assign Drivers, and Reports

### Collections (`/intermediary/collections`)
View and manage all incoming e-waste collection jobs from citizens.
- Filter by status: Pending, Assigned, In Transit, Completed, Cancelled
- Each row shows: Collection ID, citizen name, device type, pickup address, scheduled date, assigned driver, and current status
- Click any row to view full collection details
- Use the **Export** button to download collection data as CSV

### Clients (`/intermediary/clients`)
Manage the directory of citizens and organizations that have submitted requests to your facility.
- View client contact details, total requests, and recycling history
- Search and filter clients by name, location, or request count

### Assign Drivers (`/intermediary/assign-drivers`)
Assign available drivers to pending pickup requests.
- View all unassigned requests alongside available drivers
- Filter drivers by vehicle type (two-wheeler, three-wheeler, truck) and availability status
- Click **Assign** next to a request to select a driver — the driver receives a notification
- Bulk-assign multiple requests to a single driver for route optimization

### Schedule (`/intermediary/schedule`)
View and manage the pickup schedule in a calendar view.
- See all scheduled pickups by date and time slot
- Identify scheduling conflicts or overloaded days
- Reschedule pickups by dragging to a new date (if the citizen has not yet been notified)
- Filter by driver to see individual workloads

### Reports (`/intermediary/reports`)
Generate and export operational and compliance reports. Four report types:
1. **Volume Report** — total weight and item count collected per period
2. **Driver Performance Report** — pickups completed, on-time rate, and distance covered per driver
3. **Financials Report** — revenue, costs, and net margin per period
4. **CPCB Compliance Report** — Form-2 and Form-6 data formatted for regulatory submission

To export a report: select the report type, choose the date range, then click **Export** in the top-right of the Reports tab. Downloads as CSV or PDF.

### Transactions (`/intermediary/transactions`)
View all financial transactions — payments received from the platform, payouts to drivers, and processing fees.

### Withdrawals (`/intermediary/withdrawals`)
Request withdrawal of earned balance to your registered bank account.
- View pending and completed withdrawal requests
- Minimum withdrawal amount applies (check platform settings)

### Settings (`/intermediary/settings`)
Manage your facility profile and account preferences.
- Update facility name, address, contact details, and operating hours
- Manage notification preferences (email, SMS)
- Change password and security settings
- View your CPCB registration number and license details

---

## CPCB E-WASTE (MANAGEMENT) RULES, 2022

### Key Obligations for Intermediaries / Dismantlers / Recyclers
- Must be registered with the **Central Pollution Control Board (CPCB)** or the relevant **State Pollution Control Board (SPCB)**.
- Must maintain records of all e-waste received, processed, and dispatched.
- Must file **Form-2** (Annual Return) and **Form-6** (Quarterly Return) as per the schedule below.

### Form-2 — Annual Return
- **What it covers:** Total e-waste collected, processed, and recycled in the financial year.
- **Filing deadline:** On or before **30th June** of the following financial year.
- **Where to file:** CPCB's online portal (https://ewasteportal.cpcb.gov.in).
- **Key fields:** Facility registration number, total weight collected (in MT), categories of e-waste, disposal method, and end-of-life destination.
- On E-Locate: Go to **Reports → CPCB Compliance Report**, select the financial year, and click **Export Form-2** to download the pre-filled schema.

### Form-6 — Quarterly Return
- **What it covers:** E-waste collected and processed in each quarter.
- **Filing deadlines:**
  - Q1 (Apr–Jun): by **31st July**
  - Q2 (Jul–Sep): by **31st October**
  - Q3 (Oct–Dec): by **31st January**
  - Q4 (Jan–Mar): by **30th April**
- On E-Locate: Go to **Reports → CPCB Compliance Report**, select the quarter, and click **Export Form-6**.

### Extended Producer Responsibility (EPR) Targets
- Producers must meet annual EPR collection targets set by CPCB.
- Intermediaries supporting EPR schemes must maintain channel partner agreements and submit proof of collection to the producer.
- EPR targets are device-category specific (e.g., IT equipment, consumer electronics, large appliances).

### Prohibited Practices
- Dismantling e-waste in open areas or burning components is illegal and punishable under the Environment Protection Act.
- Selling e-waste to unregistered recyclers is a violation.
- Mixing e-waste with municipal solid waste is prohibited.

---

## DRIVER MANAGEMENT BEST PRACTICES
- Assign drivers based on vehicle capacity relative to the device size/weight in the request.
- Two-wheelers: suitable for small items (phones, tablets, accessories).
- Three-wheelers / vans: suitable for medium items (laptops, monitors, small appliances).
- Trucks: required for large items (TVs, refrigerators, washing machines).
- Check driver availability status before assigning — avoid assigning to drivers already on a route.
- Use the Schedule view to balance workload across drivers and avoid overloading any single driver.

---

## OPERATIONAL WORKFLOWS

### Standard Pickup Workflow
1. Citizen submits a recycle request → appears in **Collections** as "Pending".
2. Intermediary reviews the request details (device type, address, preferred date).
3. Intermediary goes to **Assign Drivers** and assigns an available driver.
4. Status changes to "Assigned" — driver receives notification.
5. Driver completes pickup → status changes to "In Transit".
6. Device arrives at facility → intermediary marks as "Completed".
7. Data is recorded for CPCB compliance reporting.

### Handling Cancellations
- If a citizen cancels before driver assignment: request disappears from the queue automatically.
- If a citizen cancels after driver assignment: intermediary must manually unassign the driver in the **Assign Drivers** page and update the status.

### Escalation
- For disputes or platform issues, contact E-Locate support through the **Settings** page or email the admin team.
"""
