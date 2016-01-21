/* The primary class for this project */
var BusMap = {};

/*
    Creates and manipulates a Leaflet map, abstracting away the ugly parts.
    Updating the map (Vehicles, Routes) is also handled here.
*/
BusMap.Map = function(opts) {
    this.opts = opts;
    var that = this;
    var stops = {};
    var stopMarkers = {};
    var routes = {};
    init();

    /* Constructor - create/initialize the map */
    function init() {
        // Create Map
        var mapOptions = {
            zoomControl: false,
        };
        var boundsOptions = {
            animate: false,
            reset: true,
        };
        that.leaflet = L.map(that.opts.mapElement, mapOptions)
            .fitBounds(that.opts.bounds)
            .setMaxBounds(that.opts.bounds, boundsOptions);
        if (that.opts.center) { that.leaflet.setView(that.opts.center); }
        else {that.leaflet.fitBounds(that.opts.bounds)}
        if (that.opts.zoom) that.leaflet.setZoom(that.opts.zoom);

        // Configure and apply the map tile layer
        var tileUrl = that.opts.tileUrl;
        var tileOptions = {}
        if (that.opts.tileOptions) { tileOptions = that.opts.tileOptions; }
        L.tileLayer(tileUrl, tileOptions).addTo(that.leaflet);

        // Fetch initial data
        updateRoutes();
        updateVehicles();

        // Begin timed data updates
        if (that.opts.refresh.routes) {
            setInterval(updateRoutes, that.opts.refresh.routes * 1000);
        }
        if (that.opts.refresh.vehicles) {
            setInterval(updateVehicles, that.opts.refresh.vehicles * 1000);
        }
    };

    /* Get Routes (and Stops, and Directions) */
    function updateRoutes() {
        var url = "ajax";
        var params = {
            "dataset": "routes",
            "agency": that.opts.agency,
        };
        function updateStopsUI(stops) {
            for (var s in stops) {
                // TODO: Put the stop marker on the map.
                var markerIcon = L.icon({
                    iconUrl: 'http://rutge.rs/img/bluedot.png',
                    iconSize: [24,24],
                    // options
                });
                var text = '<header>' + stops[s].title + '</header>';
                var markerOpts = {
                    icon: markerIcon,
                    title: stops[s].title,
                    opacity: 1,
                };
                var popupOpts = {
                    closeButton: true,
                    keepInView: true,
                };
                stopMarkers[stops[s].tag + "*" + stops[s].route] = L.marker(
                    [stops[s].lat, stops[s].lon],
                    markerOpts).addTo(that.leaflet);
            }
        }
        $.getJSON(url, params)
            .done(function(data) {
                stops = data.stops;
                routes = data.routes;
                updateStopsUI(stops);
                console.log(data);
            });
        return that;
    };

    /* Get Vehicles (and Predictions) */
    function updateVehicles() {
        var url = "ajax";
        var params = {
            "dataset": "vehicles",
            "agency": that.opts.agency,
        };
        $.getJSON(url, params)
            .done(function(data) {
                console.log(data);
            });
        // todo
        return that;
    };

    return that;
};

