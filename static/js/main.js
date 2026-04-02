document.addEventListener('DOMContentLoaded', function () {
  const sidebar = document.getElementById('admin-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  const openButton = document.getElementById('sidebar-open');
  const closeButton = document.getElementById('sidebar-close');

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

  if (openButton) {
    openButton.addEventListener('click', openSidebar);
  }

  if (closeButton) {
    closeButton.addEventListener('click', closeSidebar);
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeSidebar);
  }
});

document.getElementById('registerForm').addEventListener('submit', function(e) {
  const btn = document.getElementById('submitBtn');
  // Empêche les soumissions multiples
  if (btn.disabled) {
            e.preventDefault();
            return false;
        }
        // Désactive le bouton + état de chargement
        btn.disabled = true;
        btn.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            Création en cours...
        `;
        
        // Optionnel : timeout de sécurité (10s max)
        setTimeout(() => {
            if (btn.disabled) {
            btn.disabled = false;
            btn.innerHTML = 'Créer mon compte';
            alert('Le serveur met trop de temps à répondre. Veuillez réessayer.');
            }
        }, 10000);
        });


document.addEventListener('DOMContentLoaded', () => {
  const firstError = document.querySelector('.text-red-600, .text-red-400');
  if (firstError) {
      // Trouve le champ associé : généralement le <input> juste avant l'erreur
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
    
    // Animation de l'icône
    toggleIcon.style.transform = 'scale(1.2)';
    setTimeout(() => {
        toggleIcon.style.transform = 'scale(1)';
    }, 150);
    
    // Toggle du type d'input
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.textContent = 'visibility_off';
        toggleIcon.classList.replace('text-slate-400', 'text-slate-600');
    } else {
        passwordInput.type = 'password';
        toggleIcon.textContent = 'visibility';
        toggleIcon.classList.replace('text-slate-600', 'text-slate-400');
    }
}