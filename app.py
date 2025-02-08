import os
import datetime
from functools import wraps

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# Initialize Flask and SQLAlchemy
app = Flask(__name__)

# DATABASE_URL is read from environment variables.
# For local testing you can use SQLite; for production, set it to your Cloud SQL (MySQL) connection string.
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///bm.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- SIMPLE AUTHENTICATION ---
AUTH_TOKEN = "IKnowYou241202"

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '')
        if token != AUTH_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return func(*args, **kwargs)
    return wrapper

# --- MODELS ---

class AOP(db.Model):
    __tablename__ = 'aops'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_approved_amount = db.Column(db.Float, nullable=False)
    state = db.Column(db.String(10), nullable=False, default="Draft")  # Draft, Active, EOL

    details = db.relationship("AOPDetail", backref="aop", cascade="all, delete-orphan")
    budgets = db.relationship("Budget", backref="aop", cascade="all, delete-orphan")

class AOPDetail(db.Model):
    __tablename__ = 'aop_details'
    id = db.Column(db.Integer, primary_key=True)
    aop_id = db.Column(db.Integer, db.ForeignKey('aops.id'), nullable=False)
    cost_center_code = db.Column(db.String(50), nullable=False)
    allocated_amount = db.Column(db.Float, nullable=False)

class CostCenter(db.Model):
    __tablename__ = 'cost_centers'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    ldap = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    cost_center_code = db.Column(db.String(50), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)

    reports = db.relationship("Employee", backref=db.backref('manager', remote_side=[id]))

class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    aop_id = db.Column(db.Integer, db.ForeignKey('aops.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    project = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    amount = db.Column(db.Float, nullable=False)
    state = db.Column(db.String(10), nullable=False, default="Active")  # Active, Inactive
    soft_deleted = db.Column(db.Boolean, default=False)

    employee = db.relationship("Employee", backref="budgets")
    purchase_requests = db.relationship("PurchaseRequest", backref="budget", cascade="all, delete-orphan")
    purchase_orders = db.relationship("PurchaseOrder", backref="budget", cascade="all, delete-orphan")

class PurchaseRequest(db.Model):
    __tablename__ = 'purchase_requests'
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), nullable=False)
    requestor_ldap = db.Column(db.String(50), nullable=False)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.date.today)

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(100), nullable=False)
    line_number = db.Column(db.Integer, nullable=False)
    requestor_ldap = db.Column(db.String(50), nullable=False)
    budget_id = db.Column(db.Integer, db.ForeignKey('budgets.id'), nullable=False)
    item = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.date.today)

class Receipt(db.Model):
    __tablename__ = 'receipts'
    id = db.Column(db.Integer, primary_key=True)
    receipt_date = db.Column(db.Date, nullable=False, default=datetime.date.today)
    order_number = db.Column(db.String(100), nullable=False)
    line_number = db.Column(db.Integer, nullable=False)
    item = db.Column(db.String(255), nullable=False)

# --- UTILITY FUNCTIONS ---

def calculate_active_budgets_total(aop_id):
    total = db.session.query(func.sum(Budget.amount)).filter(
        Budget.aop_id == aop_id,
        Budget.state == "Active",
        Budget.soft_deleted == False
    ).scalar()
    return total or 0.0

def get_active_aop():
    return AOP.query.filter_by(state="Active").first()

# --- API ENDPOINTS ---

# ---------- AOP CRUD ----------
@app.route('/api/aops', methods=['GET'])
@require_auth
def get_aops():
    aops = AOP.query.all()
    result = []
    for aop in aops:
        result.append({
            "id": aop.id,
            "name": aop.name,
            "total_approved_amount": aop.total_approved_amount,
            "state": aop.state,
            "details": [
                {"id": d.id, "cost_center_code": d.cost_center_code, "allocated_amount": d.allocated_amount}
                for d in aop.details
            ]
        })
    return jsonify(result)

@app.route('/api/aops', methods=['POST'])
@require_auth
def create_aop():
    data = request.json
    # Expected JSON: {"name": ..., "total_approved_amount": ..., "details": [{ "cost_center_code": ..., "allocated_amount": ... }, ...]}
    aop = AOP(
        name=data['name'],
        total_approved_amount=data['total_approved_amount'],
        state="Draft"
    )
    db.session.add(aop)
    db.session.commit()
    # Add details if provided
    if "details" in data:
        for detail in data["details"]:
            d = AOPDetail(
                aop_id=aop.id,
                cost_center_code=detail["cost_center_code"],
                allocated_amount=detail["allocated_amount"]
            )
            db.session.add(d)
        db.session.commit()
    return jsonify({"message": "AOP created", "id": aop.id}), 201

@app.route('/api/aops/<int:aop_id>', methods=['GET'])
@require_auth
def get_aop(aop_id):
    aop = AOP.query.get_or_404(aop_id)
    result = {
        "id": aop.id,
        "name": aop.name,
        "total_approved_amount": aop.total_approved_amount,
        "state": aop.state,
        "details": [
            {"id": d.id, "cost_center_code": d.cost_center_code, "allocated_amount": d.allocated_amount}
            for d in aop.details
        ]
    }
    return jsonify(result)

@app.route('/api/aops/<int:aop_id>', methods=['PUT'])
@require_auth
def update_aop(aop_id):
    aop = AOP.query.get_or_404(aop_id)
    data = request.json
    # Once Active, modifications are not allowed except via Adjusted Plan (not implemented here)
    if aop.state == "Active":
        return jsonify({"error": "Active AOP cannot be modified except via Adjusted Plan process"}), 400
    aop.name = data.get('name', aop.name)
    aop.total_approved_amount = data.get('total_approved_amount', aop.total_approved_amount)
    # Replace details if provided
    if "details" in data:
        AOPDetail.query.filter_by(aop_id=aop.id).delete()
        for detail in data["details"]:
            d = AOPDetail(
                aop_id=aop.id,
                cost_center_code=detail["cost_center_code"],
                allocated_amount=detail["allocated_amount"]
            )
            db.session.add(d)
    db.session.commit()
    return jsonify({"message": "AOP updated"})

@app.route('/api/aops/<int:aop_id>', methods=['DELETE'])
@require_auth
def delete_aop(aop_id):
    aop = AOP.query.get_or_404(aop_id)
    db.session.delete(aop)
    db.session.commit()
    return jsonify({"message": "AOP deleted"})

# Transition AOP state (Draft → Active, EOL → Active, etc.)
@app.route('/api/aops/<int:aop_id>/transition', methods=['POST'])
@require_auth
def transition_aop(aop_id):
    # Expected JSON: {"target_state": "Active" or "EOL" or "Draft"}
    aop = AOP.query.get_or_404(aop_id)
    data = request.json
    target_state = data.get("target_state")
    if target_state not in ["Draft", "Active", "EOL"]:
        return jsonify({"error": "Invalid target state"}), 400

    # Only one AOP can be Active at any time.
    if target_state == "Active":
        active_aop = get_active_aop()
        if active_aop and active_aop.id != aop.id:
            return jsonify({"error": "Another AOP is already active"}), 400
        # Validate: active budgets must not exceed approved total.
        active_budget_total = calculate_active_budgets_total(aop.id)
        if active_budget_total > aop.total_approved_amount:
            return jsonify({"error": "Active budgets exceed AOP total"}), 400

    aop.state = target_state
    db.session.commit()
    return jsonify({"message": f"AOP transitioned to {target_state}"})

# ---------- Cost Center CRUD ----------
@app.route('/api/costcenters', methods=['GET'])
@require_auth
def get_cost_centers():
    centers = CostCenter.query.all()
    result = [{"id": c.id, "code": c.code, "name": c.name} for c in centers]
    return jsonify(result)

@app.route('/api/costcenters', methods=['POST'])
@require_auth
def create_cost_center():
    data = request.json
    center = CostCenter(code=data['code'], name=data['name'])
    db.session.add(center)
    db.session.commit()
    return jsonify({"message": "Cost center created", "id": center.id}), 201

@app.route('/api/costcenters/<int:center_id>', methods=['PUT'])
@require_auth
def update_cost_center(center_id):
    center = CostCenter.query.get_or_404(center_id)
    data = request.json
    center.code = data.get('code', center.code)
    center.name = data.get('name', center.name)
    db.session.commit()
    return jsonify({"message": "Cost center updated"})

@app.route('/api/costcenters/<int:center_id>', methods=['DELETE'])
@require_auth
def delete_cost_center(center_id):
    center = CostCenter.query.get_or_404(center_id)
    db.session.delete(center)
    db.session.commit()
    return jsonify({"message": "Cost center deleted"})

# ---------- Employee CRUD & Hierarchy ----------
@app.route('/api/employees', methods=['GET'])
@require_auth
def get_employees():
    employees = Employee.query.all()
    result = []
    for emp in employees:
        result.append({
            "id": emp.id,
            "ldap": emp.ldap,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "email": emp.email,
            "level": emp.level,
            "cost_center_code": emp.cost_center_code,
            "manager_id": emp.manager_id,
            "active": emp.active
        })
    return jsonify(result)

@app.route('/api/employees', methods=['POST'])
@require_auth
def create_employee():
    data = request.json
    emp = Employee(
        ldap=data['ldap'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        level=data['level'],
        cost_center_code=data['cost_center_code'],
        manager_id=data.get('manager_id')
    )
    db.session.add(emp)
    db.session.commit()
    return jsonify({"message": "Employee created", "id": emp.id}), 201

@app.route('/api/employees/<int:emp_id>', methods=['PUT'])
@require_auth
def update_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    data = request.json
    emp.first_name = data.get('first_name', emp.first_name)
    emp.last_name = data.get('last_name', emp.last_name)
    emp.email = data.get('email', emp.email)
    emp.level = data.get('level', emp.level)
    emp.cost_center_code = data.get('cost_center_code', emp.cost_center_code)
    emp.manager_id = data.get('manager_id', emp.manager_id)
    db.session.commit()
    return jsonify({"message": "Employee updated"})

@app.route('/api/employees/<int:emp_id>', methods=['DELETE'])
@require_auth
def delete_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    # Prevent deletion if tied to active budgets.
    active_budgets = Budget.query.filter_by(employee_id=emp.id, state="Active", soft_deleted=False).count()
    if active_budgets > 0:
        return jsonify({"error": "Cannot remove employee tied to active budgets"}), 400
    emp.active = False  # Soft remove by marking inactive.
    db.session.commit()
    return jsonify({"message": "Employee marked as inactive"})

# ---------- Budget CRUD & Operations ----------
@app.route('/api/budgets', methods=['GET'])
@require_auth
def get_budgets():
    budgets = Budget.query.filter_by(soft_deleted=False).all()
    result = []
    for b in budgets:
        result.append({
            "id": b.id,
            "aop_id": b.aop_id,
            "employee_id": b.employee_id,
            "project": b.project,
            "description": b.description,
            "amount": b.amount,
            "state": b.state
        })
    return jsonify(result)

@app.route('/api/budgets', methods=['POST'])
@require_auth
def create_budget():
    data = request.json
    # In a full app, you would check whether the requester is allowed to allocate on behalf of someone else.
    budget = Budget(
        aop_id=data['aop_id'],
        employee_id=data['employee_id'],
        project=data['project'],
        description=data.get('description', ''),
        amount=data['amount'],
        state="Active"
    )
    # Validate against AOP total.
    aop = AOP.query.get(budget.aop_id)
    if not aop:
        return jsonify({"error": "Invalid AOP"}), 400
    active_budget_total = calculate_active_budgets_total(aop.id)
    if (active_budget_total + budget.amount) > aop.total_approved_amount:
        return jsonify({"error": "Budget allocation exceeds AOP total"}), 400
    db.session.add(budget)
    db.session.commit()
    return jsonify({"message": "Budget created", "id": budget.id}), 201

@app.route('/api/budgets/<int:budget_id>', methods=['PUT'])
@require_auth
def update_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    data = request.json
    new_amount = data.get('amount', budget.amount)
    if new_amount < 0:
        return jsonify({"error": "Budget cannot be negative"}), 400
    budget.project = data.get('project', budget.project)
    budget.description = data.get('description', budget.description)
    budget.amount = new_amount
    db.session.commit()
    return jsonify({"message": "Budget updated"})

@app.route('/api/budgets/<int:budget_id>', methods=['DELETE'])
@require_auth
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    # Soft delete (flag-based); here we assume there are no linked actuals.
    budget.soft_deleted = True
    db.session.commit()
    return jsonify({"message": "Budget soft-deleted"})

# Budget Operations

# Copy Budget to another AOP
@app.route('/api/budgets/<int:budget_id>/copy', methods=['POST'])
@require_auth
def copy_budget(budget_id):
    data = request.json  # Expected: {"destination_aop_id": ...}
    destination_aop_id = data.get("destination_aop_id")
    original_budget = Budget.query.get_or_404(budget_id)
    destination_aop = AOP.query.get(destination_aop_id)
    if not destination_aop:
        return jsonify({"error": "Destination AOP not found"}), 400
    active_budget_total = calculate_active_budgets_total(destination_aop_id)
    if (active_budget_total + original_budget.amount) > destination_aop.total_approved_amount:
        return jsonify({"error": "Copy would exceed destination AOP total"}), 400
    new_budget = Budget(
        aop_id=destination_aop_id,
        employee_id=original_budget.employee_id,
        project=original_budget.project,
        description=original_budget.description,
        amount=original_budget.amount,
        state=original_budget.state
    )
    db.session.add(new_budget)
    db.session.commit()
    return jsonify({"message": "Budget copied", "new_budget_id": new_budget.id})

# Reduce Budget
@app.route('/api/budgets/<int:budget_id>/reduce', methods=['POST'])
@require_auth
def reduce_budget(budget_id):
    data = request.json  # Expected: {"new_amount": ...}
    new_amount = data.get("new_amount")
    if new_amount is None:
        return jsonify({"error": "new_amount required"}), 400
    budget = Budget.query.get_or_404(budget_id)
    # For simplicity, assume actuals = 0
    if new_amount < 0:
        return jsonify({"error": "Budget cannot be negative"}), 400
    budget.amount = new_amount
    db.session.commit()
    return jsonify({"message": "Budget reduced", "new_amount": new_amount})

# Reconcile Budgets: compare each active AOP’s total vs. its active budgets.
@app.route('/api/budgets/reconcile', methods=['GET'])
@require_auth
def reconcile_budget():
    issues = []
    active_aops = AOP.query.filter_by(state="Active").all()
    for aop in active_aops:
        active_budget_total = calculate_active_budgets_total(aop.id)
        if active_budget_total > aop.total_approved_amount:
            issues.append({
                "aop_id": aop.id,
                "aop_name": aop.name,
                "active_budget_total": active_budget_total,
                "aop_total": aop.total_approved_amount
            })
    if issues:
        return jsonify({"status": "issues", "details": issues}), 400
    return jsonify({"status": "reconciled"})

# ---------- Purchase Requests ----------
@app.route('/api/purchase_requests', methods=['POST'])
@require_auth
def create_purchase_request():
    data = request.json
    pr = PurchaseRequest(
        reference=data['reference'],
        requestor_ldap=data['requestor_ldap'],
        budget_id=data['budget_id'],
        amount=data['amount'],
        date=datetime.datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else datetime.date.today()
    )
    db.session.add(pr)
    db.session.commit()
    return jsonify({"message": "Purchase Request created", "id": pr.id}), 201

# ---------- Purchase Orders ----------
@app.route('/api/purchase_orders', methods=['POST'])
@require_auth
def create_purchase_order():
    data = request.json
    po = PurchaseOrder(
        order_number=data['order_number'],
        line_number=data['line_number'],
        requestor_ldap=data['requestor_ldap'],
        budget_id=data['budget_id'],
        item=data['item'],
        amount=data['amount'],
        date=datetime.datetime.strptime(data['date'], '%Y-%m-%d').date() if data.get('date') else datetime.date.today()
    )
    db.session.add(po)
    db.session.commit()
    return jsonify({"message": "Purchase Order created", "id": po.id}), 201

# ---------- Receipts ----------
@app.route('/api/receipts', methods=['POST'])
@require_auth
def create_receipt():
    data = request.json
    receipt = Receipt(
        receipt_date=datetime.datetime.strptime(data['receipt_date'], '%Y-%m-%d').date() if data.get('receipt_date') else datetime.date.today(),
        order_number=data['order_number'],
        line_number=data['line_number'],
        item=data['item']
    )
    db.session.add(receipt)
    db.session.commit()
    return jsonify({"message": "Receipt created", "id": receipt.id}), 201

# ---------- Chatbot Endpoint ----------
@app.route('/api/chat', methods=['POST'])
def chat():
    # The chatbot processes a simple command (see below for examples)
    message = request.json.get("message", "")
    response = process_chat_command(message)
    return jsonify({"response": response})

def process_chat_command(message):
    """Process a few example chatbot commands."""
    message = message.strip()
    if message.lower().startswith("add user"):
        # Example: "Add user lsamuel, first name Samuel, last name Larkins"
        parts = message.split(',')
        ldap_part = parts[0].split()
        if len(ldap_part) < 3:
            return "Invalid command format for adding user."
        ldap = ldap_part[2]
        first_name = ""
        last_name = ""
        email = ""
        level = 1
        cost_center_code = ""
        for part in parts[1:]:
            if "first name" in part.lower():
                first_name = part.split("first name")[-1].strip()
            elif "last name" in part.lower():
                last_name = part.split("last name")[-1].strip()
            elif "email" in part.lower():
                email = part.split("email")[-1].strip()
            elif "level" in part.lower():
                try:
                    level = int(part.split("level")[-1].strip())
                except:
                    level = 1
            elif "cost center" in part.lower():
                cost_center_code = part.split("cost center")[-1].strip()
        missing = []
        if not first_name:
            missing.append("first name")
        if not last_name:
            missing.append("last name")
        if not email:
            missing.append("email")
        if not cost_center_code:
            missing.append("cost center")
        if missing:
            return f"Missing fields: {', '.join(missing)}"
        new_emp = Employee(
            ldap=ldap,
            first_name=first_name,
            last_name=last_name,
            email=email,
            level=level,
            cost_center_code=cost_center_code
        )
        db.session.add(new_emp)
        db.session.commit()
        return f"User {ldap} added successfully."
    elif message.lower().startswith("remove user"):
        # Example: "Remove user lsamuel"
        parts = message.split()
        if len(parts) < 3:
            return "Invalid command format for removing user."
        ldap = parts[2]
        emp = Employee.query.filter_by(ldap=ldap, active=True).first()
        if not emp:
            return f"User {ldap} not found or already inactive."
        active_budgets = Budget.query.filter_by(employee_id=emp.id, state="Active", soft_deleted=False).count()
        if active_budgets > 0:
            return f"User {ldap} cannot be removed due to active budgets."
        emp.active = False
        db.session.commit()
        return f"User {ldap} marked as inactive."
    elif message.lower().startswith("show budget chart for"):
        # Example: "Show budget chart for AOP-2025"
        aop_name = message.split("for")[-1].strip()
        aop = AOP.query.filter(AOP.name.ilike(f"%{aop_name}%")).first()
        if not aop:
            return f"AOP {aop_name} not found."
        budgets = Budget.query.filter_by(aop_id=aop.id, state="Active", soft_deleted=False).order_by(Budget.amount.desc()).limit(10).all()
        chart = "\n".join([f"{b.project}: {b.amount}" for b in budgets])
        return f"Budget Chart for {aop.name}:\n{chart}"
    elif message.lower().startswith("show my organization"):
        # For simplicity, display all active employees (a real app would show a hierarchy)
        employees = Employee.query.filter_by(active=True).all()
        org_chart = "\n".join([f"{e.ldap}: {e.first_name} {e.last_name} (Manager: {e.manager_id})" for e in employees])
        return f"Organization:\n{org_chart}"
    elif message.lower().startswith("show my budget"):
        # For demonstration, assume a fixed user (e.g. 'demo') and sum their budgets.
        ldap = "demo"
        emp = Employee.query.filter_by(ldap=ldap, active=True).first()
        if not emp:
            return "User not found."
        total_budget = sum(b.amount for b in emp.budgets if b.state=="Active" and not b.soft_deleted)
        return f"Total budget for {ldap}: {total_budget}"
    else:
        return "I'm sorry, I didn't understand that command."

# ---------- Basic Chatbot UI ----------
@app.route('/')
def index():
    # A very simple HTML page with a chatbot interface.
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Budget Management Chatbot</title>
    </head>
    <body>
        <h1>Budget Management Chatbot</h1>
        <div id="chatbox" style="border:1px solid #ccc; width:500px; height:300px; overflow:auto; padding:5px;"></div>
        <br>
        <input type="text" id="message" placeholder="Enter your command" style="width:400px;">
        <button onclick="sendMessage()">Send</button>
        <script>
            function sendMessage(){
                var msg = document.getElementById('message').value;
                fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({message: msg})
                })
                .then(response => response.json())
                .then(data => {
                    var chatbox = document.getElementById('chatbox');
                    chatbox.innerHTML += '<p><b>You:</b> ' + msg + '</p>';
                    chatbox.innerHTML += '<p><b>Bot:</b> ' + data.response + '</p>';
                    document.getElementById('message').value = '';
                });
            }
        </script>
    </body>
    </html>
    '''

# ---------- Main ----------
if __name__ == '__main__':
    # On first run, create the database tables.
    db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
