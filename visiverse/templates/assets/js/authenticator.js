(() => {

    const loginForm = document.getElementById("loginForm");

    async function submitLoginForm() {
        // Get credentials from login form
        let loginData = new FormData(loginForm);
        let username = loginData.get("username");
        let password = loginData.get("password");
        // Check for blank credentials
        if (username === "" || password === "") {
            window.alert("A username and password are required.");
            return;
        }
        // Send login request
        await doLogin(username, password);
    }

    loginForm.addEventListener("submit", e => {
        e.preventDefault();
        submitLoginForm();
    });

    let doingLogin = false;

    async function doLogin(username, password) {
        // Prevent spam-clicking
        doingLogin = true;
        // The server does not need to know the real password!
        passwordHash = await sha256(password);
        // Response is scoped for access inside the catch block
        let response;
        try {
            // POST to login route
            response = await fetch("{{ url_for('auth_login') }}", {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    "username": username,
                    "password": passwordHash,
                })
            });
            const responseJson = await response.json();
            // Login request finished
            doingLogin = false;
            if (response.ok) {
                // submission successful
                window.location.href = "{{ url_for('page_home') }}";
            } else {
                // throw error with server message
                throw new Error(responseJson.message);
            }
        } catch (error) {
            if (error instanceof SyntaxError) {
                // syntax error from parsing non-JSON server error response
                window.alert(`Error during login: ${response.status} - ${response.statusText}`);
            } else {
                // generic error
                window.alert(`Error during login: ${error.message}`);
            }
        }
    }

    async function doLogout(username) {
        // TODO implement logout
    }

    // Modified from: https://stackoverflow.com/a/74243445
    async function sha256(str) {
        const encodedStr = new TextEncoder("utf-8").encode(str);
        const hashBuffer = await window.crypto.subtle.digest("SHA-256", encodedStr);
        const hashArray = Array.from(new Uint8Array(hashBuffer))
        const digest = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
        return digest;
    }

})();
