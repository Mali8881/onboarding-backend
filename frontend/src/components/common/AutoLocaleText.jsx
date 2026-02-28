import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useLocale } from '../../context/LocaleContext';

const TEXT_SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA']);

export default function AutoLocaleText() {
  const { locale, tr } = useLocale();
  const location = useLocation();
  const nodeTextMap = useRef(new WeakMap());
  const attrMap = useRef(new WeakMap());

  useEffect(() => {
    const root = document.body;
    if (!root) return;

    const walkText = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walkText.nextNode()) {
      const node = walkText.currentNode;
      const parentTag = node.parentElement?.tagName;
      if (!node.nodeValue || !node.nodeValue.trim()) continue;
      if (parentTag && TEXT_SKIP_TAGS.has(parentTag)) continue;

      if (!nodeTextMap.current.has(node)) {
        nodeTextMap.current.set(node, node.nodeValue);
      }
      const base = nodeTextMap.current.get(node);
      node.nodeValue = locale === 'ru' ? base : tr(base.trim()) || base;
      if (locale !== 'ru' && node.nodeValue === base) {
        node.nodeValue = base;
      } else if (locale !== 'ru' && base !== base.trim()) {
        const lead = base.match(/^\s*/)?.[0] || '';
        const tail = base.match(/\s*$/)?.[0] || '';
        const translated = tr(base.trim());
        node.nodeValue = translated === base.trim() ? base : `${lead}${translated}${tail}`;
      }
    }

    const elements = root.querySelectorAll('[placeholder], [title], [aria-label]');
    elements.forEach((el) => {
      if (!attrMap.current.has(el)) {
        attrMap.current.set(el, {
          placeholder: el.getAttribute('placeholder'),
          title: el.getAttribute('title'),
          ariaLabel: el.getAttribute('aria-label'),
        });
      }
      const src = attrMap.current.get(el);
      const patch = (attr, val) => {
        if (!val) return;
        if (locale === 'ru') {
          el.setAttribute(attr, val);
          return;
        }
        const translated = tr(val);
        el.setAttribute(attr, translated || val);
      };
      patch('placeholder', src.placeholder);
      patch('title', src.title);
      patch('aria-label', src.ariaLabel);
    });
  }, [locale, location.pathname, tr]);

  return null;
}

