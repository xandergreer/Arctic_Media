(function () {
    function setupRow(rowId) {
        const viewport = document.getElementById(`row-${rowId}`);
        if (!viewport) return;
        const left = document.querySelector(`.row .row-arrow.left[data-row="${rowId}"]`);
        const right = document.querySelector(`.row .row-arrow.right[data-row="${rowId}"]`);

        const getCardWidth = () => {
            const card = viewport.querySelector('.poster-card');
            if (!card) return 300;
            const style = getComputedStyle(card);
            return card.getBoundingClientRect().width + parseFloat(style.marginRight || 12);
        };

        const page = () => Math.max(viewport.clientWidth - getCardWidth(), getCardWidth() * 3 / 2);

        function scrollDir(dir) {
            viewport.scrollBy({ left: dir * page(), behavior: 'smooth' });
        }

        function updateArrows() {
            const max = viewport.scrollWidth - viewport.clientWidth - 1;
            const x = viewport.scrollLeft;
            left.classList.toggle('hide', x <= 0);
            right.classList.toggle('hide', x >= max);
        }

        left?.addEventListener('click', () => scrollDir(-1));
        right?.addEventListener('click', () => scrollDir(1));
        viewport.addEventListener('scroll', updateArrows);
        window.addEventListener('resize', updateArrows);
        updateArrows();
    }

    setupRow('movies');
    setupRow('tv');
})();
