/* The primary class for this project */
var BusMap = {
    cookiePrefix: "BM_",
    zoomShowVehicles: 15,
    vehicleMaxAge: 10,
};

/*
    Creates and manipulates a Leaflet map, abstracting away the ugly parts.
    Updating the map (Vehicles, Routes) is also handled here.
*/
BusMap.Map = function(opts) {
    this.opts = opts;
    var stops = {};
    var routes = {};
    var that = this;
    init();

    /* Constructor - create/initialize the map */
    function init() {
        // Create Map
        var mapOptions = {
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

        // Restore the user's last view (if exists).
        lastViewRecover();

        // Store view parameters for recovery later.
        that.leaflet.on('moveend', lastViewStore);

        // Show/hide markers based on zoom.
        that.leaflet.on('zoomend', zoomShowHide);

        // Configure and apply the map tile layer
        var tileUrl = that.opts.tileUrl;
        var tileOptions = {
        };
        if (that.opts.tileOptions) {
            for (o in that.opts.tileOptions) {
                tileOptions[o] = that.opts.tileOptions[o];
            }
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
            dataset: "routes",
            agency: that.opts.agency,
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
            dataset: "vehicles",
            agency: that.opts.agency,
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
                    that.vehicles[v].predictions = [];
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
                        that.vehicles[pr.vehicle].predictions.push(pr);
                    }
                }
                that.vehicles = data.locations;
                updateVehiclesUI(that.vehicles);
                updateStopsUI(that.stops);
            });
        return that;
    };

    /* Refresh (and/or create) UI elements for Vehicles */
    function updateVehiclesUI(vehicles) {
        if (!(that.vehicleMarkersGroup)) {
            that.vehicleMarkersGroup = L.layerGroup();
            that.leaflet.addLayer(that.vehicleMarkersGroup);
        }
        if (!that.vehicleMarkers) {
            that.vehicleMarkers = {};
        }
        for (var v in vehicles) {
            if (!that.routes) {
                // Try again in half a second, routes are loading or refreshing.
                setTimeout(function() { updateVehiclesUI(vehicles) }, 500);
                return false;
            }

            var route = that.routes[vehicles[v].route].title;
            var text = '<header>' + route + '</header>';
            var text_after = '<footer>Bus # ' + vehicles[v].vehicle + '</footer>';
            var popupOpts = {
                closeButton: false,
                keepInView: true,
            };
            if (!(v in that.vehicleMarkers)) {
                var markerIcon = L.icon({
                    iconUrl: 'static/img/bus.png',
                    iconSize: [21,25],
                    iconAnchor: [10,12],
                });
                that.vehicleMarkers[v] = L.marker([vehicles[v].lat, vehicles[v].lon], {
                    icon: markerIcon,
                    iconAngle: vehicles[v].heading
                }).bindLabel(route, {
                    noHide: true,
                    direction: 'right',
                }).bindPopup(text + text_after, popupOpts).addTo(that.vehicleMarkersGroup);
            } else {
                that.vehicleMarkers[v].setLatLng([vehicles[v].lat, vehicles[v].lon])
                    .setIconAngle(vehicles[v].heading);
            }
            that.vehicleMarkers[v].bm_updated = Date.now()

            // Add predictions to the marker popup, if available
            if (that.stops && vehicles[v].predictions) {
                var predictions = [];
                var now = new Date();
                var offset_mins = now.getTimezoneOffset();
                psorted = vehicles[v].predictions.sort(function(a,b){
                    return new Date(a.prediction).getTime() - new Date(b.prediction).getTime();
                });
                for (p in psorted) {
                    pr = psorted[p];
                    var p_line = "<strong>" + that.stops[pr.stop_id].title + "</strong>: ";
                    var pdate = new Date(pr.prediction);
                    var diff_sec = (pdate.getTime() - now.getTime()) / 1000;
                    var diff_min = Math.ceil(diff_sec / 60) + offset_mins;
                    // CSS classes for predictions
                    var pclass = "";
                    if (diff_min <= 1) { pclass = "lt1min"; }
                    else if (diff_min <= 2 ) { pclass = "lt2mins"; }
                    else if (diff_min <= 5 ) { pclass = "lt5mins"; }
                    p_line += ("<span class='prediction " + pclass
                             + "' title='" + pr.vehicle + "'>"
                             + diff_min + "</span>");

                    predictions.push("<div class='stop'" + p_line + "</div>");
                }
                if (predictions.length == 0) {
                    predictions = ['<div class="none">No arrival predictions.</div>'];
                } else if (predictions.length > 5) {
                    predictions.push("<div class='more'><a href='javascript:void(0);' onclick='$(this).hide().parent().parent().parent().addClass(\"show-all-predictions\");'>see more</a></div>");
                }
                text += '<section class="predictions vehicle-predictions">'
                      + predictions.join("") + '</section>' + text_after;
                that.vehicleMarkers[v]._popup.setContent(text);
            }
        }
        // Remove stale markes from the map
        for (v in that.vehicleMarkers) {
            var min_updated = Date.now() - (that.vehicleMaxAge * 1000)
            if (that.vehicleMarkers[v].bm_updated < min_updated) {
                delete that.vehicleMarkers[v];
            }
        }
        // Call this here to hide/show vehicles markers based on zoom level.
        zoomShowHide();
    }

    /* Refresh (and/or create) UI elements for Stops */
    function updateStopsUI(stops) {
        if (!(that.stopMarkersClusterGroup)) {
            that.stopMarkersClusterGroup = L.markerClusterGroup({
                disableClusteringAtZoom: 14,
                maxClusterRadius: 40,
                showCoverageOnHover: false,
            });
            that.leaflet.addLayer(that.stopMarkersClusterGroup);
        }
        if (!that.stopMarkers) {
            that.stopMarkers = {};
        }
        for (var s in stops) {
            var text = '<header>' + stops[s].title + '</header>';
            var popupOpts = {
                closeButton: false,
                keepInView: true,
                offset: [1,-9],
            };
            if (!(s in that.stopMarkers)) {
                // Stop marker doesn't exist yet - create it now.
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
                that.stopMarkers[s] = L.marker(
                    [stops[s].lat, stops[s].lon],
                    markerOpts).bindPopup(text, popupOpts);
                that.stopMarkersClusterGroup.addLayer(that.stopMarkers[s]);
            }
            // Add predictions to the marker popup, if available
            if (stops[s].predictions) {
                var predictions = [];
                var now = new Date();
                var offset_mins = now.getTimezoneOffset();
                for (r in stops[s].predictions) {
                    if (!(r in that.routes)) {
                        console.log("Unknown route " + r + " for stop " + stops[s].title);
                    }
                    var p_line = "<strong>" + that.routes[r].title + "</strong>: ";
                    var times = [];
                    // Sort by estimated time to arrival
                    psorted = stops[s].predictions[r].sort(function(a,b){
                        return new Date(a.prediction).getTime() - new Date(b.prediction).getTime();
                    });
                    for (p in psorted) {
                        pr = psorted[p];
                        var pdate = new Date(pr.prediction);
                        var diff_sec = (pdate.getTime() - now.getTime()) / 1000;
                        var diff_min = Math.ceil(diff_sec / 60) + offset_mins;
                        // CSS classes for predictions
                        var pclass = "";
                        if (diff_min <= 1) { pclass = "lt1min"; }
                        else if (diff_min <= 2 ) { pclass = "lt2mins"; }
                        else if (diff_min <= 5 ) { pclass = "lt5mins"; }
                        times.push("<span class='prediction " + pclass
                                 + "' title='" + pr.vehicle + "'>"
                                 + diff_min + "</span>");
                    }
                    p_line += times.join(", ");
                    predictions.push("<span class='route'" + p_line + "</span>");
                }
                if (predictions.length == 0) {
                    predictions = ['<span class="none">No arrival predictions.</span>'];
                }
                text += '<section class="predictions stop-predictions">'
                      + predictions.sort().join("<br>") + '</section>';
                that.stopMarkers[s]._popup.setContent(text);
            }
        }
    }

    // Map view persistence functions
    function lastViewRecover() {
        var last = BusMap.getCookie('last_view');
        if (last && last != "") {
            last = last.split(",");
            that.leaflet.setView([last[0], last[1]], last[2]);
            return true;
        } else {
            return false;
        }
    }
    function lastViewStore() {
        var ll = that.leaflet.getCenter();
        view = Math.round(ll.lat * 1000000) / 1000000 + ','
             + Math.round(ll.lng * 1000000) / 1000000 + ','
             + that.leaflet.getZoom();
        BusMap.setCookie('last_view', view);
    }

    // Scaling: update what is displayed based on zoom level
    function zoomShowHide() {
        var zoom = that.leaflet.getZoom();
        if (that.vehicleMarkersGroup) {
            if (zoom >= that.zoomShowVehicles && !(that.leaflet.hasLayer(that.vehicleMarkersGroup))) {
                that.leaflet.addLayer(that.vehicleMarkersGroup);
                $('#msg-zoomForVehicles').hide();
            } else if (zoom < that.zoomShowVehicles && that.leaflet.hasLayer(that.vehicleMarkersGroup)) {
                that.leaflet.removeLayer(that.vehicleMarkersGroup);
                $('#msg-zoomForVehicles').show();
            }
        }
    }

    return that;
};

/* Methods to set and get BusMap-related cookies */
BusMap.getCookies = function() {
    // http://stackoverflow.com/a/4004010
    // String Prototype Methods - these are useful, declare for older browsers.
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
    // Retrieve and return all cookies
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
        c_re = /(?:^|\s+)([!#$%&'*+\-.0-9A-Z^`a-z|~]+)=([!#$%&'*+\-.0-9A-Z^`a-z|~]*|"(?:[\x20-\x7E\x80\xFF]|\\[\x00-\x7F])*")(?=\s*[,;]|$)/g
        c.match(c_re).map(function($0, $1) {
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
    return BusMap.getCookies()[BusMap.cookiePrefix + name];
}
BusMap.setCookie = function(name, value, exp_days) {
    if (exp_days == undefined) {
        exp_days = 365;
    }
    exp_date = new Date();
    exp_date.setDate(exp_date.getDate() + exp_days);
    value = escape(value) + "; expires=" + exp_date.toUTCString();
    document.cookie = BusMap.cookiePrefix + name + "=" + value;
}
