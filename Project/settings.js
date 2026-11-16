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
