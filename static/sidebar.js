/**
 * ToddlerBites - Profile Sidebar Menu
 * Handles dropdown toggle and click-outside to close
 */
(function() {
    'use strict';

    var profileSection = document.getElementById('profileSection');
    var profileDropdown = document.getElementById('profileDropdown');

    if (!profileSection || !profileDropdown) return;

    function openMenu() {
        profileDropdown.classList.add('is-open');
        profileDropdown.setAttribute('aria-hidden', 'false');
        profileSection.setAttribute('aria-expanded', 'true');
    }

    function closeMenu() {
        profileDropdown.classList.remove('is-open');
        profileDropdown.setAttribute('aria-hidden', 'true');
        profileSection.setAttribute('aria-expanded', 'false');
    }

    function toggleMenu() {
        var isOpen = profileDropdown.classList.contains('is-open');
        if (isOpen) {
            closeMenu();
        } else {
            openMenu();
        }
    }

    function handleClickOutside(event) {
        var sidebar = document.getElementById('sidebar');
        var isInsideSidebar = sidebar && sidebar.contains(event.target);
        if (!isInsideSidebar) {
            closeMenu();
        }
    }

    profileSection.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        toggleMenu();
    });

    profileSection.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleMenu();
        }
    });

    document.addEventListener('click', handleClickOutside);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeMenu();
        }
    });

    profileDropdown.querySelectorAll('.dropdown-item').forEach(function(item) {
        item.addEventListener('click', function(e) {
            if (item.getAttribute('href') === '#') {
                e.preventDefault();
            }
            closeMenu();
        });
    });
})();
