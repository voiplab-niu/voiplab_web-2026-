const chatFloat = document.getElementById("chatFloat");
const chatModal = document.getElementById("chatModal");
const closeChat = document.getElementById("closeChat");
const sendBtn = document.getElementById("sendBtn");
const userInput = document.getElementById("userInput");
const chatBox = document.getElementById("chatBox");
let userMessage ="";

// 點擊懸浮小球顯示模態框
chatFloat.addEventListener("click", () => {
    const ballRect = chatFloat.getBoundingClientRect();
    chatModal.style.display = "flex";
    chatModal.style.right = `${window.innerWidth - ballRect.right}px`;
    chatModal.style.bottom = `${window.innerHeight - ballRect.top + 10}px`;
});

// 點擊關閉按鈕隱藏模態框
closeChat.addEventListener("click", () => {
     chatModal.style.display = "none";
});

// 點擊送出按鈕發送訊息
sendBtn.addEventListener("click", () => {
    const userMessage = userInput.value.trim(); // 取得用戶輸入訊息
    if (userMessage) {
        addMessage(userMessage, "user"); // 將用戶訊息添加到聊天室
        userInput.value = ""; // 清空輸入框
        // 呼叫 AI 回應
        daiSDK.push("message-I", userMessage);
        console.log(userMessage)
    }
});
document.getElementById("clearChat").addEventListener("click", () => {
    const chatBox = document.getElementById("chatBox");
    chatBox.innerHTML = ""; // 清空聊天室內容
});
        // 添加訊息到對話框
function addMessage(message, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");
    messageDiv.innerHTML = `<p>${message}</p>`;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}
