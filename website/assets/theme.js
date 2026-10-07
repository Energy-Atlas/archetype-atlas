/* Apply the visitor's colour scheme to record pages, which have no Material runtime (design/ui-design-spec.md, 0.3).
   Material stores the toggle's choice under the site path; without one, the system preference decides. */
(function () {
  var scheme;
  try {
    var site = new URL('..', document.currentScript.src).pathname;
    var palette = JSON.parse(localStorage.getItem(site + '.__palette'));
    scheme = palette && palette.color && palette.color.scheme;
  } catch (error) { /* Storage unavailable: fall back to the system preference. */ }
  if (scheme !== 'slate' && scheme !== 'default') {
    scheme = matchMedia('(prefers-color-scheme: dark)').matches ? 'slate' : 'default';
  }
  document.documentElement.setAttribute('data-md-color-scheme', scheme);
})();
