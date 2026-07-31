/* Home-page slider module. Edit only the slides list below. */
(function () {
    var slides = [
        {
            image: "images/暫時的.png",
            link: "https://academic.niu.edu.tw/p/412-1003-5550.php",
            title: "恭喜陳懷恩特聘教授接任國立宜蘭大學研發長",
            description: ""
        },
        {
            image: "images/衛星數位應用評審特別獎.jpg",
            link: "https://moda.gov.tw/ADI/news/latest-news/19484",
            title: "數產署 2026衛星數位應用評審特別獎",
            description: "本實驗室(圖右一)榮獲數位部數產署 衛星數位應用評審特別獎"
        },
        {
            image: "images/智慧創新大賞佳作.jpg",
            link: "https://www.moea.gov.tw/MNS/populace/news/News.aspx?kind=1&menu_id=40&news_id=122509",
            title: "經濟部 2026智慧創新大賞佳作",
            description: "本實驗室學生(由左至右)陳品嶧、余成恩、林士哲、周俊丞、王浩庭榮獲經濟部 智慧創新大賞佳作"
        },
        {
            image: "images/2025智慧創新應用大賽暨5G加速器徵 亞軍.jpg",
            link: "https://www.mirrormedia.mg/story/20251202mkt001",
            title: "2025 中華電信智慧創新應用大賽暨5G加速器徵選 亞軍",
            description: "本實驗室學生(由左至右)陳品嶧、王浩庭、余成恩、周俊丞、陳富翔、李振豐中華電信智慧創新應用大賽暨5G加速器徵選 亞軍"
        }
        /*
        {
            image: "images/%E5%A4%9A%E5%85%83%E7%AB%B6%E8%B3%BD.jpg",
            title: "\u591a\u5143\u7af6\u8cfd\u6210\u679c",
            description: "PlaceHolder"
        }
        */
    ];

    function escapeHtml(value) {
        return String(value || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }

    function addStyles() {
        var style = document.createElement("style");
        style.textContent =
            ".flexslider.home-slider{height:clamp(260px,50vh,560px)!important;margin:0 auto!important;overflow:visible;}" +
            ".flexslider.home-slider .flex-viewport,.flexslider.home-slider .slides,.flexslider.home-slider .slides>li{height:100%!important;}" +
            ".flexslider.home-slider .slides>li,.flexslider.home-slider .slides>li>a{display:flex;align-items:center;justify-content:center;background:#f5f5f5;}" +
            ".flexslider.home-slider .slides>li>a{width:100%;height:100%;}" +
            ".flexslider.home-slider .slides img{width:100%!important;height:100%!important;margin:0!important;object-fit:contain!important;}" +
            ".flexslider.home-slider .flex-direction-nav a{z-index:100!important;width:78px!important;height:100%!important;top:0!important;margin:0!important;display:flex!important;align-items:center;opacity:.78!important;background:rgba(255,255,255,.55);font-size:0!important;}" +
            ".flexslider.home-slider .flex-direction-nav a:before{font-size:40px!important;}" +
            ".flexslider.home-slider .flex-direction-nav .flex-prev{left:0!important;justify-content:flex-start;}.flexslider.home-slider .flex-direction-nav .flex-next{right:0!important;justify-content:flex-end;}" +
            ".flexslider.home-slider .flex-direction-nav a:hover{opacity:1!important;background:rgba(255,255,255,.8);}" +
            ".home-slider-caption{width:80%;margin:20px auto 40px;text-align:center;color:#333;}.home-slider-caption h2{margin:0;font-size:1.35em;}.home-slider-caption p{margin:.4em 0 0;color:#666;}" +
            ".home-slider-caption + .flex-control-nav{width:80%;position:static;margin:-25px auto 40px;text-align:center;}";
        document.head.appendChild(style);
    }

    function renderCaption(caption, index) {
        var slide = slides[index] || {};
        caption.innerHTML = (slide.title ? "<h2>" + escapeHtml(slide.title) + "</h2>" : "") + (slide.description ? "<p>" + escapeHtml(slide.description) + "</p>" : "");
    }

    function renderSlider() {
        var target = document.querySelector(".flexslider");
        if (!target) return;
        target.className += " home-slider";
        target.innerHTML = "<ul class=\"slides\">" + slides.map(function (slide) {
            var image = "<img src=\"" + escapeHtml(slide.image) + "\" alt=\"" + escapeHtml(slide.title) + "\" draggable=\"false\">";
            return "<li>" + (slide.link ? "<a href=\"" + escapeHtml(slide.link) + "\">" + image + "</a>" : image) + "</li>";
        }).join("") + "</ul>";
        var caption = document.createElement("div");
        caption.className = "home-slider-caption";
        target.parentNode.insertBefore(caption, target.nextSibling);
        renderCaption(caption, 0);

        var controlObserver = new MutationObserver(function () {
            var controls = target.querySelector(".flex-control-nav");
            if (controls) {
                caption.parentNode.insertBefore(controls, caption.nextSibling);
                controlObserver.disconnect();
            }
        });
        controlObserver.observe(target, { childList: true });
        new MutationObserver(function () {
            var active = target.querySelector(".slides > li.flex-active-slide");
            if (active) renderCaption(caption, Array.prototype.indexOf.call(active.parentNode.children, active));
        }).observe(target, { attributes: true, subtree: true, attributeFilter: ["class"] });
    }

    addStyles();
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", renderSlider);
    else renderSlider();
}());
