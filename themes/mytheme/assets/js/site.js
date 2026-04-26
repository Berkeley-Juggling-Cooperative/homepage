// BaguetteBox initialization
baguetteBox.run('div#content', {
    ignoreClass: 'islink',
    captions: function(element){
        var i = element.getElementsByTagName('img')[0];
        return i === undefined ? '' : i.alt;
    }
});

// Bulma navbar burger toggle
document.addEventListener('DOMContentLoaded', () => {
    const $navbarBurgers = Array.prototype.slice.call(document.querySelectorAll('.navbar-burger'), 0);
    $navbarBurgers.forEach( el => {
        el.addEventListener('click', () => {
            const target = el.dataset.target;
            const $target = document.getElementById(target);
            el.classList.toggle('is-active');
            $target.classList.toggle('is-active');
        });
    });
});
