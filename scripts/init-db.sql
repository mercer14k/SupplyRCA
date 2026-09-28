-- Public localhost demo credentials, never reuse for a network deployment.
CREATE ROLE supplyrca LOGIN PASSWORD 'local-demo-writer' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE supplyrca_reader LOGIN PASSWORD 'local-demo-reader' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE supplyrca TO supplyrca, supplyrca_reader;
GRANT USAGE, CREATE ON SCHEMA public TO supplyrca;
GRANT USAGE ON SCHEMA public TO supplyrca_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE supplyrca IN SCHEMA public GRANT SELECT ON TABLES TO supplyrca_reader;
