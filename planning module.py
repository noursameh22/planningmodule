from flask import Flask, request, render_template_string, jsonify
import pyodbc
import datetime

app = Flask(__name__)

# Connection string with Windows Authentication
conn_str = (
    'DRIVER={SQL Server};'
    'SERVER=NourLap;'  # Replace with your SQL Server name
    'DATABASE=stevadoring;'  # Replace with your database name
    'Trusted_Connection=yes;'
)

# Function to validate and parse date fields
def parse_date(value):
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return None

def create_tables():
    conn = None
    cursor = None
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Create Vessel table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Vessel' AND xtype='U')
            CREATE TABLE Vessel (
                id INT IDENTITY(1,1) PRIMARY KEY,
                date DATE NOT NULL,
                vessel_name NVARCHAR(50) NOT NULL,
                cargo NVARCHAR(50) NOT NULL,
                daily_rate FLOAT NOT NULL,
                quantity FLOAT NOT NULL,
                client_name NVARCHAR(50) NOT NULL,
                factory NVARCHAR(50) NOT NULL
            )
        """)

        # Create Warehouse table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Warehouse' AND xtype='U')
            CREATE TABLE Warehouse (
                id INT IDENTITY(1,1) PRIMARY KEY,
                client NVARCHAR(50) NOT NULL,
                factory NVARCHAR(50) NOT NULL,
                cargo NVARCHAR(50) NOT NULL,
                quantity2 FLOAT NOT NULL,
                place NVARCHAR(50) NOT NULL
            )
        """)

        conn.commit()
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def fetch_vessel_data():
    conn = None
    cursor = None
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Vessel")
        return cursor.fetchall()  # Returns a list of tuples
    except Exception as e:
        print(f"Error fetching vessel data: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def fetch_warehouse_data():
    conn = None
    cursor = None
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Warehouse")
        return cursor.fetchall()  # Returns a list of tuples
    except Exception as e:
        print(f"Error fetching warehouse data: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    errors = {}
    message = ""
    daily_need = None

    # Fetch data from the tables
    vessels = fetch_vessel_data()
    warehouses = fetch_warehouse_data()

    if request.method == 'POST':
        data = {
            'date': request.form.get('date'),
            'vessel_name': request.form.get('vessel_name'),
            'cargo': request.form.get('cargo'),
            'daily_rate': request.form.get('daily_rate'),
            'quantity': request.form.get('quantity'),
            'client_name': request.form.get('client_name'),
            'factory': request.form.get('factory'),
            'client': request.form.get('client'),
            'factory_warehouse': request.form.get('factory_warehouse'),
            'cargo_warehouse': request.form.get('cargo_warehouse'),
            'quantity2': request.form.get('quantity2'),
            'place': request.form.get('place')
        }

        # Validate required fields
        required_fields = ['date', 'vessel_name', 'cargo', 'daily_rate', 'quantity', 
                           'client_name', 'factory', 'client', 'factory_warehouse', 
                           'cargo_warehouse', 'quantity2', 'place']
        for field in required_fields:
            if not data.get(field):
                errors[field] = "This field is required."

        # Validate date fields
        if data.get('date'):
            parsed_date = parse_date(data['date'])
            if parsed_date is None:
                errors['date'] = "Invalid date format. Use 'YYYY-MM-DD'."
            else:
                data['date'] = parsed_date.strftime('%Y-%m-%d')

        # Calculate daily need if no errors
        if not errors:
            # Insert data into SQL Server
            conn = None
            cursor = None
            try:
                conn = pyodbc.connect(conn_str)
                cursor = conn.cursor()

                # Insert into Vessel table
                cursor.execute("""
                    INSERT INTO Vessel (date, vessel_name, cargo, daily_rate, quantity, client_name, factory)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, data['date'], data['vessel_name'], data['cargo'], data['daily_rate'], 
                data['quantity'], data['client_name'], data['factory'])

                # Insert into Warehouse table
                cursor.execute("""
                    INSERT INTO Warehouse (client, factory, cargo, quantity2, place)
                    VALUES (?, ?, ?, ?, ?)
                """, data['client'], data['factory_warehouse'], data['cargo_warehouse'], 
                data['quantity2'], data['place'])
                
                conn.commit()
                message = "Data added successfully."

                # Calculate daily need
                total_quantity = float(data['quantity'])
                warehouse_quantity = float(data['quantity2'])
                days_until_trip = (parsed_date - datetime.datetime.now()).days

                if days_until_trip > 0:
                    daily_need = (total_quantity - warehouse_quantity) / days_until_trip
                else:
                    message = "Trip date must be in the future."

            except Exception as e:
                message = f"Error: {e}"
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        else:
            message = "There were errors in the form submission."

    # Render the form and tables
    return render_template_string("""
        <form method="POST">
            Date: <input type="date" name="date" required><br>
            Vessel Name: <input type="text" name="vessel_name" required><br>
            Cargo: <input type="text" name="cargo" required><br>
            Daily Rate: <input type="number" step="0.01" name="daily_rate" required><br>
            Quantity: <input type="number" step="0.01" name="quantity" required><br>
            Client Name: <input type="text" name="client_name" required><br>
            Factory: <input type="text" name="factory" required><br>
            Client (Warehouse): <input type="text" name="client" required><br>
            Factory (Warehouse): <input type="text" name="factory_warehouse" required><br>
            Cargo (Warehouse): <input type="text" name="cargo_warehouse" required><br>
            Quantity2 (Warehouse): <input type="number" step="0.01" name="quantity2" required><br>
            Place (Warehouse): <input type="text" name="place" required><br>
            <input type="submit" value="Submit">
        </form>
        {% if message %}<p>{{ message }}</p>{% endif %}
        {% if daily_need is not none %}<p>Daily Need: {{ daily_need }}</p>{% endif %}
        {% if errors %}<p style="color:red;">{{ errors|tojson }}</p>{% endif %}

        <h2>Vessel Data</h2>
        <table border="1">
            <tr>
                <th>ID</th>
                <th>Date</th>
                <th>Vessel Name</th>
                <th>Cargo</th>
                <th>Daily Rate</th>
                <th>Quantity</th>
                <th>Client Name</th>
                <th>Factory</th>
            </tr>
            {% for vessel in vessels %}
            <tr>
                <td>{{ vessel[0] }}</td>
                <td>{{ vessel[1] }}</td>
                <td>{{ vessel[2] }}</td>
                <td>{{ vessel[3] }}</td>
                <td>{{ vessel[4] }}</td>
                <td>{{ vessel[5] }}</td>
                <td>{{ vessel[6] }}</td>
                <td>{{ vessel[7] }}</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Warehouse Data</h2>
        <table border="1">
            <tr>
                <th>ID</th>
                <th>Client</th>
                <th>Factory</th>
                <th>Cargo</th>
                <th>Quantity2</th>
                <th>Place</th>
            </tr>
            {% for warehouse in warehouses %}
            <tr>
                <td>{{ warehouse[0] }}</td>
                <td>{{ warehouse[1] }}</td>
                <td>{{ warehouse[2] }}</td>
                <td>{{ warehouse[3] }}</td>
                <td>{{ warehouse[4] }}</td>
                <td>{{ warehouse[5] }}</td>
            </tr>
            {% endfor %}
        </table>
    """, message=message, daily_need=daily_need, errors=errors, vessels=vessels, warehouses=warehouses)

if __name__ == '__main__':
    create_tables()  # Create tables if they don't exist
    app.run(debug=True)


