let html5QrCode;
// 開始 QR 碼掃描器
function startQRScanner() {
    const userConsent = confirm("是否允許開啟鏡頭進行 QR Code 掃描？");
    if (!userConsent) {
        return; // 如果用戶拒絕，則返回
    }
    // 初始化 QR 碼掃描器
    if (!html5QrCode) {
        html5QrCode = new Html5Qrcode("qr-reader"); // 將掃描結果顯示在指定元素中
    }
    // 當成功掃描到 QR 碼後的回調函數
    const qrCodeSuccessCallback = (decodedText, decodedResult) => {
        if (confirm(`現在要前往 ${decodedText} 嗎？`)) {
            window.location.href = decodedText; // 轉跳到掃描到的網址
        }
        stopQRScanner(); // 停止掃描
    };

    const config = { fps: 10, qrbox: 250 }; // 設定 FPS 和掃描框的大小
    html5QrCode.start({ facingMode: "environment" }, config, qrCodeSuccessCallback)
        .catch(err => {
            console.error(`啟動失敗: ${err}`); // 捕獲錯誤
        });
}
// 停止 QR 碼掃描器
function stopQRScanner() {
    if (html5QrCode) {
        html5QrCode.stop().then(ignore => {
            console.log("QR code scanner stopped."); // 停止成功的提示
        }).catch(err => {
            console.error(`停止掃描失敗: ${err}`); // 捕獲停止錯誤
        });
    } else {
        console.log("QR code scanner is not initialized."); // 提示掃描器尚未初始化
    }
}
// 從上傳的文件中掃描 QR 碼
function scanQRCodeFromFile(event) {
    const file = event.target.files[0]; // 獲取上傳的文件
    if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
            const image = event.target.result; // 獲取文件的數據 URL
            const img = new Image();
            img.src = image;
            img.onload = function() {
                const canvas = document.createElement("canvas");
                canvas.width = img.width; // 設定畫布的寬度
                canvas.height = img.height; // 設定畫布的高度
                const ctx = canvas.getContext("2d");
                ctx.drawImage(img, 0, 0); // 在畫布上繪製圖片
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height); // 獲取圖片的數據
                
                // 使用 jsQR 庫進行 QR Code 解碼
                const decoded = jsQR(imageData.data, canvas.width, canvas.height, {
                    inversionAttempts: "dontInvert",
                });
                if (decoded && decoded.data) {
                    console.log(`QR code scanned text: ${decoded.data}`);
                    if (confirm(`現在要前往 ${decoded.data} 嗎？`)) {
                        window.location.href = decoded.data; // 轉跳到掃描到的網址
                    }
                } else {
                    console.log("沒有找到 QR Code。"); // 如果未找到 QR 碼
                }
            };
        };
        reader.readAsDataURL(file); // 讀取文件為數據 URL
    }
}
// 切換側邊菜單的顯示與隱藏
function toggleMenu() {
    const sideMenu = document.getElementById('sideMenu');
    // 判斷側邊菜單當前的顯示狀態，進行切換
    if (sideMenu.style.left === '0px') {
        sideMenu.style.left = '-250px'; // 隱藏菜單
    } else {
        sideMenu.style.left = '0px'; // 顯示菜單
    }
}
// LINE Notify 的 Token
const LINE_NOTIFY_TOKEN = "8LCibtpxccr13fPPya0bCMO7wXd57hakBqqIgMh6avE"; 




