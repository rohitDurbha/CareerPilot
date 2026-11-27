// Added by scripts/build-site.mjs for the hosted site.
window.CAREERPILOT_SETTINGS = Object.assign({"apiUrl":"demo-api","meetUrl":"."}, window.CAREERPILOT_SETTINGS || {});
// Where the CareerPilot pages send their requests.
//
// index.html and dashboard.html load this file before their own scripts, so
// these two addresses are the only place to change when the backend or the
// interview room moves. A page can also set window.CAREERPILOT_SETTINGS before
// loading this file to override either value without editing it.
(function (root) {
  var DEFAULTS = {
    apiUrl: 'http://localhost:5001',
    meetUrl: 'http://localhost:3000',
  };

  function trimSlashes(value) {
    return String(value).replace(/\/+$/, '');
  }

  function join(base, path) {
    var cleanPath = String(path || '').replace(/^\/+/, '');
    return cleanPath ? trimSlashes(base) + '/' + cleanPath : trimSlashes(base);
  }

  function buildSettings(overrides) {
    var given = overrides || {};
    var apiUrl = given.apiUrl ? trimSlashes(given.apiUrl) : DEFAULTS.apiUrl;
    var meetUrl = given.meetUrl ? trimSlashes(given.meetUrl) : DEFAULTS.meetUrl;
    return {
      apiUrl: apiUrl,
      meetUrl: meetUrl,
      api: function (path) {
        return join(apiUrl, path);
      },
      meet: function (path) {
        return join(meetUrl, path);
      },
    };
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DEFAULTS: DEFAULTS, buildSettings: buildSettings };
  }
  if (root) {
    root.CareerPilot = buildSettings(root.CAREERPILOT_SETTINGS);
  }
})(typeof window !== 'undefined' ? window : null);

// Recorded mock backend answers for the static demo.
window.CAREERPILOT_DEMO_RESPONSES = {"GET /":{"status":200,"body":"Backend is running in mock mode."},"GET /health":{"status":200,"body":{"missing":[],"mode":"mock","ready":true,"services":{"job_search_webhook":{"configured":false,"needed":false},"mongodb":{"configured":false,"needed":false},"resume_match_webhook":{"configured":false,"needed":false}}}},"GET /latest_jobs":{"status":200,"body":{"count":3,"jobs":[{"_id":"mock-1003","companyName":"Cedar Logistics","companyUrl":"https://example.com/jobs/mock-1003","jobDescription":"Maintain Airflow pipelines that load shipment events into Snowflake and help the analytics team with data quality checks.","jobId":"mock-1003","jobTitle":"Junior Data Engineer","lastUpdatedTime":"2026-11-11T08:15:00Z","location":"Oakland, CA","matchedSkills":["Python","SQL"],"missingSkills":["Airflow","Snowflake"],"mock":true,"publishedAt":"2026-11-11T08:15:00Z","resumeScore":64},{"_id":"mock-1002","companyName":"Northwind Health","companyUrl":"https://example.com/jobs/mock-1002","jobDescription":"Model clinical operations data in dbt, maintain Tableau workbooks and write clear summaries for leadership.","jobId":"mock-1002","jobTitle":"Business Intelligence Analyst","lastUpdatedTime":"2026-11-10T19:30:00Z","location":"Remote","matchedSkills":["SQL","Tableau"],"missingSkills":["dbt","healthcare data"],"mock":true,"publishedAt":"2026-11-10T19:30:00Z","resumeScore":78},{"_id":"mock-1001","companyName":"Harbor Analytics","companyUrl":"https://example.com/jobs/mock-1001","jobDescription":"Build dashboards in SQL and Python, own weekly reporting for the sales team and partner with product managers on experiment readouts.","jobId":"mock-1001","jobTitle":"Data Analyst","lastUpdatedTime":"2026-11-10T16:00:00Z","location":"San Jose, CA","matchedSkills":["SQL","Python","dashboards","reporting"],"missingSkills":["A/B testing"],"mock":true,"publishedAt":"2026-11-10T16:00:00Z","resumeScore":91}],"mock":true}},"POST /trigger":{"status":200,"body":{"message":"Both workflows succeeded","results":[{"data":{"jobs":[{"companyName":"Harbor Analytics","companyUrl":"https://example.com/jobs/mock-1001","jobDescription":"Build dashboards in SQL and Python, own weekly reporting for the sales team and partner with product managers on experiment readouts.","jobId":"mock-1001","jobTitle":"Data Analyst","location":"San Jose, CA","publishedAt":"2026-11-10T16:00:00Z"},{"companyName":"Northwind Health","companyUrl":"https://example.com/jobs/mock-1002","jobDescription":"Model clinical operations data in dbt, maintain Tableau workbooks and write clear summaries for leadership.","jobId":"mock-1002","jobTitle":"Business Intelligence Analyst","location":"Remote","publishedAt":"2026-11-10T19:30:00Z"},{"companyName":"Cedar Logistics","companyUrl":"https://example.com/jobs/mock-1003","jobDescription":"Maintain Airflow pipelines that load shipment events into Snowflake and help the analytics team with data quality checks.","jobId":"mock-1003","jobTitle":"Junior Data Engineer","location":"Oakland, CA","publishedAt":"2026-11-11T08:15:00Z"}],"message":"Job search finished","mock":true,"received":{"keyword":["Data Analyst"],"location":"Remote","publishedAt":"r86400"}},"status":200},{"data":{"message":"Resume scored against the latest jobs","mock":true,"received":{"resume_text_length":44},"scores":[{"jobId":"mock-1001","matchedSkills":["SQL","Python","dashboards","reporting"],"missingSkills":["A/B testing"],"resumeScore":91},{"jobId":"mock-1002","matchedSkills":["SQL","Tableau"],"missingSkills":["dbt","healthcare data"],"resumeScore":78},{"jobId":"mock-1003","matchedSkills":["Python","SQL"],"missingSkills":["Airflow","Snowflake"],"resumeScore":64}]},"status":200}]}},"POST /upload_resume":{"status":200,"body":{"data":{"jobs":[{"companyName":"Harbor Analytics","companyUrl":"https://example.com/jobs/mock-1001","jobDescription":"Build dashboards in SQL and Python, own weekly reporting for the sales team and partner with product managers on experiment readouts.","jobId":"mock-1001","jobTitle":"Data Analyst","location":"San Jose, CA","publishedAt":"2026-11-10T16:00:00Z"},{"companyName":"Northwind Health","companyUrl":"https://example.com/jobs/mock-1002","jobDescription":"Model clinical operations data in dbt, maintain Tableau workbooks and write clear summaries for leadership.","jobId":"mock-1002","jobTitle":"Business Intelligence Analyst","location":"Remote","publishedAt":"2026-11-10T19:30:00Z"},{"companyName":"Cedar Logistics","companyUrl":"https://example.com/jobs/mock-1003","jobDescription":"Maintain Airflow pipelines that load shipment events into Snowflake and help the analytics team with data quality checks.","jobId":"mock-1003","jobTitle":"Junior Data Engineer","location":"Oakland, CA","publishedAt":"2026-11-11T08:15:00Z"}],"message":"Job search finished","mock":true,"received":{"email":"","job_description":"","job_id":"demo","resume_text_length":44}},"status":200}},"POST /run_agents":{"status":200,"body":{"message":"Mock mode is on, so the agents were not started","mock":true,"pids":{"agent1":null,"agent2":null},"received":{"job_description":"Sample","job_title":"Data Analyst"},"status":"started"}},"GET /cancel_file1":{"status":200,"body":{"details":{"agent1":"terminated","agent2":"terminated"},"message":"All scripts handled and logs uploaded","status":"completed"}}};
// Replays recorded mock backend answers in the browser for the static demo.
//
// scripts/build-site.mjs appends this file to settings.js only when it builds
// the GitHub Pages copy of the site, together with the answers recorded by
// scripts/record_demo_api.py. Any fetch to the backend address is then answered
// from those recordings, and every other fetch goes to the network as usual.
(function (root) {
  function pathOf(url, apiUrl) {
    var text = typeof url === 'string' ? url : (url && url.url) || '';
    var base = String(apiUrl).replace(/\/+$/, '');
    if (text !== base && text.indexOf(base + '/') !== 0) return null;
    var path = text.slice(base.length).split('?')[0].split('#')[0];
    return '/' + path.replace(/^\/+/, '');
  }

  function createDemoFetch(responses, apiUrl, realFetch) {
    return function demoFetch(url, init) {
      var path = pathOf(url, apiUrl);
      if (path === null) return realFetch(url, init);
      var method = String((init && init.method) || (url && url.method) || 'GET').toUpperCase();
      var recorded = responses[method + ' ' + path];
      if (!recorded) {
        recorded = { status: 404, body: { error: 'The static demo has no answer for ' + method + ' ' + path } };
      }
      var isText = typeof recorded.body === 'string';
      var body = isText ? recorded.body : JSON.stringify(recorded.body);
      var type = isText ? 'text/plain' : 'application/json';
      return Promise.resolve(
        new Response(body, { status: recorded.status, headers: { 'Content-Type': type } })
      );
    };
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { createDemoFetch: createDemoFetch, pathOf: pathOf };
  }
  if (root && root.CAREERPILOT_DEMO_RESPONSES && root.CareerPilot && root.fetch) {
    root.fetch = createDemoFetch(
      root.CAREERPILOT_DEMO_RESPONSES,
      root.CareerPilot.apiUrl,
      root.fetch.bind(root)
    );
  }
})(typeof window !== 'undefined' ? window : null);

// Built from 8782b04edfa9d83fac5b1348d307136ef8818b6a
