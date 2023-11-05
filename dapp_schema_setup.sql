CREATE SCHEMA dapp;

CREATE TABLE dapp.addresses (
    address_id SERIAL PRIMARY KEY,
    address VARCHAR(255) UNIQUE
);

CREATE TABLE dapp.streamable_erc20s (
    token_id SERIAL PRIMARY KEY,
    address_id INT UNIQUE REFERENCES dapp.addresses(address_id),
    is_pair BOOLEAN DEFAULT FALSE,
    total_supply VARCHAR(255),
    pair_token_0 INT REFERENCES dapp.streamable_erc20s(token_id),
    pair_token_1 INT REFERENCES dapp.streamable_erc20s(token_id)
);

CREATE TABLE dapp.balance (
    balance_id SERIAL PRIMARY KEY,
    address_id INT REFERENCES dapp.addresses(address_id),
    token_id INT REFERENCES dapp.streamable_erc20s(token_id),
    amount VARCHAR(255)
);

CREATE TABLE dapp.streams (
    stream_id VARCHAR(255) PRIMARY KEY,
    from_address_id INT REFERENCES dapp.addresses(address_id),
    to_address_id INT REFERENCES dapp.addresses(address_id),
    token_id INT REFERENCES dapp.streamable_erc20s(token_id),
    amount VARCHAR(255),
    start INT,
    duration INT,
    executed BOOLEAN DEFAULT FALSE,
    parent_id VARCHAR(255)
);

CREATE TABLE dapp.cursors (
    cursor_id SERIAL PRIMARY KEY,
    cursor VARCHAR(255) UNIQUE
);

ALTER TABLE dapp.balance ADD CONSTRAINT balance_address_token_unique UNIQUE (address_id, token_id);

-- The following is just for testing/benchmarking purposes

-- Step 1: Add time column to inputs, notices, and reports tables

ALTER TABLE public.inputs ADD COLUMN time bigint;
ALTER TABLE public.notices ADD COLUMN time bigint;
ALTER TABLE public.reports ADD COLUMN time bigint;

-- Step 2: Create trigger function to set time column in milliseconds

CREATE OR REPLACE FUNCTION set_time_milliseconds()
RETURNS TRIGGER AS $$
BEGIN
    NEW.time := EXTRACT(EPOCH FROM CURRENT_TIMESTAMP) * 1000; -- Multiply by 1000 to convert seconds to milliseconds
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 3: Create triggers to set time column for each of the tables

CREATE TRIGGER set_time_inputs
BEFORE INSERT ON public.inputs
FOR EACH ROW
EXECUTE FUNCTION set_time_milliseconds();

CREATE TRIGGER set_time_notices
BEFORE INSERT ON public.notices
FOR EACH ROW
EXECUTE FUNCTION set_time_milliseconds();

CREATE TRIGGER set_time_reports
BEFORE INSERT ON public.reports
FOR EACH ROW
EXECUTE FUNCTION set_time_milliseconds();
