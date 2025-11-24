-- ==============================================
-- Database Initialization Script
-- Creates all tables for the Agent Ecosystem
-- ==============================================

-- Create ENUM types first
CREATE TYPE user_role_enum AS ENUM ('admin', 'user', 'assistant');
CREATE TYPE message_role_enum AS ENUM ('user', 'assistant', 'system');
CREATE TYPE order_status_enum AS ENUM ('PENDING', 'SUCCESS', 'PAID', 'FAILED', 'CANCELLED');

-- ==============================================
-- Table: merchant
-- Description: Stores merchant information
-- ==============================================
CREATE TABLE IF NOT EXISTS merchant (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ==============================================
-- Table: user
-- Description: Stores user account information
-- ==============================================
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    full_name VARCHAR(200),
    hashed_password VARCHAR(255) NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);

-- ==============================================
-- Table: product
-- Description: Stores product catalog
-- ==============================================
CREATE TABLE IF NOT EXISTS product (
    sku VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(5) NOT NULL DEFAULT 'USD',
    stock INTEGER NOT NULL,
    merchant_id INTEGER REFERENCES merchant(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_sku ON product(sku);
CREATE INDEX IF NOT EXISTS idx_product_updated_at ON product(updated_at);

-- Trigger function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_product_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS product_updated_at_trigger ON product;
CREATE TRIGGER product_updated_at_trigger
    BEFORE UPDATE ON product
    FOR EACH ROW
    EXECUTE FUNCTION update_product_updated_at();

-- ==============================================
-- Table: order
-- Description: Stores customer orders
-- ==============================================
CREATE TABLE IF NOT EXISTS "order" (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    product_sku VARCHAR(255) NOT NULL REFERENCES product(sku) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1,
    total_amount DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(5) NOT NULL DEFAULT 'USD',
    status order_status_enum NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ==============================================
-- Table: conversation
-- Description: Stores user conversation sessions
-- ==============================================
CREATE TABLE IF NOT EXISTS conversation (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- ==============================================
-- Table: message
-- Description: Stores messages within conversations
-- ==============================================
CREATE TABLE IF NOT EXISTS message (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    role message_role_enum NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==============================================
-- Insert sample data
-- ==============================================

-- Insert sample merchants
INSERT INTO merchant (name) VALUES 
    ('Tech Store'),
    ('Fashion Boutique'),
    ('Home & Living'),
    ('Sports World')
ON CONFLICT DO NOTHING;

-- Insert sample products (100 products)
INSERT INTO product (sku, name, price, currency, stock, merchant_id) VALUES
    ('SKU0001', 'Wireless Mouse', 15.99, 'USD', 120, 1),
    ('SKU0002', 'Mechanical Keyboard', 45.50, 'USD', 60, 1),
    ('SKU0003', 'HD Monitor 24 inch', 129.99, 'USD', 30, 1),
    ('SKU0004', 'USB-C Charger', 18.75, 'USD', 200, 1),
    ('SKU0005', 'Bluetooth Headphones', 59.90, 'USD', 80, 1),
    ('SKU0006', 'Gaming Laptop', 999.00, 'USD', 12, 1),
    ('SKU0007', 'Smartphone Stand', 9.99, 'USD', 150, 1),
    ('SKU0008', 'Portable SSD 1TB', 110.00, 'USD', 45, 1),
    ('SKU0009', 'Webcam 1080p', 39.95, 'USD', 72, 1),
    ('SKU0010', 'Wireless Earbuds', 69.90, 'USD', 95, 1),
    ('SKU0011', 'Cotton T-Shirt', 12.99, 'USD', 300, 2),
    ('SKU0012', 'Blue Jeans', 35.00, 'USD', 120, 2),
    ('SKU0013', 'Leather Jacket', 150.00, 'USD', 25, 2),
    ('SKU0014', 'Sneakers White', 59.99, 'USD', 80, 2),
    ('SKU0015', 'Running Shoes', 75.00, 'USD', 64, 2),
    ('SKU0016', 'Wool Sweater', 42.50, 'USD', 47, 2),
    ('SKU0017', 'Summer Dress', 39.99, 'USD', 51, 2),
    ('SKU0018', 'Formal Shirt', 29.00, 'USD', 100, 2),
    ('SKU0019', 'Baseball Cap', 15.00, 'USD', 180, 2),
    ('SKU0020', 'Sports Jacket', 95.00, 'USD', 36, 2),
    ('SKU0021', 'Wooden Dining Table', 450.00, 'USD', 10, 3),
    ('SKU0022', 'Office Chair', 120.00, 'USD', 22, 3),
    ('SKU0023', 'Bookshelf 5-tier', 80.00, 'USD', 40, 3),
    ('SKU0024', 'Coffee Table', 65.00, 'USD', 28, 3),
    ('SKU0025', 'Bed Frame Queen', 350.00, 'USD', 15, 3),
    ('SKU0026', 'Nightstand Lamp', 32.00, 'USD', 50, 3),
    ('SKU0027', 'Sofa 3-Seater', 699.00, 'USD', 8, 3),
    ('SKU0028', 'Wardrobe 2-Door', 250.00, 'USD', 12, 3),
    ('SKU0029', 'Office Desk', 140.00, 'USD', 18, 3),
    ('SKU0030', 'Recliner Chair', 220.00, 'USD', 9, 3),
    ('SKU0031', 'Cooking Pan Set', 59.00, 'USD', 70, 3),
    ('SKU0032', 'Stainless Steel Knife Set', 49.50, 'USD', 90, 3),
    ('SKU0033', 'Microwave Oven', 120.00, 'USD', 25, 3),
    ('SKU0034', 'Blender 600W', 45.00, 'USD', 60, 3),
    ('SKU0035', 'Air Fryer', 89.99, 'USD', 40, 3),
    ('SKU0036', 'Rice Cooker', 75.00, 'USD', 33, 3),
    ('SKU0037', 'Electric Kettle', 25.00, 'USD', 110, 3),
    ('SKU0038', 'Toaster 4-Slice', 39.99, 'USD', 52, 3),
    ('SKU0039', 'Refrigerator 300L', 499.00, 'USD', 7, 3),
    ('SKU0040', 'Dishwasher', 650.00, 'USD', 5, 3),
    ('SKU0041', 'Novel - The Great Escape', 14.99, 'USD', 75, 1),
    ('SKU0042', 'Science Fiction - Galaxy Wars', 19.50, 'USD', 60, 1),
    ('SKU0043', 'Cookbook - Easy Meals', 22.00, 'USD', 45, 1),
    ('SKU0044', 'Biography - Steve Jobs', 18.90, 'USD', 90, 1),
    ('SKU0045', 'Self-help - Atomic Habits', 20.00, 'USD', 120, 1),
    ('SKU0046', 'Fantasy - Dragon Realm', 25.00, 'USD', 32, 1),
    ('SKU0047', 'Children Book - ABC Fun', 9.99, 'USD', 200, 1),
    ('SKU0048', 'Thriller - Dark Woods', 17.00, 'USD', 54, 1),
    ('SKU0049', 'Romance - Love in Paris', 15.50, 'USD', 65, 1),
    ('SKU0050', 'History - Ancient Empires', 24.00, 'USD', 40, 1),
    ('SKU0051', 'Toy Car Set', 12.00, 'USD', 180, 1),
    ('SKU0052', 'Building Blocks 100 pcs', 29.90, 'USD', 95, 1),
    ('SKU0053', 'Doll House', 45.00, 'USD', 36, 1),
    ('SKU0054', 'Puzzle 1000 Pieces', 20.00, 'USD', 74, 1),
    ('SKU0055', 'Action Figure - Hero X', 15.00, 'USD', 112, 1),
    ('SKU0056', 'Board Game - Strategy Quest', 39.00, 'USD', 43, 1),
    ('SKU0057', 'Stuffed Animal Bear', 18.50, 'USD', 134, 1),
    ('SKU0058', 'Remote Control Drone', 120.00, 'USD', 21, 1),
    ('SKU0059', 'Rubik Cube', 9.50, 'USD', 160, 1),
    ('SKU0060', 'Play Tent', 35.00, 'USD', 55, 1),
    ('SKU0061', 'Chocolate Box 500g', 15.00, 'USD', 140, 1),
    ('SKU0062', 'Organic Honey 1L', 20.00, 'USD', 80, 1),
    ('SKU0063', 'Green Tea Pack 200g', 12.00, 'USD', 95, 1),
    ('SKU0064', 'Coffee Beans 1kg', 25.00, 'USD', 70, 1),
    ('SKU0065', 'Olive Oil 750ml', 18.00, 'USD', 88, 1),
    ('SKU0066', 'Pasta Pack 1kg', 5.00, 'USD', 200, 1),
    ('SKU0067', 'Cereal Box 400g', 7.50, 'USD', 150, 1),
    ('SKU0068', 'Bottled Water 24-pack', 8.99, 'USD', 250, 1),
    ('SKU0069', 'Protein Powder 2kg', 55.00, 'USD', 48, 1),
    ('SKU0070', 'Almonds 500g', 14.00, 'USD', 92, 1),
    ('SKU0071', 'Shampoo 500ml', 9.90, 'USD', 140, 1),
    ('SKU0072', 'Conditioner 500ml', 10.50, 'USD', 120, 1),
    ('SKU0073', 'Face Cream 50ml', 25.00, 'USD', 60, 1),
    ('SKU0074', 'Perfume - Rose Scent', 45.00, 'USD', 33, 1),
    ('SKU0075', 'Lipstick Red', 15.00, 'USD', 90, 1),
    ('SKU0076', 'Hand Sanitizer 250ml', 4.99, 'USD', 300, 1),
    ('SKU0077', 'Hair Dryer 2000W', 29.90, 'USD', 50, 1),
    ('SKU00078', 'Electric Toothbrush', 55.00, 'USD', 42, 1),
    ('SKU0079', 'Body Lotion 400ml', 12.50, 'USD', 110, 1),
    ('SKU0080', 'Sunscreen SPF50', 18.00, 'USD', 76, 1),
    ('SKU0081', 'Soccer Ball', 25.00, 'USD', 85, 4),
    ('SKU0082', 'Tennis Racket', 75.00, 'USD', 32, 4),
    ('SKU0083', 'Basketball', 29.00, 'USD', 70, 4),
    ('SKU0084', 'Yoga Mat', 20.00, 'USD', 105, 4),
    ('SKU0085', 'Dumbbell Set 20kg', 65.00, 'USD', 28, 4),
    ('SKU0086', 'Skipping Rope', 6.00, 'USD', 170, 4),
    ('SKU0087', 'Cycling Helmet', 49.00, 'USD', 37, 4),
    ('SKU0088', 'Camping Tent 4-Person', 150.00, 'USD', 15, 4),
    ('SKU0089', 'Sleeping Bag', 45.00, 'USD', 40, 4),
    ('SKU0090', 'Fishing Rod', 60.00, 'USD', 22, 4),
    ('SKU0091', 'Smartwatch', 199.00, 'USD', 34, 1),
    ('SKU0092', 'Tablet 10 inch', 320.00, 'USD', 20, 1),
    ('SKU0093', 'Portable Speaker', 55.00, 'USD', 44, 1),
    ('SKU0094', 'Fitness Tracker Band', 49.90, 'USD', 52, 1),
    ('SKU0095', 'Digital Camera', 450.00, 'USD', 18, 1),
    ('SKU0096', 'E-book Reader', 120.00, 'USD', 27, 1),
    ('SKU0097', 'VR Headset', 350.00, 'USD', 12, 1),
    ('SKU0098', 'Power Bank 20000mAh', 39.90, 'USD', 65, 1),
    ('SKU0099', 'Gaming Console', 499.00, 'USD', 9, 1),
    ('SKU0100', 'Smart TV 55 inch', 799.00, 'USD', 6, 1)
ON CONFLICT (sku) DO NOTHING;

-- Insert sample users
INSERT INTO "user" (username, email, full_name, hashed_password, role) VALUES
    ('admin', 'admin@example.com', 'System Administrator', '$2b$12$KIXxPz7VFjakaZPiQ6KVWO2Y.A8LWrEwLmY0yJQp9EfGJO78KKJmS', 'admin'),
    ('testuser', 'test@example.com', 'Test User', '$2b$12$KIXxPz7VFjakaZPiQ6KVWO2Y.A8LWrEwLmY0yJQp9EfGJO78KKJmS', 'user')
ON CONFLICT (username) DO NOTHING;

-- ==============================================
-- End of initialization script
-- ==============================================
