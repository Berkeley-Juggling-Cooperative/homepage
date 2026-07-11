// Play/pause and single-beat stepping for the animated causal diagrams.
// One control bar per diagram; click the buttons, or focus a diagram
// and use space (play/pause) and the left/right arrow keys (step).
document.addEventListener("DOMContentLoaded", function() {
    function makeButton(text, label) {
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = text;
        b.title = label;
        b.setAttribute('aria-label', label);
        return b;
    }

    // one control bar per animated diagram group: either a synced
    // causal+position container, or a lone scrolling causal diagram
    // (the .causal-diagram-container wrappers are created by
    // causal-diagram-scroll.js, which must run before this script)
    var groups = Array.prototype.slice.call(
        document.querySelectorAll('.diagram-sync-container'));
    document.querySelectorAll('.causal-diagram-container').forEach(function(el) {
        if (!el.closest('.diagram-sync-container')) {
            groups.push(el);
        }
    });

    groups.forEach(function(group) {
        var svgs = Array.prototype.slice.call(group.querySelectorAll('svg'));
        if (!svgs.length || typeof svgs[0].pauseAnimations !== 'function') {
            return; // no SMIL timeline support
        }
        var ref = group.querySelector('svg.causal-diagram-svg') || svgs[0];
        var duration = parseFloat(ref.getAttribute('data-duration')) || 0;

        var bar = document.createElement('div');
        bar.className = 'diagram-controls';
        var back = makeButton('⏮', 'one beat back');
        var play = makeButton('⏸', 'play/pause');
        var fwd = makeButton('⏭', 'one beat forward');
        var beat = document.createElement('span');
        beat.className = 'diagram-beat';
        bar.appendChild(back);
        bar.appendChild(play);
        bar.appendChild(fwd);
        bar.appendChild(beat);
        group.insertBefore(bar, group.firstChild);

        var paused = false;

        function setPaused(p) {
            paused = p;
            svgs.forEach(function(s) {
                if (p) {
                    s.pauseAnimations();
                } else {
                    s.unpauseAnimations();
                }
            });
            play.textContent = p ? '⏵' : '⏸';
        }

        function step(delta) {
            if (!paused) {
                setPaused(true);
            }
            var t = Math.round(svgs[0].getCurrentTime()) + delta;
            if (duration > 0) {
                t = ((t % duration) + duration) % duration;
            } else if (t < 0) {
                t = 0;
            }
            svgs.forEach(function(s) { s.setCurrentTime(t); });
        }

        play.addEventListener('click', function() { setPaused(!paused); });
        back.addEventListener('click', function() { step(-1); });
        fwd.addEventListener('click', function() { step(1); });

        group.setAttribute('tabindex', '0');
        group.addEventListener('keydown', function(ev) {
            if (ev.key === ' ' && ev.target.tagName === 'BUTTON') {
                return; // space on a focused button already clicks it
            }
            if (ev.key === ' ') {
                ev.preventDefault();
                setPaused(!paused);
            } else if (ev.key === 'ArrowRight') {
                ev.preventDefault();
                step(1);
            } else if (ev.key === 'ArrowLeft') {
                ev.preventDefault();
                step(-1);
            }
        });

        function updateBeat() {
            var t = svgs[0].getCurrentTime();
            if (duration > 0) {
                t = t % duration;
            }
            beat.textContent = 'beat ' + (Math.round(t * 10) / 10);
            requestAnimationFrame(updateBeat);
        }
        requestAnimationFrame(updateBeat);
    });
});
