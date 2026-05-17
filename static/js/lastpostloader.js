// lastpostloader.js - Shows the last saved post date

async function loadLastPostDate() {
    try {
        const response = await fetch('/get_posts');
        const posts = await response.json();
        
        const container = document.getElementById('lastPostInfo');
        
        if (!container) {
            console.error('Element with id "lastPostInfo" not found');
            return;
        }
        
        if (posts.length === 0) {
            container.innerHTML = '📅 No posts saved yet. Paste your first post above.';
            return;
        }
        
        // Get the most recent post (last one in the array)
        const lastPost = posts[posts.length - 1];
        
        // Get the date - prefer post_date, fallback to saved_at
        const displayDate = lastPost.post_date || lastPost.saved_at;
        
        // Get just the date part for easy reading
        const dateOnly = displayDate.split(' ')[0];
        const timeOnly = displayDate.split(' ')[1] || '';
        
        container.innerHTML = `
            <div style="background: #e8f4fd; border-left: 4px solid #1877f2; padding: 12px 15px; border-radius: 8px;">
                <strong>📅 Last saved post date:</strong><br>
                <span style="font-size: 18px; font-weight: bold;">${dateOnly}</span>
                <span style="font-size: 14px; color: #555;"> ${timeOnly}</span><br>
                <small style="color: #666;">📍 ${lastPost.location || 'No location'} | 👤 ${lastPost.source || 'unknown'}</small>
            </div>
        `;
    } catch (error) {
        console.error('Error loading last post:', error);
        const container = document.getElementById('lastPostInfo');
        if (container) {
            container.innerHTML = '📅 Error loading last post date. Make sure the server is running.';
        }
    }
}

// Load when page is ready
document.addEventListener('DOMContentLoaded', function() {
    loadLastPostDate();
});