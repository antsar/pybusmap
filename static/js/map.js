/* The primary class for this project */
var BusMap = {};

/*
    Creates and manipulates a Leaflet map, abstracting away the ugly parts.
    Updating the map (Vehicles, Routes) is also handled here.
*/
BusMap.Map = function(opts) {
    this.opts = opts;
    var that = this;
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
        $.getJSON(url, params)
            .done(function(data) {
                console.log(data);
            });
        // cb: update that.routes && update map (and UI?). data bindings??
        // todo
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

