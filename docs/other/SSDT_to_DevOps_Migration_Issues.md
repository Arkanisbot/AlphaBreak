# SSDT to DevOps Automation — Potential Issues & Recommended Solutions

**Prepared for:** SDT & CI/CD Working Session
**Date:** April 10, 2026
**Author:** Nick Major

---

## Context

We are shifting from SSDT-based database source control and deployment to automation through DevOps scripts. This document identifies potential issues across three areas — Configuration & Implementation, Monitoring, and Troubleshooting — and proposes how to address each.

---

## 1. Configuration & Implementation

### 1.1 Schema Drift Between Environments

**Issue:** Without SSDT's dacpac-based state comparison, environments (Dev, QA, Staging, Prod) can drift apart. Manual hotfixes applied directly to Prod without going through the pipeline create schema inconsistencies that scripts won't account for.

**Recommendation:**
- Implement a drift detection step in the pipeline that compares the target database schema against the expected state before deploying
- Use tools like `SqlPackage /Action:DeployReport` or a custom schema snapshot script to generate a diff report at the start of each run
- Block deployments when unexpected drift is detected and require manual review
- Enforce a policy: no direct DDL changes to Staging or Prod outside the pipeline

---

### 1.2 Migration Script Ordering & Idempotency

**Issue:** SSDT handles dependency ordering automatically (tables before views, FKs after tables). With raw migration scripts, incorrect ordering causes deployment failures. Scripts that aren't idempotent will fail on re-run.

**Recommendation:**
- Adopt a numbered migration pattern (e.g., `V001__create_users_table.sql`, `V002__add_index.sql`) enforced by naming convention
- Require all scripts to be idempotent — wrap DDL in existence checks (`IF NOT EXISTS`, `IF COL_EXISTS`, etc.)
- Consider a lightweight migration framework (DbUp, Flyway, or Liquibase) rather than raw scripts to handle ordering, checksums, and execution tracking
- Maintain a `__migration_history` table that records which scripts have been applied

---

### 1.3 Environment-Specific Configuration

**Issue:** Connection strings, linked servers, service accounts, and security configurations differ between environments. Hard-coded values in scripts will break across environments or expose credentials.

**Recommendation:**
- Externalize all environment-specific values into pipeline variables or Azure DevOps variable groups
- Use tokenized scripts with placeholders (e.g., `#{DatabaseName}#`, `#{ServiceAccount}#`) that get replaced at deploy time
- Store secrets in Azure Key Vault or the pipeline's secure variable store — never in source control
- Create an environment manifest file per target that documents expected configuration

---

### 1.4 Permissions & Security Model

**Issue:** SSDT projects often include security objects (users, roles, permissions) in the dacpac. Moving to scripts means these can be missed, leaving new objects without proper access controls or breaking existing access.

**Recommendation:**
- Create a dedicated `security` folder in the migration scripts for role and permission management
- Run permission scripts as a separate pipeline stage after schema changes, using a high-privilege service account
- Audit permissions post-deployment with a validation query that checks expected role memberships
- Document the security model separately so it's reviewable outside of code

---

### 1.5 Data Motion & Reference Data

**Issue:** SSDT post-deployment scripts handle reference data (lookup tables, seed data). In a script-based approach, these need explicit management or they get missed during deployments.

**Recommendation:**
- Separate reference data scripts from schema migration scripts — different folders, different pipeline stages
- Use MERGE statements for reference data to handle inserts, updates, and deletes idempotently
- Version reference data independently so it can be deployed without a full schema migration
- Flag any data motion scripts that touch transactional data for mandatory DBA review

---

### 1.6 Rollback Strategy

**Issue:** SSDT dacpac deployments can be difficult to roll back, but at least the previous dacpac exists as a known-good state. With scripts, there's no automatic rollback — a failed migration can leave the database in a partially applied state.

**Recommendation:**
- Require a corresponding rollback script for every migration (`V001__create_users.sql` + `V001__rollback_create_users.sql`)
- Wrap multi-statement migrations in explicit transactions where possible
- Take a database snapshot or backup before every Prod deployment as part of the pipeline
- Define a clear rollback SOP: who decides, how fast, and what the communication chain looks like

---

### 1.7 Pipeline Agent Permissions

**Issue:** The DevOps build agent needs sufficient SQL Server permissions to deploy schema changes, but overly broad permissions create a security risk. Different environments may have different authentication methods (SQL auth vs. Windows auth vs. managed identity).

**Recommendation:**
- Use a dedicated service account per environment with least-privilege permissions scoped to DDL operations
- Prefer managed identity or Windows authentication over SQL auth where possible
- Audit and rotate service account credentials on a schedule
- Test the agent's connectivity and permissions in a pre-deployment validation step

---

## 2. Monitoring

### 2.1 Deployment Success/Failure Visibility

**Issue:** Without SSDT's Visual Studio publish feedback, teams lose visibility into what was deployed, what changed, and whether it succeeded. Failed deployments may go unnoticed.

**Recommendation:**
- Configure pipeline notifications (email, Teams/Slack) for deployment success and failure
- Generate and publish a deployment report as a pipeline artifact — include scripts executed, duration, and row counts for data changes
- Create a deployment dashboard showing recent deployments per environment, status, and who triggered them
- Log all deployments to a central `deployment_history` table with timestamp, environment, scripts applied, and result

---

### 2.2 Post-Deployment Validation

**Issue:** A deployment can succeed (all scripts run without error) but still break the application — missing indexes, broken views, invalid stored procedures, or data integrity violations.

**Recommendation:**
- Add a post-deployment validation stage that runs:
  - `sp_refreshview` on all views to catch broken dependencies
  - Schema comparison against expected state
  - Key query smoke tests (critical stored procedures execute without error)
  - Row count spot checks on critical tables
- Gate the pipeline so Prod deployments require passing validation in Staging first

---

### 2.3 Performance Regression Detection

**Issue:** Schema changes (new indexes, altered columns, changed statistics) can cause query plan regressions that aren't visible until production load hits.

**Recommendation:**
- Capture baseline query performance metrics (top 20 queries by CPU/duration) before and after deployment
- Use Query Store data to compare plan changes post-deployment
- Set up alerts for significant performance deviations (>50% regression in p95 query duration)
- Consider running a representative workload against Staging before Prod deployment

---

### 2.4 Long-Running Migration Visibility

**Issue:** Large data migrations or index rebuilds can take hours. Without visibility, teams don't know if the pipeline is stuck or working.

**Recommendation:**
- Add progress logging within long-running scripts (e.g., `RAISERROR('Processing batch %d of %d', 0, 1, @batch, @total) WITH NOWAIT`)
- Set pipeline timeouts with appropriate thresholds per environment (shorter for Dev, longer for Prod)
- For data migrations affecting millions of rows, implement batching with progress checkpoints

---

## 3. Troubleshooting

### 3.1 "Script Worked in Dev, Failed in Prod"

**Issue:** The most common deployment failure. Differences in data volume, collation, schema drift, permissions, or SQL Server version between environments.

**Recommendation:**
- Maintain a Staging environment that mirrors Prod as closely as possible (same edition, collation, approximate data volume)
- Run all migrations through the full pipeline (Dev → QA → Staging → Prod) — never skip environments
- Include environment metadata in error logs (SQL Server version, edition, collation, compatibility level)
- Create a pre-deployment checklist that validates environment parity

---

### 3.2 Partial Migration Failures

**Issue:** A migration script fails mid-execution, leaving tables in an inconsistent state. The next run may fail because objects already exist partially.

**Recommendation:**
- Wrap each migration in a transaction with TRY/CATCH and explicit ROLLBACK on failure
- For scripts that can't be fully transactional (e.g., `ALTER TABLE` with data motion), design them with checkpoint logic so they can resume
- Record script execution status in the migration history table: `pending`, `running`, `completed`, `failed`
- Provide a manual intervention playbook for each common partial failure scenario

---

### 3.3 Deadlocks and Blocking During Deployment

**Issue:** DDL operations acquire schema modification locks (Sch-M) that block all concurrent queries. On a production system with active users, this causes timeouts and deadlocks.

**Recommendation:**
- Schedule Prod deployments during maintenance windows or low-traffic periods
- Use online operations where available (`ALTER INDEX REBUILD WITH (ONLINE = ON)`, `ALTER TABLE ... WITH (ONLINE = ON)` in Enterprise Edition)
- Set `LOCK_TIMEOUT` in deployment scripts to fail fast rather than wait indefinitely
- For high-availability environments, consider blue-green deployment patterns or rolling updates

---

### 3.4 Orphaned Objects After Migration

**Issue:** SSDT automatically drops objects that are removed from the project. With scripts, deleted stored procedures, unused tables, or old indexes remain unless explicitly dropped.

**Recommendation:**
- Maintain a "cleanup" migration category for object removal
- Run a periodic orphan detection query that compares source-controlled objects against the live database
- Never auto-drop in production — generate a report of candidates for removal and require manual approval
- Add a pipeline step that warns when the live database contains objects not present in source control

---

### 3.5 Source Control Conflicts in Migration Scripts

**Issue:** Multiple developers creating migration scripts simultaneously can create ordering conflicts, duplicate version numbers, or conflicting schema changes.

**Recommendation:**
- Use a timestamp-based naming convention (e.g., `V20260410_0930__add_column.sql`) instead of sequential numbers to reduce conflicts
- Require PR reviews for all migration scripts with DBA approval for Prod-bound changes
- Run a CI check that validates migration script ordering and checksums on every PR
- Establish a convention: one structural change per script, no bundling unrelated changes

---

### 3.6 Debugging Failed Pipeline Runs

**Issue:** Pipeline failures can be opaque — generic error messages, truncated logs, or failures in infrastructure rather than SQL.

**Recommendation:**
- Configure verbose logging in the pipeline for the deployment steps
- Capture the full SQL error output (error number, severity, state, line number) and publish as a pipeline artifact
- Add a "diagnostic" task that runs on failure — captures agent connectivity, SQL Server status, disk space, and recent error log entries
- Document the top 10 most common pipeline failure modes and their resolutions in a runbook

---

## Summary: Priority Actions

| Priority | Action | Effort |
|----------|--------|--------|
| **P0** | Drift detection before every deployment | Low |
| **P0** | Idempotent script requirement + migration history table | Medium |
| **P0** | Rollback scripts + pre-deployment backup | Medium |
| **P1** | Environment variable groups + secret management | Low |
| **P1** | Post-deployment validation (views, smoke tests) | Medium |
| **P1** | Deployment notifications + dashboard | Low |
| **P2** | Performance regression detection | Medium |
| **P2** | Orphan detection reports | Low |
| **P2** | Staging environment parity audit | High |

---

## Discussion Points for the Meeting

1. **Migration framework vs. raw scripts** — Do we adopt DbUp/Flyway, or build our own script runner? Trade-off: framework adds a dependency but handles ordering, checksums, and history automatically.

2. **Rollback policy** — Are rollback scripts mandatory for every migration, or only for Prod-bound changes? What's our maximum acceptable rollback time?

3. **Deployment windows** — Do we enforce maintenance windows for Prod, or do we target zero-downtime deployments with online operations?

4. **DBA review gate** — Which changes require DBA sign-off? Suggestion: any DDL affecting tables with >1M rows, any security changes, any data motion scripts.

5. **Existing SSDT projects** — Are we migrating existing dacpac projects to scripts, or only new work goes through the DevOps pipeline? What's the transition plan?
