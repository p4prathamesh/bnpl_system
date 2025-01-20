# BNPL System (Buy Now, Pay Later)

This project implements a Buy Now, Pay Later (BNPL) system using Flask and MySQL. It allows users to make purchases on credit and repay in full or through EMI plans. The system also calculates penalties for late payments and supports reporting capabilities.

---

## **Prerequisites**
- **Python**: Version 3.7 or higher.
- **MySQL Database**: Ensure MySQL is installed and running.
- **Python Libraries**: Install required packages using the command:
  ```bash
  pip install Flask mysql-connector-python
  ```

---

## **Database Setup**

### Create Database and Tables
1. **Create the Database**:
   ```sql
   CREATE DATABASE bnpl_system;
   ```
2. **Switch to the Database**:
   ```sql
   USE bnpl_system;
   ```
3. **Create Tables**:

   #### Users Table
   ```sql
   CREATE TABLE users (
       user_id VARCHAR(50) PRIMARY KEY,
       name VARCHAR(100) NOT NULL,
       credit_limit DECIMAL(10, 2) NOT NULL,
       available_credit DECIMAL(10, 2) NOT NULL
   );
   ```

   #### Purchases Table
   ```sql
   CREATE TABLE purchases (
       id INT AUTO_INCREMENT PRIMARY KEY,
       user_id VARCHAR(50),
       amount DECIMAL(10, 2) NOT NULL,
       date DATETIME NOT NULL,
       repayment_type ENUM('full', 'emi') NOT NULL,
       FOREIGN KEY (user_id) REFERENCES users(user_id)
   );
   ```

   #### Repayment Plans Table
   ```sql
   CREATE TABLE repayment_plans (
       id INT AUTO_INCREMENT PRIMARY KEY,
       purchase_id INT,
       user_id VARCHAR(50),
       principal DECIMAL(10, 2) NOT NULL,
       emi DECIMAL(10, 2) NOT NULL,
       months INT NOT NULL,
       remaining_installments INT NOT NULL,
       next_due_date DATE,
       penalties DECIMAL(10, 2) NOT NULL DEFAULT 0,
       FOREIGN KEY (purchase_id) REFERENCES purchases(id),
       FOREIGN KEY (user_id) REFERENCES users(user_id)
   );
   ```

   #### Payments Table
   ```sql
   CREATE TABLE payments (
       id INT AUTO_INCREMENT PRIMARY KEY,
       user_id VARCHAR(50),
       amount DECIMAL(10, 2) NOT NULL,
       date DATETIME NOT NULL,
       FOREIGN KEY (user_id) REFERENCES users(user_id)
   );
   ```

---

## **Application Setup**
1. Clone the repository or copy the `app.py` file.
2. Update the database connection details in the `get_db_connection()` function inside `app.py`:
   ```python
   def get_db_connection():
       return mysql.connector.connect(
           host="localhost",
           user="root",
           password="your_password",
           database="bnpl_system"
       )
   ```
3. Run the Flask application:
   ```bash
   python app.py
   ```
4. The application will be available at `http://127.0.0.1:5000`.

---

## **API Endpoints**

### 1. **Register a User**
- **Endpoint**: `/register`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "user_id": "user123",
    "name": "John Doe"
  }
  ```

---

### 2. **Record a Purchase**
- **Endpoint**: `/purchase`
- **Method**: `POST`
- **Payload for Full Payment**:
  ```json
  {
    "user_id": "user123",
    "amount": 5000,
    "repayment_type": "full"
  }
  ```
- **Payload for EMI**:
  ```json
  {
    "user_id": "user123",
    "amount": 20000,
    "repayment_type": "emi",
    "months": 6
  }
  ```

---

### 3. **Record a Payment**
- **Endpoint**: `/payment`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "user_id": "user123",
    "amount": 3000
  }
  ```

---

### 4. **Fetch Active Plans**
- **Endpoint**: `/active_plans/<user_id>`
- **Method**: `GET`
- **Example**: `/active_plans/user123`

---

### 5. **Fetch Outstanding Balance**
- **Endpoint**: `/outstanding_balance/<user_id>`
- **Method**: `GET`
- **Example**: `/outstanding_balance/user123`

---

### 6. **Fetch Reports**
- **Endpoint**: `/reports`
- **Method**: `GET`
- **Query Parameters**:
  - `user_ids`: Comma-separated user IDs.
  - `date_range`: `start_date,end_date` (e.g., `2025-01-01,2025-12-31`).
  - `amount_range`: `min,max` (e.g., `1000,5000`).
- **Example**:
  ```
  /reports?user_ids=user123,user456&date_range=2025-01-01,2025-12-31&amount_range=1000,5000
  ```

---

### 7. **Fetch Repayment History**
- **Endpoint**: `/repayment_history/<user_id>`
- **Method**: `GET`
- **Example**: `/repayment_history/user123`

---

## **Testing the Application**
- Use tools like Postman or `curl` to test the endpoints.
- Verify data in the MySQL tables after each operation to ensure correctness.

---

## **Future Improvements**
1. Add analytics to determine the most common EMI plans.
2. Implement an automated process for applying penalties on overdue plans at regular intervals.
3. Enhance the reporting endpoint to include more aggregate data.

---


