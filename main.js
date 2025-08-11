// This function runs once the entire HTML document has been loaded and parsed.
document.addEventListener('DOMContentLoaded', function () {

    // --- Toast Notification Auto-hide ---
    const toastElements = document.querySelectorAll('.toast-card');
    toastElements.forEach(toast => {
        setTimeout(() => {
            toast.style.transition = 'opacity 0.5s ease';
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 500); // Remove from DOM after fade out
        }, 5000); // 5 seconds
    });


    // --- Asynchronous Like Button Functionality ---
    document.querySelectorAll('.like-button').forEach(button => {
        button.addEventListener('click', function (event) {
            const postId = this.dataset.postId;
            const likeCountElement = document.getElementById(`like-count-${postId}`);
            const likeIcon = this.querySelector('svg');

            fetch(`/like_post/${postId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                likeCountElement.textContent = data.likes_count;
                if (data.status === 'liked') {
                    likeIcon.classList.add('text-red-500');
                    likeIcon.setAttribute('fill', 'currentColor');
                } else {
                    likeIcon.classList.remove('text-red-500');
                    likeIcon.setAttribute('fill', 'none');
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });


    // --- ADVANCED STORY VIEWER MODAL ---
    const storyModal = document.getElementById('story-modal');
    if (storyModal) {
        const storyMediaContainer = document.getElementById('story-media-container');
        const storyAuthorPic = document.getElementById('story-author-pic');
        const storyAuthorName = document.getElementById('story-author-name');
        const closeButton = document.getElementById('story-close-button');
        const deleteStoryContainer = document.getElementById('story-delete-container');
        const deleteStoryForm = document.getElementById('delete-story-form');
        
        let allUserStories = [];
        let currentStoryIndex = 0;
        let storyTimeout;

        const showStory = (index) => {
            clearTimeout(storyTimeout);
            storyMediaContainer.innerHTML = ''; // Clear previous content

            const story = allUserStories[index];
            const storyUrl = `/static/story_pics/${story.filename}`;
            
            // Update progress bars
            const progressBarsContainer = document.createElement('div');
            progressBarsContainer.className = 'absolute top-2 left-0 right-0 flex items-center gap-1 px-2 z-30';
            allUserStories.forEach((s, i) => {
                const bar = document.createElement('div');
                bar.className = 'h-1 flex-1 bg-white/30 rounded-full';
                const innerBar = document.createElement('div');
                innerBar.className = 'h-full bg-white rounded-full';
                if (i < index) {
                    innerBar.style.width = '100%';
                } else if (i === index) {
                    // Trigger reflow to restart animation
                    innerBar.style.animation = 'none';
                    void innerBar.offsetWidth; // Reflow trick
                    innerBar.style.animation = `fill-progress 7s linear forwards`;
                } else {
                    innerBar.style.width = '0%';
                }
                bar.appendChild(innerBar);
                progressBarsContainer.appendChild(bar);
            });
            storyMediaContainer.appendChild(progressBarsContainer);

            const fileExtension = story.filename.split('.').pop().toLowerCase();
            if (['mp4', 'mov', 'avi'].includes(fileExtension)) {
                const video = document.createElement('video');
                video.src = storyUrl;
                video.className = 'w-full h-full object-contain';
                video.autoplay = true;
                video.muted = true;
                video.playsInline = true;
                video.onended = () => showNextStory();
                storyMediaContainer.appendChild(video);
            } else {
                const img = document.createElement('img');
                img.src = storyUrl;
                img.className = 'w-full h-full object-contain';
                storyMediaContainer.appendChild(img);
                storyTimeout = setTimeout(showNextStory, 7000); // 7 seconds for images
            }

            // Add navigation controls
            const prevButton = document.createElement('div');
            prevButton.className = 'absolute left-0 top-0 h-full w-1/2 cursor-pointer z-20';
            prevButton.onclick = () => showPrevStory();
            const nextButton = document.createElement('div');
            nextButton.className = 'absolute right-0 top-0 h-full w-1/2 cursor-pointer z-20';
            nextButton.onclick = () => showNextStory();
            storyMediaContainer.appendChild(prevButton);
            storyMediaContainer.appendChild(nextButton);

            // Update delete button if owner
            if (deleteStoryForm.dataset.isOwner === 'true') {
                deleteStoryForm.action = `/delete_story/${story.id}`;
            }
        };

        const showNextStory = () => {
            if (currentStoryIndex < allUserStories.length - 1) {
                currentStoryIndex++;
                showStory(currentStoryIndex);
            } else {
                closeModal();
            }
        };

        const showPrevStory = () => {
            if (currentStoryIndex > 0) {
                currentStoryIndex--;
                showStory(currentStoryIndex);
            }
        };

        const closeModal = () => {
            clearTimeout(storyTimeout);
            storyModal.classList.add('hidden');
            const video = storyMediaContainer.querySelector('video');
            if (video) video.pause();
        };

        document.querySelectorAll('.story-item').forEach(item => {
            item.addEventListener('click', function (e) {
                e.preventDefault();
                allUserStories = JSON.parse(this.dataset.stories);
                const authorName = this.dataset.storyAuthor;
                const authorPic = this.dataset.storyAuthorPic;
                const isOwner = this.dataset.isOwner === 'true';

                storyAuthorPic.src = authorPic;
                storyAuthorName.textContent = authorName;
                
                deleteStoryForm.dataset.isOwner = isOwner; // Store ownership status
                if (isOwner) {
                    deleteStoryContainer.classList.remove('hidden');
                } else {
                    deleteStoryContainer.classList.add('hidden');
                }

                currentStoryIndex = 0;
                showStory(currentStoryIndex);
                storyModal.classList.remove('hidden');
            });
        });

        closeButton.addEventListener('click', closeModal);
    }


    // --- Video Play/Pause on Click ---
    document.querySelectorAll('.video-overlay').forEach(overlay => {
        const video = overlay.previousElementSibling;
        overlay.addEventListener('click', () => {
            if (video.paused) video.play();
            else video.pause();
        });
        video.addEventListener('play', () => overlay.style.opacity = '0');
        video.addEventListener('pause', () => overlay.style.opacity = '1');
    });

    
    // --- Post Options Menu (for delete button) ---
    document.querySelectorAll('.post-options-menu > button').forEach(button => {
        button.addEventListener('click', function(event) {
            event.stopPropagation();
            const dropdown = this.nextElementSibling;
            document.querySelectorAll('.post-options-menu .absolute').forEach(menu => {
                if (menu !== dropdown) menu.classList.add('hidden');
            });
            dropdown.classList.toggle('hidden');
        });
    });

    // Close dropdowns if clicking outside
    window.addEventListener('click', function(event) {
        document.querySelectorAll('.post-options-menu .absolute').forEach(menu => {
            if (!menu.parentElement.contains(event.target)) {
                menu.classList.add('hidden');
            }
        });
    });

});
