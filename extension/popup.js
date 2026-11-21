const browserAPI = typeof browser !== "undefined" ? browser : chrome;
const status = document.getElementById("status");

document.getElementById("ping").addEventListener("click", () => {
  status.textContent = "Pinging native host…";
  status.className = "";
  browserAPI.runtime.sendMessage({ type: "ping", id: "popup-ping" }, (response) => {
    const err = browserAPI.runtime.lastError;
    if (err) {
      status.className = "bad";
      status.textContent = "Failed: " + err.message;
      return;
    }
    if (response && response.ok) {
      status.className = "ok";
      status.textContent = "OK\n" + JSON.stringify(response.response, null, 2);
    } else {
      status.className = "bad";
      status.textContent = "Host error\n" + JSON.stringify(response, null, 2);
    }
  });
});
