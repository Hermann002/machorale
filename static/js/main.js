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
