/* The primary class for this project */
var BusMap = {};

/*
    Creates and manipulates a Leaflet map, abstracting away the ugly parts.
    Updating the map (Vehicles, Routes) is also handled here.
*/
BusMap.Map = function(opts) {
    this.opts = opts;
    var stops = {};
    var stopMarkers = {};
    var routes = {};
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

        // Put "About" link into the attribution box
        $(".leaflet-control-attribution").html('<a id="show-about" href="#">About</a>');
        $("#show-about").click(function() { $("#about").show(); });
        $("#close-about").click(function() { $("#about").hide(); });

        // Restore the user's last view (if exists).
        goToLastView();

        // Store view parameters for recovery later.
        that.leaflet.on('moveend', function() {
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
                // Store vehicle locations
                that.vehicles = data.locations;
                // Store predictions
                for (var s in that.stops) {
                    that.stops[s].predictions = {};
                }
                for (var v in that.vehicles) {
                    that.vehicles[v].predictions = {};
                }
                for (var p in data.predictions) {
                    pr = data.predictions[p];
                    if (that.stops && pr.stop_id in that.stops) {
                        // Store this prediction with the relevant stop
                        if (!(pr.route in that.stops[pr.stop_id].predictions)) {
                            that.stops[pr.stop_id].predictions[pr.route] = [];
                        }
                        that.stops[pr.stop_id].predictions[pr.route].push(pr);
                    }
                    if (that.vehicles && pr.vehicle in that.vehicles) {
                        // Store this prediction with the relevant vehicle
                        that.vehicles[pr.vehicle].predictions[pr.stop_id] = pr;
                    }
                }
                that.vehicles = data.locations;
                updateStopsUI(that.stops);
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
            var text = '<header>' + stops[s].title + '</header>';
            var popupOpts = {
                closeButton: true,
                keepInView: true,
            };
            if (!(s in stopMarkers)) {
                /* Stop marker doesn't exist yet - create it now. */
                var markerIcon = L.icon({
                    iconUrl: 'static/img/stop27x60.png',
                    iconSize: [13, 30],
                    iconAnchor: [6, 30],
                });
                var markerOpts = {
                    title: stops[s].title,
                    icon: markerIcon,
                    opacity: 1,
                };
                stopMarkers[s] = L.marker(
                    [stops[s].lat, stops[s].lon],
                    markerOpts).bindPopup(text, popupOpts);
                markers.addLayer(stopMarkers[s]);
            }
            /* Add predictions to the marker popup, if available  */
            if (that.stops[s].predictions) {
                var predictions = [];
                var now = new Date();
                var offset_mins = now.getTimezoneOffset();
                for (r in stops[s].predictions) {
                    var p_line = "<strong>" + that.routes[r].title + "</strong>:";
                    var times = [];
                    for (p in stops[s].predictions[r]) {
                        pr = stops[s].predictions[r][p];
                        var pdate = new Date(pr.prediction);
                        var diff_sec = (pdate.getTime() - now.getTime()) / 1000;
                        var diff_min = Math.ceil(diff_sec / 60) + offset_mins;
                        // CSS classes for predictions
                        var pclass = "";
                        if (diff_min <= 1) { pclass = "lt1min"; }
                        else if (diff_min <= 2 ) { pclass = "lt2mins"; }
                        else if (diff_min <= 5 ) { pclass = "lt5mins"; }
                        times.push(" <span class='prediction " + pclass + "' title='" + pr.vehicle + "'>"
                                    + diff_min + "</span>");
                    }
                    p_line += times.join(", ");
                    predictions.push(p_line);
                }
                if (predictions.length == 0) { predictions = ['No vehicle arrival predictions.']; }
                text += '<section class="predictions">' + predictions.sort().join("<br>") + '</section>';
                stopMarkers[s]._popup.setContent(text);
            }
        }
        that.leaflet.addLayer(markers);
        return that;
    }

    function goToLastView() {
        var last = BusMap.getCookie('last_view');
        if (last && last != "") {
            last = last.split(",");
            that.leaflet.setView([last[0], last[1]], last[2]);
            return true;
        } else {
            return false;
        }
    }

    function updateLastView() {
        var ll = that.leaflet.getCenter();
        view = Math.round(ll.lat * 1000000) / 1000000 + ',' + Math.round(ll.lng * 1000000) / 1000000+ ',' + that.leaflet.getZoom();
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
    return BusMap.getCookies()["BM-" + name];
}

BusMap.setCookie = function(name, value, exp_days) {
    if (exp_days == undefined) {
        exp_days = 365;
    }
    exp_date = new Date();
    exp_date.setDate(exp_date.getDate() + exp_days);
    value = escape(value) + "; expires=" + exp_date.toUTCString();
    document.cookie = "BM-" + name + "=" + value;
}
