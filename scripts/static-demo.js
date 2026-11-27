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
