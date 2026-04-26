/**
 * ToddlerBites - View switching and sidebar navigation
 * Handles: Profile, Recent Searches, Settings, Logout modal
 */
(function() {
    'use strict';

    var VIEWS = {
        home: 'viewHome',
        profile: 'viewProfile',
        searches: 'viewSearches',
        settings: 'viewSettings'
    };

    var currentView = 'home';

    var dummySearches = [
        {
            id: '1',
            productName: 'Organic Baby Rice Cereal',
            date: 'Jan 28, 2025',
            ageGroup: '1-2 years',
            safety: 'safe',
            imageUrl: null
        },
        {
            id: '2',
            productName: 'Fruit Yogurt Pouch',
            date: 'Jan 25, 2025',
            ageGroup: '0-1 years',
            safety: 'caution',
            imageUrl: null
        },
        {
            id: '3',
            productName: 'Whole Grain Crackers',
            date: 'Jan 20, 2025',
            ageGroup: '2-3 years',
            safety: 'safe',
            imageUrl: null
        }
    ];

    function getViewElement(viewId) {
        return document.getElementById(VIEWS[viewId] || viewId);
    }

    function showView(viewId) {
        if (viewId === 'logout') {
            openLogoutModal();
            return;
        }

        var target = getViewElement(viewId);
        if (!target) return;

        document.querySelectorAll('.content-view').forEach(function(el) {
            el.classList.remove('active');
        });
        target.classList.add('active');
        currentView = viewId;

        document.querySelectorAll('.dropdown-item[data-view]').forEach(function(item) {
            item.classList.toggle('active', item.getAttribute('data-view') === viewId);
        });

        if (viewId === 'searches') {
            renderSearchCards();
        }
    }

    function renderSearchCards() {
        var container = document.getElementById('searchCardsContainer');
        if (!container) return;

        var searches = JSON.parse(localStorage.getItem('toddlerbites_searches') || JSON.stringify(dummySearches));

        if (searches.length === 0) {
            container.innerHTML = '<div class="search-card-empty"><i class="fas fa-search"></i><p>No recent searches yet.</p><p>Analyze a product to see results here.</p></div>';
            return;
        }

        container.innerHTML = searches.map(function(s) {
            var badgeClass = s.safety === 'safe' ? 'safe' : (s.safety === 'caution' ? 'caution' : 'unsuitable');
            var badgeText = s.safety === 'safe' ? 'Suitable' : (s.safety === 'caution' ? 'Use with Caution' : 'Not Recommended');
            var imgHtml = s.imageUrl
                ? '<img src="' + s.imageUrl + '" alt="" class="search-card-image">'
                : '<div class="search-card-image placeholder"><i class="fas fa-image"></i></div>';
            return '<div class="search-card" data-id="' + s.id + '">' +
                imgHtml +
                '<div class="search-card-body">' +
                '<div class="search-card-title">' + escapeHtml(s.productName) + '</div>' +
                '<div class="search-card-meta">' + s.date + ' · ' + s.ageGroup + '</div>' +
                '<span class="search-card-badge ' + badgeClass + '"><i class="fas fa-' + (s.safety === 'safe' ? 'check-circle' : (s.safety === 'caution' ? 'exclamation-triangle' : 'times-circle')) + '"></i> ' + badgeText + '</span>' +
                '</div>' +
                '<div class="search-card-actions">' +
                '<button type="button" class="btn btn-sm btn-outline view-report-btn"><i class="fas fa-file-alt"></i> View</button>' +
                '<button type="button" class="btn btn-sm btn-outline download-pdf-btn"><i class="fas fa-download"></i> PDF</button>' +
                '<button type="button" class="btn btn-sm btn-outline-danger delete-search-btn"><i class="fas fa-trash"></i></button>' +
                '</div></div>';
        }).join('');

        container.querySelectorAll('.view-report-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var card = this.closest('.search-card');
                if (card) showView('home');
            });
        });

        container.querySelectorAll('.download-pdf-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                alert('PDF download would be generated here. Connect to backend when ready.');
            });
        });

        container.querySelectorAll('.delete-search-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var card = this.closest('.search-card');
                if (card) {
                    var id = card.dataset.id;
                    var searches = JSON.parse(localStorage.getItem('toddlerbites_searches') || JSON.stringify(dummySearches));
                    searches = searches.filter(function(s) { return s.id !== id; });
                    localStorage.setItem('toddlerbites_searches', JSON.stringify(searches));
                    renderSearchCards();
                }
            });
        });
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function openLogoutModal() {
        var modal = document.getElementById('logoutModal');
        if (modal) {
            modal.classList.add('is-open');
            modal.setAttribute('aria-hidden', 'false');
        }
    }

    function closeLogoutModal() {
        var modal = document.getElementById('logoutModal');
        if (modal) {
            modal.classList.remove('is-open');
            modal.setAttribute('aria-hidden', 'true');
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.dropdown-item[data-view]').forEach(function(item) {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                var view = this.getAttribute('data-view');
                if (view) showView(view);
            });
        });

        var profileForm = document.getElementById('profileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', function(e) {
                e.preventDefault();
                var data = {
                    childName: document.getElementById('childName').value,
                    ageBracket: document.getElementById('ageBracketProfile').value,
                    allergies: document.getElementById('allergies').value,
                    dietPreference: document.getElementById('dietPreference').value
                };
                localStorage.setItem('toddlerbites_profile', JSON.stringify(data));
                alert('Profile saved successfully!');
            });
        }

        var clearDataBtn = document.getElementById('clearDataBtn');
        if (clearDataBtn) {
            clearDataBtn.addEventListener('click', function() {
                if (confirm('Clear all search history? This cannot be undone.')) {
                    localStorage.removeItem('toddlerbites_searches');
                    renderSearchCards();
                    alert('Search history cleared.');
                }
            });
        }

        var darkModeToggle = document.getElementById('darkMode');
        if (darkModeToggle) {
            darkModeToggle.checked = localStorage.getItem('toddlerbites_dark') === '1';
            darkModeToggle.addEventListener('change', function() {
                document.body.classList.toggle('dark-mode', this.checked);
                localStorage.setItem('toddlerbites_dark', this.checked ? '1' : '0');
            });
            if (darkModeToggle.checked) document.body.classList.add('dark-mode');
        }

        document.querySelector('.modal-close') && document.querySelector('.modal-close').addEventListener('click', closeLogoutModal);
        document.getElementById('logoutCancel') && document.getElementById('logoutCancel').addEventListener('click', closeLogoutModal);
        document.querySelector('.modal-backdrop') && document.querySelector('.modal-backdrop').addEventListener('click', closeLogoutModal);

        // Handle logout
        var logoutConfirm = document.getElementById('logoutConfirm');
        if (logoutConfirm) {
            logoutConfirm.addEventListener('click', function(e) {
                localStorage.removeItem('loggedInUser');
                localStorage.removeItem('toddlerbites_profile');
                // Continue with redirect
            });
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') closeLogoutModal();
        });

        var savedProfile = localStorage.getItem('toddlerbites_profile');
        var loggedInUser = localStorage.getItem('loggedInUser');
        var userData = null;
        if (loggedInUser) {
            try {
                userData = JSON.parse(loggedInUser);
            } catch (err) {}
        }

        if (savedProfile) {
            try {
                var p = JSON.parse(savedProfile);
                var el;
                if (p.childName && (el = document.getElementById('childName'))) el.value = p.childName;
                if (p.ageBracket && (el = document.getElementById('ageBracketProfile'))) el.value = p.ageBracket;
                if (p.allergies && (el = document.getElementById('allergies'))) el.value = p.allergies;
                if (p.dietPreference && (el = document.getElementById('dietPreference'))) el.value = p.dietPreference;
            } catch (err) {}
        }

        // Always set parent name from logged in user
        if (userData && userData.name) {
            var el = document.getElementById('parentName');
            if (el) el.value = userData.name;
        }

        // Set defaults if not set
        var el;
        if (!document.getElementById('childName').value && (el = document.getElementById('childName'))) el.value = '';
        if (!document.getElementById('ageBracketProfile').value && (el = document.getElementById('ageBracketProfile'))) el.value = '1-2';
        if (!document.getElementById('allergies').value && (el = document.getElementById('allergies'))) el.value = '';
        if (!document.getElementById('dietPreference').value && (el = document.getElementById('dietPreference'))) el.value = 'none';
    });

    function addRecentSearch(data) {
        var searches = JSON.parse(localStorage.getItem('toddlerbites_searches') || JSON.stringify(dummySearches));
        var safety = 'safe';
        if (data.analysis && /not suitable|avoid|unsafe/i.test(data.analysis)) safety = 'unsuitable';
        else if (data.analysis && /caution|moderate/i.test(data.analysis)) safety = 'caution';
        var name = (data.ingredients && data.ingredients[0]) ? data.ingredients[0] : 'Product Analysis';
        searches.unshift({
            id: String(Date.now()),
            productName: name,
            date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
            ageGroup: (data.age_bracket || '') + ' years',
            safety: safety,
            imageUrl: null
        });
        localStorage.setItem('toddlerbites_searches', JSON.stringify(searches));
    }

    window.showView = showView;
    window.addRecentSearch = addRecentSearch;
})();
