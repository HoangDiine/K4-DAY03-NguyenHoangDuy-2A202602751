const form = document.querySelector("#chat-form");
const message = document.querySelector("#message");
const submitButton = document.querySelector("#submit-button");
const result = document.querySelector("#result");
const answer = document.querySelector("#answer");
const trace = document.querySelector("#trace");
const error = document.querySelector("#error");
const providerStatus = document.querySelector("#provider-status");

function renderTrace(steps) {
  trace.replaceChildren();
  steps.forEach((step) => {
    const item = document.createElement("li");
    const label = step.action_type === "TOOL_EXECUTION"
      ? "Bước " + step.step + ": gọi " + step.tool_name + " (" + step.status + ")"
      : "Bước " + step.step + ": tạo câu trả lời cuối";
    item.textContent = label;
    trace.append(item);
  });
}

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    providerStatus.textContent = data.provider + " · " + data.model;
  } catch {
    providerStatus.textContent = "Không thể kiểm tra provider";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const requestMessage = message.value.trim();
  if (!requestMessage) return;

  error.hidden = true;
  result.hidden = true;
  submitButton.disabled = true;
  submitButton.textContent = "Agent đang xử lý…";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: requestMessage }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Yêu cầu không thành công.");

    answer.textContent = data.answer;
    renderTrace(data.trace);
    result.hidden = false;
  } catch (requestError) {
    error.textContent = requestError.message;
    error.hidden = false;
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Gửi yêu cầu →";
  }
});

document.querySelectorAll(".sample").forEach((button) => {
  button.addEventListener("click", () => {
    message.value = button.dataset.prompt;
    message.focus();
  });
});

loadHealth();
