// Auto-scroll causal diagrams to keep the animated red bar centered
document.addEventListener("DOMContentLoaded", function() {
    const svgs = document.querySelectorAll('.causal-diagram-svg');

    svgs.forEach(function(svg) {
        const svgWidth = parseFloat(svg.getAttribute('data-diagram-width')); // SVG coordinate width
        const xMin = parseFloat(svg.getAttribute('data-x-min'));
        const xMax = parseFloat(svg.getAttribute('data-x-max'));
        const duration = parseFloat(svg.getAttribute('data-duration'));

        if (!svgWidth || !duration || xMin === null || xMax === null) {
            return; // Missing data, skip this SVG
        }

        // Wrap the SVG in a scrollable container
        const container = document.createElement('div');
        container.className = 'causal-diagram-container';
        svg.parentNode.insertBefore(container, svg);
        container.appendChild(svg);

        // Wait for layout to complete
        requestAnimationFrame(function() {
            const containerWidth = container.clientWidth;
            const renderedWidth = svg.getBoundingClientRect().width; // Actual pixel width
            const maxScroll = Math.max(0, renderedWidth - containerWidth);

            // Scale factor: SVG coordinates to screen pixels
            const scale = renderedWidth / svgWidth;

            // Only auto-scroll if the SVG is wider than the container
            if (maxScroll > 0) {
                let startTime = null;

                function updateScroll(timestamp) {
                    if (!startTime) startTime = timestamp;

                    // Calculate elapsed time in seconds, loop after duration
                    const elapsed = ((timestamp - startTime) % (duration * 1000)) / 1000;

                    // Calculate how far along the animation we are (0 to 1)
                    const progress = elapsed / duration;

                    // Calculate the red bar's current X position in SVG coordinates
                    const barSvgX = xMin + (progress * (xMax - xMin));

                    // Convert to pixel position
                    const barPixelX = barSvgX * scale;

                    // Center the bar: scroll so bar is at containerWidth / 2
                    const targetScroll = barPixelX - (containerWidth / 2);

                    // Clamp to valid scroll range
                    container.scrollLeft = Math.max(0, Math.min(maxScroll, targetScroll));

                    requestAnimationFrame(updateScroll);
                }

                requestAnimationFrame(updateScroll);
            }
        });
    });
});
