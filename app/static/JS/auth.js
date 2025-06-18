document.addEventListener("DOMContentLoaded", function () {
  const signUpButton = document.getElementById("signUp");
  const signInButton = document.getElementById("signIn");
  const container = document.getElementById("container");

  const signupForm = document.getElementById("signupForm");
  const signinForm = document.getElementById("signinForm");

  const signupName = document.getElementById("signupName");
  const signupEmail = document.getElementById("signupEmail");
  const signupPassword = document.getElementById("signupPassword");
  const confirmPassword = document.getElementById("confirmPassword");

  const signinEmail = document.getElementById("signinEmail");
  const signinPassword = document.getElementById("signinPassword");

  // Animation between sign up and sign in
  signUpButton.addEventListener("click", () => {
    container.classList.add("right-panel-active");
  });

  signInButton.addEventListener("click", () => {
    container.classList.remove("right-panel-active");
  });

  // Sign up functionality
  signupForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    // Validation
    if (signupPassword.value !== confirmPassword.value) {
      NotificationSystem.error('Passwords do not match');
      return;
    }

    if (signupPassword.value.length < 6) {
      NotificationSystem.error('Password must be at least 6 characters');
      return;
    }

    // Create new user
    const newUser = {
      name: signupName.value,
      email: signupEmail.value,
      password: signupPassword.value, // In a real app, you would encrypt this
    };

    const response = await fetch("/api/signup", {
      method: "POST",
      headers: {"Content-type": "application/json"},
      body: JSON.stringify(newUser)
    });
    const result = await response.json();

    if (response.ok && result.success) {
      // Show success message
      NotificationSystem.success(result.message, "Success!", 2000);
      
      signupForm.reset(); // Reset form

      // Automatically switch to sign in after 2 seconds
      setTimeout(() => {
        container.classList.remove("right-panel-active");
      }, 2000);
    } else {
      NotificationSystem.error(result.message, "Error!", 2000);
    }
  });

  // Sign in functionality
  signinForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const response = await fetch("/api/login", {
      method: "POST",
      headers: {"Content-type": "application/json"},
      credentials: "include",
      body: JSON.stringify({
        email: signinEmail.value,
        password: signinPassword.value
      })
    });
    const result = await response.json();

    if (response.ok && result.success) {
      // Reset form
      signinForm.reset();

      // Redirect to dashboard (in a real app)
      window.location.href = result.redirect_url;
    } else {
      NotificationSystem.error(result.message, "Error!", 2000);
    }
  });
});
