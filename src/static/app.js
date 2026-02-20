document.addEventListener("DOMContentLoaded", () => {
  const capabilitiesList = document.getElementById("capabilities-list");
  const capabilitySelect = document.getElementById("capability");
  const registerForm = document.getElementById("register-form");
  const messageDiv = document.getElementById("message");
  const emailInput = document.getElementById("email");

  const authToggleButton = document.getElementById("auth-toggle-btn");
  const authUserBadge = document.getElementById("auth-user");
  const logoutButton = document.getElementById("logout-btn");

  const loginModal = document.getElementById("login-modal");
  const loginCloseButton = document.getElementById("login-close-btn");
  const loginForm = document.getElementById("login-form");
  const loginUsername = document.getElementById("login-username");
  const loginPassword = document.getElementById("login-password");

  let currentUser = null;

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function openLoginModal() {
    loginModal.classList.remove("hidden");
  }

  function closeLoginModal() {
    loginModal.classList.add("hidden");
    loginForm.reset();
  }

  function updateAuthUI() {
    if (currentUser) {
      authToggleButton.textContent = "🔐 Switch User";
      authUserBadge.textContent = `${currentUser.username} (${currentUser.role})`;
      authUserBadge.classList.remove("hidden");
      logoutButton.classList.remove("hidden");
      registerForm.querySelector("button[type='submit']").disabled = false;

      if (currentUser.role === "consultant") {
        emailInput.value = currentUser.email;
        emailInput.readOnly = true;
      } else {
        emailInput.readOnly = false;
      }
    } else {
      authToggleButton.textContent = "🔐 Login";
      authUserBadge.classList.add("hidden");
      logoutButton.classList.add("hidden");
      registerForm.querySelector("button[type='submit']").disabled = true;
      emailInput.readOnly = false;
      emailInput.value = "";
    }
  }

  async function fetchCurrentUser() {
    try {
      const response = await fetch("/auth/me");
      const data = await response.json();
      currentUser = data.user;
      updateAuthUI();
    } catch (error) {
      currentUser = null;
      updateAuthUI();
      console.error("Error fetching auth state:", error);
    }
  }

  // Function to fetch capabilities from API
  async function fetchCapabilities() {
    try {
      const response = await fetch("/capabilities");
      const capabilities = await response.json();

      // Clear loading message
      capabilitiesList.innerHTML = "";
      capabilitySelect.innerHTML = "<option value=''>-- Select a capability --</option>";

      // Populate capabilities list
      Object.entries(capabilities).forEach(([name, details]) => {
        const capabilityCard = document.createElement("div");
        capabilityCard.className = "capability-card";

        const availableCapacity = details.capacity || 0;
        const currentConsultants = details.consultants ? details.consultants.length : 0;

        // Create consultants HTML with delete icons
        const consultantsHTML =
          details.consultants && details.consultants.length > 0
            ? `<div class="consultants-section">
              <h5>Registered Consultants:</h5>
              <ul class="consultants-list">
                ${details.consultants
                  .map(
                    (email) =>
                      `<li>
                        <span class="consultant-email">${email}</span>
                        ${
                          currentUser && currentUser.role === "practice_lead"
                            ? `<button class="delete-btn" data-capability="${name}" data-email="${email}">❌</button>`
                            : ""
                        }
                      </li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No consultants registered yet</em></p>`;

        capabilityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Practice Area:</strong> ${details.practice_area}</p>
          <p><strong>Industry Verticals:</strong> ${details.industry_verticals ? details.industry_verticals.join(', ') : 'Not specified'}</p>
          <p><strong>Capacity:</strong> ${availableCapacity} hours/week available</p>
          <p><strong>Current Team:</strong> ${currentConsultants} consultants</p>
          <div class="consultants-container">
            ${consultantsHTML}
          </div>
        `;

        capabilitiesList.appendChild(capabilityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        capabilitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      capabilitiesList.innerHTML =
        "<p>Failed to load capabilities. Please try again later.</p>";
      console.error("Error fetching capabilities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    if (!currentUser || currentUser.role !== "practice_lead") {
      showMessage("Only practice leads can unregister consultants.", "error");
      return;
    }

    const button = event.target;
    const capability = button.getAttribute("data-capability");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(
          capability
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");

        // Refresh capabilities list to show updated consultants
        fetchCapabilities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!currentUser) {
      showMessage("Please log in before registering expertise.", "error");
      return;
    }

    const email = emailInput.value;
    const capability = capabilitySelect.value;

    try {
      const response = await fetch(
        `/capabilities/${encodeURIComponent(
          capability
        )}/register?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        registerForm.reset();

        if (currentUser && currentUser.role === "consultant") {
          emailInput.value = currentUser.email;
        }

        // Refresh capabilities list to show updated consultants
        fetchCapabilities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to register. Please try again.", "error");
      console.error("Error registering:", error);
    }
  });

  authToggleButton.addEventListener("click", () => {
    openLoginModal();
  });

  loginCloseButton.addEventListener("click", () => {
    closeLoginModal();
  });

  loginModal.addEventListener("click", (event) => {
    if (event.target === loginModal) {
      closeLoginModal();
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: loginUsername.value,
          password: loginPassword.value,
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        showMessage(result.detail || "Login failed", "error");
        return;
      }

      currentUser = result.user;
      updateAuthUI();
      closeLoginModal();
      showMessage(`Welcome, ${currentUser.username}!`, "success");
      fetchCapabilities();
    } catch (error) {
      showMessage("Failed to log in. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
      currentUser = null;
      updateAuthUI();
      showMessage("Logged out successfully.", "info");
      fetchCapabilities();
    } catch (error) {
      showMessage("Failed to log out.", "error");
      console.error("Error logging out:", error);
    }
  });

  // Initialize app
  fetchCurrentUser().then(fetchCapabilities);
});
