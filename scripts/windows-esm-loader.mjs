import { pathToFileURL } from 'node:url';

export function resolve(specifier, context, nextResolve) {
  const normalized = /^[A-Za-z]:[\\/]/.test(specifier) ? pathToFileURL(specifier).href : specifier;
  return nextResolve(normalized, context);
}
