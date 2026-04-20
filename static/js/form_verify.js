const inputs = document.querySelectorAll('.single-digit-input');
const hiddenInput = document.getElementById('otp-hidden');

inputs.forEach((input, index) => {
  input.addEventListener('input', () => {
    // Keep only digits
    input.value = input.value.replace(/\D/g, '');

    // Move to next field
    if (input.value && index < inputs.length - 1) {
      inputs[index + 1].focus();
    }

    // Update hidden input
    if (hiddenInput) {
      hiddenInput.value = Array.from(inputs).map(i => i.value).join('');
    }
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' && !input.value && index > 0) {
      inputs[index - 1].focus();
    }
  });
});