// Small UI helpers only. Does not touch the signing engine or the 3D scene.
const words = document.getElementById('words');
const compile = document.getElementById('compile');

document.querySelectorAll('[data-phrase]').forEach((btn) => {
  btn.addEventListener('click', () => {
    if (!words || !compile) return;
    words.value = btn.dataset.phrase;
    compile.click();
  });
});

if (words && compile) {
  words.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      compile.click();
    }
  });
}