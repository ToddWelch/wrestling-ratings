// Railway infrastructure-as-code for the "Pro Wrestling Ratings" project.
// Replaces railway.toml, which Railway stops reading on 2026-12-01.
//
// This file is the COMPLETE desired state: on apply, anything not declared
// here is deleted (volumes excepted). Renaming or removing the service deletes
// the live service and its custom domain; a variable added in the dashboard
// and not listed below is deleted on the next apply.
//
// Workflow, from the repo root with the project linked: `cd .railway && npm ci`,
// then `railway config plan --out <file>`, then `railway config apply --plan
// <file>` with Todd's approval. Any plan with something "to destroy" or a
// variable delete stops for Todd; never pass --confirm-destructive without
// him. Nothing here applies on git push.
import { defineRailway, github, preserve, project, service } from "railway/iac";

export default defineRailway(() => {
  const app = service("wrestling-ratings", {
    source: github("ToddWelch/wrestling-ratings"),
    // The Dockerfile CMD loads backend/gunicorn.conf.py, which starts the
    // scrape scheduler. Without the Dockerfile builder the scheduler never runs.
    build: { builder: "DOCKERFILE", dockerfilePath: "Dockerfile" },
    healthcheck: "/api/health",
    healthcheckTimeout: 10,
    // One replica in Virginia (moved from Singapore on 2026-10-28)
    replicas: { "us-east4-eqdc4a": 1 },
    // Every service variable must be listed (omitted = deleted on apply).
    // Values live in Railway only; preserve() keeps them out of this file.
    variables: {
      SCRAPE_KEY: preserve(),
      SLACK_WEBHOOK_URL: preserve(),
      YOUTUBE_API_KEY: preserve(),
    },
  });

  return project("Pro Wrestling Ratings", {
    resources: [app],
  });
});
