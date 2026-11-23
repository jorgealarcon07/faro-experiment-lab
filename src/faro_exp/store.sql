CREATE SCHEMA IF NOT EXISTS faro_exp;
CREATE TABLE IF NOT EXISTS faro_exp.experiment (
 experiment_id text PRIMARY KEY, enrollment_hash text NOT NULL, protocol_hash text NOT NULL, seed bigint NOT NULL
);
CREATE TABLE IF NOT EXISTS faro_exp.account (
 experiment_id text REFERENCES faro_exp.experiment, account_id bigint, balance_cop integer NOT NULL,
 high_risk boolean NOT NULL, measured_at timestamptz NOT NULL, eligible boolean NOT NULL,
 PRIMARY KEY(experiment_id,account_id)
);
CREATE TABLE IF NOT EXISTS faro_exp.assignment (
 experiment_id text, account_id bigint, variant text NOT NULL CHECK(variant IN ('T','C')),
 probability double precision NOT NULL, assigned_at timestamptz NOT NULL,
 PRIMARY KEY(experiment_id,account_id), FOREIGN KEY(experiment_id,account_id) REFERENCES faro_exp.account
);
CREATE TABLE IF NOT EXISTS faro_exp.batch (
 batch_hash text PRIMARY KEY, experiment_id text REFERENCES faro_exp.experiment NOT NULL
);
CREATE TABLE IF NOT EXISTS faro_exp.recorded (
 batch_hash text REFERENCES faro_exp.batch, experiment_id text NOT NULL,account_id bigint NOT NULL,
 variant text NOT NULL,probability double precision NOT NULL,assigned_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS faro_exp.outcome (
 batch_hash text REFERENCES faro_exp.batch, experiment_id text NOT NULL, account_id bigint NOT NULL,
 paid boolean NOT NULL,complained boolean NOT NULL,window_end timestamptz NOT NULL,available_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS faro_exp.event (
 batch_hash text REFERENCES faro_exp.batch, experiment_id text NOT NULL, account_id bigint NOT NULL,event_id text NOT NULL,
 status text NOT NULL, attempted_at timestamptz NOT NULL,received_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS recorded_keys ON faro_exp.recorded(batch_hash,account_id);
CREATE INDEX IF NOT EXISTS outcome_keys ON faro_exp.outcome(batch_hash,account_id);
CREATE INDEX IF NOT EXISTS event_keys ON faro_exp.event(batch_hash,event_id);
CREATE TABLE IF NOT EXISTS faro_exp.run (
 run_id text PRIMARY KEY,experiment_id text REFERENCES faro_exp.experiment NOT NULL,
 batch_hash text REFERENCES faro_exp.batch NOT NULL,as_of timestamptz NOT NULL,
 parent_run text REFERENCES faro_exp.run,state text NOT NULL CHECK(state IN ('pending','invalid','ship','hold')),
 record jsonb NOT NULL,manifest jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE OR REPLACE VIEW faro_exp.decisions AS SELECT run_id,experiment_id,as_of,parent_run,state,record,manifest FROM faro_exp.run;
