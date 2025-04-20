document.addEventListener('DOMContentLoaded', function() {
    const form               = document.querySelector('.login-form');
    const loginContainer     = document.getElementById('loginContainer');
    const dashboardContainer = document.getElementById('dashboardContainer');
  
    form?.addEventListener('submit', function(e) {
      // 1) Prevent the immediate submission…
      e.preventDefault();
  
      // 2) Play your slide‑up animation
      loginContainer.classList.add('slide-up');
      dashboardContainer.classList.add('slide-up');
  
      // 3) After the animation (500ms), submit the form for real
      setTimeout(() => {
        form.submit();
      }, 500);
    });
  });
  