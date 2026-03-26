(function () {
  var STORAGE_KEY = 'mindsense_theme';

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      // Ignore storage issues in private mode.
    }

    var allToggles = document.querySelectorAll('[data-theme-toggle]');
    allToggles.forEach(function (btn) {
      btn.setAttribute('aria-label', theme === 'light' ? 'Switch to dark theme' : 'Switch to light theme');
      btn.textContent = theme === 'light' ? '🌙 Dark' : '☀ Light';
      btn.title = theme === 'light' ? 'Dark mode' : 'Light mode';
    });
  }

  function getInitialTheme() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'light' || saved === 'dark') {
        return saved;
      }
    } catch (e) {
      // Ignore storage issues.
    }
    return 'dark';
  }

  function bindInlineToggles() {
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      if (btn.dataset.boundThemeToggle === 'true') {
        return;
      }
      btn.dataset.boundThemeToggle = 'true';
      btn.addEventListener('click', function () {
        var current = document.documentElement.getAttribute('data-theme') || 'dark';
        setTheme(current === 'dark' ? 'light' : 'dark');
      });
    });
  }

  function initThemeSystem() {
    setTheme(getInitialTheme());
    bindInlineToggles();
    initResponsiveNavigation();

    // Re-bind if page scripts update part of the DOM.
    setTimeout(function () {
      bindInlineToggles();
      initResponsiveNavigation();
      setTheme(document.documentElement.getAttribute('data-theme') || 'dark');
    }, 250);
  }

  function ensureSidebarToggle() {
    var sidebar = document.getElementById('sidebar');
    var mainHeader = document.querySelector('.main-header');
    if (!sidebar || !mainHeader) {
      return;
    }

    var existingToggle = document.getElementById('sidebarToggle');
    if (!existingToggle) {
      existingToggle = document.createElement('button');
      existingToggle.id = 'sidebarToggle';
      existingToggle.className = 'sidebar-toggle';
      existingToggle.type = 'button';
      existingToggle.setAttribute('aria-label', 'Open navigation menu');
      existingToggle.innerHTML = '☰';
      mainHeader.insertBefore(existingToggle, mainHeader.firstChild);
    }

    var existingOverlay = document.getElementById('sidebarOverlay');
    if (!existingOverlay) {
      existingOverlay = document.createElement('div');
      existingOverlay.id = 'sidebarOverlay';
      existingOverlay.className = 'sidebar-overlay';
      document.body.appendChild(existingOverlay);
    }

    if (existingToggle.dataset.boundSidebarToggle === 'true') {
      return;
    }

    function closeSidebar() {
      sidebar.classList.remove('open');
      existingOverlay.classList.remove('open');
    }

    function toggleSidebar() {
      var opening = !sidebar.classList.contains('open');
      sidebar.classList.toggle('open', opening);
      existingOverlay.classList.toggle('open', opening);
    }

    existingToggle.addEventListener('click', toggleSidebar);
    existingOverlay.addEventListener('click', closeSidebar);

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        closeSidebar();
      }
    });

    document.querySelectorAll('.sidebar-link').forEach(function (link) {
      link.addEventListener('click', closeSidebar);
    });

    existingToggle.dataset.boundSidebarToggle = 'true';
  }

  function ensureNavbarToggle() {
    var navbar = document.querySelector('.navbar');
    if (!navbar) {
      return;
    }

    var links = navbar.querySelector('.navbar-links');
    if (!links) {
      return;
    }

    var toggle = document.getElementById('navbarMenuToggle');
    if (!toggle) {
      toggle = document.createElement('button');
      toggle.id = 'navbarMenuToggle';
      toggle.className = 'navbar-menu-toggle';
      toggle.type = 'button';
      toggle.setAttribute('aria-label', 'Toggle navigation menu');
      toggle.innerHTML = '☰';
      navbar.appendChild(toggle);
    }

    if (toggle.dataset.boundNavbarToggle === 'true') {
      return;
    }

    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });

    document.addEventListener('click', function (event) {
      if (!navbar.contains(event.target)) {
        links.classList.remove('open');
      }
    });

    links.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        links.classList.remove('open');
      });
    });

    toggle.dataset.boundNavbarToggle = 'true';
  }

  function initResponsiveNavigation() {
    ensureSidebarToggle();
    ensureNavbarToggle();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThemeSystem);
  } else {
    initThemeSystem();
  }
})();
