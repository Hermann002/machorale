const inputs = document.querySelectorAll('.single-digit-input');
const hiddenInput = document.getElementById('otp-hidden');

inputs.forEach((input, index) => {
    input.addEventListener('input', () => {
        // Ne garde que les chiffres
        input.value = input.value.replace(/\D/g, '');

        // Passe au champ suivant
        if (input.value && index < inputs.length - 1) {
        inputs[index + 1].focus();
        }

        // Met à jour le champ caché
        const fullCode = Array.from(inputs).map(i => i.value).join('');
        hiddenInput.value = fullCode;
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && !input.value && index > 0) {
        inputs[index - 1].focus();
        }
    });
    console.log(input);
});