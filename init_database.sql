
DROP DATABASE IF EXISTS pet_care_system;
CREATE DATABASE pet_care_system;
\c pet_care_system


CREATE TABLE "User" (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(50) NOT NULL CHECK (role IN ('Pet Owner', 'Veterinarian', 'Pet Sitter', 'Pet Shop Manager')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE Pet (
    pet_id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    species VARCHAR(50) NOT NULL CHECK (species IN ('Dog', 'Cat', 'Bird', 'Rabbit', 'Hamster', 'Other')),
    breed VARCHAR(100),
    birth_date DATE,
    weight DECIMAL(5,2),
    gender VARCHAR(10) CHECK (gender IN ('Male', 'Female', 'Unknown')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Veterinarian (
    vet_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
    clinic_name VARCHAR(200) NOT NULL,
    specialty VARCHAR(100),
    license_number VARCHAR(50) UNIQUE NOT NULL,
    consultation_fee DECIMAL(10,2) NOT NULL,
    available_slots INTEGER DEFAULT 10,
    avg_rating DECIMAL(3,2) DEFAULT 0.0 CHECK (avg_rating >= 0.0 AND avg_rating <= 5.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PetSitter (
    sitter_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
    hourly_rate DECIMAL(10,2) NOT NULL,
    experience_years INTEGER DEFAULT 0,
    available_pets TEXT,
    service_area VARCHAR(200),
    avg_rating DECIMAL(3,2) DEFAULT 0.0 CHECK (avg_rating >= 0.0 AND avg_rating <= 5.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE PetShop (
    shop_id SERIAL PRIMARY KEY,
    manager_id INTEGER NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
    shop_name VARCHAR(200) NOT NULL,
    location VARCHAR(300),
    business_number VARCHAR(50) UNIQUE NOT NULL,
    operating_hours VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Product (
    product_id SERIAL PRIMARY KEY,
    shop_id INTEGER NOT NULL REFERENCES PetShop(shop_id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock_quantity INTEGER DEFAULT 0 CHECK (stock_quantity >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Appointment (
    appointment_id SERIAL PRIMARY KEY,
    pet_id INTEGER NOT NULL REFERENCES Pet(pet_id) ON DELETE CASCADE,
    vet_id INTEGER NOT NULL REFERENCES Veterinarian(vet_id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Confirmed', 'Completed', 'Cancelled')),
    reason TEXT,
    cancel_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE MedicalRecord (
    record_id SERIAL PRIMARY KEY,
    pet_id INTEGER NOT NULL REFERENCES Pet(pet_id) ON DELETE CASCADE,
    vet_id INTEGER NOT NULL REFERENCES Veterinarian(vet_id) ON DELETE CASCADE,
    appointment_id INTEGER REFERENCES Appointment(appointment_id),
    diagnosis TEXT NOT NULL,
    treatment TEXT,
    prescription TEXT,
    notes TEXT,
    record_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Booking (
    booking_id SERIAL PRIMARY KEY,
    pet_id INTEGER NOT NULL REFERENCES Pet(pet_id) ON DELETE CASCADE,
    sitter_id INTEGER NOT NULL REFERENCES PetSitter(sitter_id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Confirmed', 'Completed', 'Cancelled')),
    total_hours INTEGER,
    total_fee DECIMAL(10,2),
    special_requests TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Review (
    review_id SERIAL PRIMARY KEY,
    reviewer_id INTEGER NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
    reviewee_id INTEGER NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    review_type VARCHAR(20) NOT NULL CHECK (review_type IN ('Veterinarian', 'PetSitter')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Orders (
    order_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
    shop_id INTEGER NOT NULL REFERENCES PetShop(shop_id) ON DELETE CASCADE,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending' CHECK (status IN ('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled')),
    shipping_address TEXT NOT NULL
);

CREATE TABLE OrderItem (
    item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES Orders(order_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES Product(product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price DECIMAL(10,2) NOT NULL
);

CREATE TABLE Notification (
    notification_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "User"(user_id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);




CREATE INDEX idx_product_stock ON Product(stock_quantity);
CREATE INDEX idx_product_category ON Product(category);
CREATE INDEX idx_appointment_date ON Appointment(appointment_date);
CREATE INDEX idx_appointment_vet ON Appointment(vet_id);
CREATE INDEX idx_booking_dates ON Booking(start_date, end_date);
CREATE INDEX idx_booking_sitter ON Booking(sitter_id);
CREATE INDEX idx_user_email ON "User"(email);
CREATE INDEX idx_pet_owner ON Pet(owner_id);
CREATE INDEX idx_review_reviewee ON Review(reviewee_id);



CREATE VIEW PetDashboard AS
SELECT 
    p.pet_id, p.name AS pet_name, p.species, p.breed, p.owner_id,
    a.appointment_id, a.appointment_date, a.appointment_time, a.status AS appointment_status,
    v.clinic_name, u.name AS vet_name
FROM Pet p
LEFT JOIN Appointment a ON p.pet_id = a.pet_id AND a.status IN ('Pending', 'Confirmed')
LEFT JOIN Veterinarian v ON a.vet_id = v.vet_id
LEFT JOIN "User" u ON v.user_id = u.user_id;

CREATE VIEW TodayAppointments AS
SELECT 
    a.appointment_id, a.vet_id, a.appointment_time, a.status, a.reason,
    p.pet_id, p.name AS pet_name, p.species, p.breed,
    o.name AS owner_name, o.phone AS owner_phone
FROM Appointment a
JOIN Pet p ON a.pet_id = p.pet_id
JOIN "User" o ON p.owner_id = o.user_id
WHERE a.appointment_date = CURRENT_DATE
ORDER BY a.appointment_time;

CREATE VIEW SitterRatings AS
SELECT 
    ps.sitter_id, u.name AS sitter_name, ps.hourly_rate, ps.service_area,
    ps.experience_years, ps.avg_rating, COUNT(r.review_id) AS review_count
FROM PetSitter ps
JOIN "User" u ON ps.user_id = u.user_id
LEFT JOIN Review r ON u.user_id = r.reviewee_id AND r.review_type = 'PetSitter'
GROUP BY ps.sitter_id, u.name, ps.hourly_rate, ps.service_area, ps.experience_years, ps.avg_rating
HAVING ps.avg_rating >= 4.0 OR COUNT(r.review_id) = 0
ORDER BY ps.avg_rating DESC;

CREATE VIEW LowStockProducts AS
SELECT p.product_id, p.name, p.category, p.stock_quantity, p.price, s.shop_name, s.shop_id
FROM Product p
JOIN PetShop s ON p.shop_id = s.shop_id
WHERE p.stock_quantity < 10
ORDER BY p.stock_quantity;

CREATE VIEW MonthlyVetStats AS
SELECT 
    v.vet_id, u.name AS vet_name,
    DATE_TRUNC('month', a.appointment_date) AS month,
    COUNT(*) AS total_appointments,
    COUNT(CASE WHEN a.status = 'Completed' THEN 1 END) AS completed,
    COUNT(CASE WHEN a.status = 'Cancelled' THEN 1 END) AS cancelled
FROM Veterinarian v
JOIN "User" u ON v.user_id = u.user_id
JOIN Appointment a ON v.vet_id = a.vet_id
GROUP BY v.vet_id, u.name, DATE_TRUNC('month', a.appointment_date)
HAVING COUNT(*) >= 1
ORDER BY month DESC;


CREATE OR REPLACE FUNCTION update_vet_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE Veterinarian v
    SET avg_rating = (
        SELECT COALESCE(AVG(rating), 0) FROM Review r
        WHERE r.reviewee_id = v.user_id AND r.review_type = 'Veterinarian'
    )
    WHERE v.user_id = NEW.reviewee_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_vet_rating
AFTER INSERT ON Review
FOR EACH ROW WHEN (NEW.review_type = 'Veterinarian')
EXECUTE FUNCTION update_vet_rating();

CREATE OR REPLACE FUNCTION update_sitter_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE PetSitter ps
    SET avg_rating = (
        SELECT COALESCE(AVG(rating), 0) FROM Review r
        WHERE r.reviewee_id = ps.user_id AND r.review_type = 'PetSitter'
    )
    WHERE ps.user_id = NEW.reviewee_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_sitter_rating
AFTER INSERT ON Review
FOR EACH ROW WHEN (NEW.review_type = 'PetSitter')
EXECUTE FUNCTION update_sitter_rating();

CREATE OR REPLACE FUNCTION decrease_stock()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE Product SET stock_quantity = stock_quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
    IF (SELECT stock_quantity FROM Product WHERE product_id = NEW.product_id) < 0 THEN
        RAISE EXCEPTION '재고 부족: product_id=%', NEW.product_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_decrease_stock
AFTER INSERT ON OrderItem
FOR EACH ROW EXECUTE FUNCTION decrease_stock();

CREATE OR REPLACE FUNCTION restore_vet_slot()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'Cancelled' AND OLD.status != 'Cancelled' THEN
        UPDATE Veterinarian SET available_slots = available_slots + 1 WHERE vet_id = NEW.vet_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_restore_vet_slot
AFTER UPDATE ON Appointment
FOR EACH ROW EXECUTE FUNCTION restore_vet_slot();



-- 샘플 데이터 

INSERT INTO "User" (email, password_hash, name, phone, role) VALUES
('owner1@test.com', 'password123', '고대광', '010-1111-1111', 'Pet Owner'),
('owner2@test.com', 'password123', '이주인', '010-1111-2222', 'Pet Owner'),
('vet1@test.com', 'password123', '박수의', '010-2222-1111', 'Veterinarian'),
('vet2@test.com', 'password123', '최동물', '010-2222-2222', 'Veterinarian'),
('sitter1@test.com', 'password123', '정돌봄', '010-3333-1111', 'Pet Sitter'),
('sitter2@test.com', 'password123', '한케어', '010-3333-2222', 'Pet Sitter'),
('shop1@test.com', 'password123', '송펫샵', '010-4444-1111', 'Pet Shop Manager'),
('shop2@test.com', 'password123', '윤용품', '010-4444-2222', 'Pet Shop Manager');

INSERT INTO Veterinarian (user_id, clinic_name, specialty, license_number, consultation_fee, available_slots) VALUES
(3, '사랑동물병원', '일반진료', 'VET-2024-001', 50000, 10),
(4, '행복동물의료센터', '외과', 'VET-2024-002', 70000, 8);

INSERT INTO PetSitter (user_id, hourly_rate, experience_years, available_pets, service_area) VALUES
(5, 15000, 3, 'Dog, Cat', '부산 금정구'),
(6, 20000, 5, 'Dog, Cat, Bird', '부산 연제구');

INSERT INTO PetShop (manager_id, shop_name, location, business_number, operating_hours) VALUES
(7, '해피펫', '부산 연제구 연산동', '123-45-67890', '09:00-21:00'),
(8, '펫프렌즈', '부산 동래구 수안동', '234-56-78901', '10:00-22:00');

INSERT INTO Pet (owner_id, name, species, breed, birth_date, weight, gender) VALUES
(1, '멍멍이', 'Dog', '골든리트리버', '2022-03-15', 28.5, 'Male'),
(1, '야옹이', 'Cat', '페르시안', '2021-07-20', 4.2, 'Female'),
(2, '초코', 'Dog', '푸들', '2023-01-10', 5.5, 'Male'),
(2, '나비', 'Cat', '러시안블루', '2022-11-05', 3.8, 'Female');

INSERT INTO Product (shop_id, name, category, description, price, stock_quantity) VALUES
(1, '프리미엄 강아지 사료 5kg', '사료', '영양가 높은 프리미엄 사료', 45000, 50),
(1, '고양이 캣타워 3단', '용품', '튼튼한 3단 캣타워', 89000, 15),
(1, '강아지 장난감 세트', '장난감', '다양한 장난감 5종 세트', 25000, 100),
(2, '유기농 고양이 사료 3kg', '사료', '유기농 원료 사용', 38000, 30),
(2, '반려동물 이동장', '용품', '통풍이 잘되는 이동장', 55000, 20),
(2, '고양이 스크래처', '용품', '천연 마 재질', 18000, 8);

INSERT INTO Appointment (pet_id, vet_id, appointment_date, appointment_time, status, reason) VALUES
(1, 1, CURRENT_DATE, '10:00', 'Confirmed', '정기검진'),
(2, 1, CURRENT_DATE, '11:00', 'Pending', '예방접종'),
(3, 2, CURRENT_DATE + 1, '14:00', 'Confirmed', '피부질환 상담');

INSERT INTO Booking (pet_id, sitter_id, start_date, end_date, status, total_hours, total_fee, special_requests) VALUES
(1, 1, CURRENT_DATE + 7, CURRENT_DATE + 9, 'Confirmed', 48, 720000, '산책 하루 2회'),
(3, 2, CURRENT_DATE + 14, CURRENT_DATE + 15, 'Pending', 24, 480000, NULL);

INSERT INTO Review (reviewer_id, reviewee_id, rating, comment, review_type) VALUES
(1, 3, 5, '친절하고 꼼꼼하게 진료해주셨습니다.', 'Veterinarian'),
(2, 3, 4, '설명을 잘 해주셔서 좋았어요.', 'Veterinarian'),
(1, 5, 5, '강아지를 정말 잘 돌봐주셨어요!', 'PetSitter');

SELECT '데이터베이스 초기화 완료!' AS status;
