from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import mysql.connector

app = Flask(__name__)

# Database connection setup
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="bnpl_system"
    )

# Constants
DEFAULT_CREDIT_LIMIT = 100000  # INR
INTEREST_RATE = 0.02  # Monthly interest rate for EMI (2%)
LATE_PAYMENT_PENALTY_RATE = 0.01  # Penalty rate (1%) per overdue day

# Helper functions
def calculate_emi(principal, months, interest_rate):
    monthly_interest = interest_rate / 12
    emi = principal * monthly_interest * ((1 + monthly_interest) ** months) / (((1 + monthly_interest) ** months) - 1)
    return round(emi, 2)

def calculate_penalty(overdue_days, amount):
    return round(overdue_days * amount * LATE_PAYMENT_PENALTY_RATE, 2)

@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    user_id = data['user_id']
    name = data['name']
    
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    if cursor.fetchone():
        return jsonify({"error": "User already exists."}), 400

    cursor.execute(
        "INSERT INTO users (user_id, name, credit_limit, available_credit) VALUES (%s, %s, %s, %s)",
        (user_id, name, DEFAULT_CREDIT_LIMIT, DEFAULT_CREDIT_LIMIT)
    )
    db.commit()
    db.close()

    return jsonify({"message": "User registered successfully."}), 201

@app.route('/purchase', methods=['POST'])
def record_purchase():
    data = request.json
    user_id = data['user_id']
    amount = data['amount']
    repayment_type = data['repayment_type']  # 'full' or 'emi'
    months = data.get('months', 0)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found."}), 404

    if amount > user['available_credit']:
        return jsonify({"error": "Insufficient credit."}), 400

    # Deduct credit
    new_available_credit = user['available_credit'] - amount
    cursor.execute("UPDATE users SET available_credit = %s WHERE user_id = %s", (new_available_credit, user_id))

    # Record purchase
    cursor.execute(
        "INSERT INTO purchases (user_id, amount, date, repayment_type) VALUES (%s, %s, %s, %s)",
        (user_id, amount, datetime.now(), repayment_type)
    )
    purchase_id = cursor.lastrowid

    if repayment_type == 'emi':
        if months <= 0:
            return jsonify({"error": "Invalid EMI duration."}), 400
        emi = calculate_emi(amount, months, INTEREST_RATE)
        next_due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute(
            "INSERT INTO repayment_plans (purchase_id, user_id, principal, emi, months, remaining_installments, next_due_date, penalties) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (purchase_id, user_id, amount, emi, months, months, next_due_date, 0)
        )

    db.commit()
    db.close()

    return jsonify({"message": "Purchase recorded successfully.", "purchase_id": purchase_id}), 201

@app.route('/payment', methods=['POST'])
def record_payment():
    data = request.json
    user_id = data['user_id']
    amount = data['amount']

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found."}), 404

    remaining_amount = amount

    # Apply payment to active EMI plans
    cursor.execute("SELECT * FROM repayment_plans WHERE user_id = %s ORDER BY next_due_date ASC", (user_id,))
    plans = cursor.fetchall()

    for plan in plans:
        if remaining_amount <= 0:
            break

        overdue_days = (datetime.now() - datetime.strptime(plan['next_due_date'], '%Y-%m-%d')).days
        penalties = calculate_penalty(max(0, overdue_days), plan['principal'])
        
        # Apply penalties to the principal
        plan['principal'] += penalties

        plan_payment = min(remaining_amount, plan['emi'] * plan['remaining_installments'])

        # Update principal and remaining installments
        new_principal = plan['principal'] - plan_payment
        remaining_amount -= plan_payment
        remaining_installments = max(0, int(new_principal // plan['emi']))
        next_due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d') if remaining_installments > 0 else None

        # Update the plan
        cursor.execute(
            "UPDATE repayment_plans SET principal = %s, remaining_installments = %s, next_due_date = %s, penalties = 0 WHERE id = %s",
            (new_principal, remaining_installments, next_due_date, plan['id'])
        )

        if new_principal <= 0:
            cursor.execute("DELETE FROM repayment_plans WHERE id = %s", (plan['id'],))

    # Update user's available credit
    new_available_credit = user['available_credit'] + (amount - remaining_amount)
    cursor.execute("UPDATE users SET available_credit = %s WHERE user_id = %s", (new_available_credit, user_id))

    # Record payment
    cursor.execute(
        "INSERT INTO payments (user_id, amount, date) VALUES (%s, %s, %s)",
        (user_id, amount, datetime.now())
    )

    db.commit()
    db.close()

    return jsonify({"message": "Payment recorded successfully."}), 201

@app.route('/active_plans/<user_id>', methods=['GET'])
def get_active_plans(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM repayment_plans WHERE user_id = %s", (user_id,))
    plans = cursor.fetchall()

    # Update penalties dynamically
    for plan in plans:
        overdue_days = (datetime.now() - datetime.strptime(plan['next_due_date'], '%Y-%m-%d')).days
        plan['penalties'] = calculate_penalty(max(0, overdue_days), plan['principal'])

    db.close()
    return jsonify(plans), 200

@app.route('/outstanding_balance/<user_id>', methods=['GET'])
def get_outstanding_balance(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM purchases WHERE user_id = %s", (user_id,))
    purchases = cursor.fetchall()

    outstanding_balance = sum(purchase['amount'] for purchase in purchases)

    db.close()
    return jsonify({"outstanding_balance": outstanding_balance}), 200

@app.route('/reports', methods=['GET'])
def get_reports():
    filters = request.args
    user_ids = filters.get('user_ids', None)
    date_range = filters.get('date_range', None)
    amount_range = filters.get('amount_range', None)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM purchases WHERE 1=1"
    params = []

    if user_ids:
        user_ids = user_ids.split(',')
        query += " AND user_id IN (%s)" % (','.join(['%s'] * len(user_ids)))
        params.extend(user_ids)

    if date_range:
        start_date, end_date = date_range.split(',')
        query += " AND date BETWEEN %s AND %s"
        params.extend([start_date, end_date])

    if amount_range:
        min_amount, max_amount = map(float, amount_range.split(','))
        query += " AND amount BETWEEN %s AND %s"
        params.extend([min_amount, max_amount])

    cursor.execute(query, tuple(params))
    reports = cursor.fetchall()

    db.close()
    return jsonify(reports), 200

@app.route('/repayment_history/<user_id>', methods=['GET'])
def get_repayment_history(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM payments WHERE user_id = %s ORDER BY date DESC", (user_id,))
    history = cursor.fetchall()

    db.close()
    return jsonify(history), 200

if __name__ == '__main__':
    app.run(debug=True)
