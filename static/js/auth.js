// static/js/auth.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { 
    getAuth, 
    signInWithPopup, 
    GoogleAuthProvider, 
    signOut, 
    onAuthStateChanged 
} from "https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js";
import { firebaseConfig } from './firebase-config.js';

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// DOM Elements
const authToggleBtn = document.getElementById('authToggleBtn');
const userDisplay = document.getElementById('userDisplay');

// ============================================================
// UPDATE UI BASED ON AUTH STATE
// ============================================================
function updateUI(user) {
    if (user) {
        // User is logged in - display their info
        console.log("✅ User logged in:", user.displayName, user.email);
        
        // Get user details
        const userName = user.displayName || user.email.split('@')[0];
        const userEmail = user.email;
        const userPhoto = user.photoURL;
        
        // Update button to show user info
        if (authToggleBtn) {
            authToggleBtn.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px;">
                    ${userPhoto ? `<img src="${userPhoto}" style="width: 28px; height: 28px; border-radius: 50%;">` : '👤'}
                    <span>${userName}</span>
                    <span style="font-size: 12px;">▼</span>
                </div>
            `;
            authToggleBtn.style.background = '#f0f0f0';
            authToggleBtn.style.color = '#333';
            authToggleBtn.title = "Click to sign out";
        }
        
        // Create user display panel (optional)
        if (userDisplay) {
            userDisplay.innerHTML = `
                <div class="user-info">
                    <span class="user-email">${userEmail}</span>
                </div>
            `;
        }
        
        // Store user info globally for other scripts
        window.currentUser = {
            uid: user.uid,
            name: userName,
            email: userEmail,
            photo: userPhoto
        };
        
        // Dispatch a custom event so other scripts know user logged in
        window.dispatchEvent(new CustomEvent('userLoggedIn', { detail: window.currentUser }));
        
    } else {
        // User is logged out
        console.log("❌ User logged out");
        
        // Reset button to login state
        if (authToggleBtn) {
            authToggleBtn.innerHTML = '🔐 Login with Google';
            authToggleBtn.style.background = '#c41e3a';
            authToggleBtn.style.color = 'white';
            authToggleBtn.title = "Click to sign in";
        }
        
        // Clear user display
        if (userDisplay) {
            userDisplay.innerHTML = '';
        }
        
        // Clear global user
        window.currentUser = null;
        
        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('userLoggedOut'));
    }
}

// ============================================================
// SHOW TOAST MESSAGE
// ============================================================
function showToast(message, isError = false) {
    const toast = document.getElementById('toastMsg');
    if (toast) {
        toast.textContent = message;
        toast.style.backgroundColor = isError ? '#dc3545' : '#28a745';
        toast.style.opacity = '1';
        setTimeout(() => {
            toast.style.opacity = '0';
        }, 4000);
    }
    console.log(isError ? "❌" : "✅", message);
}

// ============================================================
// GOOGLE SIGN IN
// ============================================================
async function signInWithGoogle() {
    try {
        console.log("🔐 Attempting Google sign in...");
        const result = await signInWithPopup(auth, provider);
        const user = result.user;
        
        showToast(`✅ Welcome ${user.displayName || user.email}!`);
        
        // Return user info
        return { success: true, user };
        
    } catch (error) {
        console.error("❌ Sign in error:", error);
        
        let errorMessage = "Sign in failed. Please try again.";
        if (error.code === 'auth/popup-blocked') {
            errorMessage = "Popup was blocked. Please allow popups for this site.";
        } else if (error.code === 'auth/network-request-failed') {
            errorMessage = "Network error. Please check your connection.";
        }
        
        showToast(errorMessage, true);
        return { success: false, error: error.message };
    }
}

// ============================================================
// SIGN OUT
// ============================================================
async function signOutUser() {
    try {
        await signOut(auth);
        showToast("👋 You have been signed out.");
        return { success: true };
    } catch (error) {
        console.error("❌ Sign out error:", error);
        showToast("Sign out failed. Please try again.", true);
        return { success: false, error: error.message };
    }
}

// ============================================================
// TOGGLE AUTH (Sign in / Sign out)
// ============================================================
async function toggleAuth() {
    if (auth.currentUser) {
        // User is logged in - sign out
        await signOutUser();
    } else {
        // User is logged out - sign in
        await signInWithGoogle();
    }
}

// ============================================================
// GET CURRENT USER (for other scripts)
// ============================================================
function getCurrentUser() {
    return auth.currentUser;
}

// ============================================================
// CHECK IF USER IS LOGGED IN (async)
// ============================================================
async function isUserLoggedIn() {
    return new Promise((resolve) => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            unsubscribe();
            resolve(!!user);
        });
    });
}

// ============================================================
// INITIALIZE AUTH LISTENERS
// ============================================================
function initAuth() {
    // Listen for auth state changes
    onAuthStateChanged(auth, (user) => {
        updateUI(user);
    });
    
    // Set up toggle button click handler
    if (authToggleBtn) {
        authToggleBtn.addEventListener('click', toggleAuth);
        console.log("✅ Auth button listener attached");
    } else {
        console.warn("⚠️ authToggleBtn not found in DOM");
    }
}

// ============================================================
// EXPORTS (for use in other modules)
// ============================================================
export { 
    auth, 
    signInWithGoogle, 
    signOutUser, 
    toggleAuth, 
    getCurrentUser, 
    isUserLoggedIn,
    initAuth
};

// Auto-initialize when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    initAuth();
});