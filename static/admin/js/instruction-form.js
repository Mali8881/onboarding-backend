(() => {
  function rowForField(fieldName) {
    const input = document.querySelector(`[name="${fieldName}"]`);
    if (!input) return null;
    return input.closest('.form-row') || input.closest('[class*="field-"]') || input.parentElement;
  }

  function setVisible(element, visible) {
    if (!element) return;
    element.style.display = visible ? '' : 'none';
  }

  function setRequired(fieldName, required) {
    const input = document.querySelector(`[name="${fieldName}"]`);
    if (!input) return;
    input.required = required;
    if (!required) {
      input.setAttribute('aria-required', 'false');
    }
  }

  function clearField(fieldName) {
    const input = document.querySelector(`[name="${fieldName}"]`);
    if (!input) return;
    if (input.type === 'file') {
      input.value = '';
      return;
    }
    input.value = '';
  }

  function syncInstructionFields() {
    const typeSelect = document.querySelector('[name="type"]');
    if (!typeSelect) return;

    const typeValue = (typeSelect.value || '').toLowerCase();
    const textRow = rowForField('text');
    const linkRow = rowForField('external_url');
    const fileRow = rowForField('file');
    const isText = typeValue === 'text' || !typeValue;
    const isLink = typeValue === 'link';
    const isFile = typeValue === 'file';

    setVisible(textRow, isText);
    setVisible(linkRow, isLink);
    setVisible(fileRow, isFile);

    setRequired('text', isText);
    setRequired('external_url', isLink);
    setRequired('file', isFile);

    if (!isText) clearField('text');
    if (!isLink) clearField('external_url');
    if (!isFile) clearField('file');
  }

  document.addEventListener('DOMContentLoaded', () => {
    const typeSelect = document.querySelector('[name="type"]');
    if (!typeSelect) return;
    syncInstructionFields();
    typeSelect.addEventListener('change', syncInstructionFields);
  });
})();
