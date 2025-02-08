# Budget_management_system
Budget Management System


Requirements:
### ** Budget Management System (BM) on GCP**  

#### **Objective**  
Design and develop a **three-tier application** on **Google Cloud Platform (GCP)** to manage the **budget lifecycle** across one or more **Annual Operating Plans (AOPs)**. The system should support a chatbot-driven **user experience (UX)**, CRUD APIs for all key entities, and various budget-related operations while maintaining strict constraints on spending and allocations. The solution must be **cost-efficient**, **scalable**, and **deployed on GCP** with **GitHub-based CI/CD pipelines**.

---

### **1. System Overview**  

#### **Architecture**  
- **Presentation Layer**: Chatbot-based **user interface** accessible via a website from the open internet.  
- **Business Logic Layer**: Implemented in either **Python** or **Java**, handling budget rules, workflows, and validations.  
- **Data Persistence Layer**: Cloud database for storing AOPs, budgets, employees, and transactions.  

#### **Technology Stack**  
- **Frontend**: Web-based chatbot interface.  
- **Backend**: Python or Java-based API services.  
- **Database**: Cloud SQL / MySQL.  
- **Authentication**: **Simple token-based access** (users enter “IKnowYou241202” for authentication).  
- **Hosting**: Google Cloud Run / App Engine.  
- **Version Control**: **GitHub repository** with **CI/CD pipelines** for deployment.  


---

### **2. Key Features & Functional Requirements**  

#### **2.1 Annual Operating Plans (AOPs)**  
- An **AOP consists of a header and details**:  
  - **Header**: Name, total approved amount, and states (**Draft, Active, EOL**).  
  - **Details**: Cost center, amount allocated.  
- **Lifecycle Management**:  
  - A new AOP defaults to **Draft**.  
  - Users can transition AOP from **Draft → Active** or **EOL → Active**.  
  - **Only one AOP** can be in **Active** state at any time.  
  - **Validation Rule**: **Total active budgets must not exceed total active AOP amount**.  
- **Modification Rules**:  
  - Once **Active**, no modifications are allowed **except via the Adjusted Plan process** (defined separately).  
  - Any AOP **detail update** should **auto-update** the AOP’s total amount.  
- **APIs**: CRUD operations for AOP management.  

#### **2.2 Cost Centers**  
- **Master List**: Each cost center is identified by **code** and **name**.  
- **APIs**: CRUD operations for cost center management.  

#### **2.3 Employees & Organization Hierarchy**  
- Employee details include **LDAP, first name, last name, email, level (1-12), and cost center**.  
- **Hierarchy Management**:  
  - Each employee reports to a **manager** (recursive hierarchy).  
  - Only **managers** (Level > 1) can **assign budgets** to their direct reports.  
- **APIs**: CRUD operations for employee and hierarchy management.  

#### **2.4 Budget Management**  
- Each **budget entry** represents a **spending line item** for an employee.  
- Budgets must be associated with an **AOP** and can be **Active** or **Inactive**.  
- **Rules & Validations**:  
  - Total **active budgets must not exceed active AOP’s total amount**.  
  - Employees **can request budgets only for themselves** unless they are managers.  
  - **Managers can allocate budgets** to employees within their organization.  
  - **Actuals (real spend) cannot exceed budgeted amounts**.  
- **Tracking Fields**:  
  - **Budget Entry**: Project, description, amount, LDAP of responsible employee.  
  - **Actuals (Incremental Updates)**:  
    - **Purchase Requests**: Reference, requestor, budget ID, amount, date.  
    - **Purchase Orders**: Order number, line number, requestor, budget ID, item, amount, date.  
    - **Receipts**: Receipt date, order number, line number, item.  
- **APIs**: CRUD operations for budgets, purchase requests, purchase orders, and receipts.  

#### **2.5 Budget Operations**  
- **Copy Budget**:  
  - Copy an existing **budget to another AOP** (new ID generated).  
  - Ensure **destination AOP remains within its total limit**.  
- **Remove Budget**:  
  - **Soft delete** (flag-based removal).  
  - Budgets cannot be removed if **linked to active actuals**.  
- **Reconcile Budget**:  
  - Compare **AOP totals vs. active budget totals** for compliance.  
- **Reduce Budget**:  
  - Budgets **cannot be reduced below total actuals**.  

---

### **3. User Experience (Chatbot UX)**  
- **Users interact via a chatbot** instead of traditional forms.  
- **Example Commands**:  
  - **Adding a User**:  
    - `"Add user lsamuel"` → Chatbot prompts for missing fields.  
    - `"Add user lsamuel, first name Samuel, last name Larkins"` → Prompts for missing email, level, cost center.  
  - **Removing a User**:  
    - Marks **users as inactive**, cannot remove if tied to **active budgets**.  
  - **Charts & Reports**:  
    - `"Show budget chart for AOP-2025"` → Returns **Pareto top 10 budgets**.  
    - `"Show my organization"` → Displays **hierarchy of direct & indirect reports**.  
    - `"Show my budget"` → Aggregates total budget across the user’s reporting chain.  
  - **Non-Budget Queries**:  
    - `"What is the weather in San Francisco?"` → Processes via standard LLM app.  

---

### **4. Deployment & Infrastructure**  

#### **4.1 Hosting on GCP**  
- **Compute**: Google Cloud Run / App Engine.  
- **Database**: Cloud SQL My SQL.  
- **Storage**: Cloud Storage for logs and reports.  
- **APIs**: Exposed via **Google API Gateway**.  

#### **4.2 Version Control & CI/CD**  
- **Repository**: GitHub (public or private).  
- **CI/CD Pipeline**:  
  - **GitHub Actions / Cloud Build** for deployment.  
  - **Automated testing & security checks**.  

#### **4.3 Setup Instructions**  
1. **GitHub Repository Setup**:  
   - Clone repo, configure CI/CD, and create initial branches.  
2. **GCP Setup**:  
   - Create a **GCP Project** and **enable necessary services**.  
   - Set up **Cloud Run/App Engine, Cloud SQL, API Gateway and any other missing details for full app including UI**.  
3. **Deployment**:  
   - Push to GitHub → CI/CD deploys to GCP.  

---

### **5. Constraints & Limitations**  
- **Security**: Simple authentication with **"IKnowYou241202"**.  
- **Scalability**: Optimized for **10 users, 1000 budget lines**.  

---

### **Expected Deliverables**  
✔️ **Complete Codebase** (Python/Java) in GitHub.  
✔️ **CI/CD Setup Instructions** (GitHub → GCP Deployment).  
✔️ **Detailed Documentation** (Setup guide, API specs, chatbot commands).  


