// Initialize all Leaflet maps from data attributes
document.addEventListener("DOMContentLoaded", function() {
    var mapContainers = document.querySelectorAll('.leaflet-map-container');

    mapContainers.forEach(function(container) {
        var lat = parseFloat(container.getAttribute('data-lat'));
        var lng = parseFloat(container.getAttribute('data-lng'));
        var zoom = parseInt(container.getAttribute('data-zoom') || '13', 10);
        var popup = container.getAttribute('data-popup');
        var width = container.getAttribute('data-width');
        var float = container.getAttribute('data-float');

        // Apply custom width and float if provided
        if (width) {
            container.style.width = width;
        }
        if (float) {
            container.style.float = float;
        }

        // Initialize map
        var map = L.map(container.id).setView([lat, lng], zoom);

        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(map);

        // Add marker with popup if provided
        if (popup) {
            var marker = L.marker([lat, lng]).addTo(map);
            marker.bindPopup(popup).openPopup();
        }
    });
});
