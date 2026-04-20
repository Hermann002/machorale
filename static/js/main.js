document.addEventListener('DOMContentLoaded', function () {
  // Cache DOM elements
  const sidebar = document.getElementById('admin-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  const openButton = document.getElementById('sidebar-open');
  const closeButton = document.getElementById('sidebar-close');
  const registerForm = document.getElementById('registerForm');
  const submitBtn = document.getElementById('submitBtn');

  // Sidebar functions
  const closeSidebar = () => {
    if (sidebar) {
      sidebar.classList.remove('translate-x-0');
      sidebar.classList.add('-translate-x-full');
    }
    if (backdrop) {
      backdrop.classList.add('hidden');
    }
  };

  const openSidebar = () => {
    if (sidebar) {
      sidebar.classList.remove('-translate-x-full');
      sidebar.classList.add('translate-x-0');
    }
    if (backdrop) {
      backdrop.classList.remove('hidden');
    }
  };

  // Event listeners with null checks
  if (openButton) openButton.addEventListener('click', openSidebar);
  if (closeButton) closeButton.addEventListener('click', closeSidebar);
  if (backdrop) backdrop.addEventListener('click', closeSidebar);

  if (registerForm && submitBtn) {
    registerForm.addEventListener('submit', function (e) {
      if (submitBtn.disabled) {
        e.preventDefault();
        return false;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2" role="status"></span>
        Création en cours...
      `;

      setTimeout(() => {
        if (submitBtn.disabled) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = 'Créer mon compte';
          alert('Le serveur met trop de temps à répondre. Veuillez réessayer.');
        }
      }, 10000);
    });
  }

  const firstError = document.querySelector('.text-red-600, .text-red-400');
  if (firstError) {
    const field = firstError.previousElementSibling?.querySelector?.('input, textarea, select')
      || firstError.parentElement?.querySelector?.('input, textarea, select');

    if (field) {
      field.focus();
    }
  }
});

function togglePasswordVisibility(targetId) {
  const passwordInput = document.getElementById(targetId);
  const toggleIcon = document.getElementById(`toggle-${targetId}`);

  if (!passwordInput || !toggleIcon) return;

  // Animation de l'icône
  toggleIcon.style.transform = 'scale(1.2)';
  setTimeout(() => {
    toggleIcon.style.transform = 'scale(1)';
  }, 150);

  // Toggle du type d'input
  const isPassword = passwordInput.type === 'password';
  passwordInput.type = isPassword ? 'text' : 'password';
  toggleIcon.textContent = isPassword ? 'visibility_off' : 'visibility';
  toggleIcon.classList.toggle('text-slate-400', !isPassword);
  toggleIcon.classList.toggle('text-slate-600', isPassword);
}