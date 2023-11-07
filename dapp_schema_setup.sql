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
