// Railway infrastructure-as-code for the "Pro Wrestling Ratings" project.
// Replaces railway.toml, which Railway stops reading on 2026-12-01.
//
// Preview with `railway config plan` and apply with `railway config apply`,
// both from the repo root with the project linked. Nothing here applies on
// git push. Changing production settings needs Todd's approval.
//
// The service name must match Railway's existing service ("wrestling-ratings");
// a different name would create a second, billable service.
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
    // Values live in Railway only; preserve() keeps them out of this file
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
