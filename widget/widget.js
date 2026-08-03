(function () {
    var API_URL = "/chat";

    var sessionID = sessionStorage.getItem("aby_session_id");
    if (!sessionID) {
        sessionID = crypto.randomUUID();
        sessionStorage.setItem("aby_session_id", sessionID);
    }

    var style = document.createElement("style");
    style.textContent = [
        "#aby-bubble{position:fixed;bottom:24px;right:24px;width:60px;height:60px;",
        "border-radius:50%;background:#2e5d3b;color:#fff;font-size:26px;border:none;",
        "cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.25);z-index:99998;}",
        "#aby-panel{position:fixed;bottom:100px;right:24px;width:360px;max-width:92vw;",
        "height:480px;max-height:70vh;background:#fff;border-radius:12px;",
        "box-shadow:0 8px 30px rgba(0,0,0,.3);display:none;flex-direction:column;",
        "overflow:hidden;z-index:99999;font-family:Arial,sans-serif;}",
        "#aby-header{background:#2e5d3b;color:#fff;padding:14px 16px;font-size:16px;font-weight:bold;}",
        "#aby-header small{display:block;font-weight:normal;font-size:12px;opacity:.85;}",
        "#aby-msgs{flex:1;overflow-y:auto;padding:12px;background:#f6f6f4;}",
        ".aby-msg{max-width:80%;margin:6px 0;padding:9px 12px;border-radius:10px;",
        "font-size:14px;line-height:1.4;white-space:pre-wrap;word-wrap:break-word;}",
        ".aby-user{background:#2e5d3b;color:#fff;margin-left:auto;}",
        ".aby-bot{background:#fff;border:1px solid #ddd;margin-right:auto;}",
        ".aby-typing{opacity:.6;font-style:italic;}",
        "#aby-inputrow{display:flex;border-top:1px solid #ddd;}",
        "#aby-input{flex:1;border:none;padding:12px;font-size:14px;}",
        "#aby-input:focus{outline:2px solid #2e5d3b;outline-offset:-2px;}",
        "#aby-bubble:focus-visible,#aby-send:focus-visible{outline:3px solid #14532d;outline-offset:2px;}",
        "#aby-send{border:none;background:#2e5d3b;color:#fff;padding:0 18px;",
        "cursor:pointer;font-size:14px;}",
        "#aby-send:disabled{opacity:.5;cursor:default;}"
    ].join("");
    document.head.appendChild(style);

    var bubble = document.createElement("button");
    bubble.id = "aby-bubble";
    bubble.textContent = "💬";
    bubble.setAttribute("aria-label", "Chat with us");
    
    var panel = document.createElement("div");
    panel.id = "aby-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Nextdoor Neighbor Chat");

    var header = document.createElement("div");
    header.id = "aby-header";
    header.textContent = "Nextdoor Neighbor";
    
    var sub = document.createElement("small");
    sub.textContent = "American Backyard's Outdoor Living Assistant";
    header.appendChild(sub);

    var msgs = document.createElement("div");
    msgs.id = "aby-msgs";
    msgs.setAttribute("aria-live", "polite");

    var inputRow = document.createElement("div");
    inputRow.id = "aby-inputrow";
    
    var input = document.createElement("input");
    input.id = "aby-input";
    input.placeholder = "Ask about products, delivery, store operations, or more...";
    input.maxLength = 2000;
    input.setAttribute("aria-label", "Type your message here");

    var sendBtn = document.createElement("button");
    sendBtn.id = "aby-send";
    sendBtn.textContent = "Send";

    inputRow.appendChild(input);
    inputRow.appendChild(sendBtn);
    panel.appendChild(header);
    panel.appendChild(msgs);
    panel.appendChild(inputRow);
    document.body.appendChild(bubble);
    document.body.appendChild(panel);

    function addMessage(cls, text) {
        var m = document.createElement("div");
        m.className = "aby-msg " + cls;
        m.textContent = text;
        msgs.appendChild(m);
        msgs.scrollTop = msgs.scrollHeight;
        return m;
    }

    var opened = false;
    bubble.addEventListener("click", function () {
        var showing = panel.style.display === "flex";
        panel.style.display = showing ? "none" : "flex";
        if (!showing && !opened) {
            opened = true;
            addMessage("aby-bot",
                "Hi! I'm the Nextdoor Neighbor, American Backyard's assistant. " +
                "Ask me about products, delivery, store hours, or anything outdoor living.");
        }
        if (!showing) input.focus();
    });

    panel.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            panel.style.display = "none";
            bubble.focus();
        }
    });
    
    var pending = false;

    function send() {
        var text = input.value.trim();
        if (!text || pending) return;
        input.value = "";
        addMessage("aby-user", text);
        var typing = addMessage("aby-bot aby-typing", "Typing...");
        pending = true;
        sendBtn.disabled = true;

        fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({session_id: sessionID, message: text })
        })
        .then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status);
            return r.json(); 
        })
        .then(function (data) {
            typing.textContent = data.reply;
            typing.className = "aby-msg aby-bot";
        })
        .catch(function () {
            typing.textContent = 
            "Sorry - something went wrong on my end. Please call us at " +
            "770-754-5750 and we'll be happy to help.";
            typing.className = "aby-msg aby-bot";
        })
        .then(function () {
            pending = false;
            sendBtn.disabled = false;
            input.focus();
        });
    }

    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") send();
    });

})();