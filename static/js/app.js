const FALLBACK_IMAGE = '/static/images/placeholder.svg';
const TOAST_DURATION = 4000;

/* ============================================
   IMAGE FALLBACKS
   ============================================ */

function useFallbackImage(img) {
    if (img.dataset.fallbackUsed === 'final') return;
    // Wide hero art falls back to the regular cover first, then to the placeholder
    if (img.dataset.fallback && !img.dataset.fallbackUsed) {
        img.dataset.fallbackUsed = 'cover';
        img.src = img.dataset.fallback;
    } else {
        img.dataset.fallbackUsed = 'final';
        img.src = FALLBACK_IMAGE;
    }
}

// Error events do not bubble, so listen in the capture phase
document.addEventListener('error', (event) => {
    if (event.target.tagName === 'IMG') useFallbackImage(event.target);
}, true);

/* ============================================
   TOASTS
   ============================================ */

function dismissLater(toast) {
    setTimeout(() => toast.remove(), TOAST_DURATION);
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.getElementById('toastStack').appendChild(toast);
    dismissLater(toast);
}

/* ============================================
   HOME: FEATURED CAROUSEL
   ============================================ */

function initHero() {
    const hero = document.getElementById('heroCarousel');
    if (!hero) return;

    const slides = hero.querySelectorAll('.hero-slide');
    const dots = hero.querySelectorAll('.hero-dot');
    if (slides.length < 2) return;

    let current = 0;
    let timer = null;

    function show(index) {
        slides[current].classList.remove('active');
        dots[current].classList.remove('active');
        current = (index + slides.length) % slides.length;
        slides[current].classList.add('active');
        dots[current].classList.add('active');
    }

    function stop() {
        clearInterval(timer);
    }

    function start() {
        stop();
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        timer = setInterval(() => show(current + 1), 6000);
    }

    hero.querySelector('.hero-next').addEventListener('click', () => show(current + 1));
    hero.querySelector('.hero-prev').addEventListener('click', () => show(current - 1));
    dots.forEach((dot, index) => dot.addEventListener('click', () => show(index)));

    // Pause while the user is interacting with the carousel
    hero.addEventListener('mouseenter', stop);
    hero.addEventListener('mouseleave', start);
    hero.addEventListener('focusin', stop);
    hero.addEventListener('focusout', start);
    start();
}

/* ============================================
   STORE: SEARCH, FILTER, SORT
   ============================================ */

const PRICE_FILTERS = {
    'free': (price) => price === 0,
    'under-1000': (price) => price < 1000,
    'under-2000': (price) => price < 2000
};

const byTitle = (a, b) => a.dataset.title.localeCompare(b.dataset.title);
const byNumber = (key, direction) => (a, b) =>
    direction * (Number(a.dataset[key]) - Number(b.dataset[key])) || byTitle(a, b);

const SORTERS = {
    '': byTitle,
    'popular': byNumber('owners', -1),
    'rating': byNumber('rating', -1),
    'new': (a, b) => b.dataset.released.localeCompare(a.dataset.released) || byTitle(a, b),
    'price-asc': byNumber('price', 1),
    'price-desc': byNumber('price', -1)
};

function initStore() {
    const grid = document.getElementById('storeGrid');
    if (!grid) return;

    const cards = Array.from(grid.children);
    const search = document.getElementById('storeSearch');
    const price = document.getElementById('storePrice');
    const sort = document.getElementById('storeSort');
    const genreButtons = document.querySelectorAll('.genre-btn');
    const count = document.getElementById('storeCount');
    const empty = document.getElementById('storeEmpty');

    // State lives in the URL so filtered views can be linked and survive a reload
    const params = new URLSearchParams(window.location.search);
    const state = {
        q: params.get('q') || '',
        genre: params.get('genre') || '',
        price: params.get('price') in PRICE_FILTERS ? params.get('price') : '',
        sort: params.get('sort') in SORTERS ? params.get('sort') : ''
    };

    function render() {
        const query = state.q.trim().toLowerCase();
        const genre = state.genre.toLowerCase();
        const priceFilter = PRICE_FILTERS[state.price];
        let visible = 0;

        cards.forEach(card => {
            const genres = card.dataset.genres.toLowerCase();
            const matches =
                (!query || card.dataset.title.includes(query) || genres.includes(query)) &&
                (!genre || genres.split('|').includes(genre)) &&
                (!priceFilter || priceFilter(Number(card.dataset.price)));
            card.hidden = !matches;
            if (matches) visible++;
        });

        cards.sort(SORTERS[state.sort]).forEach(card => grid.appendChild(card));

        count.textContent = `${visible} ${visible === 1 ? 'game' : 'games'}`;
        empty.hidden = visible > 0;

        search.value = state.q;
        price.value = state.price;
        sort.value = state.sort;
        genreButtons.forEach(button => {
            const active = button.dataset.genre.toLowerCase() === genre;
            button.classList.toggle('active', active);
            button.setAttribute('aria-pressed', active);
        });

        const next = new URLSearchParams();
        Object.entries(state).forEach(([key, value]) => {
            if (value) next.set(key, value);
        });
        const queryString = next.toString();
        history.replaceState(null, '', queryString ? `?${queryString}` : window.location.pathname);
    }

    search.addEventListener('input', () => { state.q = search.value; render(); });
    price.addEventListener('change', () => { state.price = price.value; render(); });
    sort.addEventListener('change', () => { state.sort = sort.value; render(); });
    genreButtons.forEach(button => {
        button.addEventListener('click', () => { state.genre = button.dataset.genre; render(); });
    });
    document.getElementById('storeReset').addEventListener('click', () => {
        state.q = state.genre = state.price = '';
        render();
    });

    render();

    // On narrow screens the genre list scrolls sideways; bring a preselected genre into view
    const activeGenre = document.querySelector('.genre-btn.active');
    if (activeGenre) activeGenre.scrollIntoView({ block: 'nearest', inline: 'center' });
}

/* ============================================
   GAME PAGE: WISHLIST (kept in this browser only)
   ============================================ */

const WISHLIST_KEY = 'gamevault_wishlist';

function readWishlist() {
    try {
        const ids = JSON.parse(localStorage.getItem(WISHLIST_KEY));
        return Array.isArray(ids) ? ids : [];
    } catch {
        return [];
    }
}

function initWishlist() {
    const button = document.getElementById('wishlistBtn');
    if (!button) return;

    const gameId = Number(button.dataset.gameId);
    let wishlist = readWishlist();

    function update() {
        const saved = wishlist.includes(gameId);
        button.textContent = saved ? 'In wishlist ✓' : 'Add to wishlist';
        button.classList.toggle('active', saved);
        button.setAttribute('aria-pressed', saved);
    }

    button.addEventListener('click', () => {
        const saved = wishlist.includes(gameId);
        wishlist = saved ? wishlist.filter(id => id !== gameId) : [...wishlist, gameId];
        try {
            localStorage.setItem(WISHLIST_KEY, JSON.stringify(wishlist));
        } catch {
            // Storage unavailable (private mode): the toggle still works for this page view
        }
        showToast(saved ? 'Removed from wishlist' : 'Added to wishlist!');
        update();
    });

    button.hidden = false;
    update();
}

/* ============================================
   LIBRARY: GAME SELECTION AND LAUNCHER
   ============================================ */

const LAUNCH_DURATION = 2500;
const LAUNCH_STEPS = [
    { progress: 0, text: 'Initializing launch sequence…' },
    { progress: 15, text: 'Verifying game files…' },
    { progress: 35, text: 'Loading game textures…' },
    { progress: 60, text: 'Connecting to servers…' },
    { progress: 85, text: 'Synchronizing save data…' },
    { progress: 100, text: 'Game running! Enjoy playing!' }
];

function initLibrary() {
    const library = document.getElementById('library');
    if (!library) return;

    const items = Array.from(library.querySelectorAll('.library-item'));
    const details = Array.from(library.querySelectorAll('.library-detail'));

    function select(id) {
        items.forEach(item => {
            const active = item.dataset.id === id;
            item.classList.toggle('active', active);
            item.setAttribute('aria-current', active);
        });
        details.forEach(detail => { detail.hidden = detail.dataset.id !== id; });
    }

    items.forEach(item => item.addEventListener('click', () => select(item.dataset.id)));

    document.getElementById('librarySearch').addEventListener('input', (event) => {
        const query = event.target.value.trim().toLowerCase();
        items.forEach(item => {
            item.parentElement.hidden = !item.dataset.title.includes(query);
        });
    });

    // Open the game named in ?game=<id> (set after a purchase), otherwise the first one
    const requested = library.dataset.selected;
    select(items.some(item => item.dataset.id === requested) ? requested : items[0].dataset.id);

    const launcher = document.getElementById('launcher');
    const status = document.getElementById('launcherStatus');
    const progress = document.getElementById('launcherProgress');
    const closeButton = document.getElementById('launcherClose');
    let launchTimer = null;

    function launch(button) {
        document.getElementById('launcherTitle').textContent = `Launching ${button.dataset.title}`;
        closeButton.hidden = true;
        launcher.showModal();

        const startTime = Date.now();
        clearInterval(launchTimer);
        launchTimer = setInterval(() => {
            const percent = Math.min(100, ((Date.now() - startTime) / LAUNCH_DURATION) * 100);
            progress.style.width = `${percent}%`;
            status.textContent = LAUNCH_STEPS.findLast(step => percent >= step.progress).text;

            if (percent >= 100) {
                clearInterval(launchTimer);
                closeButton.hidden = false;
                closeButton.focus();
            }
        }, 50);

        fetch(`/library/${button.dataset.play}/play`, {
            method: 'POST',
            headers: { 'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content }
        }).then(response => {
            if (!response.ok) return;
            button.closest('.library-detail').querySelector('[data-last-played]').textContent = 'Just now';
        }).catch(() => {
            // Recording the play is best-effort; the launcher still runs offline
        });
    }

    library.querySelectorAll('[data-play]').forEach(button => {
        button.addEventListener('click', () => launch(button));
    });
    launcher.addEventListener('close', () => clearInterval(launchTimer));
}

/* ============================================
   STARTUP
   ============================================ */

// Images that failed before this script ran never fired a catchable error event.
// Lazy images have not been requested yet, so they are still covered by the listener.
document.querySelectorAll('img:not([loading="lazy"])').forEach(img => {
    if (img.complete && img.naturalWidth === 0 && img.getAttribute('src')) useFallbackImage(img);
});
document.querySelectorAll('.toast').forEach(dismissLater);

initHero();
initStore();
initWishlist();
initLibrary();
