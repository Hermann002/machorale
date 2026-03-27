document.addEventListener('DOMContentLoaded', function() {
        const addCustomBtn = document.getElementById('addCustomCommissionBtn');
        const modal = document.getElementById('customCommissionModal');
        const closeModalBtn = document.getElementById('closeModalBtn');
        const cancelCustomBtn = document.getElementById('cancelCustomBtn');
        const customForm = document.getElementById('customCommissionForm');
        const customContainer = document.getElementById('custom-commissions-container');

        // Ouvrir le modal
        if (addCustomBtn) {
            addCustomBtn.addEventListener('click', function() {
                modal.classList.remove('hidden');
            });
        }

        // Fermer le modal
        function closeModal() {
            modal.classList.add('hidden');
            customForm.reset();
        }

        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', closeModal);
        }
        if (cancelCustomBtn) {
            cancelCustomBtn.addEventListener('click', closeModal);
        }

        // Fermer en cliquant en dehors
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal) {
                    closeModal();
                }
            });
        }

        // Soumettre le formulaire personnalisé
        if (customForm) {
            customForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const name = document.getElementById('commissionName').value.trim();
                const description = document.getElementById('commissionDescription').value.trim();
                // const icon = document.getElementById('commissionIcon').value;
                const id = 'custom_' + encodeURIComponent(name);
                
                // Créer l'élément de commission
                const commissionHTML = `
                    <label class="flex items-center gap-4 p-5 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors bg-slate-50 dark:bg-slate-800/50">
                        <div class="size-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                            <span class="material-symbols-outlined">group</span>
                        </div>
                        <div class="flex-1">
                            <p class="text-slate-900 dark:text-white text-base font-bold">${escapeHtml(name)}</p>
                            <p class="text-slate-500 dark:text-slate-400 text-sm">${escapeHtml(description || 'No description')}</p>
                        </div>
                        <div class="flex items-center gap-2">
                            <input 
                                type="checkbox" 
                                name="commissions" 
                                value="${id}" 
                                class="h-6 w-6 rounded border-slate-300 dark:border-slate-700 text-primary focus:ring-primary focus:ring-offset-0 bg-transparent transition-all" 
                                checked
                            />
                            <button 
                                type="button" 
                                onclick="removeCustomCommission(this)" 
                                class="material-symbols-outlined text-sm text-slate-400 hover:text-red-500 transition-colors"
                            >
                                delete
                            </button>
                        </div>
                    </label>
                `;
                
                if (customContainer) {
                    customContainer.insertAdjacentHTML('beforeend', commissionHTML);
                }
                closeModal();
            });
        }
    });

    // Supprimer une commission personnalisée
    function removeCustomCommission(button) {
        const commissionElement = button.closest('label');
        if (commissionElement) {
            commissionElement.remove();
        }
    }

    // Échapper le HTML pour éviter les injections XSS
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }