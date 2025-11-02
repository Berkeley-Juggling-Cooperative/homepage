var map = L.map('map').setView([37.8727222, -122.25575], 17);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

var marker = L.marker([37.8727222, -122.25575]).addTo(map);
marker.bindPopup("Meeting location").openPopup();
