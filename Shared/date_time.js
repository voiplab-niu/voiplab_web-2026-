/* Shared date and time display for VoIP Lab pages. */
(function () {
    var weekdays = [
        "週日", "週一", "週二", "週三", "週四", "週五", "週六"
    ];

    function pad(value) {
        return value < 10 ? "0" + value : String(value);
    }

    function updateDateTime() {
        var now = new Date();
        var dateTarget = document.getElementById("whatday");
        var timeTarget = document.getElementById("thetime");

        if (dateTarget) {
            dateTarget.textContent = now.getFullYear() + "." + (now.getMonth() + 1) + "." + now.getDate() + " " + weekdays[now.getDay()];
        }
        if (timeTarget) {
            timeTarget.textContent = pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
        }
    }

    function start() {
        updateDateTime();
        window.setInterval(updateDateTime, 1000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
}());
