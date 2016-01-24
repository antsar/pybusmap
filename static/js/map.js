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

        // Restore the user's last view.
        goToLastView();

        // Bind map event handlers
        that.leaflet.on('moveend', function() {
            // Store the lat/lon/zoom so we can restore it later
            updateLastView();
        });

        // Configure and apply the map tile layer
        var tileUrl = that.opts.tileUrl;
        var tileOptions = {
        };
        if (that.opts.tileOptions) {
            for (o in that.opts.tileOptions) { tileOptions[o] = that.opts.tileOptions[o]; }
        }
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
                that.stops = data.stops;
                that.routes = data.routes;
                updateStopsUI(that.stops);
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
                /* TODO: Fix all this shit, what the fuck */
                for (var p in data.predictions) {
                    pr = data.predictions[p];
                    // Store this prediction on the stop and on the vehicle.
                }
                that.vehicles = data.locations;
                updateStopsUI(that.stops);
                console.log(data);
            });
        return that;
    };

    /* Refresh (and/or create) UI elements for Vehicles */
    function updateVehiclesUI(vehicles) {
        // TODO
        return that;
    }

    /* Refresh (and/or create) UI elements for Stops */
    function updateStopsUI(stops) {
        var markers = L.markerClusterGroup({
            disableClusteringAtZoom: 14,
            maxClusterRadius: 40,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: false,
        });
        for (var s in stops) {
            var markerIcon = L.icon({
                iconUrl: 'static/img/stop27x60.png',
                iconSize: [13, 30],
                iconAnchor: [6, 30],
            });
            var text = '<header>' + stops[s].title + '</header>';
            var predictions = ['No vehicle arrival predictions.'];
            predictions.push('No vehicle arrival predictions.');
            if (stops[s].predictions) {
                var predictions = [];
                for (rt in stops[s].predictions) {
                    // do shit with prediction
                }
            }
            text += '<section class="predictions">' + predictions.join("<br>") + '</section>';
            var markerOpts = {
                title: stops[s].title,
                icon: markerIcon,
                opacity: 1,
            };
            var popupOpts = {
                closeButton: true,
                keepInView: true,
            };
            stopMarkers[stops[s].tag + "*" + stops[s].route] = L.marker(
                [stops[s].lat, stops[s].lon],
                markerOpts).bindPopup(text, popupOpts);
            markers.addLayer(stopMarkers[stops[s].tag + "*" + stops[s].route]);
        }
        that.leaflet.addLayer(markers);
        return that;
    }

    function goToLastView() {
        var last = BusMap.getCookie('last_view');
        if (last && last != "") {
            last = last.split(",");
            that.leaflet.setView(L.latLng(last[0], last[1]), last[2]);
            return true;
        } else {
            return false;
        }
    }

    function updateLastView() {
        var ll = that.leaflet.getCenter();
        view = ll.lat + ',' + ll.lng + ',' + that.leaflet.getZoom();
        BusMap.setCookie('last_view', view);
    }

    return that;
};

// http://stackoverflow.com/a/4004010
if (typeof String.prototype.trimLeft !== "function") {
    String.prototype.trimLeft = function() {
        return this.replace(/^\s+/, "");
    };
}
if (typeof String.prototype.trimRight !== "function") {
    String.prototype.trimRight = function() {
        return this.replace(/\s+$/, "");
    };
}
if (typeof Array.prototype.map !== "function") {
    Array.prototype.map = function(callback, thisArg) {
        for (var i=0, n=this.length, a=[]; i<n; i++) {
            if (i in this) a[i] = callback.call(thisArg, this[i]);
        }
        return a;
    };
}
BusMap.getCookies = function() {
    var c = document.cookie, v = 0, cookies = {};
    if (document.cookie.match(/^\s*\$Version=(?:"1"|1);\s*(.*)/)) {
        c = RegExp.$1;
        v = 1;
    }
    if (v === 0) {
        c.split(/[,;]/).map(function(cookie) {
            var parts = cookie.split(/=/, 2),
                name = decodeURIComponent(parts[0].trimLeft()),
                value = parts.length > 1 ? decodeURIComponent(parts[1].trimRight()) : null;
            cookies[name] = value;
        });
    } else {
        c.match(/(?:^|\s+)([!#$%&'*+\-.0-9A-Z^`a-z|~]+)=([!#$%&'*+\-.0-9A-Z^`a-z|~]*|"(?:[\x20-\x7E\x80\xFF]|\\[\x00-\x7F])*")(?=\s*[,;]|$)/g).map(function($0, $1) {
            var name = $0,
                value = $1.charAt(0) === '"'
                          ? $1.substr(1, -1).replace(/\\(.)/g, "$1")
                          : $1;
            cookies[name] = value;
        });
    }
    return cookies;
}
BusMap.getCookie = function(name) {
    console.log("Getting cookie\n" + "BM-" +  name);
    return BusMap.getCookies()["BM-" + name];
}

BusMap.setCookie = function(name, value, exp_days) {
    if (exp_days == undefined) {
        exp_days = 365;
    }
    exp_date = new Date();
    exp_date.setDate(exp_date.getDate() + exp_days);
    value = escape(value) + "; expires=" + exp_date.toUTCString();
    console.log("Setting cookie\n" + "BM-" + name + "=" + value);
    document.cookie = "BM-" + name + "=" + value;
}
