DO $$
BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='faro_exp_reader') THEN
  CREATE ROLE faro_exp_reader NOLOGIN;
 END IF;
END $$;
GRANT USAGE ON SCHEMA faro_exp TO faro_exp_reader;
GRANT SELECT ON faro_exp.decisions TO faro_exp_reader;
