from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432'),
    'database': os.environ.get('DB_NAME', 'pet_care_system'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', '')
}

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def query(sql, params=None, fetch_one=False):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(sql, params or ())
        conn.commit()
        if fetch_one:
            return cur.fetchone()
        return cur.fetchall()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

def execute(sql, params=None):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = query(
            'SELECT user_id, email, name, role FROM "User" WHERE email = %s AND password_hash = %s',
            (email, password), fetch_one=True
        )
        
        if user:
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['role'] = user['role']
            execute('UPDATE "User" SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s', (user['user_id'],))
            return redirect(url_for('dashboard'))
        
        flash('이메일 또는 비밀번호가 올바르지 않습니다.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')
        role = request.form.get('role')
        
        try:
            result = query(
                '''INSERT INTO "User" (email, password_hash, name, phone, role)
                   VALUES (%s, %s, %s, %s, %s) RETURNING user_id''',
                (email, password, name, phone, role), fetch_one=True
            )
            user_id = result['user_id']
            
            if role == 'Veterinarian':
                clinic = request.form.get('clinic_name')
                specialty = request.form.get('specialty')
                license_num = request.form.get('license_number')
                fee = request.form.get('consultation_fee') or 30000
                execute(
                    '''INSERT INTO Veterinarian (user_id, clinic_name, specialty, license_number, consultation_fee)
                       VALUES (%s, %s, %s, %s, %s)''',
                    (user_id, clinic, specialty, license_num, fee)
                )
            elif role == 'Pet Sitter':
                hourly = request.form.get('hourly_rate') or 15000
                exp = request.form.get('experience_years') or 0
                pets = request.form.get('available_pets')
                area = request.form.get('service_area')
                execute(
                    '''INSERT INTO PetSitter (user_id, hourly_rate, experience_years, available_pets, service_area)
                       VALUES (%s, %s, %s, %s, %s)''',
                    (user_id, hourly, exp, pets, area)
                )
            elif role == 'Pet Shop Manager':
                shop_name = request.form.get('shop_name')
                location = request.form.get('location')
                biz_num = request.form.get('business_number')
                hours = request.form.get('operating_hours')
                execute(
                    '''INSERT INTO PetShop (manager_id, shop_name, location, business_number, operating_hours)
                       VALUES (%s, %s, %s, %s, %s)''',
                    (user_id, shop_name, location, biz_num, hours)
                )
            
            flash('회원가입이 완료되었습니다. 로그인해주세요.')
            return redirect(url_for('login'))
        except Exception as e:
            flash('회원가입에 실패했습니다. 이미 사용 중인 이메일일 수 있습니다.')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    role = session['role']
    
    if role == 'Pet Owner':
        pets = query('SELECT * FROM Pet WHERE owner_id = %s', (session['user_id'],))
        appointments = query('''
            SELECT a.*, p.name as pet_name, u.name as vet_name, v.clinic_name
            FROM Appointment a
            JOIN Pet p ON a.pet_id = p.pet_id
            JOIN Veterinarian v ON a.vet_id = v.vet_id
            JOIN "User" u ON v.user_id = u.user_id
            WHERE p.owner_id = %s
            ORDER BY a.appointment_date DESC LIMIT 5
        ''', (session['user_id'],))
        return render_template('dashboard_owner.html', pets=pets, appointments=appointments)
    
    elif role == 'Veterinarian':
        vet = query('SELECT vet_id FROM Veterinarian WHERE user_id = %s', (session['user_id'],), fetch_one=True)
        if vet:
            appointments = query('''
                SELECT a.*, p.name as pet_name, p.species, u.name as owner_name, u.phone as owner_phone
                FROM Appointment a
                JOIN Pet p ON a.pet_id = p.pet_id
                JOIN "User" u ON p.owner_id = u.user_id
                WHERE a.vet_id = %s AND a.appointment_date = CURRENT_DATE
                ORDER BY a.appointment_time
            ''', (vet['vet_id'],))
            return render_template('dashboard_vet.html', appointments=appointments, vet_id=vet['vet_id'])
        return render_template('dashboard_vet.html', appointments=[], vet_id=None)
    
    elif role == 'Pet Sitter':
        sitter = query('SELECT sitter_id FROM PetSitter WHERE user_id = %s', (session['user_id'],), fetch_one=True)
        if sitter:
            bookings = query('''
                SELECT b.*, p.name as pet_name, p.species, u.name as owner_name
                FROM Booking b
                JOIN Pet p ON b.pet_id = p.pet_id
                JOIN "User" u ON p.owner_id = u.user_id
                WHERE b.sitter_id = %s AND b.status IN ('Pending', 'Confirmed')
                ORDER BY b.start_date
            ''', (sitter['sitter_id'],))
            return render_template('dashboard_sitter.html', bookings=bookings, sitter_id=sitter['sitter_id'])
        return render_template('dashboard_sitter.html', bookings=[], sitter_id=None)
    
    elif role == 'Pet Shop Manager':
        shop = query('SELECT shop_id, shop_name FROM PetShop WHERE manager_id = %s', (session['user_id'],), fetch_one=True)
        if shop:
            products = query('SELECT * FROM Product WHERE shop_id = %s ORDER BY category', (shop['shop_id'],))
            orders = query('''
                SELECT o.*, u.name as buyer_name
                FROM Orders o
                JOIN "User" u ON o.user_id = u.user_id
                WHERE o.shop_id = %s
                ORDER BY o.order_date DESC LIMIT 10
            ''', (shop['shop_id'],))
            return render_template('dashboard_shop.html', shop=shop, products=products, orders=orders)
        return render_template('dashboard_shop.html', shop=None, products=[], orders=[])
    
    return redirect(url_for('index'))

@app.route('/pets')
def pets():
    if 'user_id' not in session or session['role'] != 'Pet Owner':
        return redirect(url_for('login'))
    
    pets = query('SELECT * FROM Pet WHERE owner_id = %s ORDER BY created_at DESC', (session['user_id'],))
    return render_template('pets.html', pets=pets)

@app.route('/pets/add', methods=['GET', 'POST'])
def add_pet():
    if 'user_id' not in session or session['role'] != 'Pet Owner':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        species = request.form.get('species')
        breed = request.form.get('breed') or None
        birth_date = request.form.get('birth_date') or None
        weight = request.form.get('weight') or None
        gender = request.form.get('gender')
        
        try:
            execute('''
                INSERT INTO Pet (owner_id, name, species, breed, birth_date, weight, gender)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (session['user_id'], name, species, breed, birth_date, weight, gender))
            flash('반려동물이 등록되었습니다.')
            return redirect(url_for('pets'))
        except Exception as e:
            flash('등록에 실패했습니다.')
    
    return render_template('add_pet.html')

@app.route('/vets')
def vets():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    vets = query('''
        SELECT v.*, u.name as vet_name
        FROM Veterinarian v
        JOIN "User" u ON v.user_id = u.user_id
        WHERE v.available_slots > 0
        ORDER BY v.avg_rating DESC
    ''')
    return render_template('vets.html', vets=vets)

@app.route('/appointment/book/<int:vet_id>', methods=['GET', 'POST'])
def book_appointment(vet_id):
    if 'user_id' not in session or session['role'] != 'Pet Owner':
        return redirect(url_for('login'))
    
    pets = query('SELECT * FROM Pet WHERE owner_id = %s', (session['user_id'],))
    vet = query('''
        SELECT v.*, u.name as vet_name
        FROM Veterinarian v
        JOIN "User" u ON v.user_id = u.user_id
        WHERE v.vet_id = %s
    ''', (vet_id,), fetch_one=True)
    
    if request.method == 'POST':
        pet_id = request.form.get('pet_id')
        date = request.form.get('date')
        time = request.form.get('time')
        reason = request.form.get('reason')
        
        try:
            execute('''
                INSERT INTO Appointment (pet_id, vet_id, appointment_date, appointment_time, reason)
                VALUES (%s, %s, %s, %s, %s)
            ''', (pet_id, vet_id, date, time, reason))
            execute('UPDATE Veterinarian SET available_slots = available_slots - 1 WHERE vet_id = %s', (vet_id,))
            flash('예약이 완료되었습니다.')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('예약에 실패했습니다.')
    
    return render_template('book_appointment.html', pets=pets, vet=vet)

@app.route('/appointment/status/<int:appointment_id>/<status>')
def update_appointment(appointment_id, status):
    if 'user_id' not in session or session['role'] != 'Veterinarian':
        return redirect(url_for('login'))
    
    if status in ['Confirmed', 'Completed', 'Cancelled']:
        execute('UPDATE Appointment SET status = %s WHERE appointment_id = %s', (status, appointment_id))
        if status == 'Cancelled':
            appt = query('SELECT vet_id FROM Appointment WHERE appointment_id = %s', (appointment_id,), fetch_one=True)
            if appt:
                execute('UPDATE Veterinarian SET available_slots = available_slots + 1 WHERE vet_id = %s', (appt['vet_id'],))
        flash('예약 상태가 변경되었습니다.')
    
    return redirect(url_for('dashboard'))

@app.route('/medical-record/add/<int:appointment_id>', methods=['GET', 'POST'])
def add_medical_record(appointment_id):
    if 'user_id' not in session or session['role'] != 'Veterinarian':
        return redirect(url_for('login'))
    
    vet = query('SELECT vet_id FROM Veterinarian WHERE user_id = %s', (session['user_id'],), fetch_one=True)
    appt = query('''
        SELECT a.*, p.name as pet_name, p.pet_id
        FROM Appointment a
        JOIN Pet p ON a.pet_id = p.pet_id
        WHERE a.appointment_id = %s
    ''', (appointment_id,), fetch_one=True)
    
    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        treatment = request.form.get('treatment')
        prescription = request.form.get('prescription')
        notes = request.form.get('notes')
        
        try:
            execute('''
                INSERT INTO MedicalRecord (pet_id, vet_id, appointment_id, diagnosis, treatment, prescription, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (appt['pet_id'], vet['vet_id'], appointment_id, diagnosis, treatment, prescription, notes))
            flash('진료 기록이 저장되었습니다.')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('저장에 실패했습니다.')
    
    return render_template('add_medical_record.html', appt=appt)

@app.route('/sitters')
def sitters():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    sitters = query('''
        SELECT ps.*, u.name as sitter_name
        FROM PetSitter ps
        JOIN "User" u ON ps.user_id = u.user_id
        ORDER BY ps.avg_rating DESC
    ''')
    return render_template('sitters.html', sitters=sitters)

@app.route('/booking/book/<int:sitter_id>', methods=['GET', 'POST'])
def book_sitter(sitter_id):
    if 'user_id' not in session or session['role'] != 'Pet Owner':
        return redirect(url_for('login'))
    
    pets = query('SELECT * FROM Pet WHERE owner_id = %s', (session['user_id'],))
    sitter = query('''
        SELECT ps.*, u.name as sitter_name
        FROM PetSitter ps
        JOIN "User" u ON ps.user_id = u.user_id
        WHERE ps.sitter_id = %s
    ''', (sitter_id,), fetch_one=True)
    
    if request.method == 'POST':
        pet_id = request.form.get('pet_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        hours = int(request.form.get('hours'))
        requests_text = request.form.get('requests')
        total_fee = float(sitter['hourly_rate']) * hours
        
        try:
            execute('''
                INSERT INTO Booking (pet_id, sitter_id, start_date, end_date, total_hours, total_fee, special_requests)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (pet_id, sitter_id, start_date, end_date, hours, total_fee, requests_text))
            flash('예약 신청이 완료되었습니다.')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('예약에 실패했습니다.')
    
    return render_template('book_sitter.html', pets=pets, sitter=sitter)

@app.route('/booking/status/<int:booking_id>/<status>')
def update_booking(booking_id, status):
    if 'user_id' not in session or session['role'] != 'Pet Sitter':
        return redirect(url_for('login'))
    
    if status in ['Confirmed', 'Completed', 'Cancelled']:
        execute('UPDATE Booking SET status = %s WHERE booking_id = %s', (status, booking_id))
        flash('예약 상태가 변경되었습니다.')
    
    return redirect(url_for('dashboard'))

@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    category = request.args.get('category')
    if category:
        products = query('''
            SELECT p.*, s.shop_name
            FROM Product p
            JOIN PetShop s ON p.shop_id = s.shop_id
            WHERE p.category = %s AND p.stock_quantity > 0
            ORDER BY p.price
        ''', (category,))
    else:
        products = query('''
            SELECT p.*, s.shop_name
            FROM Product p
            JOIN PetShop s ON p.shop_id = s.shop_id
            WHERE p.stock_quantity > 0
            ORDER BY p.category, p.price
        ''')
    return render_template('products.html', products=products)

@app.route('/order/<int:product_id>', methods=['GET', 'POST'])
def order_product(product_id):
    if 'user_id' not in session or session['role'] != 'Pet Owner':
        return redirect(url_for('login'))
    
    product = query('SELECT p.*, s.shop_name FROM Product p JOIN PetShop s ON p.shop_id = s.shop_id WHERE p.product_id = %s', (product_id,), fetch_one=True)
    
    if request.method == 'POST':
        quantity = int(request.form.get('quantity'))
        address = request.form.get('address')
        
        if quantity > product['stock_quantity']:
            flash('재고가 부족합니다.')
            return redirect(url_for('order_product', product_id=product_id))
        
        total = float(product['price']) * quantity
        
        try:
            order = query('''
                INSERT INTO Orders (user_id, shop_id, total_amount, shipping_address)
                VALUES (%s, %s, %s, %s) RETURNING order_id
            ''', (session['user_id'], product['shop_id'], total, address), fetch_one=True)
            
            execute('''
                INSERT INTO OrderItem (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            ''', (order['order_id'], product_id, quantity, product['price']))
            
            flash('주문이 완료되었습니다.')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('주문에 실패했습니다.')
    
    return render_template('order_product.html', product=product)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session or session['role'] != 'Pet Shop Manager':
        return redirect(url_for('login'))
    
    shop = query('SELECT shop_id FROM PetShop WHERE manager_id = %s', (session['user_id'],), fetch_one=True)
    
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        price = request.form.get('price')
        stock = request.form.get('stock')
        
        try:
            execute('''
                INSERT INTO Product (shop_id, name, category, description, price, stock_quantity)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (shop['shop_id'], name, category, description, price, stock))
            flash('상품이 등록되었습니다.')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('등록에 실패했습니다.')
    
    return render_template('add_product.html')

@app.route('/order/status/<int:order_id>/<status>')
def update_order(order_id, status):
    if 'user_id' not in session or session['role'] != 'Pet Shop Manager':
        return redirect(url_for('login'))
    
    if status in ['Processing', 'Shipped', 'Delivered', 'Cancelled']:
        if status == 'Cancelled':
            items = query('SELECT product_id, quantity FROM OrderItem WHERE order_id = %s', (order_id,))
            for item in items:
                execute('UPDATE Product SET stock_quantity = stock_quantity + %s WHERE product_id = %s',
                       (item['quantity'], item['product_id']))
        execute('UPDATE Orders SET status = %s WHERE order_id = %s', (status, order_id))
        flash('주문 상태가 변경되었습니다.')
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
