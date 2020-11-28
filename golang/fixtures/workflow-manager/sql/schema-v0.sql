/*
CREATE DATABASE workflow_store;
*/

CREATE TABLE workflows(
  id TEXT NOT NULL UNIQUE,
  deployment_id TEXT NOT NULL,
  dsl TEXT NOT NULL,
  PRIMARY KEY (id, deployment_id)
);

CREATE TABLE workflow_runs(
  id TEXT NOT NULL,
  workflow_id TEXT NOT NULL,
  PRIMARY KEY (id, workflow_id),
  FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
