// Gallery initialization - reads data from data attributes
(function() {
    var container = document.getElementById('gallery_container');
    if (container) {
        var photoArrayAttr = container.getAttribute('data-photo-array');
        var thumbnailSizeAttr = container.getAttribute('data-thumbnail-size');

        if (photoArrayAttr && thumbnailSizeAttr) {
            var jsonContent = JSON.parse(photoArrayAttr);
            var thumbnailSize = parseInt(thumbnailSizeAttr, 10);

            renderGallery(jsonContent, thumbnailSize);
            window.addEventListener('resize', function(){
                renderGallery(jsonContent, thumbnailSize);
            });
        }
    }
})();
