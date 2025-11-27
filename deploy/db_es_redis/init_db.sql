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
    currency VARCHAR(255) NOT NULL DEFAULT 'USD',
    stock INTEGER NOT NULL,
    merchant_id INTEGER REFERENCES merchant(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_sku ON product(sku);
CREATE INDEX IF NOT EXISTS idx_product_updated_at ON product(updated_at);
CREATE INDEX IF NOT EXISTS idx_product_merchant_id ON product(merchant_id);

CREATE OR REPLACE FUNCTION update_product_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for product
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
    context_id VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    total_amount DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(255) NOT NULL DEFAULT 'USD',
    status order_status_enum NOT NULL DEFAULT 'PENDING',
    note VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_order_context_id ON "order"(context_id);

-- ==============================================
-- Table: order_item
-- Description: Order line items - represents individual products in an order
-- ==============================================
CREATE TABLE IF NOT EXISTS order_item (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES "order"(id) ON DELETE CASCADE,
    product_sku VARCHAR(255) NOT NULL REFERENCES product(sku),
    product_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(18, 2) NOT NULL,
    currency VARCHAR(255) NOT NULL DEFAULT 'USD'
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

-- Insert sample users
-- Password for both users: 'password123' (hashed with bcrypt)
INSERT INTO "user" (username, email, full_name, hashed_password, role) VALUES
    ('admin', 'admin@example.com', 'System Administrator', '$2b$12$KIXxPz7VFjakaZPiQ6KVWO2Y.A8LWrEwLmY0yJQp9EfGJO78KKJmS', 'admin'),
    ('testuser', 'test@example.com', 'Test User', '$2b$12$KIXxPz7VFjakaZPiQ6KVWO2Y.A8LWrEwLmY0yJQp9EfGJO78KKJmS', 'user')
ON CONFLICT (username) DO NOTHING;
