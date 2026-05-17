// ============= TRACKED KEYWORDS MANAGER =============
// This file handles the keyword management UI

// Load keywords from backend and display as tags
async function loadKeywords() {
    try {
        const response = await fetch('/api/keywords');
        const keywords = await response.json();
        
        const container = document.getElementById('keywordTags');
        if (!container) return;
        
        if (keywords.length === 0) {
            container.innerHTML = '<p style="color: #999; font-size: 13px;">No keywords yet. Add some above.</p>';
            return;
        }
        
        container.innerHTML = keywords.map(kw => `
            <span class="keyword-tag" data-id="${kw.id}">
                ${kw.keyword}
                <button class="remove-keyword" onclick="deleteKeyword(${kw.id}, '${kw.keyword}')">✕</button>
            </span>
        `).join('');
    } catch (error) {
        console.error('Error loading keywords:', error);
        const container = document.getElementById('keywordTags');
        if (container) {
            container.innerHTML = '<p style="color: #e53e3e; font-size: 13px;">Error loading keywords. Check if server is running.</p>';
        }
    }
}

// Add new keyword
async function addKeyword() {
    const input = document.getElementById('newKeyword');
    const keyword = input.value.trim().toLowerCase();
    
    if (!keyword) {
        alert('Please enter a keyword');
        return;
    }
    
    // Prevent single letters (too broad)
    if (keyword.length < 2) {
        alert('Keyword must be at least 2 characters');
        return;
    }
    
    try {
        const response = await fetch('/api/keywords', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({keyword: keyword})
        });
        
        if (response.ok) {
            input.value = '';
            loadKeywords();
            // Optionally refresh stats to show new keyword counts
            if (typeof loadStats === 'function') {
                loadStats();
            }
        } else {
            const error = await response.json();
            alert(error.error || 'Error adding keyword');
        }
    } catch (error) {
        console.error('Error adding keyword:', error);
        alert('Error adding keyword. Make sure server is running.');
    }
}

// Delete keyword
async function deleteKeyword(id, keyword) {
    if (!confirm(`Remove "${keyword}" from tracked keywords?\n\nPosts already saved will keep their category, but new posts will not use this keyword.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/keywords/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadKeywords();
            if (typeof loadStats === 'function') {
                loadStats();
            }
        } else {
            alert('Error deleting keyword');
        }
    } catch (error) {
        console.error('Error deleting keyword:', error);
        alert('Error deleting keyword');
    }
}

// Initialize keyword manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Add event listeners
    const addBtn = document.getElementById('addKeywordBtn');
    const keywordInput = document.getElementById('newKeyword');
    
    if (addBtn) {
        addBtn.addEventListener('click', addKeyword);
    }
    
    if (keywordInput) {
        keywordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                addKeyword();
            }
        });
    }
    
    // Load keywords
    loadKeywords();
});