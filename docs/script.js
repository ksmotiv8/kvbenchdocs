/* ============================================
   Inference Adventures — Shared Site Scripts
   ============================================ */

/* --- Prompt domain tab switcher --- */
function switchPromptTab(btn, panelId) {
    var bar = btn.parentElement;
    var tabs = bar.parentElement;
    bar.querySelectorAll('.prompt-tab-btn').forEach(function (b) { b.classList.remove('active'); });
    tabs.querySelectorAll('.prompt-tab-panel').forEach(function (p) { p.classList.remove('active'); });
    btn.classList.add('active');
    document.getElementById(panelId).classList.add('active');
}

(function () {
    'use strict';

    /* --- Nav scroll effect --- */
    const nav = document.querySelector('nav');
    let lastScroll = 0;

    function handleScroll() {
        const scrollY = window.scrollY;
        if (scrollY > 40) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
        lastScroll = scrollY;
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    /* --- Theme toggle --- */
    const themeBtn = document.getElementById('theme-toggle');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');

    function getStoredTheme() {
        return localStorage.getItem('theme');
    }

    function setTheme(mode) {
        if (mode === 'light') {
            document.body.classList.add('light');
            themeBtn.textContent = '\u2600';
            themeBtn.setAttribute('aria-label', 'Switch to dark mode');
        } else {
            document.body.classList.remove('light');
            themeBtn.textContent = '\u263E';
            themeBtn.setAttribute('aria-label', 'Switch to light mode');
        }
        localStorage.setItem('theme', mode);
    }

    // Initialize theme
    const stored = getStoredTheme();
    if (stored) {
        setTheme(stored);
    } else {
        setTheme(prefersDark.matches ? 'dark' : 'dark'); // default dark
    }

    themeBtn.addEventListener('click', function () {
        const isLight = document.body.classList.contains('light');
        setTheme(isLight ? 'dark' : 'light');
    });

    /* --- Fade-up scroll animations --- */
    const fadeEls = document.querySelectorAll('.fade-up');

    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.08,
            rootMargin: '0px 0px -40px 0px'
        });

        fadeEls.forEach(function (el) {
            observer.observe(el);
        });
    } else {
        // Fallback: just show everything
        fadeEls.forEach(function (el) {
            el.classList.add('visible');
        });
    }

    /* --- Smooth scroll for in-page anchor links --- */
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
        link.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                const offset = 80; // nav height + padding
                const top = target.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top: top, behavior: 'smooth' });
                // Close mobile nav if open
                closeMobileNav();
            }
        });
    });

    /* --- Mobile nav --- */
    const hamburger = document.getElementById('hamburger');
    const mobileNav = document.getElementById('mobile-nav');

    function closeMobileNav() {
        if (mobileNav) {
            mobileNav.classList.remove('open');
        }
    }

    if (hamburger && mobileNav) {
        hamburger.addEventListener('click', function () {
            mobileNav.classList.toggle('open');
        });
    }

    /* --- Active nav link highlighting (cross-page aware) --- */
    const currentPage = document.body.getAttribute('data-page') || 'home';
    const pageNavLinks = document.querySelectorAll('.nav-links a');

    function updateActiveLink() {
        // First: highlight the current page link
        pageNavLinks.forEach(function (link) {
            link.style.color = '';
            link.style.fontWeight = '';
        });

        // Check for in-page section scroll highlighting
        const sections = document.querySelectorAll('section[id]');
        const scrollY = window.scrollY + 120;
        let currentId = '';

        sections.forEach(function (section) {
            if (scrollY >= section.offsetTop) {
                currentId = section.id;
            }
        });

        // Highlight matching nav link (works for both in-page anchors and page links)
        pageNavLinks.forEach(function (link) {
            var href = link.getAttribute('href');
            // Check if it's the current page link
            if (href === currentPage + '.html' || (currentPage === 'home' && href === 'index.html')) {
                link.style.color = 'var(--text-primary)';
            }
            // Check if it's an in-page anchor that matches
            if (currentId && href === '#' + currentId) {
                link.style.color = 'var(--text-primary)';
            }
        });
    }

    window.addEventListener('scroll', updateActiveLink, { passive: true });
    updateActiveLink();
})();
