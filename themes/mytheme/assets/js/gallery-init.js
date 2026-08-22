// Gallery initialization - reads data from data attributes
(function() {
    var container = document.getElementById('gallery_container');
    if (container) {
        var photoArrayAttr = container.getAttribute('data-photo-array');
        var thumbnailSizeAttr = container.getAttribute('data-thumbnail-size');

        if (photoArrayAttr && thumbnailSizeAttr) {
            var jsonContent = JSON.parse(photoArrayAttr);
            var thumbnailSize = parseInt(thumbnailSizeAttr, 10);

            // site.js runs baguetteBox.run() when all-nocdn.js loads, which is
            // before these thumbnails exist -- and renderGallery() replaces them
            // again on every resize.  Re-bind after each render or clicking a
            // thumbnail just navigates to the bare image.
            var bindLightbox = function() {
                if (typeof baguetteBox !== 'undefined') {
                    baguetteBox.run('div#content', {
                        ignoreClass: 'islink',
                        captions: function(element){
                            var i = element.getElementsByTagName('img')[0];
                            return i === undefined ? '' : i.alt;
                        }
                    });
                }
            };

            renderGallery(jsonContent, thumbnailSize);
            bindLightbox();
            window.addEventListener('resize', function(){
                renderGallery(jsonContent, thumbnailSize);
                bindLightbox();
            });
        }
    }
})();
