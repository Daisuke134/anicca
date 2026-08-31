#!/usr/bin/env node
"use strict";

const { execFileSync } = require("node:child_process");
const { Pool } = require("pg");
const {
  createGhIssueClient,
  processNextFeedback,
} = require("../lib/feedback-to-issue.js");


const RAILWAY_PROJECT = "f9c524cb-ba4a-43bb-9639-ff736afd9ec1";
const RAILWAY_POSTGRES_SERVICE = "Postgres-1nl0";


function resolveDatabaseUrl() {
  if (process.env.LM_FEEDBACK_DATABASE_PUBLIC_URL) {
    return process.env.LM_FEEDBACK_DATABASE_PUBLIC_URL;
  }
  const raw = execFileSync(
    "railway",
    [
      "variables",
      "-p", RAILWAY_PROJECT,
      "-s", RAILWAY_POSTGRES_SERVICE,
      "-e", "production",
      "--json",
    ],
    { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
  );
  const values = JSON.parse(raw);
  if (!values.DATABASE_PUBLIC_URL) throw new Error("feedback_issue_database_unavailable");
  return values.DATABASE_PUBLIC_URL;
}


async function main() {
  const pool = new Pool({ connectionString: resolveDatabaseUrl() });
  try {
    const result = await processNextFeedback({
      query: pool.query.bind(pool),
      issueClient: createGhIssueClient(),
    });
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } finally {
    await pool.end();
  }
}


main().catch((error) => {
  process.stderr.write(`feedback-to-issue failed: ${error.message}\n`);
  process.exitCode = 1;
});
