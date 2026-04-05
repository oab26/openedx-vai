(function() {
  // Only run on program detail pages
  if (window.location.pathname.indexOf('/dashboard/programs/') === -1) return;
  if (window.location.pathname === '/dashboard/programs/') return;

  // Read marketing site URL from meta tag injected by LMS settings
  var meta = document.querySelector('meta[name="vai-marketing-site"]');
  var MARKETING_SITE = meta ? meta.getAttribute('content') : 'https://dev.bytecrew.net';

  function rewriteEnrollButtons() {
    var buttons = document.querySelectorAll('button.cta-primary, .enroll-button button');
    buttons.forEach(function(btn) {
      if (btn.textContent.trim() !== 'Enroll Now') return;
      if (btn.dataset.vaiReplaced) return;

      // Walk up to find the course card container with an h5 title
      var container = btn;
      for (var i = 0; i < 8; i++) {
        container = container.parentElement;
        if (!container) return;
        if (container.querySelector('h5')) break;
      }
      var h5 = container.querySelector('h5');
      if (!h5) return;

      var title = h5.textContent.trim();
      var link = document.createElement('a');
      link.href = MARKETING_SITE + '/api/course-redirect?title=' + encodeURIComponent(title);
      link.className = btn.className;
      link.textContent = 'Enroll Now';
      link.style.cssText = 'display:inline-block;text-align:center;text-decoration:none;color:white;';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.dataset.vaiReplaced = 'true';
      btn.parentElement.replaceChild(link, btn);
    });
  }

  var observer = new MutationObserver(function() { rewriteEnrollButtons(); });
  function startObserving() {
    if (document.body) {
      observer.observe(document.body, { childList: true, subtree: true });
      rewriteEnrollButtons();
    }
  }
  if (document.body) startObserving();
  else document.addEventListener('DOMContentLoaded', startObserving);
})();
